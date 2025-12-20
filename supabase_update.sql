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
