-- 010_create_missoes_usuarios_table.up.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS missoes_usuarios (
    id_missao_usuario UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_missao         UUID NOT NULL,
    id_usuario        UUID NOT NULL,
    concluida_em      TIMESTAMP NOT NULL DEFAULT NOW(),

    -- não deixa o mesmo usuário concluir a mesma missão duas vezes
    CONSTRAINT uq_missoes_usuarios UNIQUE (id_missao, id_usuario),

    CONSTRAINT fk_missoes_usuarios_missao
        FOREIGN KEY (id_missao) REFERENCES missoes (id_missao)
        ON DELETE CASCADE,

    CONSTRAINT fk_missoes_usuarios_usuario
        FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_missoes_usuarios_missao
    ON missoes_usuarios (id_missao);

CREATE INDEX IF NOT EXISTS idx_missoes_usuarios_usuario
    ON missoes_usuarios (id_usuario);
