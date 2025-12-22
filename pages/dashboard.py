"""Dashboard financeiro com gráficos e resumos."""

import streamlit as st
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from calendar import monthrange

import pandas as pd

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from services.database import db


def get_user_id() -> str:
    """Retorna ID do usuário atual"""
    return st.session_state.get("user_id", "")


def _format_brl(value: float) -> str:
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


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


def _add_months(d: date, months: int) -> date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    last_day = monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def _sum_movimentos(transacoes: List[Dict], ate: date, incluir_previstas: bool) -> float:
    total = 0.0
    for t in transacoes:
        status = (t.get("status") or "realizada").lower()
        if status == "substituida":
            continue

        if incluir_previstas:
            if status not in {"realizada", "prevista"}:
                continue
        else:
            if status != "realizada":
                continue

        dt = _to_date(t.get("data"))
        if not dt or dt > ate:
            continue

        try:
            valor = float(t.get("valor") or 0)
        except Exception:
            valor = 0.0

        if t.get("tipo") == "receita":
            total += valor
        else:
            total -= valor
    return total


def _calcular_saldos_contas(
    user_id: str,
    hoje: date,
    fim_mes: date,
) -> Tuple[pd.DataFrame, float, float]:
    contas = db.listar_contas(user_id)

    contas_rows: List[Dict] = []
    conta_map: Dict[str, Dict] = {c.get("id"): c for c in contas if c.get("id")}

    datas_iniciais = [
        _to_date(c.get("data_saldo_inicial"))
        for c in contas
        if _to_date(c.get("data_saldo_inicial")) is not None
    ]
    data_inicio_consulta = min(datas_iniciais) if datas_iniciais else None

    transacoes = db.listar_transacoes(
        user_id=user_id,
        data_inicio=data_inicio_consulta,
        data_fim=fim_mes,
        limite=5000,
        incluir_previstas=True,
    )

    trans_por_conta: Dict[Optional[str], List[Dict]] = {}
    for t in transacoes:
        cid = t.get("conta_id")
        trans_por_conta.setdefault(cid, []).append(t)

    total_real = 0.0
    total_provisionado = 0.0

    for conta in contas:
        conta_id = conta.get("id")
        nome = conta.get("nome") or "Conta"
        tipo = conta.get("tipo") or "banco"
        try:
            saldo_inicial = float(conta.get("saldo_inicial") or 0)
        except Exception:
            saldo_inicial = 0.0

        data_ini = _to_date(conta.get("data_saldo_inicial")) or hoje
        trans_c = [t for t in trans_por_conta.get(conta_id, []) if (_to_date(t.get("data")) or date.min) >= data_ini]

        saldo_real = saldo_inicial + _sum_movimentos(trans_c, hoje, incluir_previstas=False)
        saldo_prov = saldo_inicial + _sum_movimentos(trans_c, fim_mes, incluir_previstas=True)

        total_real += saldo_real
        total_provisionado += saldo_prov

        contas_rows.append(
            {
                "Conta": nome,
                "Tipo": tipo,
                "Saldo inicial": saldo_inicial,
                "Saldo real (hoje)": saldo_real,
                "Saldo provisionado (fim do mês)": saldo_prov,
            }
        )

    # Transações sem conta (legado)
    if trans_por_conta.get(None):
        trans_sc = trans_por_conta.get(None, [])
        saldo_real = _sum_movimentos(trans_sc, hoje, incluir_previstas=False)
        saldo_prov = _sum_movimentos(trans_sc, fim_mes, incluir_previstas=True)

        total_real += saldo_real
        total_provisionado += saldo_prov

        contas_rows.append(
            {
                "Conta": "Sem conta",
                "Tipo": "-",
                "Saldo inicial": 0.0,
                "Saldo real (hoje)": saldo_real,
                "Saldo provisionado (fim do mês)": saldo_prov,
            }
        )

    df = pd.DataFrame(contas_rows)
    if not df.empty:
        df = df.sort_values(["Tipo", "Conta"], ascending=[True, True])

    return df, total_real, total_provisionado


def render_fluxo_caixa_e_projecao(user_id: str):
    """Mostra saldo real, provisionado e projeção 12/18 meses."""
    hoje = date.today()
    ultimo_dia_mes = monthrange(hoje.year, hoje.month)[1]
    fim_mes = date(hoje.year, hoje.month, ultimo_dia_mes)

    st.subheader("💳 Contas e Fluxo de Caixa")

    df_contas, total_real, total_prov = _calcular_saldos_contas(user_id, hoje, fim_mes)

    total_invest_hoje = db.total_investimentos_projetado_em(user_id, hoje)
    total_geral_hoje = float(total_real) + float(total_invest_hoje)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Saldo em contas (hoje)", _format_brl(total_real))
    with c2:
        st.metric("Saldo provisionado (fim do mês)", _format_brl(total_prov))
    with c3:
        st.metric("Investimentos (hoje)", _format_brl(total_invest_hoje))
    with c4:
        st.metric("Total (hoje)", _format_brl(total_geral_hoje))

    horizon = st.selectbox("Projeção", options=[12, 18], index=0, format_func=lambda x: f"{x} meses")

    if df_contas.empty:
        st.info("Cadastre pelo menos uma conta em Configurações para ver o fluxo de caixa.")
        return

    df_show = df_contas.copy()
    for col in ["Saldo inicial", "Saldo real (hoje)", "Saldo provisionado (fim do mês)"]:
        df_show[col] = df_show[col].map(_format_brl)
    st.dataframe(df_show, hide_index=True, use_container_width=True)

    # Projeção: a partir do saldo provisionado do fim do mês atual
    orcamentos = db.listar_orcamentos(user_id)
    total_orcamento_mensal = sum(float(o.get("valor_limite", 0) or 0) for o in orcamentos)

    recorrentes = db.listar_recorrentes(user_id, include_inactive=False)
    entradas_fixas = sum(float(r.get("valor", 0) or 0) for r in recorrentes if r.get("tipo") == "receita")
    saidas_fixas = sum(float(r.get("valor", 0) or 0) for r in recorrentes if r.get("tipo") == "despesa")

    saldo = float(total_prov)
    base = date(hoje.year, hoje.month, 1)

    rows: List[Dict] = []
    for i in range(1, int(horizon) + 1):
        mes_ref = _add_months(base, i)
        mes_label = mes_ref.strftime("%b/%Y")

        # Net do mês = fixas (recorrentes) - orçamento (variáveis planejadas)
        net = entradas_fixas - saidas_fixas - total_orcamento_mensal
        saldo = saldo + net

        ultimo = monthrange(mes_ref.year, mes_ref.month)[1]
        mes_ref_fim = date(mes_ref.year, mes_ref.month, ultimo)
        invest_mes = db.total_investimentos_projetado_em(user_id, mes_ref_fim)
        total_mes = float(saldo) + float(invest_mes)

        rows.append(
            {
                "Mês": mes_label,
                "Saldo em contas": saldo,
                "Investimentos": invest_mes,
                "Total projetado": total_mes,
                "Entradas fixas": entradas_fixas,
                "Saídas fixas": saidas_fixas,
                "Orçamento": total_orcamento_mensal,
            }
        )

    df_proj = pd.DataFrame(rows)
    st.subheader("🔮 Projeção de Saldo")
    st.caption("Projeção mensal = recorrentes (fixas) + orçamento (planejado). Total inclui investimentos.")

    if PLOTLY_AVAILABLE and not df_proj.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df_proj["Mês"],
                y=df_proj["Total projetado"],
                mode="lines+markers",
                name="Total projetado",
                line=dict(color="#1e3a8a", width=3),
                marker=dict(size=7, color="#1e3a8a"),
                hovertemplate="<b>%{x}</b><br>Saldo: R$ %{y:,.2f}<extra></extra>",
            )
        )
        fig.update_layout(
            height=380,
            margin=dict(t=30, b=30, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9", title="Saldo (R$)"),
            xaxis=dict(showgrid=False, title="Mês"),
            showlegend=False,
        )
        st.plotly_chart(fig, width="stretch")
    else:
        df_proj_show = df_proj.copy()
        for col in ["Saldo em contas", "Investimentos", "Total projetado", "Entradas fixas", "Saídas fixas", "Orçamento"]:
            df_proj_show[col] = df_proj_show[col].map(_format_brl)
        st.dataframe(df_proj_show, hide_index=True, use_container_width=True)


def render_dashboard_page():
    """Renderiza o dashboard principal"""
    
    user_id = get_user_id()
    if not user_id:
        st.warning("Usuário não identificado")
        return
    
    st.header("📊 Dashboard")

    render_fluxo_caixa_e_projecao(user_id)
    st.markdown("---")
    
    # Seletor de período
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        periodo = st.selectbox(
            "Período",
            options=["Este mês", "Últimos 30 dias", "Últimos 3 meses", "Este ano", "Personalizado"],
            key="dash_periodo"
        )
    
    # Calcular datas baseado no período
    hoje = date.today()
    
    if periodo == "Este mês":
        data_inicio = hoje.replace(day=1)
        data_fim = hoje
    elif periodo == "Últimos 30 dias":
        data_inicio = hoje - timedelta(days=30)
        data_fim = hoje
    elif periodo == "Últimos 3 meses":
        data_inicio = hoje - timedelta(days=90)
        data_fim = hoje
    elif periodo == "Este ano":
        data_inicio = hoje.replace(month=1, day=1)
        data_fim = hoje
    else:
        with col2:
            data_inicio = st.date_input("De", value=hoje.replace(day=1), key="dash_inicio")
        with col3:
            data_fim = st.date_input("Até", value=hoje, key="dash_fim")
    
    st.markdown("---")
    
    # Buscar dados
    totais = db.totais_periodo(user_id, data_inicio, data_fim)
    transacoes = db.listar_transacoes(user_id, data_inicio, data_fim)
    resumo_categorias = db.resumo_por_categoria(user_id, data_inicio, data_fim)
    
    # Cards de resumo
    render_cards_resumo(totais)
    
    st.markdown("---")
    
    # Gráficos
    if transacoes:
        col1, col2 = st.columns(2)
        
        with col1:
            render_grafico_categorias(resumo_categorias)
        
        with col2:
            render_grafico_evolucao(transacoes)
        
        st.markdown("---")
        
        # Transações recentes
        render_transacoes_recentes(transacoes[:10])
    else:
        st.info("📭 Nenhuma transação encontrada para o período selecionado.")
        st.markdown("""
        **Comece agora:**
        - Clique em **➕ Nova Transação** no menu lateral
        - Adicione suas receitas e despesas
        - Escaneie cupons fiscais para lançamento automático
        """)


def render_cards_resumo(totais: Dict):
    """Renderiza cards com resumo financeiro"""
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 Receitas",
            f"R$ {totais['receitas']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            delta=None
        )
    
    with col2:
        st.metric(
            "💸 Despesas",
            f"R$ {totais['despesas']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            delta=None
        )
    
    with col3:
        saldo = totais['saldo']
        st.metric(
            "📈 Saldo",
            f"R$ {abs(saldo):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            delta=f"{'Positivo' if saldo >= 0 else 'Negativo'}",
            delta_color="normal" if saldo >= 0 else "inverse"
        )
    
    with col4:
        # Taxa de economia
        if totais['receitas'] > 0:
            taxa = (totais['receitas'] - totais['despesas']) / totais['receitas'] * 100
        else:
            taxa = 0
        
        st.metric(
            "🎯 Taxa de Economia",
            f"{taxa:.1f}%",
            delta=f"{'Bom!' if taxa > 20 else 'Atenção' if taxa > 0 else 'Negativo'}",
            delta_color="normal" if taxa > 10 else "off" if taxa > 0 else "inverse"
        )


def render_grafico_categorias(resumo: List[Dict]):
    """Renderiza gráfico de pizza por categoria"""
    
    if not PLOTLY_AVAILABLE:
        st.warning("Plotly não instalado. Execute: pip install plotly")
        return
    
    st.subheader("📊 Despesas por Categoria")
    
    if not resumo:
        st.info("Sem dados para exibir")
        return
    
    # Filtrar apenas despesas
    dados_despesas = [r for r in resumo if r["total_despesas"] > 0]
    
    if not dados_despesas:
        st.info("Sem despesas no período")
        return
    
    df = pd.DataFrame(dados_despesas)
    
    fig = px.pie(
        df,
        values="total_despesas",
        names="categoria",
        title="",
        hole=0.6, # Donut chart mais moderno
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    
    fig.update_traces(
        textposition='outside',
        textinfo='percent+label',
        hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>",
        marker=dict(line=dict(color='#ffffff', width=2))
    )
    
    fig.update_layout(
        showlegend=False,
        margin=dict(t=20, b=20, l=20, r=20),
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, width='stretch')


def render_grafico_evolucao(transacoes: List[Dict]):
    """Renderiza gráfico de evolução mensal com receitas, despesas e orçamento"""
    
    if not PLOTLY_AVAILABLE:
        return
    
    st.subheader("📈 Evolução Mensal")
    
    if not transacoes:
        st.info("Sem dados para exibir")
        return
    
    # Buscar orçamentos do usuário
    user_id = st.session_state.get("user_id", "")
    orcamentos = db.listar_orcamentos(user_id) if user_id else []
    total_orcamento = sum(float(o.get("valor_limite", 0)) for o in orcamentos)
    
    # Converter para DataFrame
    df = pd.DataFrame(transacoes)
    df["data"] = pd.to_datetime(df["data"])
    df["valor"] = df["valor"].astype(float)
    df["mes_ano"] = df["data"].dt.to_period("M")
    
    # Agrupar por mês e tipo
    df_grouped = df.groupby(["mes_ano", "tipo"])["valor"].sum().reset_index()
    
    # Pivot para ter receitas e despesas em colunas separadas
    df_pivot = df_grouped.pivot(index="mes_ano", columns="tipo", values="valor").fillna(0).reset_index()
    
    if "receita" not in df_pivot.columns:
        df_pivot["receita"] = 0
    if "despesa" not in df_pivot.columns:
        df_pivot["despesa"] = 0
    
    # Converter período para string formatada
    df_pivot["mes_label"] = df_pivot["mes_ano"].apply(lambda x: x.strftime("%b/%Y"))
    
    # Adicionar linha de orçamento
    df_pivot["orcamento"] = total_orcamento if total_orcamento > 0 else 0
    
    # Ordenar por mês
    df_pivot = df_pivot.sort_values("mes_ano")
    
    fig = go.Figure()
    
    # Receitas (barras)
    fig.add_trace(go.Bar(
        x=df_pivot["mes_label"],
        y=df_pivot["receita"],
        name="Receitas",
        marker_color="#10b981",
        text=[f"R$ {v:,.0f}" for v in df_pivot["receita"]],
        textposition='outside',
        hovertemplate="<b>Receitas</b><br>%{x}<br>R$ %{y:,.2f}<extra></extra>"
    ))
    
    # Despesas (barras)
    fig.add_trace(go.Bar(
        x=df_pivot["mes_label"],
        y=df_pivot["despesa"],
        name="Despesas",
        marker_color="#ef4444",
        text=[f"R$ {v:,.0f}" for v in df_pivot["despesa"]],
        textposition='outside',
        hovertemplate="<b>Despesas</b><br>%{x}<br>R$ %{y:,.2f}<extra></extra>"
    ))
    
    # Orçamento (linha)
    if total_orcamento > 0:
        fig.add_trace(go.Scatter(
            x=df_pivot["mes_label"],
            y=df_pivot["orcamento"],
            name="Orçamento",
            mode='lines+markers',
            line=dict(color="#f59e0b", width=3, dash='dash'),
            marker=dict(size=8, color="#d97706"),
            hovertemplate="<b>Orçamento</b><br>%{x}<br>R$ %{y:,.2f}<extra></extra>"
        ))
    
    fig.update_layout(
        barmode='group',
        showlegend=True,
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="right", 
            x=1
        ),
        margin=dict(t=40, b=40, l=20, r=20),
        height=400,
        xaxis=dict(
            title="Mês",
            showgrid=False,
            showline=True,
            linecolor='#e2e8f0'
        ),
        yaxis=dict(
            title="Valor (R$)",
            showgrid=True,
            gridcolor='#f1f5f9',
            zeroline=False
        ),
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, width='stretch')


def render_transacoes_recentes(transacoes: List[Dict]):
    """Renderiza lista de transações recentes"""
    
    st.subheader("🕐 Transações Recentes")
    
    if not transacoes:
        st.info("Nenhuma transação recente")
        return
    
    rows: List[Dict] = []
    for t in transacoes:
        cat = t.get("categorias") or {}
        icone = cat.get("icone", "📦")
        cat_nome = cat.get("nome", "Sem categoria")

        data_value = None
        data_raw = t.get("data")
        if isinstance(data_raw, str):
            try:
                data_value = datetime.fromisoformat(data_raw.replace("Z", "+00:00")).date()
            except Exception:
                data_value = None
        elif isinstance(data_raw, (datetime, date)):
            try:
                data_value = data_raw.date() if isinstance(data_raw, datetime) else data_raw
            except Exception:
                data_value = None

        tipo_raw = t.get("tipo")
        tipo_label = "Receita" if tipo_raw == "receita" else "Despesa"

        valor = 0.0
        try:
            valor = float(t.get("valor", 0) or 0)
        except Exception:
            valor = 0.0

        # Mostrar valor sempre positivo e usar o Tipo como contexto (mais legível na tabela)
        rows.append({
            "Data": data_value,
            "Descrição": (t.get("descricao") or "")[:60],
            "Categoria": f"{icone} {cat_nome}",
            "Tipo": tipo_label,
            "Valor": abs(valor),
        })

    df = pd.DataFrame(rows)

    def _format_date(value) -> str:
        try:
            if pd.isna(value):
                return ""
        except Exception:
            pass
        try:
            if isinstance(value, (datetime, date)):
                return value.strftime("%d/%m/%Y")
        except Exception:
            pass
        return str(value) if value is not None else ""

    def _style_row(row: pd.Series):
        is_receita = str(row.get("Tipo", "")).lower().strip() == "receita"
        color = "#10b981" if is_receita else "#ef4444"
        styles = []
        for col in row.index:
            if col in ("Tipo", "Valor"):
                styles.append(f"color: {color}; font-weight: 700")
            else:
                styles.append("")
        return styles

    styler = (
        df.style
        .format({
            "Data": _format_date,
            "Valor": _format_brl,
        })
        .apply(_style_row, axis=1)
    )

    st.dataframe(
        styler,
        hide_index=True,
        use_container_width=True,
    )


def render_widget_resumo_lateral():
    """Widget de resumo para sidebar"""
    
    user_id = get_user_id()
    if not user_id:
        return
    
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    
    totais = db.totais_periodo(user_id, inicio_mes, hoje)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Este mês")
    
    st.sidebar.metric(
        "Saldo",
        f"R$ {totais['saldo']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        delta=None
    )
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("Receitas", f"R${totais['receitas']:,.0f}".replace(",", "."))
    with col2:
        st.metric("Despesas", f"R${totais['despesas']:,.0f}".replace(",", "."))
