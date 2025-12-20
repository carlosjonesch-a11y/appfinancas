"""
Página de gestão de orçamentos
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date
from services.database import db

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

def get_user_id() -> str:
    """Retorna ID do usuário atual"""
    return st.session_state.get("user_id", "")

def render_orcamentos_page():
    """Renderiza a página de orçamentos"""
    user_id = get_user_id()
    if not user_id:
        st.warning("Usuário não identificado")
        return

    st.header("📊 Orçamentos Mensais")
    st.markdown("Gerencie seus limites de gastos por categoria.")
    
    # --- Gráfico Orçado vs Realizado ---
    render_grafico_orcado_realizado(user_id)
    
    st.divider()

    # --- Dados ---
    categorias = db.listar_categorias(user_id, tipo="despesa")
    orcamentos_existentes = db.listar_orcamentos(user_id)
    
    # Mapa de orçamentos existentes por categoria_id
    ids_com_orcamento = {o["categoria_id"] for o in orcamentos_existentes}
    
    # --- 1. Adicionar Novo Orçamento ---
    st.markdown("### ➕ Novo Orçamento")
    
    # Filtrar categorias que ainda não têm orçamento
    cats_disponiveis = [c for c in categorias if c["id"] not in ids_com_orcamento]
    
    if cats_disponiveis:
        with st.container():
            c1, c2, c3 = st.columns([3, 2, 1])
            with c1:
                cat_selecionada = st.selectbox(
                    "Escolha a Categoria", 
                    options=cats_disponiveis, 
                    format_func=lambda x: f"{x.get('icone','')} {x['nome']}",
                    key="new_budget_cat"
                )
            with c2:
                novo_valor = st.number_input(
                    "Valor Limite (R$)", 
                    min_value=0.0, 
                    step=50.0, 
                    key="new_budget_val"
                )
            with c3:
                st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True) # Spacer
                if st.button("Adicionar", width='stretch', type="primary"):
                    if novo_valor > 0:
                        db.definir_orcamento(user_id, cat_selecionada["id"], novo_valor)
                        st.success(f"Orçamento para {cat_selecionada['nome']} criado!")
                        st.rerun()
                    else:
                        st.warning("O valor deve ser maior que zero.")
    else:
        if not categorias:
            st.info("Cadastre categorias de despesa primeiro.")
        else:
            st.success("Todas as suas categorias já possuem orçamentos definidos! 🎉")

    st.divider()

    # --- 2. Orçamentos Ativos ---
    st.markdown("### 📉 Orçamentos Ativos")
    
    if not orcamentos_existentes:
        st.info("Nenhum orçamento ativo no momento.")
        return

    # Ordenar por percentual de uso (decrescente) para destacar os críticos
    for o in orcamentos_existentes:
        o["_percentual"] = (float(o.get("valor_gasto", 0)) / float(o.get("valor_limite", 1))) if float(o.get("valor_limite", 1)) > 0 else 0

    orcamentos_ordenados = sorted(orcamentos_existentes, key=lambda x: x["_percentual"], reverse=True)

    for orc in orcamentos_ordenados:
        cat_nome = orc.get("categorias", {}).get("nome", "Categoria") if isinstance(orc.get("categorias"), dict) else "Categoria"
        cat_icone = orc.get("categorias", {}).get("icone", "📦") if isinstance(orc.get("categorias"), dict) else "📦"
        
        # Fallback se vier do banco local onde categorias não é join
        if "categorias" not in orc and "categoria_id" in orc:
            # Tentar achar nome na lista de categorias carregada
            cat_obj = next((c for c in categorias if c["id"] == orc["categoria_id"]), None)
            if cat_obj:
                cat_nome = cat_obj["nome"]
                cat_icone = cat_obj.get("icone", "📦")

        valor_limite = float(orc.get("valor_limite", 0))
        valor_gasto = float(orc.get("valor_gasto", 0))
        saldo = valor_limite - valor_gasto
        percentual = valor_gasto / valor_limite if valor_limite > 0 else 0
        
        # Cor da barra
        cor_barra = "#10b981" # Verde
        if percentual > 0.75: cor_barra = "#f59e0b" # Laranja
        if percentual >= 1.0: cor_barra = "#ef4444" # Vermelho

        with st.container():
            # Linha 1: Título e Botão de Excluir
            col_tit, col_del = st.columns([5, 1])
            with col_tit:
                st.markdown(f"#### {cat_icone} {cat_nome}")
            with col_del:
                if st.button("🗑️", key=f"del_orc_{orc['id']}", help="Remover orçamento"):
                    db.deletar_orcamento(orc["id"])
                    st.rerun()

            # Linha 2: Barra de Progresso Customizada
            st.markdown(f"""
            <div style="margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.9rem; margin-bottom: 4px;">
                    <span><b>Gasto:</b> R$ {valor_gasto:,.2f}</span>
                    <span><b>Meta:</b> R$ {valor_limite:,.2f}</span>
                </div>
                <div style="background-color: #e2e8f0; border-radius: 8px; height: 16px; width: 100%; overflow: hidden;">
                    <div style="background-color: {cor_barra}; width: {min(percentual, 1.0)*100}%; height: 100%;"></div>
                </div>
                <div style="text-align: right; font-size: 0.85rem; margin-top: 4px; color: {cor_barra}; font-weight: bold;">
                    {f'Restante: R$ {saldo:,.2f}' if saldo >= 0 else f'Excedido: R$ {abs(saldo):,.2f}'}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Linha 3: Edição Rápida (Expander)
            with st.expander("✏️ Editar Meta"):
                c_edit_1, c_edit_2 = st.columns([3, 1])
                with c_edit_1:
                    nova_meta = st.number_input(
                        "Nova Meta", 
                        value=valor_limite, 
                        step=50.0, 
                        key=f"edit_val_{orc['id']}",
                        label_visibility="collapsed"
                    )
                with c_edit_2:
                    if st.button("Atualizar", key=f"btn_upd_{orc['id']}"):
                        if nova_meta > 0:
                            db.definir_orcamento(user_id, orc["categoria_id"], nova_meta)
                            st.success("Atualizado!")
                            st.rerun()
            
            st.divider()


def render_grafico_orcado_realizado(user_id: str):
    """Renderiza gráfico de orçado vs realizado por mês"""
    
    if not PLOTLY_AVAILABLE:
        st.warning("Plotly não disponível. Instale com: pip install plotly")
        return
    
    st.subheader("📈 Orçado vs Realizado por Mês")
    
    # Buscar transações dos últimos 6 meses
    from datetime import datetime, timedelta
    hoje = date.today()
    data_inicio = (hoje - timedelta(days=180)).replace(day=1)
    
    transacoes = db.listar_transacoes(user_id)
    orcamentos = db.listar_orcamentos(user_id)
    
    if not orcamentos:
        st.info("Defina orçamentos para visualizar o gráfico de comparação.")
        return
    
    # Filtrar transações dos últimos 6 meses
    transacoes_periodo = [
        t for t in transacoes 
        if datetime.fromisoformat(t["data"]).date() >= data_inicio
    ]
    
    # Agrupar por mês
    meses_dados = {}
    
    for i in range(6):
        mes_ref = hoje - timedelta(days=30*i)
        mes_key = mes_ref.strftime("%Y-%m")
        mes_nome = mes_ref.strftime("%b/%Y")
        
        # Calcular total orçado
        total_orcado = sum(float(o.get("valor_limite", 0)) for o in orcamentos)
        
        # Calcular total gasto no mês
        total_gasto = sum(
            float(t["valor"]) 
            for t in transacoes_periodo
            if datetime.fromisoformat(t["data"]).strftime("%Y-%m") == mes_key
            and t["tipo"] == "despesa"
        )
        
        meses_dados[mes_nome] = {
            "orcado": total_orcado,
            "realizado": total_gasto
        }
    
    # Inverter ordem para mostrar do mais antigo ao mais recente
    meses = list(reversed(list(meses_dados.keys())))
    orcados = [meses_dados[m]["orcado"] for m in meses]
    realizados = [meses_dados[m]["realizado"] for m in meses]
    
    # Criar gráfico
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=meses,
        y=orcados,
        name="Orçado",
        marker_color="#1e3a8a",
        text=[f"R$ {v:,.0f}" for v in orcados],
        textposition='outside'
    ))
    
    fig.add_trace(go.Bar(
        x=meses,
        y=realizados,
        name="Realizado",
        marker_color="#f59e0b",
        text=[f"R$ {v:,.0f}" for v in realizados],
        textposition='outside'
    ))
    
    fig.update_layout(
        barmode='group',
        title="",
        xaxis_title="Mês",
        yaxis_title="Valor (R$)",
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(t=40, b=40, l=40, r=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(
            showgrid=True,
            gridcolor='#f1f5f9'
        )
    )
    
    st.plotly_chart(fig, width='stretch')
