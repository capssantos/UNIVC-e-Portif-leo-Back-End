-- 009_create_missoes_table.up.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS missoes (
    id_missao    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo       VARCHAR(255) NOT NULL,
    descricao    TEXT,
    tag          VARCHAR(50),          -- ex: "RAPIDA", "PBL", "DESAFIO"
    xp_reward    INTEGER NOT NULL,     -- quanto de XP a missão concede
    ordem        INTEGER,              -- para ordenar na tela (opcional)
    habilitado   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_missoes_tag ON missoes (tag);
CREATE INDEX IF NOT EXISTS idx_missoes_habilitado ON missoes (habilitado);
