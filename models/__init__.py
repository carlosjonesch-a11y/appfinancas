"""
Modelos de dados para o aplicativo de Finanças Pessoais
"""
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum


class TipoTransacao(Enum):
    """Tipos de transação"""
    RECEITA = "receita"
    DESPESA = "despesa"


class StatusProcessamento(Enum):
    """Status do processamento de cupom"""
    PENDENTE = "pendente"
    PROCESSADO = "processado"
    ERRO = "erro"
    REVISAO = "revisao"


class ModoLancamento(Enum):
    """Modo de lançamento de transações"""
    MANUAL = "manual"
    AUTOMATICO = "automatico"
    SEMI_AUTOMATICO = "semi_automatico"


@dataclass
class Usuario:
    """Modelo de usuário"""
    id: Optional[str] = None
    email: str = ""
    nome: str = ""
    ativo: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "nome": self.nome,
            "ativo": self.ativo,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class Categoria:
    """Modelo de categoria"""
    id: Optional[str] = None
    user_id: str = ""
    nome: str = ""
    tipo: TipoTransacao = TipoTransacao.DESPESA
    icone: str = "📦"
    ativo: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "nome": self.nome,
            "tipo": self.tipo.value,
            "icone": self.icone,
            "ativo": self.ativo,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class Transacao:
    """Modelo de transação financeira"""
    id: Optional[str] = None
    user_id: str = ""
    categoria_id: Optional[str] = None
    descricao: str = ""
    valor: float = 0.0
    tipo: TipoTransacao = TipoTransacao.DESPESA
    data: datetime = field(default_factory=datetime.now)
    observacao: str = ""
    modo_lancamento: ModoLancamento = ModoLancamento.MANUAL
    cupom_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "categoria_id": self.categoria_id,
            "descricao": self.descricao,
            "valor": self.valor,
            "tipo": self.tipo.value,
            "data": self.data.isoformat() if isinstance(self.data, datetime) else self.data,
            "observacao": self.observacao,
            "modo_lancamento": self.modo_lancamento.value,
            "cupom_id": self.cupom_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Transacao":
        return cls(
            id=data.get("id"),
            user_id=data.get("user_id", ""),
            categoria_id=data.get("categoria_id"),
            descricao=data.get("descricao", ""),
            valor=float(data.get("valor", 0)),
            tipo=TipoTransacao(data.get("tipo", "despesa")),
            data=datetime.fromisoformat(data["data"]) if isinstance(data.get("data"), str) else data.get("data", datetime.now()),
            observacao=data.get("observacao", ""),
            modo_lancamento=ModoLancamento(data.get("modo_lancamento", "manual")),
            cupom_id=data.get("cupom_id"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()
        )


@dataclass
class CupomFiscal:
    """Modelo de cupom fiscal escaneado"""
    id: Optional[str] = None
    user_id: str = ""
    imagem_path: str = ""
    estabelecimento: str = ""
    cnpj: str = ""
    data_cupom: Optional[datetime] = None
    valor_total: float = 0.0
    status: StatusProcessamento = StatusProcessamento.PENDENTE
    dados_brutos: str = ""  # Texto OCR bruto
    dados_json: dict = field(default_factory=dict)  # Dados estruturados
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "imagem_path": self.imagem_path,
            "estabelecimento": self.estabelecimento,
            "cnpj": self.cnpj,
            "data_cupom": self.data_cupom.isoformat() if self.data_cupom else None,
            "valor_total": self.valor_total,
            "status": self.status.value,
            "dados_brutos": self.dados_brutos,
            "dados_json": self.dados_json,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ItemCupom:
    """Modelo de item individual do cupom"""
    id: Optional[str] = None
    cupom_id: str = ""
    codigo: str = ""
    descricao: str = ""
    quantidade: float = 1.0
    valor_unitario: float = 0.0
    valor_total: float = 0.0
    categoria_sugerida: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cupom_id": self.cupom_id,
            "codigo": self.codigo,
            "descricao": self.descricao,
            "quantidade": self.quantidade,
            "valor_unitario": self.valor_unitario,
            "valor_total": self.valor_total,
            "categoria_sugerida": self.categoria_sugerida
        }
