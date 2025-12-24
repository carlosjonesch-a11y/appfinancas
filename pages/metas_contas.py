"""Página de gerenciamento de metas, tetos de gasto e contas a pagar/receber."""

import streamlit as st
from datetime import date, datetime
from typing import List, Dict, Optional

from services.database import db
from config import Config


def get_user_id() -> str:
    """Retorna ID do usuário atual"""
    return st.session_state.get("user_id", "")


def _format_brl(value: float) -> str:
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def render_metas_contas_page():
    """Página principal de metas e contas."""
    user_id = get_user_id()
    if not user_id:
        st.warning("Usuário não identificado")
        return

    st.header("🎯 Metas e Contas")
    
    tab1, tab2, tab3 = st.tabs(["💰 Tetos de Gastos", "📊 Metas", "📋 Contas a Pagar/Receber"])
    
    with tab1:
        render_tetos_gastos(user_id)
    
    with tab2:
        render_metas(user_id)
    
    with tab3:
        render_contas_pagaveis(user_id)


def render_tetos_gastos(user_id: str):
    """Renderiza seção de tetos de gastos."""
    st.subheader("💰 Tetos de Gastos")
    st.caption("Defina um limite de gasto por categoria para o mês")
    
    # Mês de referência
    mes_ref = st.date_input(
        "Mês de referência",
        value=date.today().replace(day=1),
        key="teto_ref_mes",
    )
    
    # Formulário para novo teto
    with st.expander("➕ Novo Teto de Gasto", expanded=False):
        with st.form("form_novo_teto"):
            col1, col2 = st.columns(2)
            
            with col1:
                categorias = db.listar_categorias(user_id, tipo="despesa")
                cat_options = {c["nome"]: c["id"] for c in categorias}
                categoria_nome = st.selectbox("Categoria", options=list(cat_options.keys()), key="teto_categoria")
                categoria_id = cat_options.get(categoria_nome)
            
            with col2:
                valor_limite = st.number_input("Valor Limite", min_value=0.0, step=10.0, key="teto_valor")
            
            if st.form_submit_button("Criar Teto", use_container_width=True):
                if categoria_id and valor_limite > 0:
                    resultado = db.criar_meta(
                        user_id=user_id,
                        nome=f"Teto - {categoria_nome}",
                        tipo="teto",
                        mes=mes_ref,
                        valor_limite=valor_limite,
                        categoria_id=categoria_id
                    )
                    if resultado:
                        st.success(f"Teto para {categoria_nome} criado!")
                        st.rerun()
                    else:
                        st.error("Erro ao criar teto")
                else:
                    st.warning("Preencha todos os campos")
    
    # Listar tetos do mês
    tetos = db.listar_metas(user_id, mes=mes_ref)
    tetos = [t for t in tetos if t.get("tipo") == "teto"]
    
    if tetos:
        st.markdown("### Tetos do Mês")
        
        for teto in tetos:
            col1, col2, col3 = st.columns([2, 2, 1])
            
            categoria_info = teto.get("categoria", {})
            if isinstance(categoria_info, str):
                nome_cat = categoria_info
            else:
                nome_cat = categoria_info.get("nome", "Sem categoria") if isinstance(categoria_info, dict) else "Sem categoria"
            
            limite = float(teto.get("valor_limite", 0))
            gasto = float(teto.get("gasto_realizado", 0))
            percentual = (gasto / limite * 100) if limite > 0 else 0
            
            with col1:
                st.metric(f"🏷️ {nome_cat}", _format_brl(limite))
            
            with col2:
                cor = "🔴" if percentual > 100 else ("🟡" if percentual > 80 else "🟢")
                st.metric(f"{cor} Gasto", f"{percentual:.1f}%", _format_brl(gasto))
            
            with col3:
                if st.button("🗑️", key=f"del_teto_{teto['id']}"):
                    if db.deletar_meta(teto["id"]):
                        st.success("Teto removido!")
                        st.rerun()
    else:
        st.info("Nenhum teto definido para este mês")


def render_metas(user_id: str):
    """Renderiza seção de metas."""
    st.subheader("📊 Metas de Economia")
    st.caption("Defina metas de economia para acompanhar seu progresso")
    
    # Mês de referência
    mes_ref = st.date_input(
        "Mês de referência",
        value=date.today().replace(day=1),
        key="meta_ref_mes",
    )
    
    # Formulário para nova meta
    with st.expander("➕ Nova Meta", expanded=False):
        with st.form("form_nova_meta"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                nome = st.text_input("Nome da Meta", key="meta_nome")
            
            with col2:
                valor_alvo = st.number_input("Valor Alvo", min_value=0.0, step=10.0, key="meta_valor")
            
            with col3:
                descricao = st.text_input("Descrição (opcional)", key="meta_descricao")
            
            if st.form_submit_button("Criar Meta", use_container_width=True):
                if nome and valor_alvo > 0:
                    resultado = db.criar_meta(
                        user_id=user_id,
                        nome=nome,
                        tipo="meta",
                        mes=mes_ref,
                        valor_limite=valor_alvo,
                        descricao=descricao
                    )
                    if resultado:
                        st.success(f"Meta '{nome}' criada!")
                        st.rerun()
                    else:
                        st.error("Erro ao criar meta")
                else:
                    st.warning("Preencha nome e valor")
    
    # Listar metas do mês
    metas = db.listar_metas(user_id, mes=mes_ref)
    metas = [m for m in metas if m.get("tipo") == "meta"]
    
    if metas:
        st.markdown("### Metas do Mês")
        
        for meta in metas:
            col1, col2, col3 = st.columns([2, 2, 1])
            
            alvo = float(meta.get("valor_limite", 0))
            alcançado = float(meta.get("gasto_realizado", 0))
            percentual = (alcançado / alvo * 100) if alvo > 0 else 0
            
            with col1:
                st.metric(f"🎯 {meta['nome']}", _format_brl(alvo))
            
            with col2:
                cor = "🟢" if percentual <= 100 else "🔴"
                st.metric(f"{cor} Alcançado", f"{percentual:.1f}%", _format_brl(alcançado))
            
            with col3:
                if st.button("🗑️", key=f"del_meta_{meta['id']}"):
                    if db.deletar_meta(meta["id"]):
                        st.success("Meta removida!")
                        st.rerun()
    else:
        st.info("Nenhuma meta definida para este mês")


def render_contas_pagaveis(user_id: str):
    """Renderiza seção de contas a pagar/receber."""
    st.subheader("📋 Contas a Pagar/Receber")
    st.caption("Acompanhe seus compromissos financeiros")
    
    # Abas para pagar e receber
    tab_pagar, tab_receber = st.tabs(["💸 A Pagar", "💰 A Receber"])
    
    with tab_pagar:
        render_contas_tipo(user_id, "pagar")
    
    with tab_receber:
        render_contas_tipo(user_id, "receber")


def render_contas_tipo(user_id: str, tipo: str):
    """Renderiza contas de um tipo específico."""
    tipo_label = "Pagar" if tipo == "pagar" else "Receber"
    icon = "💸" if tipo == "pagar" else "💰"
    
    # Formulário para nova conta
    with st.expander(f"➕ Nova Conta a {tipo_label}", expanded=False):
        with st.form(f"form_nova_conta_{tipo}"):
            col1, col2 = st.columns(2)
            
            with col1:
                descricao = st.text_input("Descrição", key=f"conta_desc_{tipo}")
                valor = st.number_input("Valor", min_value=0.0, step=0.01, key=f"conta_valor_{tipo}")
            
            with col2:
                data_vencimento = st.date_input("Data de Vencimento", key=f"conta_venc_{tipo}")
                categorias = db.listar_categorias(user_id)
                cat_options = {c["nome"]: c["id"] for c in categorias}
                categoria_nome = st.selectbox("Categoria (opcional)", options=["Sem categoria"] + list(cat_options.keys()), key=f"conta_cat_{tipo}")
            
            categoria_id = cat_options.get(categoria_nome) if categoria_nome != "Sem categoria" else None
            
            if st.form_submit_button(f"Criar Conta a {tipo_label}", use_container_width=True):
                if descricao and valor > 0:
                    resultado = db.criar_conta_pagavel(
                        user_id=user_id,
                        descricao=descricao,
                        valor=valor,
                        tipo=tipo,
                        data_vencimento=data_vencimento,
                        categoria_id=categoria_id
                    )
                    if resultado:
                        st.success(f"Conta a {tipo_label} criada!")
                        st.rerun()
                    else:
                        st.error("Erro ao criar conta")
                else:
                    st.warning("Preencha descrição e valor")
    
    # Listar contas não pagas
    contas = db.listar_contas_pagaveis(user_id, tipo=tipo, pago=False)
    
    if contas:
        st.markdown(f"### Contas a {tipo_label} (Pendentes)")
        
        for conta in contas:
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                st.write(f"📌 **{conta['descricao']}**")
            
            with col2:
                st.metric("Valor", _format_brl(float(conta['valor'])))
            
            with col3:
                venc = conta.get("data_vencimento")
                if venc:
                    venc_date = datetime.fromisoformat(venc).date() if isinstance(venc, str) else venc
                    dias = (venc_date - date.today()).days
                    cor = "🔴" if dias < 0 else ("🟡" if dias <= 3 else "🟢")
                    st.metric("Vencimento", f"{cor} {venc_date.strftime('%d/%m')}")
            
            with col4:
                if st.button("✅ Pago", key=f"pagar_{conta['id']}"):
                    if db.marcar_conta_como_paga(conta["id"], data_pagamento=date.today()):
                        st.success("Conta marcada como paga!")
                        st.rerun()
    
    # Listar contas pagas
    contas_pagas = db.listar_contas_pagaveis(user_id, tipo=tipo, pago=True)
    
    if contas_pagas:
        with st.expander(f"✅ Contas {tipo_label} (Realizadas)", expanded=False):
            for conta in contas_pagas:
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"✓ {conta['descricao']}")
                
                with col2:
                    st.metric("Valor", _format_brl(float(conta['valor'])))
                
                with col3:
                    if st.button("🗑️", key=f"del_conta_{conta['id']}"):
                        if db.deletar_conta_pagavel(conta["id"]):
                            st.success("Conta removida!")
                            st.rerun()
