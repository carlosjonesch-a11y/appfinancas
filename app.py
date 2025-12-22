"""
💰 Finanças Pessoais
Aplicativo de gestão financeira pessoal com OCR de cupons fiscais

Execute com: streamlit run app.py
"""
import streamlit as st
from pathlib import Path
import sys

# Adicionar diretório raiz ao path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from config import Config
from services.database import db
from pages.dashboard import render_dashboard_page, render_widget_resumo_lateral
from pages.transacoes import render_transacoes_page, render_nova_transacao_page
from pages.categorias import render_categorias_page
from pages.orcamentos import render_orcamentos_page
from pages.configuracoes import render_configuracoes_page
from pages.cartao_credito import render_cartao_page
from pages.investimentos import render_investimentos_page


# ==================== CONFIGURAÇÃO DA PÁGINA ====================

st.set_page_config(
    page_title=Config.APP_NAME,
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": f"""
        ## {Config.APP_NAME}
        
        Aplicativo de gestão financeira pessoal com:
        - 📊 Dashboard interativo
        - 📸 Leitura de cupons fiscais (OCR)
        - 🏷️ Categorização automática
        - 👤 Uso pessoal
        
        Desenvolvido com ❤️ usando Streamlit
        """
    }
)


# ==================== ESTILOS CUSTOMIZADOS ====================

st.markdown("""
<style>
    /* Esconder menu do Streamlit e Navegação Padrão */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stSidebarNav"] {display: none !important;}
    
    /* Variáveis de cores - Tema Moderno Clean */
    :root {
        --primary-color: #1e3a8a; /* Azul marinho (Blue 900) */
        --primary-hover: #1e40af; /* Azul marinho (Blue 800) */
        --background-color: #f8fafc; /* Slate 50 */
        --sidebar-bg: #1e293b; /* Slate 800 */
        --text-color: #334155; /* Slate 700 */
        --card-bg: #ffffff;
        --success-color: #10b981; /* Emerald 500 */
        --danger-color: #ef4444; /* Red 500 */
    }

    /* Melhoria nos Inputs (Campos de texto, números e selects) */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #1e293b !important; /* Slate 800 */
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px;
    }
    
    /* Fundo dos selects quando abertos */
    ul[data-testid="stSelectboxVirtualDropdown"] {
        background-color: #ffffff !important;
        color: #1e293b !important;
    }
    
    /* Texto dos labels */
    .stTextInput label, .stNumberInput label, .stSelectbox label {
        color: #475569 !important; /* Slate 600 */
        font-weight: 600;
    }
    
    /* Estilo global */
    .stApp {
        background-color: var(--background-color);
    }
    
    /* Estilo dos cards/métricas */
    div[data-testid="metric-container"] {
        background-color: var(--card-bg);
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease-in-out;
    }
    
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: var(--primary-color);
    }
    
    div[data-testid="metric-container"] label {
        color: #64748b !important; /* Slate 500 */
        font-weight: 600;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #0f172a !important; /* Slate 900 */
        font-weight: 800;
        font-size: 1.8rem;
    }
    
    /* Botões */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.2s;
        border: 1px solid #e2e8f0;
    }
    
    .stButton > button:hover {
        border-color: var(--primary-color);
        color: var(--primary-color);
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
        border: none;
        color: white;
        box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.3);
    }
    
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.4);
        transform: translateY(-1px);
    }
    
    /* Tabelas */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #000000 !important; /* Preto puro */
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        letter-spacing: -0.025em;
    }
    
    /* Divisores */
    hr {
        margin: 2.5rem 0;
        border-color: #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)


def ensure_single_user_session() -> bool:
    """Inicializa um usuário único (sem autenticação) e salva na sessão.

    Mantém o app utilizável enquanto você está testando sozinho.
    """
    try:
        if st.session_state.get("user_id"):
            return True

        email = getattr(Config, "SINGLE_USER_EMAIL", "meu@app.local")
        nome = getattr(Config, "SINGLE_USER_NAME", "Usuário")

        user = db.buscar_usuario_por_email(email=email)
        if not user:
            user = db.criar_usuario(email=email, nome=nome)
            if user and user.get("id"):
                try:
                    db.criar_categorias_padrao(user_id=str(user.get("id")))
                except Exception:
                    pass

        if not user or not user.get("id"):
            st.error("Não foi possível inicializar o usuário único. Verifique conexão do banco.")
            return False

        st.session_state.user_id = str(user.get("id"))
        st.session_state.user_name = user.get("nome") or nome
        st.session_state.user_email = user.get("email") or email
        return True
    except Exception:
        st.error("Erro ao inicializar o usuário único.")
        return False

# ==================== NAVEGAÇÃO ====================

def render_sidebar():
    """Renderiza menu lateral com design moderno"""
    
    with st.sidebar:
        # Header com gradiente
        st.markdown("""
        <style>
            /* Sidebar styling */
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
            }
            
            /* Logo/Title */
            .sidebar-title {
                background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-hover) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-size: 2rem;
                font-weight: 800;
                text-align: center;
                margin-bottom: 0.5rem;
                letter-spacing: -0.02em;
            }
            
            .sidebar-subtitle {
                text-align: center;
                color: #475569;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.1em;
                margin-bottom: 2rem;
            }
            
            /* Menu items styling */
            [data-testid="stSidebar"] .stRadio > label {
                display: none;
            }
            
            [data-testid="stSidebar"] [role="radiogroup"] {
                gap: 0.5rem;
            }

            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"] {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 0.75rem 1rem;
                cursor: pointer;
                transition: all 0.2s ease;
                font-weight: 600;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
            }
            
            /* Texto padrão em cinza claro */
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"],
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"] *,
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"] p,
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"] span,
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"] div {
                color: #94a3b8 !important; /* Cinza claro - Slate 400 */
                font-weight: 600 !important;
            }
            
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"]:hover {
                background-color: #f8fafc;
                border-color: #cbd5e1;
                transform: translateX(4px);
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            
            /* Texto PRETO no hover */
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"]:hover,
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"]:hover *,
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"]:hover p,
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"]:hover span,
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"]:hover div {
                color: #000000 !important;
                font-weight: 600 !important;
            }

            /* Item selecionado (Streamlit/Baseweb coloca um input radio dentro do label) */
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) {
                background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-hover) 100%);
                border-color: var(--primary-color);
                font-weight: 600;
                box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
            }
            
            /* Texto BRANCO quando selecionado (fundo azul) */
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked),
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) *,
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) p,
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) span,
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) div {
                color: #ffffff !important;
                font-weight: 700 !important;
            }

            /* Fallback (caso :has() não aplique): deixa o texto preto via input:checked */
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"] input:checked ~ div,
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"] input:checked ~ div *,
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"] input:checked ~ div p,
            [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"] input:checked ~ div span {
                color: #ffffff !important;
                font-weight: 700 !important;
            }
            
            /* User section */
            .user-card {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 1rem;
                margin-top: 1.5rem;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            }
            
            .user-avatar {
                font-size: 2rem;
                text-align: center;
                margin-bottom: 0.5rem;
            }
            
            /* Sidebar button */
            [data-testid="stSidebar"] button[kind="secondary"] {
                background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
                color: white !important;
                border: none !important;
                border-radius: 12px !important;
                font-weight: 600 !important;
                padding: 0.75rem !important;
                box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3) !important;
                transition: all 0.2s ease !important;
            }
            
            [data-testid="stSidebar"] button[kind="secondary"]:hover {
                background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%) !important;
                transform: translateY(-2px) !important;
                box-shadow: 0 6px 16px rgba(239, 68, 68, 0.4) !important;
            }
            
            /* Divider */
            [data-testid="stSidebar"] hr {
                margin: 1.5rem 0;
                border: none;
                border-top: 2px solid #e2e8f0;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Logo e título
        st.markdown('<div class="sidebar-title">💰 Finanças</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-subtitle">Gestão Financeira</div>', unsafe_allow_html=True)
        
        # Menu de navegação
        pagina = st.radio(
            "Navegação",
            options=[
                "📊 Dashboard",
                "➕ Nova Transação",
                "📋 Transações",
                "💳 Cartão de Crédito",
                "📈 Investimentos",
                "💰 Orçamentos",
                "🏷️ Categorias",
                "⚙️ Configurações",
            ],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Info do usuário (modo usuário único)
        nome = st.session_state.get("user_name") or "Usuário"
        email = st.session_state.get("user_email") or ""

        st.markdown('<div class="user-card">', unsafe_allow_html=True)
        st.markdown('<div class="user-avatar">👤</div>', unsafe_allow_html=True)
        st.markdown(
            f"<div style='color: #000000; font-size: 1rem; font-weight: 700; text-align: center; margin-bottom: 0.25rem;'>{nome}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='color: #64748b; font-size: 0.85rem; text-align: center;'>{email}</div>",
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        return pagina


def main():
    """Função principal do aplicativo"""

    # Modo sem autenticação (usuário único)
    if not ensure_single_user_session():
        return
    
    # Renderizar sidebar e obter página selecionada
    pagina = render_sidebar()
    
    # Renderizar página correspondente
    if pagina == "📊 Dashboard":
        render_dashboard_page()
    
    elif pagina == "📋 Transações":
        render_transacoes_page()
    
    elif pagina == "➕ Nova Transação":
        render_nova_transacao_page()
        
    elif pagina == "💰 Orçamentos":
        render_orcamentos_page()

    elif pagina == "💳 Cartão de Crédito":
        render_cartao_page()

    elif pagina == "📈 Investimentos":
        render_investimentos_page()
    
    elif pagina == "🏷️ Categorias":
        render_categorias_page()
    
    elif pagina == "⚙️ Configurações":
        render_configuracoes_page()


# ==================== EXECUÇÃO ====================

if __name__ == "__main__":
    main()
