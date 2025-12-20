"""
Configurações do aplicativo de Finanças Pessoais
"""
import os
from dotenv import load_dotenv

try:
    import streamlit as st
except Exception:
    st = None

load_dotenv()


def _get_secret(key: str, default: str = "") -> str:
    """Busca config primeiro em env vars, depois em st.secrets (Streamlit Cloud)."""
    value = os.getenv(key)
    if value is not None and value != "":
        return value

    if st is None:
        return default

    try:
        if key in st.secrets and st.secrets.get(key) not in (None, ""):
            return str(st.secrets.get(key))

        # Permite formato em seção, ex: [supabase] url=... key=...
        if key == "SUPABASE_URL":
            return str(st.secrets.get("supabase", {}).get("url", default))
        if key == "SUPABASE_KEY":
            return str(st.secrets.get("supabase", {}).get("key", default))
    except Exception:
        return default

    return default

class Config:
    """Configurações base do aplicativo"""
    
    # Supabase
    SUPABASE_URL = _get_secret("SUPABASE_URL", "")
    SUPABASE_KEY = _get_secret("SUPABASE_KEY", "")
    
    # App
    APP_NAME = _get_secret("APP_NAME", "Finanças Pessoais")
    SECRET_KEY = _get_secret("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = _get_secret("DEBUG", "False").lower() == "true"
    
    # Categorias padrão
    CATEGORIAS_PADRAO = {
        "despesas": [
            {"nome": "Alimentação", "icone": "🍔"},
            {"nome": "Transporte", "icone": "🚗"},
            {"nome": "Moradia", "icone": "🏠"},
            {"nome": "Saúde", "icone": "💊"},
            {"nome": "Educação", "icone": "📚"},
            {"nome": "Lazer", "icone": "🎬"},
            {"nome": "Vestuário", "icone": "👕"},
            {"nome": "Serviços", "icone": "🔧"},
            {"nome": "Outros", "icone": "📦"},
        ],
        "receitas": [
            {"nome": "Salário", "icone": "💰"},
            {"nome": "Freelance", "icone": "💻"},
            {"nome": "Investimentos", "icone": "📈"},
            {"nome": "Presente", "icone": "🎁"},
            {"nome": "Outros", "icone": "💵"},
        ]
    }
    
    # Palavras-chave para categorização automática
    PALAVRAS_CHAVE_CATEGORIAS = {
        "Alimentação": [
            "supermercado", "mercado", "padaria", "restaurante", "lanchonete",
            "açougue", "hortifruti", "feira", "delivery", "ifood", "rappi",
            "carrefour", "pão de açúcar", "extra", "assaí", "atacadão"
        ],
        "Transporte": [
            "posto", "combustível", "gasolina", "etanol", "diesel", "uber",
            "99", "cabify", "estacionamento", "pedágio", "oficina", "ipva"
        ],
        "Saúde": [
            "farmácia", "drogaria", "hospital", "clínica", "laboratório",
            "droga", "raia", "drogasil", "pague menos", "ultrafarma"
        ],
        "Vestuário": [
            "loja", "roupa", "calçado", "sapato", "renner", "riachuelo",
            "c&a", "zara", "hering", "marisa"
        ],
        "Lazer": [
            "cinema", "teatro", "show", "ingresso", "netflix", "spotify",
            "amazon", "disney", "hbo", "streaming"
        ],
        "Educação": [
            "livraria", "livro", "curso", "escola", "faculdade", "udemy",
            "alura", "coursera"
        ],
        "Serviços": [
            "luz", "água", "internet", "telefone", "celular", "gás",
            "condomínio", "seguro", "banco"
        ]
    }
    
    # Configurações de OCR
    OCR_IDIOMAS = ['pt', 'en']
    OCR_GPU = False  # Usar CPU por padrão
    
    # Limites
    MAX_UPLOAD_SIZE_MB = 10
    MAX_ITENS_POR_PAGINA = 50
