"""
Modelos de dados para o aplicativo de Finanças Pessoais
Estrutura de tabelas para Supabase/PostgreSQL
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
    senha_hash: str = ""
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


# SQL para criar tabelas no Supabase
SQL_CREATE_TABLES = """
-- Habilitar extensão UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabela de usuários (gerenciada pelo Supabase Auth, mas podemos estender)
CREATE TABLE IF NOT EXISTS usuarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    auth_id UUID UNIQUE,  -- ID do Supabase Auth
    email VARCHAR(255) UNIQUE NOT NULL,
    nome VARCHAR(255) NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de categorias
CREATE TABLE IF NOT EXISTS categorias (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES usuarios(id) ON DELETE CASCADE,
    nome VARCHAR(100) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('receita', 'despesa')),
    icone VARCHAR(10) DEFAULT '📦',
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, nome, tipo)
);

-- Tabela de transações
CREATE TABLE IF NOT EXISTS transacoes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES usuarios(id) ON DELETE CASCADE,
    categoria_id UUID REFERENCES categorias(id) ON DELETE SET NULL,
    descricao VARCHAR(500) NOT NULL,
    valor DECIMAL(12,2) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('receita', 'despesa')),
    data DATE NOT NULL,
    observacao TEXT,
    modo_lancamento VARCHAR(20) DEFAULT 'manual' CHECK (modo_lancamento IN ('manual', 'automatico', 'semi_automatico')),
    cupom_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de orçamentos
CREATE TABLE IF NOT EXISTS orcamentos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES usuarios(id) ON DELETE CASCADE,
    categoria_id UUID REFERENCES categorias(id) ON DELETE CASCADE,
    valor_limite DECIMAL(12,2) NOT NULL,
    periodo VARCHAR(20) DEFAULT 'mensal',
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de cupons fiscais
CREATE TABLE IF NOT EXISTS cupons_fiscais (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES usuarios(id) ON DELETE CASCADE,
    imagem_path TEXT,
    estabelecimento VARCHAR(255),
    cnpj VARCHAR(20),
    data_cupom DATE,
    valor_total DECIMAL(12,2),
    status VARCHAR(20) DEFAULT 'pendente' CHECK (status IN ('pendente', 'processado', 'erro', 'revisao')),
    dados_brutos TEXT,
    dados_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de itens do cupom
CREATE TABLE IF NOT EXISTS itens_cupom (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cupom_id UUID REFERENCES cupons_fiscais(id) ON DELETE CASCADE,
    codigo VARCHAR(50),
    descricao VARCHAR(255),
    quantidade DECIMAL(10,3) DEFAULT 1,
    valor_unitario DECIMAL(12,2),
    valor_total DECIMAL(12,2),
    categoria_sugerida UUID REFERENCES categorias(id) ON DELETE SET NULL
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_transacoes_user_id ON transacoes(user_id);
CREATE INDEX IF NOT EXISTS idx_transacoes_data ON transacoes(data);
CREATE INDEX IF NOT EXISTS idx_transacoes_categoria ON transacoes(categoria_id);
CREATE INDEX IF NOT EXISTS idx_cupons_user_id ON cupons_fiscais(user_id);
CREATE INDEX IF NOT EXISTS idx_categorias_user_id ON categorias(user_id);
CREATE INDEX IF NOT EXISTS idx_orcamentos_user_id ON orcamentos(user_id);
CREATE INDEX IF NOT EXISTS idx_orcamentos_categoria_id ON orcamentos(categoria_id);

-- Evita orçamentos duplicados ativos para a mesma categoria
CREATE UNIQUE INDEX IF NOT EXISTS uq_orcamentos_user_categoria_ativo
ON orcamentos(user_id, categoria_id)
WHERE ativo = TRUE;

-- Trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_transacoes_updated_at
    BEFORE UPDATE ON transacoes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_usuarios_updated_at
    BEFORE UPDATE ON usuarios
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orcamentos_updated_at
    BEFORE UPDATE ON orcamentos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- RLS (Row Level Security) para isolamento de dados por usuário
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE categorias ENABLE ROW LEVEL SECURITY;
ALTER TABLE transacoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE cupons_fiscais ENABLE ROW LEVEL SECURITY;
ALTER TABLE itens_cupom ENABLE ROW LEVEL SECURITY;
ALTER TABLE orcamentos ENABLE ROW LEVEL SECURITY;

-- Políticas RLS (ajuste conforme configuração do Supabase Auth)
-- CREATE POLICY "Users can view own data" ON transacoes FOR SELECT USING (auth.uid() = user_id);
-- CREATE POLICY "Users can insert own data" ON transacoes FOR INSERT WITH CHECK (auth.uid() = user_id);
-- CREATE POLICY "Users can update own data" ON transacoes FOR UPDATE USING (auth.uid() = user_id);
-- CREATE POLICY "Users can delete own data" ON transacoes FOR DELETE USING (auth.uid() = user_id);
"""
