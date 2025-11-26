CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS projetos (
    id_projeto        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_usuario        UUID NOT NULL,

    titulo            VARCHAR(255) NOT NULL,
    descricao         TEXT,
    texto             TEXT,      -- markdown ou html
    imagem_atividade  TEXT,
    tags              TEXT[],    -- ARRAY de tags

    -- NOVOS CAMPOS
    xp_conclusao      INTEGER NOT NULL DEFAULT 0,   -- XP concedido ao aluno ao concluir o projeto
    data_inicio       TIMESTAMP,                    -- quando o projeto está previsto para iniciar
    data_fim          TIMESTAMP,                    -- quando o projeto termina / prazo
    status            VARCHAR(30) NOT NULL DEFAULT 'AGUARDANDO_INICIO',

    habilitado        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP,

    CONSTRAINT fk_projetos_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES usuarios (id_usuario),

    CONSTRAINT chk_projetos_status
        CHECK (status IN (
            'AGUARDANDO_INICIO',
            'EM_ANDAMENTO',
            'PAUSADO',
            'CANCELADO'
        )),

    CONSTRAINT chk_projetos_xp_conclusao
        CHECK (xp_conclusao >= 0)
);

CREATE INDEX IF NOT EXISTS idx_projetos_tags
    ON projetos USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_projetos_usuario
    ON projetos (id_usuario);
