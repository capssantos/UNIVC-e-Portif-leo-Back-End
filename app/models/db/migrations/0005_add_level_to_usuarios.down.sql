-- 0005_add_level_to_usuarios.down.sql

-- Remove FK primeiro
ALTER TABLE usuarios
    DROP CONSTRAINT IF EXISTS fk_usuarios_level_atual;

-- Remove índice
DROP INDEX IF EXISTS idx_usuarios_id_level_atual;

-- Remove colunas
ALTER TABLE usuarios
    DROP COLUMN IF EXISTS id_level_atual,
    DROP COLUMN IF EXISTS xp_total;
