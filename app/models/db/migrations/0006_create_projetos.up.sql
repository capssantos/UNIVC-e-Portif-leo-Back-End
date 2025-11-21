CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS projetos (
    id_projeto        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_usuario        UUID NOT NULL,

    titulo            VARCHAR(255) NOT NULL,
    descricao         TEXT,
    texto             TEXT,      -- markdown ou html
    imagem_atividade  TEXT,
    tags              TEXT[],    -- agora é ARRAY

    habilitado        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP,

    CONSTRAINT fk_projetos_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES usuarios (id_usuario)
);

CREATE INDEX IF NOT EXISTS idx_projetos_tags
    ON projetos USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_projetos_usuario
    ON projetos (id_usuario);
