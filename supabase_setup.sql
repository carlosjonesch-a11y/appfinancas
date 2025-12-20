-- ===========================================
-- SCRIPT DE CRIAÇÃO DE TABELAS - SUPABASE
-- ===========================================
-- Execute este script no SQL Editor do Supabase
-- Dashboard > SQL Editor > New Query > Cole e Execute

-- Habilitar extensão UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabela de usuários
CREATE TABLE IF NOT EXISTS usuarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    auth_id UUID UNIQUE,
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
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
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

CREATE TRIGGER update_categorias_updated_at
    BEFORE UPDATE ON categorias
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_usuarios_updated_at
    BEFORE UPDATE ON usuarios
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===========================================
-- RLS (Row Level Security) - DESABILITADO
-- ===========================================
-- Para testes, vamos desabilitar o RLS primeiro
-- Depois você pode habilitar e configurar as políticas

ALTER TABLE usuarios DISABLE ROW LEVEL SECURITY;
ALTER TABLE categorias DISABLE ROW LEVEL SECURITY;
ALTER TABLE transacoes DISABLE ROW LEVEL SECURITY;
ALTER TABLE cupons_fiscais DISABLE ROW LEVEL SECURITY;
ALTER TABLE itens_cupom DISABLE ROW LEVEL SECURITY;

-- Se quiser habilitar RLS depois, descomente as linhas abaixo:
-- ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE categorias ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE transacoes ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE cupons_fiscais ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE itens_cupom ENABLE ROW LEVEL SECURITY;

-- E crie as políticas apropriadas

-- ===========================================
-- VERIFICAR CRIAÇÃO
-- ===========================================
-- Execute estas queries para verificar:

-- SELECT tablename FROM pg_tables WHERE schemaname = 'public';
-- SELECT * FROM usuarios;
-- SELECT * FROM categorias;
-- SELECT * FROM transacoes;
