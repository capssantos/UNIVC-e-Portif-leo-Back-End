ALTER TABLE projetos
    DROP CONSTRAINT IF EXISTS chk_projetos_xp_conclusao,
    DROP CONSTRAINT IF EXISTS chk_projetos_status,
    DROP COLUMN IF EXISTS xp_conclusao,
    DROP COLUMN IF EXISTS data_inicio,
    DROP COLUMN IF EXISTS data_fim,
    DROP COLUMN IF EXISTS status;
