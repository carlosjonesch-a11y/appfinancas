-- ===========================================
-- SCRIPT DE ATUALIZAÇÃO - ADICIONAR updated_at
-- ===========================================
-- Execute este script no SQL Editor do Supabase se a tabela categorias já existe

-- Adicionar coluna updated_at à tabela categorias
ALTER TABLE categorias 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Criar trigger para atualizar updated_at automaticamente
CREATE TRIGGER update_categorias_updated_at
    BEFORE UPDATE ON categorias
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Atualizar valores existentes
UPDATE categorias SET updated_at = created_at WHERE updated_at IS NULL;

-- Verificar
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'categorias' 
ORDER BY ordinal_position;


-- ===========================================
-- AUTH DO APP (persistência no Supabase)
-- ===========================================
-- Necessário para não perder usuários a cada reboot do Streamlit Cloud.
-- Armazena hash bcrypt da senha (não armazena senha em texto).

CREATE TABLE IF NOT EXISTS auth_credenciais (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    nome VARCHAR(255) NOT NULL,
    password_hash TEXT NOT NULL,
    user_id UUID REFERENCES usuarios(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_credenciais_username ON auth_credenciais(username);
CREATE INDEX IF NOT EXISTS idx_auth_credenciais_email ON auth_credenciais(email);

ALTER TABLE auth_credenciais DISABLE ROW LEVEL SECURITY;
