-- 0005_add_level_to_usuarios.up.sql

-- Adiciona coluna de XP total (ou atual) do usuário
ALTER TABLE usuarios
    ADD COLUMN xp_total INTEGER NOT NULL DEFAULT 0;

-- Adiciona coluna para referenciar o nível atual
ALTER TABLE usuarios
    ADD COLUMN id_level_atual UUID;

-- Cria a FK ligando o usuário ao nível atual
ALTER TABLE usuarios
    ADD CONSTRAINT fk_usuarios_level_atual
    FOREIGN KEY (id_level_atual)
    REFERENCES levels (id_level);

-- Índice para facilitar buscas por nível
CREATE INDEX IF NOT EXISTS idx_usuarios_id_level_atual
    ON usuarios (id_level_atual);
