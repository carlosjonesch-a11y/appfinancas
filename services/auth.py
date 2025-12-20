"""
Serviço de autenticação para o aplicativo de Finanças Pessoais
Usa streamlit-authenticator com armazenamento local em YAML
"""
import streamlit as st
import yaml
from yaml.loader import SafeLoader
from pathlib import Path
from typing import Optional, Dict, Tuple
import bcrypt
from datetime import datetime

from config import Config
from services.database import db


# Caminho para arquivo de credenciais
CREDENTIALS_FILE = Path(__file__).parent.parent / "data" / "credentials.yaml"


def ensure_data_dir():
    """Garante que o diretório de dados existe"""
    data_dir = CREDENTIALS_FILE.parent
    data_dir.mkdir(parents=True, exist_ok=True)


def hash_password(password: str) -> str:
    """Gera hash da senha"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verifica se a senha corresponde ao hash"""
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def load_credentials() -> Dict:
    """Carrega credenciais do arquivo YAML"""
    ensure_data_dir()
    
    if CREDENTIALS_FILE.exists():
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as file:
            config = yaml.load(file, Loader=SafeLoader)
            config = config or get_default_credentials()
    else:
        config = get_default_credentials()

    # Sempre forçar cookie key a vir do Config (env/secrets), evita drift entre ambientes
    try:
        config.setdefault("cookie", {})
        config["cookie"]["key"] = Config.SECRET_KEY
        config["cookie"].setdefault("name", "financas_auth")
        config["cookie"].setdefault("expiry_days", 30)
    except Exception:
        pass

    return config


def save_credentials(config: Dict):
    """Salva credenciais no arquivo YAML"""
    ensure_data_dir()
    
    with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as file:
        yaml.dump(config, file, default_flow_style=False, allow_unicode=True)


def get_default_credentials() -> Dict:
    """Retorna estrutura padrão de credenciais"""
    return {
        "credentials": {
            "usernames": {}
        },
        "cookie": {
            "expiry_days": 30,
            "key": Config.SECRET_KEY,
            "name": "financas_auth"
        },
        "preauthorized": {
            "emails": []
        }
    }


class AuthService:
    """Serviço de autenticação simplificado para Streamlit"""
    AUTH_TABLE = "auth_credenciais"
    
    def __init__(self):
        self.config = get_default_credentials()
        if not self._use_supabase_auth():
            self.config = load_credentials()
        self._init_session_state()

    def _use_supabase_auth(self) -> bool:
        """Define se a autenticação deve ser persistida no Supabase."""
        try:
            return bool(db.is_connected and (not db.is_local) and getattr(db, "_client", None) is not None)
        except Exception:
            return False

    def _supabase_client(self):
        return getattr(db, "_client", None)

    def _supabase_get_by_username(self, username: str) -> Optional[Dict]:
        client = self._supabase_client()
        if not client:
            return None
        result = client.table(self.AUTH_TABLE).select("*").eq("username", username).limit(1).execute()
        return result.data[0] if result.data else None

    def _supabase_get_by_email(self, email: str) -> Optional[Dict]:
        client = self._supabase_client()
        if not client:
            return None
        result = client.table(self.AUTH_TABLE).select("*").eq("email", email).limit(1).execute()
        return result.data[0] if result.data else None

    def has_any_users(self) -> bool:
        """Usado só para UX (mostrar dica quando não existe nenhum usuário)."""
        if self._use_supabase_auth():
            client = self._supabase_client()
            if not client:
                return False
            try:
                # "count" varia por lib/versão; usar select mínimo
                result = client.table(self.AUTH_TABLE).select("id").limit(1).execute()
                return bool(result.data)
            except Exception:
                return False

        try:
            return bool(self.config.get("credentials", {}).get("usernames"))
        except Exception:
            return False
    
    def _init_session_state(self):
        """Inicializa variáveis de sessão"""
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
        if "username" not in st.session_state:
            st.session_state.username = None
        if "user_id" not in st.session_state:
            st.session_state.user_id = None
        if "user_name" not in st.session_state:
            st.session_state.user_name = None
        if "user_email" not in st.session_state:
            st.session_state.user_email = None
    
    def register_user(self, email: str, nome: str, username: str, password: str) -> Tuple[bool, str]:
        """Registra um novo usuário"""
        # Validações
        if not email or not nome or not username or not password:
            return False, "Todos os campos são obrigatórios"
        
        if len(password) < 6:
            return False, "A senha deve ter pelo menos 6 caracteres"
        
        if len(username) < 3:
            return False, "O nome de usuário deve ter pelo menos 3 caracteres"
        
        # Backend Supabase (persistente)
        if self._use_supabase_auth():
            try:
                if self._supabase_get_by_username(username):
                    return False, "Nome de usuário já existe"
                if self._supabase_get_by_email(email):
                    return False, "Email já cadastrado"

                password_hash = hash_password(password)

                # Criar usuário no banco principal e categorias padrão
                db_user = db.criar_usuario(email=email, nome=nome)
                if db_user:
                    db.criar_categorias_padrao(db_user["id"])
                    user_id = db_user["id"]
                else:
                    # Fallback: sem usuario no banco principal
                    user_id = None

                payload = {
                    "username": username,
                    "email": email,
                    "nome": nome,
                    "password_hash": password_hash,
                    "user_id": user_id,
                }
                client = self._supabase_client()
                client.table(self.AUTH_TABLE).insert(payload).execute()
                return True, "Usuário registrado com sucesso!"
            except Exception as e:
                # Erro comum: tabela auth_credenciais não existe
                msg = str(e)
                if "auth_credenciais" in msg and ("does not exist" in msg.lower() or "not exist" in msg.lower()):
                    return False, "Tabela de autenticação não existe no Supabase. Execute o SQL em supabase_update.sql e tente novamente."
                return False, f"Erro ao registrar usuário: {msg}"

        # Backend local (YAML)
        if username in self.config["credentials"]["usernames"]:
            return False, "Nome de usuário já existe"

        for user_data in self.config["credentials"]["usernames"].values():
            if user_data.get("email") == email:
                return False, "Email já cadastrado"
        
        # Criar usuário
        password_hash = hash_password(password)
        user_id = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}_{username}"
        
        self.config["credentials"]["usernames"][username] = {
            "email": email,
            "name": nome,
            "password": password_hash,
            "user_id": user_id,
            "created_at": datetime.now().isoformat()
        }
        
        save_credentials(self.config)
        
        # Criar categorias padrão no banco (se conectado)
        if db.is_connected:
            db_user = db.criar_usuario(email=email, nome=nome)
            if db_user:
                db.criar_categorias_padrao(db_user["id"])
                # Atualizar user_id com o do banco
                self.config["credentials"]["usernames"][username]["user_id"] = db_user["id"]
                save_credentials(self.config)
        
        return True, "Usuário registrado com sucesso!"
    
    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """Realiza login do usuário"""
        if not username or not password:
            return False, "Preencha usuário e senha"

        # Backend Supabase (persistente)
        if self._use_supabase_auth():
            try:
                user_data = self._supabase_get_by_username(username)
                if not user_data:
                    return False, "Usuário não encontrado"

                if not verify_password(password, user_data.get("password_hash", "")):
                    return False, "Senha incorreta"

                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.user_id = user_data.get("user_id", username)
                st.session_state.user_name = user_data.get("nome", username)
                st.session_state.user_email = user_data.get("email", "")

                return True, f"Bem-vindo(a), {user_data.get('nome', username)}!"
            except Exception as e:
                return False, f"Erro ao autenticar: {str(e)}"
        
        users = self.config["credentials"]["usernames"]
        
        if username not in users:
            return False, "Usuário não encontrado"
        
        user_data = users[username]
        
        if not verify_password(password, user_data["password"]):
            return False, "Senha incorreta"
        
        # Autenticado com sucesso
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.user_id = user_data.get("user_id", username)
        st.session_state.user_name = user_data.get("name", username)
        st.session_state.user_email = user_data.get("email", "")
        
        return True, f"Bem-vindo(a), {user_data.get('name', username)}!"
    
    def logout(self):
        """Realiza logout do usuário"""
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.user_id = None
        st.session_state.user_name = None
        st.session_state.user_email = None
    
    def is_authenticated(self) -> bool:
        """Verifica se usuário está autenticado"""
        return st.session_state.get("authenticated", False)
    
    def get_current_user(self) -> Optional[Dict]:
        """Retorna dados do usuário atual"""
        if not self.is_authenticated():
            return None
        
        return {
            "username": st.session_state.username,
            "user_id": st.session_state.user_id,
            "name": st.session_state.user_name,
            "email": st.session_state.user_email
        }
    
    def get_user_id(self) -> Optional[str]:
        """Retorna ID do usuário atual"""
        return st.session_state.get("user_id")


def render_login_page():
    """Renderiza página de login/registro"""
    auth = AuthService()
    
    st.title("💰 Finanças Pessoais")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Cadastro"])
    
    with tab1:
        st.subheader("Entrar")

        if not auth.has_any_users():
            st.info("Nenhum usuário cadastrado neste deploy ainda. Vá na aba **Cadastro** e crie o primeiro usuário.")
        
        with st.form("login_form"):
            username = st.text_input("Usuário", key="login_username")
            password = st.text_input("Senha", type="password", key="login_password")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                submit = st.form_submit_button("Entrar", width='stretch')
            
            if submit:
                success, message = auth.login(username, password)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    
    with tab2:
        st.subheader("Criar Conta")
        
        with st.form("register_form"):
            nome = st.text_input("Nome completo", key="reg_nome")
            email = st.text_input("Email", key="reg_email")
            username = st.text_input("Nome de usuário", key="reg_username")
            password = st.text_input("Senha", type="password", key="reg_password")
            password_confirm = st.text_input("Confirmar senha", type="password", key="reg_password_confirm")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                submit = st.form_submit_button("Cadastrar", width='stretch')
            
            if submit:
                if password != password_confirm:
                    st.error("As senhas não coincidem")
                else:
                    success, message = auth.register_user(email, nome, username, password)
                    if success:
                        st.success(message)
                        st.info("Faça login para continuar")
                    else:
                        st.error(message)


def require_auth(func):
    """Decorator para exigir autenticação"""
    def wrapper(*args, **kwargs):
        auth = AuthService()
        if not auth.is_authenticated():
            render_login_page()
            return None
        return func(*args, **kwargs)
    return wrapper
