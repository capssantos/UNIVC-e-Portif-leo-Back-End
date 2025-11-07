-- Habilita pgcrypto p/ gen_random_uuid (se ainda não estiver ativa)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'jwt_token_type') THEN
    CREATE TYPE jwt_token_type AS ENUM ('access', 'refresh', 'other');
  END IF;
END$$;

CREATE TABLE IF NOT EXISTS jwt_tokens (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          UUID NOT NULL,
  jti              TEXT NOT NULL,
  token_type       jwt_token_type NOT NULL,
  audience         TEXT,
  issuer           TEXT,
  subject          TEXT,
  issued_at        TIMESTAMPTZ NOT NULL,
  expires_at       TIMESTAMPTZ NOT NULL,
  revoked_at       TIMESTAMPTZ,
  revoked_reason   TEXT,
  session_id       TEXT,
  ip               INET,
  user_agent       TEXT,
  metadata         JSONB DEFAULT '{}'::jsonb,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT fk_jwt_user
    FOREIGN KEY (user_id) REFERENCES usuarios(id_usuario)
      ON UPDATE CASCADE ON DELETE CASCADE,

  CONSTRAINT uq_jti UNIQUE (jti),
  CONSTRAINT chk_expires_future CHECK (expires_at > issued_at)
);

-- Índices úteis
CREATE INDEX IF NOT EXISTS idx_jwt_user_id        ON jwt_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_jwt_expires_at     ON jwt_tokens (expires_at);
CREATE INDEX IF NOT EXISTS idx_jwt_revoked_at     ON jwt_tokens (revoked_at);

-- ✅ Índice parcial SEM usar NOW(): ajuda muito a consulta de tokens "candidatos a ativos"
-- (deixa o filtro expires_at > NOW() para a query)
CREATE INDEX IF NOT EXISTS idx_jwt_active_candidates
  ON jwt_tokens (user_id, expires_at)
  WHERE revoked_at IS NULL;

-- (Opcional) Log de revogações
CREATE TABLE IF NOT EXISTS jwt_revocations (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  jti            TEXT NOT NULL,
  user_id        UUID,
  reason         TEXT,
  revoked_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  metadata       JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_revocations_jti     ON jwt_revocations (jti);
CREATE INDEX IF NOT EXISTS idx_revocations_user_id ON jwt_revocations (user_id);
