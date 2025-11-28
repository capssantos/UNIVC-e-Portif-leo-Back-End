-- Ativa extensão para UUIDs (se ainda não estiver ativa)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Tabela LEVELS (definição dos níveis / títulos)
CREATE TABLE IF NOT EXISTS levels (
    id_level    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo      VARCHAR(255) NOT NULL,
    tag         VARCHAR(50)  NOT NULL,
    nivel       INTEGER      NOT NULL,
    xp_min      INTEGER      NOT NULL DEFAULT 0,
    xp_max      INTEGER,
    descricao   TEXT,
    habilitado  BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP    DEFAULT NOW(),
    updated_at  TIMESTAMP,

    -- Tag controlada
    CONSTRAINT chk_levels_tag CHECK (tag IN ('iniciante', 'intermediario', 'maximo', 'ametista')),
    -- Evita repetir o mesmo nível dentro da mesma tag
    CONSTRAINT uq_levels_tag_nivel UNIQUE (tag, nivel)
);

-- Índices úteis
CREATE INDEX IF NOT EXISTS idx_levels_tag ON levels (tag);
CREATE INDEX IF NOT EXISTS idx_levels_titulo ON levels (titulo);
