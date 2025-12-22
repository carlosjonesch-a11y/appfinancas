"""Página de Cartão de Crédito: fatura atual + importação OFX (conciliação simples)."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

import streamlit as st

from services.database import db
from services.ofx_import import parse_ofx_bytes, sugerir_match_simples


def get_user_id() -> str:
    return st.session_state.get("user_id", "")


def _format_brl(value: float) -> str:
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def _cycle_dates(hoje: date, fechamento: int, vencimento: int) -> Tuple[date, date, date]:
    """Calcula (inicio_ciclo, fim_ciclo, vencimento_fatura) baseado em dia de fechamento/vencimento."""

    fechamento = int(fechamento)
    vencimento = int(vencimento)

    ultimo_dia = monthrange(hoje.year, hoje.month)[1]
    fechamento = max(1, min(fechamento, ultimo_dia))

    # fim do ciclo: fechamento do mês atual ou do próximo, dependendo do dia
    if hoje.day <= fechamento:
        fim = date(hoje.year, hoje.month, fechamento)
    else:
        # próximo mês
        y = hoje.year + (1 if hoje.month == 12 else 0)
        m = 1 if hoje.month == 12 else hoje.month + 1
        ultimo = monthrange(y, m)[1]
        fim = date(y, m, min(fechamento, ultimo))

    # início do ciclo: dia seguinte ao fechamento anterior
    # fechar anterior = fim - 1 mês
    prev_y = fim.year if fim.month > 1 else fim.year - 1
    prev_m = fim.month - 1 if fim.month > 1 else 12
    prev_ultimo = monthrange(prev_y, prev_m)[1]
    prev_fech = date(prev_y, prev_m, min(fechamento, prev_ultimo))
    inicio = prev_fech.replace(day=prev_fech.day)  # noop
    inicio = prev_fech.fromordinal(prev_fech.toordinal() + 1)

    # vencimento: por padrão no mesmo mês de fim se vencimento > fechamento, senão no mês seguinte
    if vencimento > fechamento:
        venc_m = fim.month
        venc_y = fim.year
    else:
        venc_y = fim.year + (1 if fim.month == 12 else 0)
        venc_m = 1 if fim.month == 12 else fim.month + 1

    venc_ultimo = monthrange(venc_y, venc_m)[1]
    venc = date(venc_y, venc_m, min(vencimento, venc_ultimo))

    return inicio, fim, venc


def _to_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except Exception:
            return None
    return None


def _sum_despesas_cartao(transacoes: List[Dict], inicio: date, fim: date, conta_id: str) -> float:
    total = 0.0
    for t in transacoes:
        if t.get("conta_id") != conta_id:
            continue
        if (t.get("tipo") or "").lower() != "despesa":
            continue
        status = (t.get("status") or "realizada").lower()
        if status != "realizada":
            continue
        dt = _to_date(t.get("data"))
        if not dt:
            continue
        if dt < inicio or dt > fim:
            continue
        try:
            total += float(t.get("valor") or 0)
        except Exception:
            pass
    return total


def render_cartao_page():
    st.header("💳 Cartão de Crédito")

    user_id = get_user_id()
    if not user_id:
        st.warning("Usuário não identificado")
        return

    contas = db.listar_contas(user_id)
    cartoes = [
        c
        for c in contas
        if (str(c.get("tipo") or "").strip().lower() == "cartao_credito")
        and bool(c.get("ativo", True))
    ]

    if not cartoes:
        st.info("Nenhum cartão cadastrado ainda. Cadastre um em Configurações → Contas (tipo cartao_credito).")

        # Diagnóstico para quando o usuário jura que cadastrou, mas não aparece.
        with st.expander("Diagnóstico (clique para ver)"):
            st.write({
                "user_id": user_id,
                "user_name": st.session_state.get("user_name"),
                "user_email": st.session_state.get("user_email"),
                "total_contas_retornadas": len(contas),
            })
            if contas:
                preview = [
                    {
                        "id": c.get("id"),
                        "nome": c.get("nome"),
                        "tipo": c.get("tipo"),
                        "ativo": c.get("ativo"),
                        "dia_fechamento": c.get("dia_fechamento"),
                        "dia_vencimento": c.get("dia_vencimento"),
                    }
                    for c in contas
                ]
                st.dataframe(preview, width='stretch', hide_index=True)

                st.divider()
                st.subheader("Corrigir tipo (opcional)")
                st.caption(
                    "Se você cadastrou o cartão mas marcou o tipo como 'banco' por engano, dá pra corrigir aqui. "
                    "Isso vai alterar o tipo da conta selecionada para 'cartao_credito'."
                )

                conta_opt = {f"{c.get('nome')} ({c.get('tipo')})": c.get("id") for c in contas}
                conta_label = st.selectbox(
                    "Conta para converter em cartão",
                    options=list(conta_opt.keys()),
                    key="diag_convert_conta",
                )

                colx, coly = st.columns(2)
                with colx:
                    novo_fech = st.number_input(
                        "Dia de fechamento",
                        min_value=1,
                        max_value=31,
                        value=10,
                        key="diag_convert_fech",
                    )
                with coly:
                    novo_venc = st.number_input(
                        "Dia de vencimento",
                        min_value=1,
                        max_value=31,
                        value=17,
                        key="diag_convert_venc",
                    )

                confirm = st.checkbox(
                    "Confirmo que quero converter essa conta para cartão de crédito",
                    value=False,
                    key="diag_convert_confirm",
                )

                if st.button(
                    "Converter para cartao_credito",
                    type="primary",
                    disabled=not confirm,
                    key="diag_convert_btn",
                ):
                    conta_id = conta_opt.get(conta_label)
                    atualizado = db.atualizar_conta(
                        conta_id,
                        {
                            "tipo": "cartao_credito",
                            "dia_fechamento": int(novo_fech),
                            "dia_vencimento": int(novo_venc),
                        },
                    )
                    if atualizado:
                        st.success("✅ Conta convertida para cartão. Recarregando...")
                        st.rerun()
                    else:
                        st.error("❌ Não foi possível converter. Veja os logs para mais detalhes.")
            else:
                st.caption("Nenhuma conta foi retornada para esse usuário. Se você acabou de criar, tente atualizar a página ou sair/entrar novamente.")
        st.stop()

    cartao_nome = st.selectbox("Cartão", options=[c.get("nome") for c in cartoes])
    cartao = next(c for c in cartoes if c.get("nome") == cartao_nome)

    fechamento = cartao.get("dia_fechamento")
    vencimento = cartao.get("dia_vencimento")

    if not fechamento or not vencimento:
        st.warning("Configure dia de fechamento e vencimento do cartão em Configurações → Contas.")
        st.stop()

    hoje = date.today()
    inicio_ciclo, fim_ciclo, venc = _cycle_dates(hoje, int(fechamento), int(vencimento))

    # Buscar transações do período do ciclo (um pouco mais amplo para import)
    transacoes = db.listar_transacoes(
        user_id=user_id,
        data_inicio=inicio_ciclo,
        data_fim=fim_ciclo,
        limite=5000,
        incluir_previstas=True,
    )

    total_fatura = _sum_despesas_cartao(transacoes, inicio_ciclo, fim_ciclo, cartao.get("id"))

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Fatura (ciclo atual)", _format_brl(total_fatura))
    with c2:
        st.metric("Fechamento", inicio_ciclo.strftime("%d/%m") + " → " + fim_ciclo.strftime("%d/%m"))
    with c3:
        st.metric("Vencimento", venc.strftime("%d/%m/%Y"))

    st.divider()

    st.subheader("Fechamento e pagamento (modo simples)")
    st.caption(
        "Para cartões cujo extrato é PDF: aqui você só confere o total do ciclo e registra o pagamento. "
        "(Se você importar as compras via OFX, não lance o pagamento como despesa para não duplicar.)"
    )

    contas_pagamento = [
        c
        for c in contas
        if bool(c.get("ativo", True))
        and str(c.get("tipo") or "").strip().lower() in {"banco", "carteira", "dinheiro"}
    ]
    if not contas_pagamento:
        st.info("Cadastre uma conta do tipo banco/carteira para registrar o pagamento.")
    else:
        cats_desp = db.listar_categorias(user_id, tipo="despesa")
        cat_map = {c.get("nome") or "Categoria": c.get("id") for c in (cats_desp or [])}
        cat_default_nome = None
        for n in cat_map.keys():
            if "cart" in (n or "").lower() or "fatura" in (n or "").lower():
                cat_default_nome = n
                break
        if not cat_default_nome and cat_map:
            cat_default_nome = list(cat_map.keys())[0]

        with st.form("form_pagamento_fatura"):
            colp1, colp2 = st.columns(2)
            with colp1:
                conta_label_map = {f"{c.get('nome')}": c.get("id") for c in contas_pagamento}
                conta_nome = st.selectbox("Pagar com", options=list(conta_label_map.keys()))
                data_pag = st.date_input("Data do pagamento", value=venc)
            with colp2:
                valor_pag = st.number_input(
                    "Valor pago (R$)",
                    min_value=0.0,
                    value=float(total_fatura or 0.0),
                    step=10.0,
                    format="%.2f",
                )
                cat_nome = st.selectbox(
                    "Categoria (opcional)",
                    options=list(cat_map.keys()) if cat_map else ["(sem categoria)"] ,
                    index=(list(cat_map.keys()).index(cat_default_nome) if (cat_map and cat_default_nome in cat_map) else 0),
                )

            descricao = st.text_input(
                "Descrição",
                value=f"Pagamento fatura - {cartao.get('nome')}",
                max_chars=120,
            )

            confirmar = st.checkbox("Confirmo que este pagamento deve virar uma despesa", value=False)
            salvar = st.form_submit_button("Registrar pagamento", type="primary", disabled=not confirmar)

            if salvar:
                payload = {
                    "user_id": user_id,
                    "conta_id": conta_label_map.get(conta_nome),
                    "categoria_id": cat_map.get(cat_nome),
                    "descricao": (descricao or "Pagamento fatura")[:120],
                    "valor": float(valor_pag),
                    "tipo": "despesa",
                    "data": data_pag.isoformat(),
                    "status": "realizada",
                    "modo_lancamento": "manual",
                }
                criado = db.criar_transacao(payload)
                if criado:
                    st.success("✅ Pagamento registrado")
                    st.rerun()
                else:
                    st.error("❌ Não foi possível registrar o pagamento")

    with st.expander("Importar OFX (opcional)"):
        st.caption("Importa compras do cartão como despesas realizadas. Conciliação: data + valor (simples).")

        arquivo = st.file_uploader("OFX do cartão", type=["ofx"], key="ofx_cartao")
        if not arquivo:
            st.info("Envie um arquivo .ofx para importar.")
            return

        try:
            txs = parse_ofx_bytes(arquivo.getvalue())
        except Exception as e:
            st.error(f"Não consegui ler esse OFX: {e}")
            return

        if not txs:
            st.warning("Nenhuma transação encontrada no OFX.")
            return

        preview = [{"Data": t.data.strftime("%d/%m/%Y"), "Valor": _format_brl(t.valor), "Descrição": t.descricao} for t in txs[:50]]
        st.dataframe(preview, width='stretch', hide_index=True)

        if st.button("📥 Importar e conciliar", type="primary", key="btn_importar_ofx"):
            with st.spinner("Importando..."):
                existentes = db.listar_transacoes(
                    user_id=user_id,
                    data_inicio=min(t.data for t in txs),
                    data_fim=max(t.data for t in txs),
                    tipo="despesa",
                    conta_id=cartao.get("id"),
                    limite=5000,
                    incluir_previstas=True,
                )

                cats_desp = db.listar_categorias(user_id, tipo="despesa")
                cat_fallback = cats_desp[0]["id"] if cats_desp else None

                criadas = 0
                conciliadas = 0

                for tx in txs:
                    match = sugerir_match_simples(tx, existentes)
                    if match:
                        conciliadas += 1
                        continue

                    payload = {
                        "user_id": user_id,
                        "conta_id": cartao.get("id"),
                        "categoria_id": cat_fallback,
                        "descricao": tx.descricao[:120],
                        "valor": float(tx.valor),
                        "tipo": "despesa",
                        "data": tx.data.isoformat(),
                        "status": "realizada",
                        "modo_lancamento": "semi_automatico",
                        "ofx_fitid": tx.fitid,
                        "conciliado_em": datetime.now().isoformat(),
                    }

                    criado = db.criar_transacao(payload)
                    if criado:
                        criadas += 1

                st.success(f"✅ Importação concluída. Criadas: {criadas}. Já existentes (conciliadas): {conciliadas}.")
                st.rerun()


 
