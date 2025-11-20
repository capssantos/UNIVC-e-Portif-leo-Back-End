-- Reverso da migração: criação da tabela LEVELS

-- Remove a tabela levels (junto com constraints e índices)
DROP TABLE IF EXISTS levels CASCADE;
