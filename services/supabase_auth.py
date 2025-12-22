from __future__ import annotations

from typing import Any, Dict, Optional

from config import Config


def _get_anon_key() -> str:
    return (getattr(Config, "SUPABASE_ANON_KEY", "") or getattr(Config, "SUPABASE_KEY", "")).strip()


def _looks_like_jwt(token: str) -> bool:
    s = (token or "").strip()
    # Supabase keys (anon/service_role) são JWTs.
    # Validação simples para evitar placeholders tipo "<anon_public_key>".
    return s.count(".") == 2 and len(s) > 40


def create_auth_client():
    try:
        from supabase import create_client
    except Exception as e:
        raise RuntimeError("Dependência Supabase não instalada (supabase). Erro: " + str(e))

    url = (getattr(Config, "SUPABASE_URL", "") or "").strip()
    key = _get_anon_key()
    if not url:
        raise RuntimeError("SUPABASE_URL não está definido")
    if not key:
        raise RuntimeError("SUPABASE_ANON_KEY não está definido")

    if not _looks_like_jwt(key):
        raise RuntimeError(
            "SUPABASE_ANON_KEY inválida. Use a chave ANON (public) do seu projeto em Project Settings → API. "
            "Ela normalmente começa com 'eyJ' e contém dois pontos '.' (formato JWT)."
        )
    return create_client(url, key)


def _pick(obj: Any, key: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def sign_in_with_password(email: str, password: str) -> Dict[str, str]:
    client = create_auth_client()
    resp = client.auth.sign_in_with_password({"email": email, "password": password})
    session = _pick(resp, "session")
    user = _pick(resp, "user")

    access_token = _pick(session, "access_token", "")
    refresh_token = _pick(session, "refresh_token", "")
    user_id = _pick(user, "id", "")
    user_email = _pick(user, "email", "")

    if not access_token or not user_id:
        raise RuntimeError("Login falhou: sessão inválida retornada pelo Supabase")

    return {
        "access_token": str(access_token),
        "refresh_token": str(refresh_token or ""),
        "user_id": str(user_id),
        "email": str(user_email or email),
    }


def sign_up(email: str, password: str) -> Dict[str, str]:
    client = create_auth_client()
    resp = client.auth.sign_up({"email": email, "password": password})
    session = _pick(resp, "session")
    user = _pick(resp, "user")

    # Dependendo da config do Supabase (email confirmation), a session pode vir vazia.
    access_token = _pick(session, "access_token", "")
    refresh_token = _pick(session, "refresh_token", "")
    user_id = _pick(user, "id", "")

    if not user_id:
        raise RuntimeError("Cadastro falhou: usuário inválido retornado pelo Supabase")

    return {
        "access_token": str(access_token or ""),
        "refresh_token": str(refresh_token or ""),
        "user_id": str(user_id),
        "email": str(_pick(user, "email", email) or email),
    }


def sign_out(access_token: Optional[str] = None) -> None:
    try:
        client = create_auth_client()
        # Algumas versões aceitam sign_out() sem args.
        client.auth.sign_out()
    except Exception:
        # Não bloqueia o app: logout local via session_state é suficiente.
        return
