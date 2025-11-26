CREATE EXTENSION IF NOT EXISTS "pgcrypto";

/*
 * Criação inicial da tabela (para ambientes novos).
 * Se a tabela já existir, este bloco será ignorado
 * por causa do IF NOT EXISTS.
 */
CREATE TABLE IF NOT EXISTS projetos (
    id_projeto        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_usuario        UUID NOT NULL,

    titulo            VARCHAR(255) NOT NULL,
    descricao         TEXT,
    texto             TEXT,      -- markdown ou html
    imagem_atividade  TEXT,
    tags              TEXT[],    -- ARRAY de tags

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
            'CANCELADO',
            'CONCLUIDO'
        )),

    CONSTRAINT chk_projetos_xp_conclusao
        CHECK (xp_conclusao >= 0)
);

/*
 * Bloco de compatibilidade:
 * garante que, se a tabela já existia de uma versão antiga,
 * ela vai ganhar as colunas e constraints necessárias.
 */

-- Garante colunas novas (se estiverem faltando)
ALTER TABLE projetos
    ADD COLUMN IF NOT EXISTS tags           TEXT[],
    ADD COLUMN IF NOT EXISTS xp_conclusao   INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS data_inicio    TIMESTAMP,
    ADD COLUMN IF NOT EXISTS data_fim       TIMESTAMP,
    ADD COLUMN IF NOT EXISTS status         VARCHAR(30) NOT NULL DEFAULT 'AGUARDANDO_INICIO',
    ADD COLUMN IF NOT EXISTS habilitado     BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS created_at     TIMESTAMP DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at     TIMESTAMP;

-- Ajusta/garante a FK para usuarios
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM information_schema.table_constraints
         WHERE constraint_type = 'FOREIGN KEY'
           AND table_name = 'projetos'
           AND constraint_name = 'fk_projetos_usuario'
    ) THEN
        ALTER TABLE projetos
            ADD CONSTRAINT fk_projetos_usuario
                FOREIGN KEY (id_usuario)
                REFERENCES usuarios (id_usuario);
    END IF;
END$$;

-- Recria a constraint de status com o novo valor 'CONCLUIDO'
ALTER TABLE projetos
    DROP CONSTRAINT IF EXISTS chk_projetos_status;

ALTER TABLE projetos
    ADD CONSTRAINT chk_projetos_status
        CHECK (status IN (
            'AGUARDANDO_INICIO',
            'EM_ANDAMENTO',
            'PAUSADO',
            'CANCELADO',
            'CONCLUIDO'
        ));

-- Recria a constraint de xp_conclusao (caso não exista ou esteja incorreta)
ALTER TABLE projetos
    DROP CONSTRAINT IF EXISTS chk_projetos_xp_conclusao;

ALTER TABLE projetos
    ADD CONSTRAINT chk_projetos_xp_conclusao
        CHECK (xp_conclusao >= 0);

-- Índices (idempotentes)
CREATE INDEX IF NOT EXISTS idx_projetos_tags
    ON projetos USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_projetos_usuario
    ON projetos (id_usuario);
