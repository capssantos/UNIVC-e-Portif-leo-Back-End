-- 0012_create_usuarios_selos.up.sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS usuarios_selos (
    id_usuario_selo UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    id_usuario      UUID NOT NULL
        REFERENCES usuarios(id_usuario),

    id_selo         UUID NOT NULL
        REFERENCES selos(id_selo),

    motivo          TEXT,          -- texto livre: "projeto destaque", "ajuda a colegas", etc.
    origem          VARCHAR(50),   -- ex: "PROJETO", "ATIVIDADE", "MANUAL"
    referencia      JSONB,         -- pode guardar id_projeto, id_atividade, etc.

    habilitado      BOOLEAN NOT NULL DEFAULT TRUE,

    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP
);

-- Um mesmo selo só pode ser ganho uma vez por usuário
CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_selos_unique
    ON usuarios_selos (id_usuario, id_selo);

CREATE INDEX IF NOT EXISTS idx_usuarios_selos_usuario
    ON usuarios_selos (id_usuario);

CREATE INDEX IF NOT EXISTS idx_usuarios_selos_selo
    ON usuarios_selos (id_selo);
