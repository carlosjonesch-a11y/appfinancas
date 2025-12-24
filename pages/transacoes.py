"""
Páginas do aplicativo Streamlit - Transações e Lançamentos
"""
import streamlit as st
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import pandas as pd

from services.database import db
from services.ocr import ocr, CupomExtraido, ItemExtraido
from services.qrcode import qrcode_service, DadosNFCe
from config import Config


def formatar_data_br(data_str: str) -> str:
    """Converte data ISO (YYYY-MM-DD) para formato brasileiro (DD/MM/YYYY)"""
    if not data_str or data_str == "N/A":
        return "N/A"
    try:
        data_obj = datetime.fromisoformat(data_str).date()
        return data_obj.strftime("%d/%m/%Y")
    except:
        return data_str


def get_user_id() -> str:
    """Retorna ID do usuário atual"""
    return st.session_state.get("user_id", "")


def render_transacoes_page():
    """Página de listagem e gerenciamento de transações"""
    st.header("📋 Transações")
    
    user_id = get_user_id()
    if not user_id:
        st.warning("Usuário não identificado")
        return
    
    # Filtros
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        data_inicio = st.date_input(
            "Data inicial",
            value=date.today().replace(day=1),
            key="filtro_data_inicio"
        )
    
    with col2:
        data_fim = st.date_input(
            "Data final",
            value=date.today(),
            key="filtro_data_fim"
        )
    
    with col3:
        tipo_filtro = st.selectbox(
            "Tipo",
            options=["Todos", "Receitas", "Despesas"],
            key="filtro_tipo"
        )
    
    with col4:
        categorias = db.listar_categorias(user_id)
        cat_options = ["Todas"] + [c["nome"] for c in categorias]
        cat_filtro = st.selectbox(
            "Categoria",
            options=cat_options,
            key="filtro_categoria"
        )

    with col5:
        contas = db.listar_contas(user_id)
        conta_options = ["Todas"] + [c["nome"] for c in contas]
        conta_filtro = st.selectbox(
            "Conta",
            options=conta_options,
            key="filtro_conta"
        )
    
    # Buscar transações
    tipo_param = None
    if tipo_filtro == "Receitas":
        tipo_param = "receita"
    elif tipo_filtro == "Despesas":
        tipo_param = "despesa"
    
    cat_id = None
    if cat_filtro != "Todas":
        cat_match = next((c for c in categorias if c["nome"] == cat_filtro), None)
        if cat_match:
            cat_id = cat_match["id"]

    conta_id = None
    if conta_filtro != "Todas":
        conta_match = next((c for c in contas if c["nome"] == conta_filtro), None)
        if conta_match:
            conta_id = conta_match["id"]
    
    transacoes = db.listar_transacoes(
        user_id=user_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tipo=tipo_param,
        categoria_id=cat_id,
        conta_id=conta_id
    )

    st.markdown("---")

    # Provisões do mês (previstas) + marcar como aconteceu
    with st.expander("🗓️ Provisões (previstas) do mês"):
        hoje = date.today()
        inicio_mes = hoje.replace(day=1)
        previstas = db.listar_transacoes(
            user_id=user_id,
            data_inicio=inicio_mes,
            data_fim=hoje.replace(day=28) + timedelta(days=4),
            limite=500,
            incluir_previstas=True,
        )
        previstas = [t for t in previstas if t.get("status") == "prevista"]

        if not previstas:
            st.info("Sem transações previstas no mês. Use Configurações → Fixas do mês → Gerar previstas.")
        else:
            for t in previstas[:50]:
                col_a, col_b, col_c = st.columns([3, 1, 1])
                with col_a:
                    conta_nome = (t.get("contas") or {}).get("nome") if isinstance(t.get("contas"), dict) else ""
                    cat_nome = (t.get("categorias") or {}).get("nome") if isinstance(t.get("categorias"), dict) else ""
                    st.write(f"{t.get('data')} — {t.get('descricao')} ({cat_nome}) [{conta_nome}]")
                with col_b:
                    st.write(f"R$ {float(t.get('valor') or 0):.2f}")
                with col_c:
                    if st.button("Aconteceu", key=f"btn_aconteceu_{t.get('id')}"):
                        criada = db.criar_real_a_partir_da_prevista(t.get("id"))
                        if criada:
                            st.success("✅ Marcado como realizado")
                            st.rerun()
                        else:
                            st.error("❌ Não foi possível marcar")
    
    # Exibir transações
    if not transacoes:
        st.info("Nenhuma transação encontrada para o período selecionado.")
        return
    
    # Converter para DataFrame
    df = pd.DataFrame(transacoes)
    
    # Formatar colunas
    df["data"] = pd.to_datetime(df["data"]).dt.strftime("%d/%m/%Y")
    df["valor_formatado"] = df.apply(
        lambda x: f"{'+ ' if x['tipo'] == 'receita' else '- '}R$ {x['valor']:.2f}",
        axis=1
    )
    df["categoria_nome"] = df["categorias"].apply(
        lambda x: f"{x.get('icone', '📦')} {x.get('nome', 'Sem categoria')}" if x else "📦 Sem categoria"
    )
    
    # Tabela de transações
    st.dataframe(
        df[["data", "descricao", "categoria_nome", "valor_formatado", "modo_lancamento"]].rename(columns={
            "data": "Data",
            "descricao": "Descrição",
            "categoria_nome": "Categoria",
            "valor_formatado": "Valor",
            "modo_lancamento": "Modo"
        }),
        width='stretch',
        hide_index=True
    )
    
    # Totais
    total_receitas = df[df["tipo"] == "receita"]["valor"].sum()
    total_despesas = df[df["tipo"] == "despesa"]["valor"].sum()
    saldo = total_receitas - total_despesas
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Receitas", f"R$ {total_receitas:.2f}", delta=None)
    with col2:
        st.metric("Despesas", f"R$ {total_despesas:.2f}", delta=None)
    with col3:
        st.metric("Saldo", f"R$ {saldo:.2f}", delta=f"{saldo:.2f}")


def render_nova_transacao_page():
    """Página de lançamento de contas a pagar/receber"""
    st.header("💳 Contas")
    st.caption("Registre contas a pagar ou receber com método de pagamento")
    
    user_id = get_user_id()
    if not user_id:
        st.warning("Usuário não identificado")
        return
    
    # Tabs para tipo de lançamento
    tab1, tab2 = st.tabs(["📝 Manual", "📸 Escanear Cupom"])
    
    with tab1:
        render_lancamento_manual(user_id)
    
    with tab2:
        render_lancamento_cupom(user_id)


def render_lancamento_manual(user_id: str):
    """Formulário de lançamento de contas a pagar/receber"""

    # Tipo de conta (Pagar ou Receber)
    col_tipo, col_data = st.columns(2)
    with col_tipo:
        tipo = st.selectbox(
            "Tipo",
            options=["Pagar", "Receber"],
            key="manual_tipo"
        )
    tipo_conta = "pagar" if tipo == "Pagar" else "receber"

    with st.form("form_transacao_manual"):
        with col_data:
            data_vencimento = st.date_input(
                "Data de Vencimento",
                value=date.today(),
                key="manual_data"
            )

        descricao = st.text_input("Descrição", key="manual_descricao")

        col1, col2 = st.columns(2)

        with col1:
            valor = st.number_input(
                "Valor (R$)",
                min_value=0.01,
                step=0.01,
                format="%.2f",
                key="manual_valor"
            )

        with col2:
            tipo_pagamento_options = ["Cartão", "Pix", "Débito", "Dinheiro", "Transferência", "Outro"]
            tipo_pagamento_label = st.selectbox(
                "Método de Pagamento",
                options=tipo_pagamento_options,
                key="manual_tipo_pag",
            )
            tipo_pagamento_map = {
                "Cartão": "cartao",
                "Pix": "pix",
                "Débito": "debito",
                "Dinheiro": "dinheiro",
                "Transferência": "transferencia",
                "Outro": "outro"
            }
            tipo_pagamento = tipo_pagamento_map.get(tipo_pagamento_label, "outro")

        # Categoria (apenas despesas)
        if tipo_conta == "pagar":
            categorias = db.listar_categorias(user_id, tipo="despesa")
            cat_options = {f"{c['icone']} {c['nome']}": c["id"] for c in categorias}
            options = list(cat_options.keys()) if cat_options else ["Sem categoria"]

            if "manual_categoria" in st.session_state and st.session_state["manual_categoria"] not in options:
                del st.session_state["manual_categoria"]

            categoria_selecionada = st.selectbox(
                "Categoria",
                options=options,
                key="manual_categoria"
            )
        else:
            cat_options = {}
            categoria_selecionada = None

        observacao = st.text_area("Observação (opcional)", key="manual_obs")

        # Opção de recorrência
        st.divider()
        st.markdown("### 🔄 Configuração de Recorrência")
        recorrente = st.checkbox("Cadastrar como recorrente", key="manual_recorrente", value=False)

        # Sempre mostrar as opções para evitar timing issues
        periodo_opcao = st.selectbox(
            "Período de recorrência",
            options=["Próximos 12 meses", "Período personalizado"],
            key="manual_periodo",
            disabled=not recorrente
        )

        if periodo_opcao == "Período personalizado":
            col_data_inicio, col_data_fim = st.columns(2)
            with col_data_inicio:
                data_inicio_rec = st.date_input(
                    "Data início",
                    value=data_vencimento,
                    key="manual_data_inicio_rec",
                    disabled=not recorrente
                )
            with col_data_fim:
                data_fim_rec = st.date_input(
                    "Data fim",
                    value=data_vencimento.replace(year=data_vencimento.year + 1),
                    key="manual_data_fim_rec",
                    disabled=not recorrente
                )
        else:
            data_inicio_rec = data_vencimento
            data_fim_rec = data_vencimento.replace(year=data_vencimento.year + 1)

        submitted = st.form_submit_button("💾 Salvar Conta", width='stretch')
    
    if submitted:
        if not descricao:
            st.error("Descrição é obrigatória")
            return

        categoria_id = cat_options.get(categoria_selecionada) if cat_options and categoria_selecionada else None

        # Se for recorrente, criar múltiplas contas
        if recorrente:
            from dateutil.relativedelta import relativedelta

            contas_criadas = 0
            data_atual = data_inicio_rec

            while data_atual <= data_fim_rec:
                resultado = db.criar_conta_pagavel(
                    user_id=user_id,
                    descricao=descricao,
                    valor=valor,
                    tipo=tipo_conta,
                    data_vencimento=data_atual,
                    categoria_id=categoria_id,
                    tipo_pagamento=tipo_pagamento
                )

                if resultado:
                    contas_criadas += 1
                else:
                    st.error(f"Erro ao criar conta para {data_atual.strftime('%d/%m/%Y')}")
                    break

                # Próximo mês
                data_atual += relativedelta(months=1)

            if contas_criadas > 0:
                st.success(f"✅ {contas_criadas} contas recorrentes criadas com sucesso!")
                st.balloons()
        else:
            # Criar conta única
            resultado = db.criar_conta_pagavel(
                user_id=user_id,
                descricao=descricao,
                valor=valor,
                tipo=tipo_conta,
                data_vencimento=data_vencimento,
                categoria_id=categoria_id,
                tipo_pagamento=tipo_pagamento
            )

            if resultado:
                st.success(f"✅ Conta a {tipo.lower()} criada com sucesso!")
                st.balloons()

        # Limpar dados do formulário
        for key in [
            "manual_tipo",
            "manual_data",
            "manual_descricao",
            "manual_valor",
            "manual_tipo_pag",
            "manual_categoria",
            "manual_obs",
            "manual_recorrente",
            "manual_periodo",
            "manual_data_inicio_rec",
            "manual_data_fim_rec"
        ]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    # Seção de Gerenciamento de Contas
    st.divider()
    st.subheader("📋 Suas Contas")
    
    # Abas para Pendentes, Pagas e Recebidas
    tab_pendentes, tab_pagas, tab_recebidas = st.tabs(["⏳ Pendentes", "✅ Pagas", "💰 Recebidas"])
    
    with tab_pendentes:
        render_gerenciar_contas(user_id, pago=False, tab_name="pendentes")
    
    with tab_pagas:
        render_gerenciar_contas(user_id, tipo="pagar", pago=True, tab_name="pagas")
    
    with tab_recebidas:
        render_gerenciar_contas(user_id, tipo="receber", pago=True, tab_name="recebidas")


def render_gerenciar_contas(user_id: str, tipo: str | None = None, pago: bool = False, tab_name: str = "default"):
    """Gerencia contas a pagar/receber com interface linha por linha"""
    
    contas = db.listar_contas_pagaveis(user_id, tipo=tipo, pago=pago)

    if not contas:
        st.info("Nenhuma conta registrada")
        return

    # Filtros de data - mais compacto
    st.markdown("### 🔍 Filtrar por período")
    col_mes, col_ano, col_limpar = st.columns([1.5, 1.5, 1])
    
    with col_mes:
        mes_filtro = st.selectbox(
            "Mês",
            options=list(range(1, 13)),
            format_func=lambda x: ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"][x-1],
            key=f"filtro_mes_{tab_name}",
            label_visibility="collapsed"
        )
    
    with col_ano:
        ano_filtro = st.number_input(
            "Ano",
            min_value=2020,
            max_value=2050,
            value=date.today().year,
            key=f"filtro_ano_{tab_name}",
            label_visibility="collapsed"
        )
    
    with col_limpar:
        if st.button("🔄", use_container_width=True, key=f"limpar_filtro_{tab_name}", help="Limpar filtros"):
            st.session_state.pop(f"filtro_mes_{tab_name}", None)
            st.session_state.pop(f"filtro_ano_{tab_name}", None)
            st.rerun()
    
    # Filtrar contas por mês/ano
    contas_filtradas = []
    for conta in contas:
        data_venc = conta.get("data_vencimento", "")
        if data_venc:
            try:
                from datetime import datetime
                data_obj = datetime.fromisoformat(data_venc).date()
                if data_obj.month == mes_filtro and data_obj.year == ano_filtro:
                    contas_filtradas.append(conta)
            except:
                pass
    
    if not contas_filtradas:
        mes_nomes = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        st.warning(f"📭 Nenhuma conta para {mes_nomes[mes_filtro-1]}/{int(ano_filtro)}")
        return

    st.markdown("---")

    pag_display = {
        "cartao": "💳 Cartão",
        "pix": "📱 Pix",
        "debito": "💰 Débito",
        "dinheiro": "💵 Dinheiro",
        "transferencia": "🏦 Transferência",
        "outro": "❓ Outro"
    }

    # Exibir cada conta em uma linha com ações
    for idx, conta in enumerate(contas_filtradas):
        cat_nome = "Sem categoria"
        if conta.get("categoria_id"):
            cat = db.buscar_categoria(conta["categoria_id"])
            if cat:
                cat_nome = cat.get("nome", "Sem categoria")

        tipo_icon = "💳" if conta.get("tipo") == "pagar" else "💰"
        status_icon = "✅" if conta.get("pago", False) else "⏳"
        pago_classe = "bg-green-50" if conta.get("pago", False) else "bg-orange-50"
        
        # Container para cada conta com CSS melhorado
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2.5, 1.2, 1.2, 1.5, 1.5], gap="small")

            with col1:
                st.markdown(f"<span style='font-size: 16px; font-weight: 600; color: #1e40af;'>{tipo_icon} {conta['descricao'][:30]}</span>", unsafe_allow_html=True)
                st.caption(f"📁 {cat_nome}")

            with col2:
                valor_display = f"R$ {float(conta.get('valor', 0)):.2f}"
                st.markdown(f"<span style='font-size: 15px; font-weight: 600; color: #059669;'>{valor_display}</span>", unsafe_allow_html=True)
                st.caption("Valor")

            with col3:
                data_venc_br = formatar_data_br(conta.get('data_vencimento', 'N/A'))
                st.markdown(f"<span style='font-size: 15px; font-weight: 600; color: #d97706;'>{data_venc_br}</span>", unsafe_allow_html=True)
                st.caption("Vence em")

            with col4:
                tipo_display = pag_display.get(conta.get('tipo_pagamento', ''), 'Outro')
                status_display = f"{status_icon} {'Paga' if conta.get('pago', False) else 'Pendente'}"
                st.markdown(f"<span style='font-size: 14px;'>{tipo_display}</span>", unsafe_allow_html=True)
                status_color = "#059669" if conta.get('pago', False) else "#dc2626"
                st.markdown(f"<span style='font-size: 14px; font-weight: 600; color: {status_color};'>{status_display}</span>", unsafe_allow_html=True)

            with col5:
                col_a1, col_a2, col_a3 = st.columns(3, gap="small")
                with col_a1:
                    if pago:
                        if st.button("↩️", key=f"pendente_{idx}_{conta['id']}", help="Voltar para pendente", use_container_width=True):
                            db.marcar_conta_como_pendente(conta["id"])
                            st.rerun()
                    else:
                        if st.button("✓", key=f"pago_{idx}_{conta['id']}", help="Marcar como paga", use_container_width=True):
                            db.marcar_conta_como_paga(conta["id"], date.today())
                            st.rerun()
                with col_a2:
                    if st.button("🗑️", key=f"delete_{idx}_{conta['id']}", help="Excluir", use_container_width=True):
                        db.deletar_conta_pagavel(conta["id"])
                        st.success("✅ Excluído!")
                        st.rerun()
                with col_a3:
                    if st.button("✏️", key=f"edit_{idx}_{conta['id']}", help="Editar", use_container_width=True):
                        st.session_state[f"edit_conta_{conta['id']}"] = not st.session_state.get(f"edit_conta_{conta['id']}", False)
                        st.rerun()

        # Seção de edição
        if st.session_state.get(f"edit_conta_{conta['id']}", False):
            with st.expander(f"✏️ Editar: {conta['descricao']}", expanded=True):
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    new_desc = st.text_input("Descrição", value=conta.get("descricao", ""), key=f"desc_{conta['id']}")
                
                with col_b:
                    new_val = st.number_input("Valor", value=float(conta.get("valor", 0)), min_value=0.01, step=0.01, key=f"val_{conta['id']}")
                
                with col_c:
                    tipo_opts = ["Cartão", "Pix", "Débito", "Dinheiro", "Transferência", "Outro"]
                    current = {"cartao": "Cartão", "pix": "Pix", "debito": "Débito", "dinheiro": "Dinheiro", "transferencia": "Transferência", "outro": "Outro"}.get(conta.get("tipo_pagamento", "outro"), "Outro")
                    new_tipo = st.selectbox("Tipo", tipo_opts, index=tipo_opts.index(current), key=f"tipo_{conta['id']}")
                
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("💾 Salvar", key=f"save_{conta['id']}", use_container_width=True):
                        tipo_map = {"Cartão": "cartao", "Pix": "pix", "Débito": "debito", "Dinheiro": "dinheiro", "Transferência": "transferencia", "Outro": "outro"}
                        db.atualizar_conta_pagavel(conta["id"], {"descricao": new_desc, "valor": new_val, "tipo_pagamento": tipo_map[new_tipo]})
                        st.session_state[f"edit_conta_{conta['id']}"] = False
                        st.success("✅ Atualizado!")
                        st.rerun()
                with col_cancel:
                    if st.button("❌ Fechar", key=f"cancel_{conta['id']}", use_container_width=True):
                        st.session_state[f"edit_conta_{conta['id']}"] = False
                        st.rerun()
        
        st.divider()


def render_lancamento_cupom(user_id: str):
    """Interface para escanear e processar cupom fiscal"""
    
    # Verificar se estamos no modo de revisão (QR Code)
    if "cupom_processado" in st.session_state:
        dados_salvos = st.session_state["cupom_processado"]
        modo_auto_salvo = st.session_state.get("cupom_modo_auto", False)
        
        if modo_auto_salvo:
            # Modo automático já salvou, mostrar confirmação
            st.success("✅ Cupom processado e salvo automaticamente!")
            if st.button("📸 Processar novo cupom", width='stretch'):
                # Limpar todo o estado
                for key in list(st.session_state.keys()):
                    if key.startswith("cupom_"):
                        del st.session_state[key]
                st.rerun()
        else:
            # Modo semi-automático, mostrar interface de revisão
            render_revisao_itens_qrcode(user_id, dados_salvos)
        return
    
    # Verificar se estamos no modo de revisão (OCR)
    if "cupom_processado_ocr" in st.session_state:
        dados_salvos = st.session_state["cupom_processado_ocr"]
        render_revisao_itens_ocr(user_id, dados_salvos)
        return
    
    # Tela de upload
    st.markdown("""
    📸 **Faça upload da foto do cupom fiscal**
    
    🎯 **Método recomendado:** O app lê o **QR Code** do cupom e busca os dados oficiais direto da SEFAZ!
    
    Para melhores resultados:
    - Certifique-se que o **QR Code** está visível e nítido
    - Boa iluminação ajuda na leitura
    - Se o QR Code falhar, o OCR será usado como fallback
    """)
    
    # Upload de imagem
    uploaded_file = st.file_uploader(
        "Selecione a imagem do cupom",
        type=["jpg", "jpeg", "png", "webp"],
        key="cupom_upload"
    )
    
    # Método de leitura
    metodo = st.radio(
        "Método de leitura",
        options=["🎯 QR Code (Recomendado)", "📝 OCR (Texto da imagem)"],
        key="metodo_leitura",
        horizontal=True
    )
    usar_qrcode = "QR Code" in metodo
    
    # Modo de lançamento
    modo = st.radio(
        "Modo de lançamento",
        options=["Semi-automático (revisar antes de salvar)", "Automático (salvar direto)"],
        key="modo_lancamento"
    )
    modo_auto = "Automático" in modo
    
    if uploaded_file is not None:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.image(uploaded_file, caption="Cupom enviado", width=300)
        
        with col2:
            if st.button("🔍 Processar Cupom", width='stretch', type="primary"):
                # Reset do arquivo para leitura
                uploaded_file.seek(0)
                image_bytes = uploaded_file.read()
                
                # Salvar modo
                st.session_state["cupom_modo_auto"] = modo_auto
                
                if usar_qrcode:
                    with st.spinner("📱 Lendo QR Code e buscando dados na SEFAZ..."):
                        processar_cupom_qrcode(user_id, image_bytes, modo_auto)
                else:
                    with st.spinner("🔍 Processando imagem com OCR..."):
                        processar_cupom_ocr(user_id, image_bytes, modo_auto)


def processar_cupom_qrcode(user_id: str, image_bytes: bytes, modo_automatico: bool):
    """Processa o cupom fiscal via QR Code - MÉTODO PRINCIPAL"""
    
    # Verificar se serviço está disponível
    if not qrcode_service.is_available:
        st.warning("⚠️ Leitor de QR Code não disponível. Tentando OCR...")
        processar_cupom_ocr(user_id, image_bytes, modo_automatico)
        return
    
    # Ler QR Code
    url = qrcode_service.ler_qrcode(image_bytes)
    
    if not url:
        st.warning("⚠️ QR Code não encontrado na imagem. Tentando OCR...")
        processar_cupom_ocr(user_id, image_bytes, modo_automatico)
        return
    
    st.success(f"✅ QR Code encontrado!")
    
    # Buscar dados na SEFAZ
    with st.spinner("🌐 Buscando dados na SEFAZ..."):
        dados = qrcode_service.extrair_dados_url(url)
    
    if not dados.sucesso:
        st.error(f"❌ Erro ao buscar dados: {dados.erro}")
        st.info("💡 Tentando OCR como alternativa...")
        processar_cupom_ocr(user_id, image_bytes, modo_automatico)
        return
    
    # Mostrar dados extraídos
    st.success("✅ Dados obtidos com sucesso da SEFAZ!")
    
    with st.expander("🔗 URL do QR Code"):
        st.code(url, language=None)
    
    # Informações do emitente
    st.subheader("📊 Dados Identificados")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Estabelecimento:** {dados.emitente_nome or 'Não identificado'}")
        st.write(f"**CNPJ:** {dados.emitente_cnpj or 'Não identificado'}")
    with col2:
        st.write(f"**Data:** {dados.data_emissao.strftime('%d/%m/%Y') if dados.data_emissao else 'Não identificada'}")
    
    if dados.forma_pagamento:
        st.write(f"**Forma de pagamento:** {dados.forma_pagamento}")
    
    st.divider()
    
    # Itens
    if dados.itens:
        st.subheader(f"🛒 Itens ({len(dados.itens)})")
        
        # Salvar dados no session_state para não perder após rerun
        st.session_state["cupom_processado"] = dados
        
        if modo_automatico:
            salvar_transacoes_qrcode_auto(user_id, dados)
        else:
            render_revisao_itens_qrcode(user_id, dados)
    else:
        st.warning("Nenhum item foi identificado.")
        
        # Permitir lançamento manual do total
        if dados.valor_total > 0:
            st.info("Você pode lançar o valor total como uma única transação.")
            render_lancamento_total_qrcode(user_id, dados)


def salvar_transacoes_qrcode_auto(user_id: str, dados: DadosNFCe):
    """Salva transações automaticamente a partir dos dados do QR Code"""
    
    categorias = db.listar_categorias(user_id, tipo="despesa")
    cat_map = {c["nome"]: c["id"] for c in categorias}
    
    # Encontrar categoria apropriada baseado no estabelecimento
    categoria_padrao = sugerir_categoria_estabelecimento(dados.emitente_nome)
    
    transacoes = []
    for item in dados.itens:
        # Sugerir categoria por item ou usar padrão do estabelecimento
        categoria_item = sugerir_categoria_item(item.descricao) or categoria_padrao
        
        transacao = {
            "user_id": user_id,
            "descricao": item.descricao[:200] if item.descricao else dados.emitente_nome,
            "valor": item.valor_total if item.valor_total > 0 else dados.valor_total / max(len(dados.itens), 1),
            "tipo": "despesa",
            "data": dados.data_emissao.isoformat() if dados.data_emissao else date.today().isoformat(),
            "categoria_id": cat_map.get(categoria_item),
            "observacao": f"NFCe: {dados.emitente_nome} | Chave: {dados.chave_acesso[:20]}..." if dados.chave_acesso else f"NFCe: {dados.emitente_nome}",
            "modo_lancamento": "automatico"
        }
        transacoes.append(transacao)
    
    if transacoes:
        resultado = db.criar_transacoes_em_lote(transacoes)
        if resultado:
            st.success(f"✅ {len(resultado)} transações salvas automaticamente!")
            st.balloons()
        else:
            st.error("Erro ao salvar transações")
    else:
        st.warning("Nenhuma transação para salvar")


def render_revisao_itens_qrcode(user_id: str, dados: DadosNFCe):
    """Interface para revisar itens do QR Code antes de salvar - IGUAL AO OCR"""
    
    categorias = db.listar_categorias(user_id, tipo="despesa")
    cat_options = ["Sem categoria"] + [f"{c['icone']} {c['nome']}" for c in categorias]
    cat_map = {f"{c['icone']} {c['nome']}": c["id"] for c in categorias}
    
    # Categoria padrão baseada no estabelecimento
    categoria_padrao = sugerir_categoria_estabelecimento(dados.emitente_nome)
    
    # Armazenar itens em sessão para edição
    if "itens_cupom_editados_qr" not in st.session_state:
        st.session_state.itens_cupom_editados_qr = []
        for item in dados.itens:
            # Sugerir categoria
            cat_sugerida = sugerir_categoria_item(item.descricao) or categoria_padrao
            
            st.session_state.itens_cupom_editados_qr.append({
                "descricao": item.descricao[:100] if item.descricao else "Item sem nome",
                "valor": item.valor_total,
                "categoria": cat_sugerida,
                "incluir": True
            })
    
    # Formulário de edição
    st.markdown("### ✏️ Revise os itens antes de salvar")
    
    itens_para_salvar = []
    
    for i, item in enumerate(st.session_state.itens_cupom_editados_qr):
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                desc = st.text_input(
                    "Descrição",
                    value=item["descricao"],
                    key=f"item_desc_qr_{i}",
                    label_visibility="collapsed"
                )
            
            with col2:
                valor = st.number_input(
                    "Valor",
                    value=float(item["valor"]),
                    min_value=0.01,
                    step=0.01,
                    format="%.2f",
                    key=f"item_valor_qr_{i}",
                    label_visibility="collapsed"
                )
            
            with col3:
                # Encontrar categoria sugerida
                cat_default = "Sem categoria"
                for cat in categorias:
                    if cat["nome"] == item["categoria"]:
                        cat_default = f"{cat['icone']} {cat['nome']}"
                        break
                
                categoria = st.selectbox(
                    "Categoria",
                    options=cat_options,
                    index=cat_options.index(cat_default) if cat_default in cat_options else 0,
                    key=f"item_cat_qr_{i}",
                    label_visibility="collapsed"
                )
            
            with col4:
                incluir = st.checkbox(
                    "✓",
                    value=item["incluir"],
                    key=f"item_inc_qr_{i}"
                )
            
            if incluir:
                itens_para_salvar.append({
                    "descricao": desc,
                    "valor": valor,
                    "categoria_id": cat_map.get(categoria),
                    "data": dados.data_emissao or date.today()
                })
    
    # Resumo
    total_selecionado = sum(i["valor"] for i in itens_para_salvar)
    st.markdown(f"**Total selecionado:** R$ {total_selecionado:.2f} ({len(itens_para_salvar)} itens)")
    
    st.divider()
    
    # Botões de ação
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Salvar Transações Selecionadas", width='stretch', type="primary", key="btn_salvar_todas_qr"):
            transacoes = []
            for item in itens_para_salvar:
                transacao = {
                    "user_id": user_id,
                    "descricao": item["descricao"],
                    "valor": item["valor"],
                    "tipo": "despesa",
                    "data": item["data"].isoformat() if hasattr(item["data"], 'isoformat') else item["data"],
                    "categoria_id": item["categoria_id"],
                    "observacao": f"NFCe: {dados.emitente_nome} | Chave: {dados.chave_acesso[:20]}..." if dados.chave_acesso else f"NFCe: {dados.emitente_nome}",
                    "modo_lancamento": "semi_automatico"
                }
                transacoes.append(transacao)
            
            if transacoes:
                resultado = db.criar_transacoes_em_lote(transacoes)
                if resultado:
                    st.success(f"✅ {len(resultado)} transações salvas!")
                    st.balloons()
                    # Limpar sessão
                    for key in list(st.session_state.keys()):
                        if key.startswith("cupom_") or key.startswith("metodo_") or key.startswith("modo_") or key.startswith("item_"):
                            del st.session_state[key]
                    st.info("💡 Dica: Vá para 'Transações' para ver todas as suas transações salvas")
                    st.rerun()
                else:
                    st.error("❌ Erro ao salvar transações no banco de dados")
            else:
                st.warning("⚠️ Nenhum item selecionado para salvar")
    
    with col2:
        if st.button("🔄 Processar Novamente", width='stretch', key="btn_reprocessar_qr"):
            # Limpar sessão
            for key in list(st.session_state.keys()):
                if key.startswith("cupom_") or key.startswith("metodo_") or key.startswith("modo_") or key.startswith("item_"):
                    del st.session_state[key]
            st.rerun()


def render_lancamento_total_qrcode(user_id: str, dados: DadosNFCe):
    """Permite lançar o total do cupom como uma transação única (QR Code)"""
    
    categoria_sugerida = sugerir_categoria_estabelecimento(dados.emitente_nome)
    
    with st.form("form_lancamento_total_qr"):
        col1, col2 = st.columns(2)
        
        with col1:
            descricao = st.text_input(
                "Descrição",
                value=dados.emitente_nome or "Compra",
                key="total_desc_qr"
            )
        
        with col2:
            valor = st.number_input(
                "Valor Total (R$)",
                value=dados.valor_total,
                min_value=0.01,
                step=0.01,
                format="%.2f",
                key="total_valor_qr"
            )
        
        col1, col2 = st.columns(2)
        
        with col1:
            data_value = dados.data_emissao.date() if dados.data_emissao else date.today()
            data = st.date_input(
                "Data",
                value=data_value,
                key="total_data_qr"
            )
        
        with col2:
            categorias = db.listar_categorias(user_id, tipo="despesa")
            cat_options = {f"{c['icone']} {c['nome']}": c["id"] for c in categorias}
            
            # Encontrar categoria sugerida na lista
            default_cat = list(cat_options.keys())[0] if cat_options else "Sem categoria"
            for cat_name in cat_options.keys():
                if categoria_sugerida in cat_name:
                    default_cat = cat_name
                    break
            
            categoria = st.selectbox(
                "Categoria",
                options=list(cat_options.keys()) if cat_options else ["Sem categoria"],
                index=list(cat_options.keys()).index(default_cat) if default_cat in cat_options else 0,
                key="total_categoria_qr"
            )
        
        if st.form_submit_button("💾 Salvar", use_container_width=True):
            transacao = {
                "user_id": user_id,
                "descricao": descricao,
                "valor": valor,
                "tipo": "despesa",
                "data": data.isoformat(),
                "categoria_id": cat_options.get(categoria) if cat_options else None,
                "observacao": f"CNPJ: {dados.emitente_cnpj} | Chave: {dados.chave_acesso[:20]}..." if dados.chave_acesso else f"CNPJ: {dados.emitente_cnpj}",
                "modo_lancamento": "semi_automatico"
            }
            
            resultado = db.criar_transacao(transacao)
            if resultado:
                st.success("✅ Transação salva!")
                st.balloons()
                # Limpar upload
                if "cupom_upload" in st.session_state:
                    del st.session_state["cupom_upload"]
                st.info("💡 Dica: Vá para 'Transações' para ver todas as suas transações salvas")
            else:
                st.error("❌ Erro ao salvar transação no banco de dados")


def sugerir_categoria_estabelecimento(nome_estabelecimento: str) -> str:
    """Sugere categoria baseado no nome do estabelecimento"""
    if not nome_estabelecimento:
        return "Outros"
    
    nome_lower = nome_estabelecimento.lower()
    
    categorias_keywords = {
        "Alimentação": ["supermercado", "mercado", "market", "atacad", "hortifruti", "padaria", 
                       "restaurante", "lanchonete", "pizzaria", "burger", "sushi", "açougue",
                       "carrefour", "extra", "pão de açúcar", "assaí", "big", "walmart"],
        "Transporte": ["posto", "shell", "ipiranga", "br", "petrobras", "auto", "veículo", 
                      "combustível", "estacionamento"],
        "Saúde": ["farmácia", "drogaria", "droga", "raia", "drogasil", "pague menos", 
                 "hospital", "clínica", "lab"],
        "Vestuário": ["roupa", "loja", "moda", "renner", "riachuelo", "c&a", "marisa",
                     "hering", "zara", "calçado"],
        "Lazer": ["cinema", "teatro", "ingresso", "diversão", "parque", "shopping"],
        "Educação": ["livraria", "papelaria", "livro", "escola", "curso"],
        "Serviços": ["luz", "energia", "água", "telefone", "internet"]
    }
    
    for categoria, keywords in categorias_keywords.items():
        for keyword in keywords:
            if keyword in nome_lower:
                return categoria
    
    return "Outros"


def sugerir_categoria_item(descricao_item: str) -> Optional[str]:
    """Sugere categoria baseado na descrição do item"""
    if not descricao_item:
        return None
    
    desc_lower = descricao_item.lower()
    
    # Usar as palavras-chave do config
    for categoria, palavras in Config.PALAVRAS_CHAVE_CATEGORIAS.items():
        for palavra in palavras:
            if palavra in desc_lower:
                return categoria
    
    return None


def processar_cupom_ocr(user_id: str, image_bytes: bytes, modo_automatico: bool):
    """Processa o cupom fiscal via OCR - MÉTODO FALLBACK"""
    
    # Verificar se OCR está disponível
    if not ocr.is_available:
        st.error("❌ Serviço de OCR não disponível. Instale o EasyOCR.")
        return
    
    # Extrair dados
    cupom_data = ocr.extrair_dados_cupom(image_bytes)
    
    if not cupom_data.texto_bruto:
        st.error("❌ Não foi possível extrair texto da imagem. Tente outra foto.")
        return
    
    # Mostrar dados extraídos
    st.success(f"✅ Texto extraído! Confiança: {cupom_data.confianca:.1%}")
    
    with st.expander("📄 Texto bruto extraído"):
        st.text(cupom_data.texto_bruto)
    
    # Mostrar dados estruturados
    st.subheader("📊 Dados Identificados")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Estabelecimento:** {cupom_data.estabelecimento or 'Não identificado'}")
        st.write(f"**CNPJ:** {cupom_data.cnpj or 'Não identificado'}")
    with col2:
        st.write(f"**Data:** {cupom_data.data.strftime('%d/%m/%Y') if cupom_data.data else 'Não identificada'}")
    
    if cupom_data.forma_pagamento:
        st.write(f"**Forma de pagamento:** {cupom_data.forma_pagamento}")
    
    st.divider()
    
    # Processar itens
    if cupom_data.itens:
        st.subheader(f"🛒 Itens ({len(cupom_data.itens)})")
        
        # Salvar no session_state para persistir após rerun
        st.session_state["cupom_processado_ocr"] = cupom_data
        
        if modo_automatico:
            # Modo automático - salvar diretamente
            salvar_transacoes_ocr_auto(user_id, cupom_data)
        else:
            # Modo semi-automático - permitir edição com interface interativa
            render_revisao_itens_ocr(user_id, cupom_data)
    else:
        st.warning("Nenhum item foi identificado automaticamente.")
        
        # Permitir lançamento manual do total
        if cupom_data.total > 0:
            st.info("Você pode lançar o valor total como uma única transação.")
            render_lancamento_total(user_id, cupom_data)


def salvar_transacoes_automatico(user_id: str, cupom: CupomExtraido):
    """Salva transações automaticamente a partir do cupom"""
    
    categorias = db.listar_categorias(user_id, tipo="despesa")
    cat_map = {c["nome"]: c["id"] for c in categorias}
    
    transacoes = []
    for item in cupom.itens:
        transacao = {
            "user_id": user_id,
            "descricao": item.descricao,
            "valor": item.valor_total,
            "tipo": "despesa",
            "data": cupom.data.isoformat() if cupom.data else date.today().isoformat(),
            "categoria_id": cat_map.get(item.categoria_sugerida),
            "observacao": f"Cupom: {cupom.estabelecimento}" if cupom.estabelecimento else "",
            "modo_lancamento": "automatico"
        }
        transacoes.append(transacao)
    
    if transacoes:
        resultado = db.criar_transacoes_em_lote(transacoes)
        if resultado:
            st.success(f"✅ {len(resultado)} transações salvas automaticamente!")
            st.balloons()
        else:
            st.error("Erro ao salvar transações")
    else:
        st.warning("Nenhuma transação para salvar")


def salvar_transacoes_ocr_auto(user_id: str, cupom: CupomExtraido):
    """Salva transações automaticamente a partir do cupom OCR"""
    
    categorias = db.listar_categorias(user_id, tipo="despesa")
    cat_map = {c["nome"]: c["id"] for c in categorias}
    
    transacoes = []
    for item in cupom.itens:
        transacao = {
            "user_id": user_id,
            "descricao": item.descricao,
            "valor": item.valor_total,
            "tipo": "despesa",
            "data": cupom.data.isoformat() if cupom.data else date.today().isoformat(),
            "categoria_id": cat_map.get(item.categoria_sugerida),
            "observacao": f"Cupom OCR: {cupom.estabelecimento}" if cupom.estabelecimento else "",
            "modo_lancamento": "automatico"
        }
        transacoes.append(transacao)
    
    if transacoes:
        resultado = db.criar_transacoes_em_lote(transacoes)
        if resultado:
            st.success(f"✅ {len(resultado)} transações salvas automaticamente!")
            st.balloons()
        else:
            st.error("Erro ao salvar transações")
    else:
        st.warning("Nenhuma transação para salvar")


def render_revisao_itens_ocr(user_id: str, cupom: CupomExtraido):
    """Interface para revisar itens do OCR antes de salvar"""
    
    categorias = db.listar_categorias(user_id, tipo="despesa")
    cat_options = ["Sem categoria"] + [f"{c['icone']} {c['nome']}" for c in categorias]
    cat_map = {f"{c['icone']} {c['nome']}": c["id"] for c in categorias}
    
    # Armazenar itens em sessão para edição
    if "itens_cupom_editados_ocr" not in st.session_state:
        st.session_state.itens_cupom_editados_ocr = []
        for item in cupom.itens:
            st.session_state.itens_cupom_editados_ocr.append({
                "descricao": item.descricao,
                "valor": item.valor_total,
                "categoria": item.categoria_sugerida,
                "incluir": True
            })
    
    # Formulário de edição
    st.markdown("### ✏️ Revise os itens antes de salvar")
    
    itens_para_salvar = []
    
    for i, item in enumerate(st.session_state.itens_cupom_editados_ocr):
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                desc = st.text_input(
                    "Descrição",
                    value=item["descricao"],
                    key=f"item_desc_ocr_{i}",
                    label_visibility="collapsed"
                )
            
            with col2:
                valor = st.number_input(
                    "Valor",
                    value=float(item["valor"]),
                    min_value=0.01,
                    step=0.01,
                    format="%.2f",
                    key=f"item_valor_ocr_{i}",
                    label_visibility="collapsed"
                )
            
            with col3:
                # Encontrar categoria sugerida
                cat_default = "Sem categoria"
                for cat in categorias:
                    if cat["nome"] == item["categoria"]:
                        cat_default = f"{cat['icone']} {cat['nome']}"
                        break
                
                categoria = st.selectbox(
                    "Categoria",
                    options=cat_options,
                    index=cat_options.index(cat_default) if cat_default in cat_options else 0,
                    key=f"item_cat_ocr_{i}",
                    label_visibility="collapsed"
                )
            
            with col4:
                incluir = st.checkbox(
                    "✓",
                    value=item["incluir"],
                    key=f"item_inc_ocr_{i}"
                )
            
            if incluir:
                itens_para_salvar.append({
                    "descricao": desc,
                    "valor": valor,
                    "categoria_id": cat_map.get(categoria),
                    "data": cupom.data or date.today()
                })
    
    # Resumo
    total_selecionado = sum(i["valor"] for i in itens_para_salvar)
    st.markdown(f"**Total selecionado:** R$ {total_selecionado:.2f} ({len(itens_para_salvar)} itens)")
    
    st.divider()
    
    # Botões de ação
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Salvar Transações Selecionadas", width='stretch', type="primary", key="btn_salvar_ocr"):
            transacoes = []
            for item in itens_para_salvar:
                transacao = {
                    "user_id": user_id,
                    "descricao": item["descricao"],
                    "valor": item["valor"],
                    "tipo": "despesa",
                    "data": item["data"].isoformat() if hasattr(item["data"], 'isoformat') else item["data"],
                    "categoria_id": item["categoria_id"],
                    "observacao": f"Cupom OCR: {cupom.estabelecimento}" if cupom.estabelecimento else "",
                    "modo_lancamento": "semi_automatico"
                }
                transacoes.append(transacao)
            
            if transacoes:
                resultado = db.criar_transacoes_em_lote(transacoes)
                if resultado:
                    st.success(f"✅ {len(resultado)} transações salvas!")
                    st.balloons()
                    # Limpar sessão
                    for key in list(st.session_state.keys()):
                        if key.startswith("cupom_") or key.startswith("metodo_") or key.startswith("modo_") or key.startswith("item_"):
                            del st.session_state[key]
                    st.info("💡 Dica: Vá para 'Transações' para ver todas as suas transações salvas")
                    st.rerun()
                else:
                    st.error("❌ Erro ao salvar transações")
            else:
                st.warning("⚠️ Nenhum item selecionado para salvar")
    
    with col2:
        if st.button("🔄 Processar Novamente", width='stretch', key="btn_reprocessar_ocr"):
            # Limpar sessão
            for key in list(st.session_state.keys()):
                if key.startswith("cupom_") or key.startswith("metodo_") or key.startswith("modo_") or key.startswith("item_"):
                    del st.session_state[key]
            st.rerun()


def render_revisao_itens(user_id: str, cupom: CupomExtraido):
    """Interface para revisar e editar itens antes de salvar"""
    
    categorias = db.listar_categorias(user_id, tipo="despesa")
    cat_options = ["Sem categoria"] + [f"{c['icone']} {c['nome']}" for c in categorias]
    cat_map = {f"{c['icone']} {c['nome']}": c["id"] for c in categorias}
    
    # Armazenar itens em sessão para edição
    if "itens_cupom_editados" not in st.session_state:
        st.session_state.itens_cupom_editados = []
        for item in cupom.itens:
            st.session_state.itens_cupom_editados.append({
                "descricao": item.descricao,
                "valor": item.valor_total,
                "categoria": item.categoria_sugerida,
                "incluir": True
            })
    
    # Formulário de edição
    st.markdown("### ✏️ Revise os itens antes de salvar")
    
    itens_para_salvar = []
    
    for i, item in enumerate(st.session_state.itens_cupom_editados):
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                desc = st.text_input(
                    "Descrição",
                    value=item["descricao"],
                    key=f"item_desc_{i}",
                    label_visibility="collapsed"
                )
            
            with col2:
                valor = st.number_input(
                    "Valor",
                    value=float(item["valor"]),
                    min_value=0.01,
                    step=0.01,
                    format="%.2f",
                    key=f"item_valor_{i}",
                    label_visibility="collapsed"
                )
            
            with col3:
                # Encontrar categoria sugerida
                cat_default = "Sem categoria"
                for cat in categorias:
                    if cat["nome"] == item["categoria"]:
                        cat_default = f"{cat['icone']} {cat['nome']}"
                        break
                
                categoria = st.selectbox(
                    "Categoria",
                    options=cat_options,
                    index=cat_options.index(cat_default) if cat_default in cat_options else 0,
                    key=f"item_cat_{i}",
                    label_visibility="collapsed"
                )
            
            with col4:
                incluir = st.checkbox(
                    "✓",
                    value=item["incluir"],
                    key=f"item_inc_{i}"
                )
            
            if incluir:
                itens_para_salvar.append({
                    "descricao": desc,
                    "valor": valor,
                    "categoria_id": cat_map.get(categoria),
                    "data": cupom.data or date.today()
                })
    
    # Resumo
    total_selecionado = sum(i["valor"] for i in itens_para_salvar)
    st.markdown(f"**Total selecionado:** R$ {total_selecionado:.2f} ({len(itens_para_salvar)} itens)")
    
    # Botão salvar
    if st.button("💾 Salvar Transações Selecionadas", width='stretch', type="primary"):
        transacoes = []
        for item in itens_para_salvar:
            transacao = {
                "user_id": user_id,
                "descricao": item["descricao"],
                "valor": item["valor"],
                "tipo": "despesa",
                "data": item["data"].isoformat() if hasattr(item["data"], 'isoformat') else item["data"],
                "categoria_id": item["categoria_id"],
                "observacao": f"Cupom: {cupom.estabelecimento}" if cupom.estabelecimento else "",
                "modo_lancamento": "semi_automatico"
            }
            transacoes.append(transacao)
        
        if transacoes:
            resultado = db.criar_transacoes_em_lote(transacoes)
            if resultado:
                st.success(f"✅ {len(resultado)} transações salvas!")
                st.balloons()
                # Limpar sessão
                del st.session_state.itens_cupom_editados
            else:
                st.error("Erro ao salvar transações")


def render_lancamento_total(user_id: str, cupom: CupomExtraido):
    """Permite lançar o total do cupom como uma transação única"""
    
    with st.form("form_lancamento_total"):
        col1, col2 = st.columns(2)
        
        with col1:
            descricao = st.text_input(
                "Descrição",
                value=cupom.estabelecimento or "Compra",
                key="total_desc"
            )
        
        with col2:
            valor = st.number_input(
                "Valor Total (R$)",
                value=cupom.total,
                min_value=0.01,
                step=0.01,
                format="%.2f",
                key="total_valor"
            )
        
        col1, col2 = st.columns(2)
        
        with col1:
            data = st.date_input(
                "Data",
                value=cupom.data or date.today(),
                key="total_data"
            )
        
        with col2:
            categorias = db.listar_categorias(user_id, tipo="despesa")
            cat_options = {f"{c['icone']} {c['nome']}": c["id"] for c in categorias}
            
            categoria = st.selectbox(
                "Categoria",
                options=list(cat_options.keys()) if cat_options else ["Sem categoria"],
                key="total_categoria"
            )
        
        if st.form_submit_button("💾 Salvar", width='stretch'):
            transacao = {
                "user_id": user_id,
                "descricao": descricao,
                "valor": valor,
                "tipo": "despesa",
                "data": data.isoformat(),
                "categoria_id": cat_options.get(categoria) if cat_options else None,
                "observacao": f"CNPJ: {cupom.cnpj}" if cupom.cnpj else "",
                "modo_lancamento": "semi_automatico"
            }
            
            resultado = db.criar_transacao(transacao)
            if resultado:
                st.success("✅ Transação salva!")
                st.balloons()
            else:
                st.error("Erro ao salvar transação")
