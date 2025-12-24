"""
Página de gerenciamento de categorias
"""
import streamlit as st
from typing import List, Dict

from services.database import db
from config import Config


def get_user_id() -> str:
    """Retorna ID do usuário atual"""
    return st.session_state.get("user_id", "")


def render_categorias_page():
    """Página de gerenciamento de categorias"""
    
    user_id = get_user_id()
    if not user_id:
        st.warning("Usuário não identificado")
        return
    
    st.header("🏷️ Categorias")
    
    # Tabs para receitas e despesas
    tab1, tab2 = st.tabs(["💸 Despesas", "💰 Receitas"])
    
    with tab1:
        render_lista_categorias(user_id, "despesa")
    
    with tab2:
        render_lista_categorias(user_id, "receita")


def render_lista_categorias(user_id: str, tipo: str):
    """Renderiza lista de categorias por tipo"""
    
    categorias = db.listar_categorias(user_id, tipo=tipo)
    
    # Formulário para nova categoria
    with st.expander("➕ Adicionar Nova Categoria", expanded=False):
        with st.form(f"form_nova_cat_{tipo}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                nome = st.text_input("Nome da categoria", key=f"nova_cat_nome_{tipo}")
            
            with col2:
                icone = st.text_input("Ícone (emoji)", value="📦", key=f"nova_cat_icone_{tipo}")
            
            if st.form_submit_button("Adicionar", width='stretch'):
                if nome:
                    resultado = db.criar_categoria(user_id, nome, tipo, icone)
                    if resultado:
                        st.success(f"Categoria '{nome}' criada!")
                        st.rerun()
                    else:
                        st.error(f"Categoria '{nome}' já existe neste tipo!")
                else:
                    st.warning("Digite o nome da categoria")
    
    # Lista de categorias existentes
    if categorias:
        st.markdown("### Categorias Existentes")
        
        for cat in categorias:
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.write(f"{cat.get('icone', '📦')} {cat['nome']}")
            
            with col2:
                # Botão de excluir
                if st.button("🗑️", key=f"del_cat_{cat['id']}_{tipo}"):
                    if db.deletar_categoria(cat['id']):
                        st.success("Categoria removida!")
                        st.rerun()
                    else:
                        st.error("Erro ao remover")
    else:
        st.info("Nenhuma categoria cadastrada.")
        
        # Botão para criar categorias padrão
        if st.button(f"Criar categorias padrão de {tipo}s", key=f"criar_padrao_{tipo}"):
            criar_categorias_padrao(user_id, tipo)


def criar_categorias_padrao(user_id: str, tipo: str):
    """Cria categorias padrão para o usuário"""
    
    tipo_key = "receitas" if tipo == "receita" else "despesas"
    categorias_padrao = Config.CATEGORIAS_PADRAO.get(tipo_key, [])
    
    criadas = 0
    for cat in categorias_padrao:
        resultado = db.criar_categoria(
            user_id=user_id,
            nome=cat["nome"],
            tipo=tipo,
            icone=cat["icone"]
        )
        if resultado:
            criadas += 1
    
    if criadas > 0:
        st.success(f"{criadas} categorias criadas!")
        st.rerun()
    else:
        st.warning("Não foi possível criar as categorias")
