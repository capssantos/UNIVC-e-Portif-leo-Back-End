-- Ativa UUIDs
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Criação da tabela CURSOS
CREATE TABLE IF NOT EXISTS cursos (
    id_curso       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome           VARCHAR(255) NOT NULL,
    descricao      TEXT,
    periodo        INTEGER,  -- quantidade de períodos do curso
    lista_periodos TEXT[],     -- lista de períodos
    habilitado     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMP DEFAULT NOW(),
    updated_at     TIMESTAMP,
    
    CONSTRAINT chk_cursos_periodo_nao_negativo CHECK (periodo IS NULL OR periodo >= 0),
    CONSTRAINT uq_cursos_nome UNIQUE (nome)
);

-- Índice útil para buscas rápidas por nome
CREATE INDEX IF NOT EXISTS idx_cursos_nome ON cursos (nome);
