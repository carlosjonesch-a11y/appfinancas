"""Página de Investimentos: saldo lançado e atualizado mensalmente."""

from __future__ import annotations

from datetime import date
from calendar import monthrange

import streamlit as st

from services.database import db
from services.selic import obter_selic_meta_aa, calcular_rendimento_percentual_selic


@st.cache_data(ttl=60 * 60)
def _get_selic_cache():
    return obter_selic_meta_aa(timeout=10)


def _format_brl(value: float) -> str:
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def _month_ref(d: date) -> date:
    return date(d.year, d.month, 1)


def _month_end(d: date) -> date:
    ultimo = monthrange(d.year, d.month)[1]
    return date(d.year, d.month, ultimo)


def get_user_id() -> str:
    return st.session_state.get("user_id", "")


def render_investimentos_page():
    st.header("📈 Investimentos")

    user_id = get_user_id()
    if not user_id:
        st.warning("Usuário não identificado")
        return

    st.subheader("Saldo (atualização mensal)")
    st.caption(
        "Modelo simples: você lança o saldo atual e, quando virar o mês, atualiza o saldo-base. "
        "O Dashboard usa sempre o último saldo conhecido de cada investimento."
    )

    investimentos = db.listar_investimentos(user_id, incluir_inativos=False)
    hoje = date.today()

    total_hoje = db.total_investimentos_projetado_em(user_id, hoje)
    st.metric("Total em investimentos (hoje)", _format_brl(total_hoje))

    if not investimentos:
        st.info("Você ainda não cadastrou investimentos. Use o formulário abaixo para criar o primeiro.")
    else:
        # Montar tabela com último saldo vigente
        rows = []
        for inv in investimentos:
            saldo_vigente = db.obter_saldo_investimento_em(user_id, inv.get("id"), hoje)

            # Melhor esforço para descobrir o mês do último saldo (pega o maior <= hoje)
            ultimo_mes = None
            try:
                saldos = db.listar_saldos_investimentos(user_id, inv.get("id"))
                alvo = _month_ref(hoje)
                datas = []
                for s in saldos:
                    dr = s.get("data_referencia")
                    if isinstance(dr, str):
                        try:
                            dref = date.fromisoformat(dr)
                            dref = _month_ref(dref)
                            if dref <= alvo:
                                datas.append(dref)
                        except Exception:
                            pass
                if datas:
                    ultimo_mes = max(datas)
            except Exception:
                pass

            rows.append(
                {
                    "Investimento": inv.get("nome"),
                    "Saldo vigente": saldo_vigente,
                    "Mês base": ultimo_mes.strftime("%m/%Y") if ultimo_mes else "—",
                }
            )

        st.dataframe(
            [{"Investimento": r["Investimento"], "Mês base": r["Mês base"], "Saldo vigente": _format_brl(r["Saldo vigente"])} for r in rows],
            hide_index=True,
            use_container_width=True,
        )

    st.divider()

    col_a, col_b = st.columns([2, 3])
    with col_a:
        with st.form("form_criar_investimento"):
            st.markdown("**Cadastrar investimento**")
            nome = st.text_input("Nome", placeholder="Ex.: Tesouro Selic / CDB / Corretora X")
            criar = st.form_submit_button("Criar", type="primary")
            if criar:
                inv = db.criar_investimento(user_id, nome)
                if inv:
                    st.success("✅ Investimento criado")
                    st.rerun()
                else:
                    st.error("❌ Não foi possível criar")

    with col_b:
        with st.form("form_atualizar_saldo"):
            st.markdown("**Atualizar saldo mensal**")
            if investimentos:
                inv_map = {inv.get("nome"): inv.get("id") for inv in investimentos}
                inv_nome = st.selectbox("Investimento", options=list(inv_map.keys()))
                data_ref = st.date_input("Mês de referência", value=_month_ref(hoje))
                data_conh = st.date_input("Data do saldo conhecido (consulta)", value=hoje)
                saldo = st.number_input("Saldo (R$)", min_value=0.0, value=0.0, step=100.0, format="%.2f")
                salvar = st.form_submit_button("Salvar", type="primary")
                if salvar:
                    inv_id = inv_map.get(inv_nome)
                    ok = db.definir_saldo_investimento(
                        user_id,
                        inv_id,
                        _month_ref(data_ref),
                        float(saldo),
                        data_conhecido_em=data_conh,
                    )
                    if ok:
                        st.success("✅ Saldo salvo")
                        st.rerun()
                    else:
                        st.error("❌ Não foi possível salvar")
            else:
                st.info("Crie um investimento para poder lançar saldo.")

    st.subheader("Horizonte 12 meses")
    st.caption("Mostra o total de investimentos por mês, projetando crescimento a partir do saldo conhecido.")

    base = _month_ref(hoje)
    meses = []
    for i in range(0, 12):
        m = date(base.year + (base.month - 1 + i) // 12, (base.month - 1 + i) % 12 + 1, 1)
        meses.append(m)

    serie = []
    for m in meses:
        serie.append({"Mês": m.strftime("%b/%Y"), "Total": db.total_investimentos_projetado_em(user_id, _month_end(m))})

    st.dataframe(
        [{"Mês": r["Mês"], "Total": _format_brl(r["Total"])} for r in serie],
        hide_index=True,
        use_container_width=True,
    )

    st.divider()

    with st.expander("Calculadora de renda fixa (opcional)"):
        st.subheader("SELIC (auto)")
        d, selic = _get_selic_cache()

        if selic is None:
            st.warning("Não consegui buscar a SELIC agora. Verifique sua internet ou tente novamente.")
        else:
            st.success(f"SELIC Meta: {selic:.2f}% a.a. (última atualização: {d.strftime('%d/%m/%Y') if d else '—'})")

        st.divider()

        st.subheader("Renda fixa (LCI/percentual da SELIC)")
        st.caption("Cálculo aproximado usando capitalização composta com base na SELIC anual.")

        col1, col2, col3 = st.columns(3)
        with col1:
            principal = st.number_input(
                "Valor investido (R$)", min_value=0.0, value=1000.0, step=100.0, format="%.2f", key="inv_calc_principal"
            )
        with col2:
            percentual = st.number_input(
                "Percentual da SELIC (%)", min_value=0.0, max_value=300.0, value=90.0, step=1.0, key="inv_calc_percentual"
            )
        with col3:
            dias = st.number_input(
                "Prazo (dias)", min_value=1, max_value=3650, value=365, step=30, key="inv_calc_dias"
            )

        taxa = selic if selic is not None else 0.0

        valor_final = calcular_rendimento_percentual_selic(
            principal=principal,
            selic_aa_percent=taxa,
            dias=int(dias),
            percentual_selic=float(percentual),
        )
        rendimento = max(0.0, valor_final - float(principal or 0))

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Valor final (aprox.)", _format_brl(valor_final))
        with c2:
            st.metric("Rendimento (aprox.)", _format_brl(rendimento))
        with c3:
            st.metric("Data alvo", (date.today()).strftime("%d/%m/%Y"))

        st.info("Obs.: LCI/LCAs geralmente são isentas de IR para PF; aqui mostramos apenas o bruto aproximado.")


 
