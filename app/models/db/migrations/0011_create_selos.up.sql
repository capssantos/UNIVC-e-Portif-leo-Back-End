-- 0011_create_selos.up.sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS selos (
    id_selo        UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    titulo         VARCHAR(120) NOT NULL,
    slug           VARCHAR(120),      -- opcional, caso queira usar no front como chave estável
    descricao      TEXT,

    icone          VARCHAR(80),       -- ex: "trophy", "sparkles", "users"
    cor_inicio     VARCHAR(20),       -- ex: "#22c55e"
    cor_fim        VARCHAR(20),       -- ex: "#a3e635"
    tipo           VARCHAR(40),       -- ex: "CRIATIVIDADE", "RESOLUCAO_PROBLEMAS"
    ordem          INTEGER NOT NULL DEFAULT 0,  -- para ordenar na tela

    habilitado     BOOLEAN NOT NULL DEFAULT TRUE,

    created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_selos_titulo
    ON selos (LOWER(titulo));

CREATE UNIQUE INDEX IF NOT EXISTS idx_selos_slug
    ON selos (LOWER(slug));
