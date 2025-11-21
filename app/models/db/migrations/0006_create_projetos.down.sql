-- Remove índices (opcional, pois DROP TABLE já remove, mas é bom ser explícito)
DROP INDEX IF EXISTS idx_projetos_tags;
DROP INDEX IF EXISTS idx_projetos_usuario;

-- Remove a tabela de projetos
DROP TABLE IF EXISTS projetos;
