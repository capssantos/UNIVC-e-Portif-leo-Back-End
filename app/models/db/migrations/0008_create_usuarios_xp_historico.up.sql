-- 0008_create_usuarios_xp_historico.up.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS usuarios_xp_historico (
    id_xp          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_usuario     UUID NOT NULL REFERENCES usuarios(id_usuario),

    delta_xp       INTEGER NOT NULL,    -- quanto foi somado/subtraído
    xp_antes       INTEGER NOT NULL,    -- xp_total antes da alteração
    xp_depois      INTEGER NOT NULL,    -- xp_total depois da alteração

    motivo         TEXT,                -- ex: "atividade concluída", "ajuste manual"
    origem         VARCHAR(50),         -- ex: "ATIVIDADE", "PROJETO", "ADMIN"
    referencia     JSONB,               -- guarda infos extras (id_projeto, id_atividade, etc.)

    id_responsavel UUID NULL REFERENCES usuarios(id_usuario), -- quem deu o XP (ou null = sistema)
    created_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_xp_hist_usuario_data
    ON usuarios_xp_historico (id_usuario, created_at DESC);
