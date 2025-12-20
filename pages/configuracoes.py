"""
Página de Configurações e Ferramentas
"""
import streamlit as st
from pathlib import Path
import sys

# Adicionar diretório raiz ao path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from services.database import db
from scripts.popular_banco import popular_dados_exemplo, limpar_dados


def get_user_id() -> str:
    """Retorna ID do usuário atual"""
    return st.session_state.get("user_id", "")


def render_configuracoes_page():
    """Renderiza página de configurações"""
    user_id = get_user_id()
    if not user_id:
        st.warning("Usuário não identificado")
        return
    
    st.header("⚙️ Configurações e Ferramentas")
    
    # --- Ferramentas de Desenvolvimento ---
    st.subheader("🛠️ Ferramentas de Desenvolvimento")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Popular Banco de Dados")
        st.markdown("""
        Adiciona dados de exemplo ao banco:
        - 12 categorias (receitas e despesas)
        - 8 orçamentos mensais
        - ~50 transações dos últimos 3 meses
        - Receitas e despesas variadas
        """)
        
        if st.button("🚀 Popular com Dados de Exemplo", type="primary", key="btn_popular"):
            with st.spinner("Populando banco de dados..."):
                try:
                    popular_dados_exemplo(user_id)
                    st.success("✅ Banco populado com sucesso!")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Erro ao popular banco: {str(e)}")
    
    with col2:
        st.markdown("### 🗑️ Limpar Banco de Dados")
        st.markdown("""
        Remove todos os seus dados:
        - ⚠️ **AÇÃO IRREVERSÍVEL**
        - Todas as transações
        - Todos os orçamentos
        - Todas as categorias
        """)
        
        # Checkbox de confirmação
        confirmar = st.checkbox("Confirmo que quero deletar TODOS os dados", key="confirm_delete")
        
        if st.button(
            "🗑️ Limpar Todos os Dados", 
            type="secondary",
            disabled=not confirmar,
            key="btn_limpar"
        ):
            with st.spinner("Limpando banco de dados..."):
                try:
                    limpar_dados(user_id)
                    st.success("✅ Dados limpos com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao limpar banco: {str(e)}")
    
    st.divider()
    
    # --- Estatísticas ---
    st.subheader("📈 Estatísticas do Banco")
    
    transacoes = db.listar_transacoes(user_id)
    categorias = db.listar_categorias(user_id)
    orcamentos = db.listar_orcamentos(user_id)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Transações", len(transacoes))
    
    with col2:
        st.metric("Categorias", len(categorias))
    
    with col3:
        st.metric("Orçamentos", len(orcamentos))
    
    with col4:
        receitas = sum(1 for t in transacoes if t["tipo"] == "receita")
        st.metric("Receitas", receitas)
