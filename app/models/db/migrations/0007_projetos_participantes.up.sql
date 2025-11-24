-- Tabela de participação em projetos
CREATE TABLE IF NOT EXISTS projetos_participantes (
    id_participacao   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_projeto        UUID NOT NULL,
    id_usuario        UUID NOT NULL,

    papel             VARCHAR(50) NOT NULL DEFAULT 'MEMBRO', -- MONITOR (1) | MEMBRO
    status            VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',  -- PENDENTE | APROVADO | RECUSADO | CANCELADO
    mensagem          TEXT,

    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP,

    CONSTRAINT fk_proj_part_projeto
        FOREIGN KEY (id_projeto)
        REFERENCES projetos (id_projeto)
        ON DELETE CASCADE,

    CONSTRAINT fk_proj_part_usuario
        FOREIGN KEY (id_usuario)
        REFERENCES usuarios (id_usuario)
        ON DELETE CASCADE
);

-- Índices para acelerar consultas
CREATE INDEX IF NOT EXISTS idx_proj_part_projeto
    ON projetos_participantes (id_projeto);

CREATE INDEX IF NOT EXISTS idx_proj_part_usuario
    ON projetos_participantes (id_usuario);

CREATE INDEX IF NOT EXISTS idx_proj_part_status
    ON projetos_participantes (status);

-- (Opcional, mas bem legal)
-- Garante que não exista mais de uma inscrição "ativa" (PENDENTE/APROVADO)
-- para o mesmo usuário no mesmo projeto
CREATE UNIQUE INDEX IF NOT EXISTS uq_proj_part_ativo
    ON projetos_participantes (id_projeto, id_usuario)
    WHERE status IN ('PENDENTE', 'APROVADO');
