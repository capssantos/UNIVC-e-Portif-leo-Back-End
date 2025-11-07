-- Ativa extensão para UUIDs (gera IDs únicos com gen_random_uuid)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Tabela USUARIOS
CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome             VARCHAR(255) NOT NULL,
    password         VARCHAR(255) NOT NULL,
    curso            VARCHAR(255),
    periodo          VARCHAR(255),
    ano_inicio       INTEGER,
    ano_fim          INTEGER,
    data_nascimento  DATE,
    contato          VARCHAR(255) NOT NULL,
    email            VARCHAR(255) NOT NULL,
    imagem           TEXT,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP,
    last_signed      TIMESTAMP,
    premissao        VARCHAR(255),
    new              BOOLEAN NOT NULL DEFAULT TRUE,
    habilitado       BOOLEAN NOT NULL DEFAULT TRUE,
    validacao        BOOLEAN NOT NULL DEFAULT FALSE,

    -- Garantias adicionais
    CONSTRAINT chk_ano CHECK (ano_fim IS NULL OR ano_fim >= ano_inicio),
    CONSTRAINT uq_email UNIQUE (email)
);

-- Índice útil para buscas rápidas
CREATE INDEX IF NOT EXISTS idx_usuarios_nome ON usuarios (nome);
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios (email);
CREATE INDEX IF NOT EXISTS idx_usuarios_curso ON usuarios (curso);
