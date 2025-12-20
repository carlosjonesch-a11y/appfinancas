"""
Dashboard financeiro com gráficos e resumos
"""
import streamlit as st
from datetime import datetime, date, timedelta
from typing import Dict, List
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


def render_dashboard_page():
    """Renderiza o dashboard principal"""
    
    user_id = get_user_id()
    if not user_id:
        st.warning("Usuário não identificado")
        return
    
    st.header("📊 Dashboard")
    
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
    
    for t in transacoes:
        cat = t.get("categorias") or {}
        icone = cat.get("icone", "📦")
        cat_nome = cat.get("nome", "Sem categoria")
        
        # Formatar data
        data_str = t["data"]
        if isinstance(data_str, str):
            try:
                data_obj = datetime.fromisoformat(data_str.replace("Z", "+00:00"))
                data_formatada = data_obj.strftime("%d/%m")
            except:
                data_formatada = data_str[:10]
        else:
            data_formatada = str(data_str)[:10]
        
        # Cor baseada no tipo
        cor = "🟢" if t["tipo"] == "receita" else "🔴"
        sinal = "+" if t["tipo"] == "receita" else "-"
        
        col1, col2, col3 = st.columns([0.5, 3, 1])
        
        with col1:
            st.write(f"{data_formatada}")
        
        with col2:
            st.write(f"{icone} **{t['descricao'][:40]}** - {cat_nome}")
        
        with col3:
            valor_formatado = f"{sinal} R$ {float(t['valor']):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if t["tipo"] == "receita":
                st.markdown(f"<span style='color: #2ecc71; font-weight: bold;'>{valor_formatado}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span style='color: #e74c3c; font-weight: bold;'>{valor_formatado}</span>", unsafe_allow_html=True)


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
