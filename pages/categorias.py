"""
Página de gerenciamento de Categorias, Contas, Investimentos e Orçamentos
"""
import streamlit as st
from datetime import date
from typing import List, Dict

from services.database import db
from config import Config


def get_user_id() -> str:
    """Retorna ID do usuário atual"""
    return st.session_state.get("user_id", "")


def render_categorias_page():
    """Página de gerenciamento centralizado"""
    
    user_id = get_user_id()
    if not user_id:
        st.warning("Usuário não identificado")
        return
    
    st.header("� Cadastros")
    st.caption("Categorias, contas, investimentos e orçamentos")
    
    # Tabs principais
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏷️ Categorias",
        "🏦 Contas de Banco",
        "📈 Investimentos",
        "🎯 Orçamentos"
    ])
    
    with tab1:
        render_categorias(user_id)
    
    with tab2:
        render_contas_banco(user_id)
    
    with tab3:
        render_investimentos(user_id)
    
    with tab4:
        render_orcamentos(user_id)


# ===================== CATEGORIAS =====================

def render_categorias(user_id: str):
    """Gerenciamento de categorias de despesas e receitas"""
    
    st.subheader("🏷️ Categorias")
    
    # Tabs para tipos
    col_desp, col_rec = st.columns(2)
    
    with col_desp:
        st.write("**💸 Despesas**")
        render_lista_categorias(user_id, "despesa")
    
    with col_rec:
        st.write("**💰 Receitas**")
        render_lista_categorias(user_id, "receita")


def render_lista_categorias(user_id: str, tipo: str):
    """Renderiza lista de categorias por tipo"""
    
    categorias = db.listar_categorias(user_id, tipo=tipo)
    
    # Formulário para nova categoria
    with st.expander("➕ Nova Categoria", expanded=False):
        with st.form(f"form_nova_cat_{tipo}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                nome = st.text_input("Nome", key=f"nova_cat_nome_{tipo}")
            
            with col2:
                icone = st.text_input("Ícone", value="📦", key=f"nova_cat_icone_{tipo}", max_chars=1)
            
            if st.form_submit_button("Adicionar", use_container_width=True):
                if nome:
                    resultado = db.criar_categoria(user_id, nome, tipo, icone)
                    if resultado:
                        st.success(f"✅ '{nome}' criada!")
                        st.rerun()
                    else:
                        st.error(f"❌ '{nome}' já existe!")
                else:
                    st.warning("Nome obrigatório")
    
    # Lista de categorias
    if categorias:
        for cat in categorias:
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.write(f"{cat.get('icone', '📦')} {cat['nome']}")
            
            with col2:
                if st.button("✏️", key=f"edit_cat_{cat['id']}", use_container_width=True):
                    st.session_state[f"edit_cat_{cat['id']}"] = True
            
            with col3:
                if st.button("🗑️", key=f"del_cat_{cat['id']}", use_container_width=True):
                    if db.deletar_categoria(cat['id']):
                        st.success("Removida!")
                        st.rerun()
    else:
        st.info("Nenhuma categoria cadastrada")


# ===================== CONTAS DE BANCO =====================

def render_contas_banco(user_id: str):
    """Gerenciamento de saldos de contas bancárias"""
    
    st.subheader("🏦 Saldos de Contas de Banco")
    
    # Formulário para adicionar conta
    with st.expander("➕ Adicionar Conta de Banco", expanded=False):
        with st.form("form_nova_conta"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome da Conta", placeholder="Conta Corrente")
            
            with col2:
                banco = st.text_input("Banco", placeholder="Ex: Itaú, Bradesco")
            
            col3, col4 = st.columns(2)
            
            with col3:
                saldo_inicial = st.number_input(
                    "Saldo Inicial (R$)",
                    value=0.0,
                    step=0.01
                )
            
            with col4:
                data_saldo = st.date_input("Data do Saldo", value=date.today())
            
            if st.form_submit_button("Salvar Conta", use_container_width=True):
                if nome:
                    resultado = db.criar_conta(
                        user_id=user_id,
                        nome=nome,
                        tipo="banco",
                        saldo_inicial=saldo_inicial,
                        data_saldo_inicial=data_saldo
                    )
                    if resultado:
                        st.success(f"✅ Conta '{nome}' criada!")
                        st.rerun()
                else:
                    st.warning("Nome obrigatório")
    
    # Lista de contas
    contas = db.listar_contas(user_id)
    contas_banco = [c for c in contas if c.get("tipo") == "banco"]
    
    if contas_banco:
        st.markdown("### Contas Cadastradas")
        
        for conta in contas_banco:
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**{conta['nome']}**")
                st.caption(f"{conta.get('tipo', 'banco')}")
            
            with col2:
                st.metric(
                    "Saldo",
                    f"R$ {float(conta.get('saldo_inicial', 0)):.2f}"
                )
            
            with col3:
                if st.button("🗑️", key=f"del_conta_{conta['id']}", use_container_width=True):
                    if db.deletar_conta(conta['id']):
                        st.success("Removida!")
                        st.rerun()
    else:
        st.info("Nenhuma conta cadastrada")


# ===================== INVESTIMENTOS =====================

def render_investimentos(user_id: str):
    """Gerenciamento de investimentos"""
    
    st.subheader("📈 Investimentos")
    
    # Formulário para adicionar investimento
    with st.expander("➕ Adicionar Investimento", expanded=False):
        with st.form("form_novo_investimento"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome do Investimento", placeholder="Ex: Tesouro Direto")
            
            with col2:
                tipo_inv = st.selectbox(
                    "Tipo",
                    options=["Renda Fixa", "Renda Variável", "Criptomoedas", "Outro"]
                )
            
            col3, col4 = st.columns(2)
            
            with col3:
                valor_inicial = st.number_input(
                    "Valor Inicial (R$)",
                    value=0.0,
                    step=0.01
                )
            
            with col4:
                data_investimento = st.date_input("Data", value=date.today())
            
            if st.form_submit_button("Salvar Investimento", use_container_width=True):
                if nome:
                    resultado = db.criar_investimento(
                        user_id=user_id,
                        nome=nome,
                        descricao=tipo_inv,
                        valor_inicial=valor_inicial,
                        data_investimento=data_investimento
                    )
                    if resultado:
                        st.success(f"✅ Investimento '{nome}' criado!")
                        st.rerun()
                else:
                    st.warning("Nome obrigatório")
    
    # Lista de investimentos
    investimentos = db.listar_investimentos(user_id)
    
    if investimentos:
        st.markdown("### Investimentos Cadastrados")
        
        for inv in investimentos:
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.write(f"**{inv['nome']}**")
                st.caption(f"{inv.get('descricao', 'Investimento')}")
            
            with col2:
                st.metric(
                    "Saldo",
                    f"R$ {float(inv.get('valor_inicial', 0)):.2f}"
                )
            
            with col3:
                if st.button("🗑️", key=f"del_inv_{inv['id']}", use_container_width=True):
                    if db.deletar_investimento(inv['id']):
                        st.success("Removido!")
                        st.rerun()
    else:
        st.info("Nenhum investimento cadastrado")


# ===================== ORÇAMENTOS (METAS) =====================

def render_orcamentos(user_id: str):
    """Gerenciamento de orçamentos/metas por categoria para confrontar com realizado"""
    
    st.subheader("🎯 Orçamentos (Metas por Categoria)")
    st.caption("Defina limite de gastos por categoria para acompanhar o realizado")
    
    # Formulário para adicionar orçamento
    with st.expander("➕ Novo Orçamento", expanded=False):
        with st.form("form_novo_orcamento"):
            # Buscar categorias de despesa
            categorias = db.listar_categorias(user_id, tipo="despesa")
            
            if categorias:
                cat_options = {f"{c['icone']} {c['nome']}": c["id"] for c in categorias}
                
                col1, col2 = st.columns(2)
                
                with col1:
                    categoria_selecionada = st.selectbox(
                        "Categoria",
                        options=list(cat_options.keys())
                    )
                    categoria_id = cat_options.get(categoria_selecionada)
                
                with col2:
                    valor_limite = st.number_input(
                        "Limite de Gastos (R$)",
                        value=0.0,
                        step=0.01
                    )
                
                col3, col4 = st.columns(2)
                
                with col3:
                    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
                    mes_atual = date.today().month - 1  # 0-based index
                    mes_nome = st.selectbox("Mês", options=meses, index=mes_atual)
                    mes_num = meses.index(mes_nome) + 1
                
                with col4:
                    ano = st.number_input("Ano", value=date.today().year, step=1)
                
                # Opção de recorrência para orçamentos
                recorrente_orc = st.checkbox("Cadastrar como recorrente (próximos 12 meses)", key="orc_recorrente")
                
                if st.form_submit_button("Salvar Orçamento", use_container_width=True):
                    from dateutil.relativedelta import relativedelta
                    
                    orcamentos_criados = 0
                    
                    if recorrente_orc:
                        # Criar orçamentos para os próximos 12 meses
                        data_atual = date(ano, mes_num, 1)
                        
                        for i in range(12):
                            resultado = db.criar_orcamento(
                                user_id=user_id,
                                categoria_id=categoria_id,
                                valor_limite=valor_limite,
                                mes=data_atual.month,
                                ano=data_atual.year
                            )
                            
                            if resultado:
                                orcamentos_criados += 1
                            else:
                                st.error(f"Erro ao criar orçamento para {data_atual.strftime('%m/%Y')}")
                                break
                            
                            data_atual += relativedelta(months=1)
                        
                        if orcamentos_criados > 0:
                            st.success(f"✅ {orcamentos_criados} orçamentos recorrentes criados!")
                    else:
                        # Criar orçamento único
                        resultado = db.criar_orcamento(
                            user_id=user_id,
                            categoria_id=categoria_id,
                            valor_limite=valor_limite,
                            mes=mes_num,
                            ano=ano
                        )
                        
                        if resultado:
                            st.success("✅ Orçamento criado!")
                            orcamentos_criados = 1
                    
                    if orcamentos_criados > 0:
                        # Limpar formulário
                        if "orc_recorrente" in st.session_state:
                            del st.session_state["orc_recorrente"]
                        st.rerun()
                    else:
                        st.error("Erro ao criar orçamento")
            else:
                st.warning("Crie categorias de despesa primeiro!")
    
    # Lista de orçamentos
    orcamentos = db.listar_orcamentos(user_id)

    if orcamentos:
        st.markdown("### Orçamentos Cadastrados")

        # Preparar dados para tabela
        dados_tabela = []
        for orc in orcamentos:
            cat = db.buscar_categoria(orc.get("categoria_id"))
            cat_nome = f"{cat.get('icone')} {cat.get('nome')}" if cat else "Sem categoria"

            limite = float(orc.get("valor_limite", 0))
            gasto = float(orc.get("valor_gasto", 0))
            restante = limite - gasto
            percentual = (gasto / limite * 100) if limite > 0 else 0

            status = "✅ Dentro do limite"
            if percentual > 90:
                status = "⚠️ Próximo do limite"
            elif percentual > 100:
                status = "❌ Ultrapassou o limite"

            dados_tabela.append({
                "Categoria": cat_nome,
                "Período": orc.get("periodo_display", "Mensal"),
                "Limite": f"R$ {limite:.2f}",
                "Gasto": f"R$ {gasto:.2f}",
                "Restante": f"R$ {restante:.2f}",
                "Status": status,
                "ID": orc["id"]
            })

        # Exibir tabela
        df = pd.DataFrame(dados_tabela)
        df = df.drop(columns=["ID"])  # Não mostrar ID na tabela
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Ações individuais
        st.markdown("### Ações")
        cols = st.columns(4, gap="small")

        for idx, orc in enumerate(orcamentos):
            with cols[idx % 4]:
                cat = db.buscar_categoria(orc.get("categoria_id"))
                cat_nome = f"{cat.get('icone')} {cat.get('nome')}" if cat else "Sem categoria"
                periodo = orc.get("periodo_display", "Mensal")

                if st.button(f"🗑️ {cat_nome[:15]}...", key=f"del_orc_{orc['id']}", use_container_width=True):
                    if db.deletar_orcamento(orc['id']):
                        st.success("Orçamento removido!")
                        st.rerun()
                    else:
                        st.error("Erro ao remover")
    else:
        st.info("Nenhum orçamento cadastrado")
