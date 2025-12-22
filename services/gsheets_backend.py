from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


def parse_spreadsheet_id(value: str) -> str:
    """Aceita ID puro ou URL do Google Sheets e retorna o Spreadsheet ID."""
    if not value:
        return ""
    s = str(value).strip()
    if "/spreadsheets/d/" in s:
        try:
            return s.split("/spreadsheets/d/", 1)[1].split("/", 1)[0]
        except Exception:
            return ""
    return s


def load_service_account_info_from_env_or_secrets(st_secrets: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Carrega o JSON do Service Account.

    Suporta:
      - GOOGLE_SERVICE_ACCOUNT_JSON (string JSON)
      - st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
      - st.secrets["gcp_service_account"] (formato padrão do Streamlit)
    """

    env_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if env_json:
        try:
            return json.loads(env_json)
        except Exception as e:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON inválido no ambiente: " + str(e))

    if st_secrets:
        if "GOOGLE_SERVICE_ACCOUNT_JSON" in st_secrets and st_secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]:
            try:
                return json.loads(str(st_secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]))
            except Exception as e:
                raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON inválido em secrets: " + str(e))

        if "gcp_service_account" in st_secrets and st_secrets["gcp_service_account"]:
            val = st_secrets["gcp_service_account"]
            if isinstance(val, dict):
                return val
            try:
                return json.loads(str(val))
            except Exception as e:
                raise ValueError("gcp_service_account inválido em secrets: " + str(e))

    raise ValueError(
        "Service account não configurado. Defina GOOGLE_SERVICE_ACCOUNT_JSON (string) ou gcp_service_account (dict) em Secrets."
    )


class GoogleSheetsStore:
    """Persistência simples em Google Sheets.

    Implementa uma interface parecida com o storage local (read/write por 'kind').
    """

    def __init__(self, spreadsheet_id_or_url: str, service_account_info: dict[str, Any]):
        self.spreadsheet_id = parse_spreadsheet_id(spreadsheet_id_or_url)
        if not self.spreadsheet_id:
            raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID inválido")

        self._service_account_info = service_account_info
        self._client = None
        self._spreadsheet = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        try:
            import gspread
            from google.oauth2.service_account import Credentials
        except Exception as e:
            raise RuntimeError(
                "Dependências Google Sheets não instaladas. Garanta gspread e google-auth no requirements.txt. Erro: "
                + str(e)
            )

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        creds = Credentials.from_service_account_info(self._service_account_info, scopes=scopes)
        self._client = gspread.authorize(creds)
        return self._client

    def _get_spreadsheet(self):
        if self._spreadsheet is not None:
            return self._spreadsheet
        client = self._get_client()
        try:
            self._spreadsheet = client.open_by_key(self.spreadsheet_id)
            return self._spreadsheet
        except Exception as e:
            raise RuntimeError(
                "Não foi possível abrir a planilha. Verifique se ela foi compartilhada com o e-mail do service account. Erro: "
                + str(e)
            )

    def _worksheet(self, title: str):
        ss = self._get_spreadsheet()
        try:
            return ss.worksheet(title)
        except Exception:
            return None

    def ensure_worksheet(self, title: str, headers: list[str]):
        ss = self._get_spreadsheet()
        ws = self._worksheet(title)
        if ws is None:
            ws = ss.add_worksheet(title=title, rows=5000, cols=max(12, len(headers) + 2))
            if headers:
                ws.update([headers])
            return ws

        try:
            first_row = ws.row_values(1)
        except Exception:
            first_row = []

        if not first_row and headers:
            ws.update([headers])
        return ws

    def read_records(self, title: str) -> List[Dict[str, Any]]:
        ws = self._worksheet(title)
        if ws is None:
            return []

        values = ws.get_all_values()
        if not values or len(values) < 2:
            return []

        header = values[0]
        rows = values[1:]

        out: List[Dict[str, Any]] = []
        for row in rows:
            # normaliza tamanho
            row = (row + [""] * len(header))[: len(header)]
            rec = {header[i]: (row[i] if row[i] != "" else None) for i in range(len(header))}
            out.append(rec)
        return out

    def write_records(self, title: str, headers: list[str], records: List[Dict[str, Any]]) -> None:
        ws = self.ensure_worksheet(title, headers=headers)
        ws.clear()
        ws.update([headers])

        if not records:
            return

        values: List[List[Any]] = []
        for r in records:
            row: List[Any] = []
            for h in headers:
                v = r.get(h)
                if v is None:
                    row.append("")
                elif isinstance(v, (dict, list)):
                    row.append(json.dumps(v, ensure_ascii=False))
                else:
                    row.append(str(v))
            values.append(row)

        ws.update(values)

    @staticmethod
    def generate_id() -> str:
        import uuid

        return str(uuid.uuid4())


class FinanceSheetsSchema:
    """Schema de abas/colunas do app finanças."""

    USUARIOS = ("usuarios", ["id", "email", "nome", "ativo", "created_at", "updated_at"])
    CATEGORIAS = (
        "categorias",
        ["id", "user_id", "nome", "tipo", "icone", "ativo", "created_at", "updated_at"],
    )
    CONTAS = (
        "contas",
        [
            "id",
            "user_id",
            "nome",
            "tipo",
            "saldo_inicial",
            "data_saldo_inicial",
            "dia_fechamento",
            "dia_vencimento",
            "ativo",
            "created_at",
            "updated_at",
        ],
    )
    TRANSACOES = (
        "transacoes",
        [
            "id",
            "user_id",
            "conta_id",
            "categoria_id",
            "descricao",
            "valor",
            "tipo",
            "data",
            "status",
            "modo_lancamento",
            "recorrente_id",
            "transacao_prevista_id",
            "observacao",
            "ofx_fitid",
            "conciliado_em",
            "created_at",
            "updated_at",
        ],
    )
    RECORRENTES = (
        "transacoes_recorrentes",
        [
            "id",
            "user_id",
            "conta_id",
            "categoria_id",
            "descricao",
            "valor",
            "tipo",
            "dia_do_mes",
            "ativo",
            "created_at",
            "updated_at",
        ],
    )
    ORCAMENTOS = (
        "orcamentos",
        ["id", "user_id", "categoria_id", "valor_limite", "periodo", "ativo", "created_at", "updated_at"],
    )
    INVESTIMENTOS = (
        "investimentos",
        ["id", "user_id", "nome", "ativo", "created_at", "updated_at"],
    )
    INVESTIMENTOS_SALDOS = (
        "investimentos_saldos",
        [
            "id",
            "user_id",
            "investimento_id",
            "data_referencia",
            "data_conhecido_em",
            "saldo",
            "created_at",
            "updated_at",
        ],
    )

    @classmethod
    def all(cls) -> list[tuple[str, list[str]]]:
        return [
            cls.USUARIOS,
            cls.CATEGORIAS,
            cls.CONTAS,
            cls.TRANSACOES,
            cls.RECORRENTES,
            cls.ORCAMENTOS,
            cls.INVESTIMENTOS,
            cls.INVESTIMENTOS_SALDOS,
        ]


def coerce_bool(v: Any, default: bool = False) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"true", "1", "yes", "y", "sim"}:
        return True
    if s in {"false", "0", "no", "n", "nao", "não"}:
        return False
    return default


def coerce_int(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == "":
            return default
        return int(float(str(v).replace(",", ".")))
    except Exception:
        return default


def coerce_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(str(v).replace(",", "."))
    except Exception:
        return default


def now_iso() -> str:
    return datetime.now().isoformat()
