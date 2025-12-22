"""
Página de Configurações e Ferramentas
"""
import streamlit as st
from pathlib import Path
import sys
from datetime import date

# Adicionar diretório raiz ao path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from services.database import db
from config import Config
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

    # Status da persistência
    url = (getattr(Config, "SUPABASE_URL", "") or "").strip()
    hint = "(vazio)"
    if url:
        try:
            hint = url.split("//", 1)[-1][:24]
        except Exception:
            hint = url[:24]
    st.info(f"Persistência ativa: Supabase ({hint}...)")
    
    # --- Ferramentas de Desenvolvimento ---
    st.subheader("🛠️ Ferramentas de Desenvolvimento")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Popular Banco de Dados")
        st.markdown("""
        Adiciona dados de exemplo ao banco:
        - 12 categorias (receitas e despesas)
        - 8 orçamentos mensais
        - ~35–45 transações dos últimos 3 meses (mais enxuto e legível)
        - Receitas e despesas consistentes (salário + despesas fixas/variáveis)
        - Contas e Fixas
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
        - Todas as fixas (recorrentes)
        - Todas as contas
        - Todos os orçamentos
        - Todas as categorias
        """)

        keep_categorias = st.checkbox(
            "Manter categorias (recomendado)",
            value=True,
            key="keep_categorias_limpar",
            help="Apaga transações e orçamentos, mas mantém categorias ativas.",
        )
        
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
                    limpar_dados(user_id, keep_categorias=keep_categorias)
                    st.success("✅ Dados limpos com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao limpar banco: {str(e)}")

    st.divider()

    # --- Contas ---
    st.subheader("🏦 Contas")

    contas = db.listar_contas(user_id)
    if contas:
        df_contas = [{
            "Nome": c.get("nome"),
            "Tipo": c.get("tipo"),
            "Saldo inicial": float(c.get("saldo_inicial") or 0),
            "Data saldo": c.get("data_saldo_inicial"),
            "Fechamento": c.get("dia_fechamento"),
            "Vencimento": c.get("dia_vencimento"),
        } for c in contas]
        st.dataframe(df_contas, width='stretch', hide_index=True)
    else:
        st.info("Nenhuma conta cadastrada ainda.")

    with st.expander("➕ Adicionar conta"):
        col_a, col_b = st.columns(2)
        with col_a:
            nome_conta = st.text_input("Nome da conta", key="conta_nome")
            tipo_conta = st.selectbox(
                "Tipo",
                options=["banco", "carteira", "cartao_credito"],
                key="conta_tipo",
            )
            saldo_inicial = st.number_input("Saldo inicial", value=0.0, step=0.01, format="%.2f", key="conta_saldo")
            data_saldo = st.date_input("Data do saldo inicial", key="conta_data_saldo")
        with col_b:
            dia_fechamento = st.number_input("Dia de fechamento (cartão)", min_value=1, max_value=31, value=10, key="conta_fechamento")
            dia_vencimento = st.number_input("Dia de vencimento (cartão)", min_value=1, max_value=31, value=17, key="conta_vencimento")

        if st.button("Salvar conta", type="primary", key="btn_salvar_conta"):
            if not nome_conta:
                st.error("Informe o nome da conta")
            else:
                df = dia_fechamento if tipo_conta == "cartao_credito" else None
                dv = dia_vencimento if tipo_conta == "cartao_credito" else None
                criada = db.criar_conta(
                    user_id=user_id,
                    nome=nome_conta,
                    tipo=tipo_conta,
                    saldo_inicial=saldo_inicial,
                    data_saldo_inicial=data_saldo,
                    dia_fechamento=df,
                    dia_vencimento=dv,
                )
                if criada:
                    st.success("✅ Conta criada")
                    st.rerun()
                else:
                    st.error("❌ Não foi possível criar a conta")

    st.divider()

    # --- Fixas / Recorrentes ---
    st.subheader("🔁 Fixas do mês")
    recorrentes = db.listar_recorrentes(user_id)

    if recorrentes:
        df_rec = [{
            "Dia": r.get("dia_do_mes"),
            "Descrição": r.get("descricao"),
            "Tipo": r.get("tipo"),
            "Valor": float(r.get("valor") or 0),
            "Conta": (r.get("contas") or {}).get("nome") if isinstance(r.get("contas"), dict) else None,
            "Categoria": (r.get("categorias") or {}).get("nome") if isinstance(r.get("categorias"), dict) else None,
        } for r in recorrentes]
        st.dataframe(df_rec, width='stretch', hide_index=True)
    else:
        st.info("Nenhuma transação fixa cadastrada ainda.")

    with st.expander("➕ Adicionar fixa"):
        contas = db.listar_contas(user_id)
        if not contas:
            st.warning("Crie ao menos uma conta antes de cadastrar fixas.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                conta_opt = {c["nome"]: c["id"] for c in contas}
                conta_nome = st.selectbox("Conta", options=list(conta_opt.keys()), key="fixa_conta")
                tipo = st.selectbox("Tipo", options=["despesa", "receita"], key="fixa_tipo")
                dia = st.number_input("Dia do mês", min_value=1, max_value=31, value=5, key="fixa_dia")
            with col2:
                descricao = st.text_input("Descrição", key="fixa_desc")
                valor = st.number_input("Valor (R$)", min_value=0.01, step=0.01, format="%.2f", key="fixa_valor")
                categorias = db.listar_categorias(user_id, tipo=tipo)
                cat_opt = {f"{c['icone']} {c['nome']}": c["id"] for c in categorias}
                cat_label = st.selectbox("Categoria", options=list(cat_opt.keys()) if cat_opt else ["Sem categoria"], key="fixa_cat")

            if st.button("Salvar fixa", type="primary", key="btn_salvar_fixa"):
                if not descricao:
                    st.error("Descrição é obrigatória")
                else:
                    rec = {
                        "user_id": user_id,
                        "conta_id": conta_opt.get(conta_nome),
                        "categoria_id": cat_opt.get(cat_label) if cat_opt else None,
                        "descricao": descricao,
                        "valor": float(valor),
                        "tipo": tipo,
                        "dia_do_mes": int(dia),
                    }
                    criado = db.criar_recorrente(rec)
                    if criado:
                        st.success("✅ Fixa criada")
                        st.rerun()
                    else:
                        st.error("❌ Não foi possível criar a fixa")

    colg1, colg2 = st.columns([1, 2])
    with colg1:
        mes_ref = st.date_input("Mês para gerar previstas", value=date.today().replace(day=1), key="gerar_prev_mes")
    with colg2:
        if st.button("Gerar previstas do mês", key="btn_gerar_previstas"):
            criadas = db.gerar_previstas_mes(user_id, ano=mes_ref.year, mes=mes_ref.month)
            st.success(f"✅ {len(criadas)} transações previstas criadas")
            st.rerun()
    
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
