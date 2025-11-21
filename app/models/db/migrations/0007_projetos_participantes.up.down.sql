-- DOWN: remove tabela de relacionamento entre projetos e participantes

-- Remove índices criados manualmente (boa prática)
DROP INDEX IF EXISTS idx_pp_projeto;
DROP INDEX IF EXISTS idx_pp_usuario;
DROP INDEX IF EXISTS idx_pp_status;

-- Remove a constraint de chave única
ALTER TABLE IF EXISTS projetos_participantes
    DROP CONSTRAINT IF EXISTS uq_pp_unica_inscricao;

-- Remove foreign keys explicitamente
ALTER TABLE IF EXISTS projetos_participantes
    DROP CONSTRAINT IF EXISTS fk_pp_projeto;

ALTER TABLE IF EXISTS projetos_participantes
    DROP CONSTRAINT IF EXISTS fk_pp_usuario;

-- Remove a tabela
DROP TABLE IF EXISTS projetos_participantes;
