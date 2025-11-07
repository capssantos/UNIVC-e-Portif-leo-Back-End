-- Reverso da migração 0002
DROP TABLE IF EXISTS jwt_revocations;
DROP TABLE IF EXISTS jwt_tokens;
DROP TYPE IF EXISTS jwt_token_type;
-- NÃO derrubamos a extensão pgcrypto (pode ser usada por outras tabelas)
