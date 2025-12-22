"""Serviço de persistência do app.

Este projeto foi simplificado para rodar sem autenticação.

Backends suportados:
- local: arquivos JSON em `data/`
- gsheets: Google Sheets (Service Account)

Seleção via env/secrets:
- STORAGE_BACKEND=local|gsheets
- GOOGLE_SHEETS_SPREADSHEET_ID=<id ou url>

Credenciais (gsheets):
- st.secrets["gcp_service_account"] (recomendado no Streamlit Cloud)
    ou GOOGLE_SERVICE_ACCOUNT_JSON (string JSON)
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import Config


class LocalDatabase:
    """Banco de dados local usando arquivos JSON."""

    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir) if data_dir is not None else (Path(__file__).parent.parent / "data")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.usuarios_file = self.data_dir / "usuarios.json"
        self.categorias_file = self.data_dir / "categorias.json"
        self.contas_file = self.data_dir / "contas.json"
        self.transacoes_file = self.data_dir / "transacoes.json"
        self.recorrentes_file = self.data_dir / "transacoes_recorrentes.json"
        self.orcamentos_file = self.data_dir / "orcamentos.json"
        self.investimentos_file = self.data_dir / "investimentos.json"
        self.investimentos_saldos_file = self.data_dir / "investimentos_saldos.json"

        self._init_files()

    def _init_files(self) -> None:
        for f in [
            self.usuarios_file,
            self.categorias_file,
            self.contas_file,
            self.transacoes_file,
            self.recorrentes_file,
            self.orcamentos_file,
            self.investimentos_file,
            self.investimentos_saldos_file,
        ]:
            if not f.exists():
                f.write_text("[]", encoding="utf-8")

    def read(self, file: Path) -> List[Dict[str, Any]]:
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def write(self, file: Path, data: List[Dict[str, Any]]) -> None:
        file.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    @staticmethod
    def generate_id() -> str:
        return str(uuid.uuid4())


class GoogleSheetsDatabase:
    """Banco de dados usando Google Sheets, mantendo a mesma interface do LocalDatabase."""

    def __init__(self, spreadsheet_id_or_url: str, service_account_info: dict[str, Any]):
        from services.gsheets_backend import FinanceSheetsSchema, GoogleSheetsStore, coerce_bool, coerce_float, coerce_int

        # "Markers" de arquivo para compatibilidade com o código existente.
        self.usuarios_file = Path("usuarios.json")
        self.categorias_file = Path("categorias.json")
        self.contas_file = Path("contas.json")
        self.transacoes_file = Path("transacoes.json")
        self.recorrentes_file = Path("transacoes_recorrentes.json")
        self.orcamentos_file = Path("orcamentos.json")
        self.investimentos_file = Path("investimentos.json")
        self.investimentos_saldos_file = Path("investimentos_saldos.json")

        self._store = GoogleSheetsStore(spreadsheet_id_or_url=spreadsheet_id_or_url, service_account_info=service_account_info)
        self._coerce_bool = coerce_bool
        self._coerce_float = coerce_float
        self._coerce_int = coerce_int

        self._schema_by_filename: dict[str, tuple[str, list[str]]] = {
            "usuarios.json": FinanceSheetsSchema.USUARIOS,
            "categorias.json": FinanceSheetsSchema.CATEGORIAS,
            "contas.json": FinanceSheetsSchema.CONTAS,
            "transacoes.json": FinanceSheetsSchema.TRANSACOES,
            "transacoes_recorrentes.json": FinanceSheetsSchema.RECORRENTES,
            "orcamentos.json": FinanceSheetsSchema.ORCAMENTOS,
            "investimentos.json": FinanceSheetsSchema.INVESTIMENTOS,
            "investimentos_saldos.json": FinanceSheetsSchema.INVESTIMENTOS_SALDOS,
        }

        for title, headers in FinanceSheetsSchema.all():
            self._store.ensure_worksheet(title, headers=headers)

    def read(self, file: Path) -> List[Dict[str, Any]]:
        filename = Path(file).name
        title, _headers = self._schema_by_filename[filename]
        records = self._store.read_records(title)

        # Coerções mínimas: no Sheets tudo chega como string e "False" é truthy.
        if filename in {
            "usuarios.json",
            "categorias.json",
            "contas.json",
            "transacoes_recorrentes.json",
            "orcamentos.json",
            "investimentos.json",
        }:
            for r in records:
                r["ativo"] = self._coerce_bool(r.get("ativo"), default=True)

        if filename == "contas.json":
            for r in records:
                r["saldo_inicial"] = self._coerce_float(r.get("saldo_inicial"), default=0.0)
                df = self._coerce_int(r.get("dia_fechamento"), default=0)
                dv = self._coerce_int(r.get("dia_vencimento"), default=0)
                r["dia_fechamento"] = df or None
                r["dia_vencimento"] = dv or None

        if filename == "transacoes.json":
            for r in records:
                r["valor"] = self._coerce_float(r.get("valor"), default=0.0)

        if filename == "transacoes_recorrentes.json":
            for r in records:
                r["valor"] = self._coerce_float(r.get("valor"), default=0.0)
                r["dia_do_mes"] = self._coerce_int(r.get("dia_do_mes"), default=1)

        if filename == "orcamentos.json":
            for r in records:
                r["valor_limite"] = self._coerce_float(r.get("valor_limite"), default=0.0)

        if filename == "investimentos_saldos.json":
            for r in records:
                r["saldo"] = self._coerce_float(r.get("saldo"), default=0.0)

        return records

    def write(self, file: Path, data: List[Dict[str, Any]]) -> None:
        filename = Path(file).name
        title, headers = self._schema_by_filename[filename]
        self._store.write_records(title, headers=headers, records=data)

    @staticmethod
    def generate_id() -> str:
        return str(uuid.uuid4())


class DatabaseService:
    """API de dados usada pelas páginas.

    Mantém a compatibilidade com o código existente (read/write por "arquivo").
    """

    _instance: Optional["DatabaseService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_local_db"):
            backend = (Config.STORAGE_BACKEND or "local").strip().lower()
            print(f"ℹ️ STORAGE_BACKEND={backend}")
            if backend == "gsheets":
                try:
                    try:
                        import streamlit as st
                    except Exception:
                        st = None

                    if not (Config.GOOGLE_SHEETS_SPREADSHEET_ID or "").strip():
                        raise RuntimeError("GOOGLE_SHEETS_SPREADSHEET_ID não está definido")

                    from services.gsheets_backend import load_service_account_info_from_env_or_secrets

                    service_account_info = load_service_account_info_from_env_or_secrets(st.secrets if st is not None else None)
                    self._local_db = GoogleSheetsDatabase(
                        spreadsheet_id_or_url=Config.GOOGLE_SHEETS_SPREADSHEET_ID,
                        service_account_info=service_account_info,
                    )
                    print("✅ Google Sheets inicializado com sucesso")
                except Exception as e:
                    msg = (
                        "Falha ao inicializar Google Sheets.\n"
                        "- Confirme STORAGE_BACKEND=gsheets\n"
                        "- Confirme GOOGLE_SHEETS_SPREADSHEET_ID\n"
                        "- Em Secrets, defina gcp_service_account (service account JSON)\n"
                        "- Compartilhe a planilha com o client_email do service account (Editor)\n"
                        f"Erro: {type(e).__name__}: {e}"
                    )
                    print("❌ " + msg)
                    raise RuntimeError(msg) from e
            else:
                self._local_db = LocalDatabase()

    @property
    def is_connected(self) -> bool:
        return True

    @property
    def is_local(self) -> bool:
        return (Config.STORAGE_BACKEND or "local").strip().lower() != "gsheets"

    # ==================== USUÁRIOS ====================

    def criar_usuario(self, email: str, nome: str) -> Optional[Dict[str, Any]]:
        usuarios = self._local_db.read(self._local_db.usuarios_file)
        novo = {
            "id": self._local_db.generate_id(),
            "email": (email or "").strip(),
            "nome": (nome or "").strip() or "Usuário",
            "ativo": True,
            "created_at": datetime.now().isoformat(),
        }
        usuarios.append(novo)
        self._local_db.write(self._local_db.usuarios_file, usuarios)
        return novo

    def buscar_usuario_por_email(self, email: str) -> Optional[Dict[str, Any]]:
        email_norm = (email or "").strip()
        if not email_norm:
            return None
        usuarios = self._local_db.read(self._local_db.usuarios_file)
        return next((u for u in usuarios if u.get("email") == email_norm), None)

    def buscar_usuario_por_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        uid = str(user_id or "")
        if not uid:
            return None
        usuarios = self._local_db.read(self._local_db.usuarios_file)
        return next((u for u in usuarios if u.get("id") == uid), None)

    # ==================== CATEGORIAS ====================

    def criar_categorias_padrao(self, user_id: str) -> bool:
        categorias = self._local_db.read(self._local_db.categorias_file)
        for tipo, cats in Config.CATEGORIAS_PADRAO.items():
            for cat in cats:
                categorias.append(
                    {
                        "id": self._local_db.generate_id(),
                        "user_id": user_id,
                        "nome": cat["nome"],
                        "tipo": "receita" if tipo == "receitas" else "despesa",
                        "icone": cat["icone"],
                        "ativo": True,
                        "created_at": datetime.now().isoformat(),
                    }
                )
        self._local_db.write(self._local_db.categorias_file, categorias)
        return True

    def listar_categorias(self, user_id: str, tipo: str | None = None, include_inactive: bool = False) -> List[Dict[str, Any]]:
        categorias = self._local_db.read(self._local_db.categorias_file)
        resultado = [c for c in categorias if c.get("user_id") == user_id and (include_inactive or c.get("ativo", True))]
        if tipo:
            resultado = [c for c in resultado if c.get("tipo") == tipo]
        return sorted(resultado, key=lambda x: x.get("nome", ""))

    def criar_categoria(self, user_id: str, nome: str, tipo: str, icone: str = "📦") -> Optional[Dict[str, Any]]:
        categorias = self._local_db.read(self._local_db.categorias_file)
        nova = {
            "id": self._local_db.generate_id(),
            "user_id": user_id,
            "nome": (nome or "").strip(),
            "tipo": tipo,
            "icone": icone,
            "ativo": True,
            "created_at": datetime.now().isoformat(),
        }
        categorias.append(nova)
        self._local_db.write(self._local_db.categorias_file, categorias)
        return nova

    def atualizar_categoria(self, categoria_id: str, dados: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        categorias = self._local_db.read(self._local_db.categorias_file)
        for i, c in enumerate(categorias):
            if c.get("id") == categoria_id:
                categorias[i] = {**c, **dados, "updated_at": datetime.now().isoformat()}
                self._local_db.write(self._local_db.categorias_file, categorias)
                return categorias[i]
        return None

    def deletar_categoria(self, categoria_id: str) -> bool:
        return self.atualizar_categoria(categoria_id, {"ativo": False}) is not None

    # ==================== CONTAS ====================

    def listar_contas(self, user_id: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
        contas = self._local_db.read(self._local_db.contas_file)
        resultado = [c for c in contas if c.get("user_id") == user_id and (include_inactive or c.get("ativo", True))]
        return sorted(resultado, key=lambda x: x.get("nome", ""))

    def criar_conta(
        self,
        user_id: str,
        nome: str,
        tipo: str,
        saldo_inicial: float = 0.0,
        data_saldo_inicial: date | str | None = None,
        dia_fechamento: int | None = None,
        dia_vencimento: int | None = None,
    ) -> Optional[Dict[str, Any]]:
        if not data_saldo_inicial:
            data_saldo_inicial = date.today()
        if isinstance(data_saldo_inicial, date):
            data_saldo_inicial = data_saldo_inicial.isoformat()

        contas = self._local_db.read(self._local_db.contas_file)
        nova = {
            "id": self._local_db.generate_id(),
            "user_id": user_id,
            "nome": (nome or "").strip(),
            "tipo": (tipo or "").strip(),
            "saldo_inicial": float(saldo_inicial or 0),
            "data_saldo_inicial": data_saldo_inicial,
            "dia_fechamento": dia_fechamento,
            "dia_vencimento": dia_vencimento,
            "ativo": True,
            "created_at": datetime.now().isoformat(),
        }
        contas.append(nova)
        self._local_db.write(self._local_db.contas_file, contas)
        return nova

    def atualizar_conta(self, conta_id: str, dados: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        contas = self._local_db.read(self._local_db.contas_file)
        for i, c in enumerate(contas):
            if c.get("id") == conta_id:
                patch = dict(dados)
                if isinstance(patch.get("data_saldo_inicial"), date):
                    patch["data_saldo_inicial"] = patch["data_saldo_inicial"].isoformat()
                contas[i] = {**c, **patch, "updated_at": datetime.now().isoformat()}
                self._local_db.write(self._local_db.contas_file, contas)
                return contas[i]
        return None

    def deletar_conta(self, conta_id: str) -> bool:
        return self.atualizar_conta(conta_id, {"ativo": False}) is not None

    # ==================== RECORRENTES ====================

    def listar_recorrentes(
        self,
        user_id: str,
        conta_id: str | None = None,
        tipo: str | None = None,
        include_inactive: bool = False,
    ) -> List[Dict[str, Any]]:
        recorrentes = self._local_db.read(self._local_db.recorrentes_file)
        resultado = [r for r in recorrentes if r.get("user_id") == user_id and (include_inactive or r.get("ativo", True))]
        if conta_id:
            resultado = [r for r in resultado if r.get("conta_id") == conta_id]
        if tipo:
            resultado = [r for r in resultado if r.get("tipo") == tipo]
        return sorted(resultado, key=lambda x: (int(x.get("dia_do_mes") or 1), x.get("descricao", "")))

    def criar_recorrente(self, recorrente: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        recorrentes = self._local_db.read(self._local_db.recorrentes_file)
        novo = {
            "id": self._local_db.generate_id(),
            **recorrente,
            "ativo": bool(recorrente.get("ativo", True)),
            "created_at": datetime.now().isoformat(),
        }
        recorrentes.append(novo)
        self._local_db.write(self._local_db.recorrentes_file, recorrentes)
        return novo

    def atualizar_recorrente(self, recorrente_id: str, dados: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        recorrentes = self._local_db.read(self._local_db.recorrentes_file)
        for i, r in enumerate(recorrentes):
            if r.get("id") == recorrente_id:
                recorrentes[i] = {**r, **dados, "updated_at": datetime.now().isoformat()}
                self._local_db.write(self._local_db.recorrentes_file, recorrentes)
                return recorrentes[i]
        return None

    def deletar_recorrente(self, recorrente_id: str) -> bool:
        return self.atualizar_recorrente(recorrente_id, {"ativo": False}) is not None

    def gerar_previstas_mes(self, user_id: str, ano: int, mes: int, conta_id: str | None = None) -> List[Dict[str, Any]]:
        from calendar import monthrange

        ultimo_dia = monthrange(ano, mes)[1]
        data_inicio = date(ano, mes, 1)
        data_fim = date(ano, mes, ultimo_dia)

        recorrentes = self.listar_recorrentes(user_id, conta_id=conta_id, include_inactive=False)
        if not recorrentes:
            return []

        existentes = self.listar_transacoes(
            user_id=user_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            limite=5000,
            incluir_previstas=True,
        )
        existentes_por_recorrente = {
            t.get("recorrente_id")
            for t in existentes
            if t.get("recorrente_id") and t.get("status") in {"prevista", "realizada", "substituida"}
        }

        lote: List[Dict[str, Any]] = []
        for r in recorrentes:
            rid = r.get("id")
            if not rid or rid in existentes_por_recorrente:
                continue

            dia = int(r.get("dia_do_mes") or 1)
            dia = min(max(dia, 1), ultimo_dia)
            data_prevista = date(ano, mes, dia)

            lote.append(
                {
                    "user_id": user_id,
                    "conta_id": r.get("conta_id"),
                    "categoria_id": r.get("categoria_id"),
                    "descricao": r.get("descricao"),
                    "valor": float(r.get("valor") or 0),
                    "tipo": r.get("tipo"),
                    "data": data_prevista.isoformat(),
                    "status": "prevista",
                    "modo_lancamento": "manual",
                    "recorrente_id": rid,
                }
            )

        return self.criar_transacoes_em_lote(lote) if lote else []

    def criar_real_a_partir_da_prevista(self, prevista_id: str, data_real: date | str | None = None) -> Optional[Dict[str, Any]]:
        if not data_real:
            data_real_str = date.today().isoformat()
        elif isinstance(data_real, date):
            data_real_str = data_real.isoformat()
        else:
            data_real_str = data_real

        transacoes = self._local_db.read(self._local_db.transacoes_file)
        prev = next((t for t in transacoes if t.get("id") == prevista_id), None)
        if not prev or prev.get("status") != "prevista":
            return None

        real = {
            "user_id": prev.get("user_id"),
            "conta_id": prev.get("conta_id"),
            "categoria_id": prev.get("categoria_id"),
            "descricao": prev.get("descricao"),
            "valor": float(prev.get("valor") or 0),
            "tipo": prev.get("tipo"),
            "data": data_real_str,
            "status": "realizada",
            "modo_lancamento": "manual",
            "recorrente_id": prev.get("recorrente_id"),
            "transacao_prevista_id": prevista_id,
            "observacao": prev.get("observacao"),
        }

        criada = self.criar_transacao(real)
        if not criada:
            return None

        self.atualizar_transacao(prevista_id, {"status": "substituida"})
        return criada

    # ==================== TRANSAÇÕES ====================

    def criar_transacao(self, transacao: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        transacoes = self._local_db.read(self._local_db.transacoes_file)
        nova = {
            "id": self._local_db.generate_id(),
            **transacao,
            "status": transacao.get("status") or "realizada",
            "created_at": datetime.now().isoformat(),
        }
        if isinstance(nova.get("data"), (datetime, date)):
            nova["data"] = nova["data"].isoformat()

        transacoes.append(nova)
        self._local_db.write(self._local_db.transacoes_file, transacoes)
        return nova

    def criar_transacoes_em_lote(self, transacoes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        criadas: List[Dict[str, Any]] = []
        for t in transacoes:
            r = self.criar_transacao(t)
            if r:
                criadas.append(r)
        return criadas

    def listar_transacoes(
        self,
        user_id: str,
        data_inicio: date | str | None = None,
        data_fim: date | str | None = None,
        tipo: str | None = None,
        categoria_id: str | None = None,
        conta_id: str | None = None,
        limite: int = 100,
        incluir_previstas: bool = False,
    ) -> List[Dict[str, Any]]:
        transacoes = self._local_db.read(self._local_db.transacoes_file)
        categorias = self._local_db.read(self._local_db.categorias_file)
        contas = self._local_db.read(self._local_db.contas_file)
        cat_map = {c.get("id"): c for c in categorias if c.get("id")}
        conta_map = {c.get("id"): c for c in contas if c.get("id")}

        resultado = [t for t in transacoes if t.get("user_id") == user_id]
        if not incluir_previstas:
            resultado = [t for t in resultado if (t.get("status") in (None, "realizada"))]

        if data_inicio:
            ini = data_inicio.isoformat() if isinstance(data_inicio, date) else str(data_inicio)
            resultado = [t for t in resultado if str(t.get("data", "")) >= ini]
        if data_fim:
            fim = data_fim.isoformat() if isinstance(data_fim, date) else str(data_fim)
            resultado = [t for t in resultado if str(t.get("data", "")) <= fim]

        if tipo:
            resultado = [t for t in resultado if t.get("tipo") == tipo]
        if categoria_id:
            resultado = [t for t in resultado if t.get("categoria_id") == categoria_id]
        if conta_id:
            resultado = [t for t in resultado if t.get("conta_id") == conta_id]

        # Copiar e enriquecer sem alterar o JSON original em memória
        enriched: List[Dict[str, Any]] = []
        for t in resultado:
            t2 = dict(t)
            cid = t2.get("categoria_id")
            if cid and cid in cat_map:
                t2["categorias"] = cat_map[cid]
            acc = t2.get("conta_id")
            if acc and acc in conta_map:
                t2["contas"] = conta_map[acc]
            enriched.append(t2)

        enriched.sort(key=lambda x: str(x.get("data", "")), reverse=True)
        return enriched[: int(limite or 100)]

    def atualizar_transacao(self, transacao_id: str, dados: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        transacoes = self._local_db.read(self._local_db.transacoes_file)
        for i, t in enumerate(transacoes):
            if t.get("id") == transacao_id:
                patch = dict(dados)
                if isinstance(patch.get("data"), (datetime, date)):
                    patch["data"] = patch["data"].isoformat()
                transacoes[i] = {**t, **patch, "updated_at": datetime.now().isoformat()}
                self._local_db.write(self._local_db.transacoes_file, transacoes)
                return transacoes[i]
        return None

    def deletar_transacao(self, transacao_id: str) -> bool:
        transacoes = self._local_db.read(self._local_db.transacoes_file)
        novo = [t for t in transacoes if t.get("id") != transacao_id]
        self._local_db.write(self._local_db.transacoes_file, novo)
        return True

    # ==================== RELATÓRIOS ====================

    def resumo_por_categoria(self, user_id: str, data_inicio: date, data_fim: date) -> List[Dict[str, Any]]:
        transacoes = self.listar_transacoes(user_id, data_inicio, data_fim)
        resumo: Dict[str, Dict[str, Any]] = {}

        for t in transacoes:
            cat = t.get("categorias") or {"nome": "Sem categoria", "icone": "❓"}
            cat_nome = cat.get("nome", "Sem categoria")
            if cat_nome not in resumo:
                resumo[cat_nome] = {
                    "categoria": cat_nome,
                    "icone": cat.get("icone", "📦"),
                    "total_receitas": 0.0,
                    "total_despesas": 0.0,
                    "quantidade": 0,
                }

            valor = float(t.get("valor") or 0)
            if t.get("tipo") == "receita":
                resumo[cat_nome]["total_receitas"] += valor
            else:
                resumo[cat_nome]["total_despesas"] += valor
            resumo[cat_nome]["quantidade"] += 1

        return list(resumo.values())

    def totais_periodo(self, user_id: str, data_inicio: date, data_fim: date) -> Dict[str, float]:
        transacoes = self.listar_transacoes(user_id, data_inicio, data_fim)
        receitas = sum(float(t.get("valor") or 0) for t in transacoes if t.get("tipo") == "receita")
        despesas = sum(float(t.get("valor") or 0) for t in transacoes if t.get("tipo") == "despesa")
        return {"receitas": receitas, "despesas": despesas, "saldo": receitas - despesas}

    # ==================== ORÇAMENTOS ====================

    def definir_orcamento(self, user_id: str, categoria_id: str, valor_limite: float, periodo: str = "mensal") -> Optional[Dict[str, Any]]:
        orcamentos = self._local_db.read(self._local_db.orcamentos_file)
        for i, o in enumerate(orcamentos):
            if o.get("user_id") == user_id and o.get("categoria_id") == categoria_id and o.get("ativo", True):
                orcamentos[i] = {
                    **o,
                    "valor_limite": float(valor_limite or 0),
                    "periodo": periodo,
                    "updated_at": datetime.now().isoformat(),
                }
                self._local_db.write(self._local_db.orcamentos_file, orcamentos)
                return orcamentos[i]

        novo = {
            "id": self._local_db.generate_id(),
            "user_id": user_id,
            "categoria_id": categoria_id,
            "valor_limite": float(valor_limite or 0),
            "periodo": periodo,
            "ativo": True,
            "created_at": datetime.now().isoformat(),
        }
        orcamentos.append(novo)
        self._local_db.write(self._local_db.orcamentos_file, orcamentos)
        return novo

    def criar_orcamento(self, user_id: str, categoria_id: str, valor_limite: float, periodo: str = "mensal") -> Optional[Dict[str, Any]]:
        return self.definir_orcamento(user_id, categoria_id, valor_limite, periodo)

    def listar_orcamentos(self, user_id: str) -> List[Dict[str, Any]]:
        orcamentos = self._local_db.read(self._local_db.orcamentos_file)
        categorias = self._local_db.read(self._local_db.categorias_file)
        cat_map = {c.get("id"): c for c in categorias if c.get("id")}

        ativos = [o for o in orcamentos if o.get("user_id") == user_id and o.get("ativo", True)]
        hoje = date.today()
        inicio_mes = hoje.replace(day=1)

        transacoes = self.listar_transacoes(user_id, data_inicio=inicio_mes, data_fim=hoje, limite=5000)

        for o in ativos:
            cat_id = o.get("categoria_id")
            if cat_id and cat_id in cat_map:
                o["categoria"] = cat_map[cat_id]

            gastos = sum(
                float(t.get("valor") or 0)
                for t in transacoes
                if t.get("categoria_id") == cat_id and t.get("tipo") == "despesa"
            )
            o["valor_gasto"] = gastos
            o["saldo_restante"] = float(o.get("valor_limite") or 0) - gastos

        return ativos

    def deletar_orcamento(self, orcamento_id: str) -> bool:
        orcamentos = self._local_db.read(self._local_db.orcamentos_file)
        for i, o in enumerate(orcamentos):
            if o.get("id") == orcamento_id:
                orcamentos[i] = {**o, "ativo": False, "updated_at": datetime.now().isoformat()}
                self._local_db.write(self._local_db.orcamentos_file, orcamentos)
                return True
        return False

    # ==================== INVESTIMENTOS ====================

    @staticmethod
    def _month_ref(d: date) -> date:
        return date(d.year, d.month, 1)

    @staticmethod
    def _to_date_safe(value) -> Optional[date]:
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
            except Exception:
                try:
                    return date.fromisoformat(value)
                except Exception:
                    return None
        return None

    def _get_selic_aa_percent_cache(self, ttl_seconds: int = 60 * 60) -> Optional[float]:
        try:
            now = datetime.now()
            cache = getattr(self, "_selic_cache", None)
            if cache and isinstance(cache, dict):
                ts = cache.get("ts")
                if isinstance(ts, datetime) and (now - ts).total_seconds() < ttl_seconds:
                    return cache.get("selic")

            from services.selic import obter_selic_meta_aa

            _, selic = obter_selic_meta_aa(timeout=10)
            self._selic_cache = {"ts": now, "selic": selic}
            return selic
        except Exception:
            return None

    @staticmethod
    def _aplicar_crescimento_selic(saldo: float, data_base: date, data_alvo: date, selic_aa_percent: Optional[float]) -> float:
        try:
            saldo_f = float(saldo or 0)
        except Exception:
            saldo_f = 0.0

        if not selic_aa_percent:
            return saldo_f

        try:
            dias = (data_alvo - data_base).days
        except Exception:
            return saldo_f
        if dias <= 0:
            return saldo_f

        r = float(selic_aa_percent) / 100.0
        fator = (1.0 + r) ** (dias / 365.0)
        return float(saldo_f * fator)

    def criar_investimento(self, user_id: str, nome: str, ativo: bool = True) -> Optional[Dict[str, Any]]:
        nome_limpo = (nome or "").strip()
        if not nome_limpo:
            return None

        investimentos = self._local_db.read(self._local_db.investimentos_file)
        for inv in investimentos:
            if inv.get("user_id") == user_id and (inv.get("nome") or "").strip().lower() == nome_limpo.lower():
                if inv.get("ativo", True) != bool(ativo):
                    inv["ativo"] = bool(ativo)
                    inv["updated_at"] = datetime.now().isoformat()
                    self._local_db.write(self._local_db.investimentos_file, investimentos)
                return inv

        novo = {
            "id": self._local_db.generate_id(),
            "user_id": user_id,
            "nome": nome_limpo,
            "ativo": bool(ativo),
            "created_at": datetime.now().isoformat(),
        }
        investimentos.append(novo)
        self._local_db.write(self._local_db.investimentos_file, investimentos)
        return novo

    def listar_investimentos(self, user_id: str, incluir_inativos: bool = False) -> List[Dict[str, Any]]:
        investimentos = self._local_db.read(self._local_db.investimentos_file)
        resultado = [i for i in investimentos if i.get("user_id") == user_id]
        if not incluir_inativos:
            resultado = [i for i in resultado if i.get("ativo", True)]
        return sorted(resultado, key=lambda x: (x.get("nome") or ""))

    def definir_saldo_investimento(
        self,
        user_id: str,
        investimento_id: str,
        data_referencia: date,
        saldo: float,
        data_conhecido_em: Optional[date] = None,
    ) -> Optional[Dict[str, Any]]:
        data_ref = self._month_ref(self._to_date_safe(data_referencia) or date.today())
        data_conh = self._to_date_safe(data_conhecido_em) or date.today()
        saldo_val = float(saldo or 0)

        saldos = self._local_db.read(self._local_db.investimentos_saldos_file)
        data_ref_iso = data_ref.isoformat()

        for i, s in enumerate(saldos):
            if s.get("user_id") == user_id and s.get("investimento_id") == investimento_id and s.get("data_referencia") == data_ref_iso:
                saldos[i] = {
                    **s,
                    "saldo": saldo_val,
                    "data_conhecido_em": data_conh.isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
                self._local_db.write(self._local_db.investimentos_saldos_file, saldos)
                return saldos[i]

        novo = {
            "id": self._local_db.generate_id(),
            "user_id": user_id,
            "investimento_id": investimento_id,
            "data_referencia": data_ref_iso,
            "data_conhecido_em": data_conh.isoformat(),
            "saldo": saldo_val,
            "created_at": datetime.now().isoformat(),
        }
        saldos.append(novo)
        self._local_db.write(self._local_db.investimentos_saldos_file, saldos)
        return novo

    def listar_saldos_investimentos(self, user_id: str, investimento_id: Optional[str] = None) -> List[Dict[str, Any]]:
        saldos = self._local_db.read(self._local_db.investimentos_saldos_file)
        resultado = [s for s in saldos if s.get("user_id") == user_id]
        if investimento_id:
            resultado = [s for s in resultado if s.get("investimento_id") == investimento_id]
        return sorted(resultado, key=lambda x: (x.get("data_referencia") or ""))

    def obter_saldo_investimento_em(self, user_id: str, investimento_id: str, data_ref: date) -> float:
        alvo = self._month_ref(self._to_date_safe(data_ref) or date.today())
        saldos = self.listar_saldos_investimentos(user_id, investimento_id)

        melhor: tuple[date, float] | None = None
        for s in saldos:
            d = self._to_date_safe(s.get("data_referencia"))
            if not d:
                continue
            d = self._month_ref(d)
            if d <= alvo and (melhor is None or d > melhor[0]):
                melhor = (d, float(s.get("saldo") or 0))

        return float(melhor[1]) if melhor else 0.0

    def _obter_ultimo_registro_saldo_ate(self, user_id: str, investimento_id: str, data_ref: date) -> Optional[Dict[str, Any]]:
        alvo = self._month_ref(self._to_date_safe(data_ref) or date.today())
        saldos = self.listar_saldos_investimentos(user_id, investimento_id)

        melhor = None
        melhor_d: date | None = None
        for s in saldos:
            d = self._to_date_safe(s.get("data_referencia"))
            if not d:
                continue
            d = self._month_ref(d)
            if d <= alvo and (melhor_d is None or d > melhor_d):
                melhor = s
                melhor_d = d
        return melhor

    def total_investimentos_em(self, user_id: str, data_ref: date) -> float:
        investimentos = self.listar_investimentos(user_id, incluir_inativos=False)
        return float(sum(self.obter_saldo_investimento_em(user_id, inv.get("id"), data_ref) for inv in investimentos if inv.get("id")))

    def total_investimentos_projetado_em(self, user_id: str, data_ref: date) -> float:
        selic = self._get_selic_aa_percent_cache()
        investimentos = self.listar_investimentos(user_id, incluir_inativos=False)
        total = 0.0

        alvo = self._to_date_safe(data_ref) or date.today()

        for inv in investimentos:
            inv_id = inv.get("id")
            if not inv_id:
                continue

            reg = self._obter_ultimo_registro_saldo_ate(user_id, inv_id, alvo)
            if not reg:
                continue

            saldo_base = float(reg.get("saldo") or 0)
            data_conh = self._to_date_safe(reg.get("data_conhecido_em"))
            if not data_conh:
                data_conh = self._to_date_safe(reg.get("created_at")) or self._to_date_safe(reg.get("data_referencia")) or date.today()

            total += self._aplicar_crescimento_selic(saldo_base, data_conh, alvo, selic)

        return float(total)


db = DatabaseService()
