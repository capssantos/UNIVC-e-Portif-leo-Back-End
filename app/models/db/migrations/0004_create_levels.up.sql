-- Ativa extensão para UUIDs (se ainda não estiver ativa)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Tabela LEVELS (definição dos níveis / títulos)
CREATE TABLE IF NOT EXISTS levels (
    id_level    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo      VARCHAR(255) NOT NULL,
    tag         VARCHAR(50)  NOT NULL,
    nivel       INTEGER      NOT NULL,
    xp_min      INTEGER      NOT NULL DEFAULT 0,
    xp_max      INTEGER,
    descricao   TEXT,
    habilitado  BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP    DEFAULT NOW(),
    updated_at  TIMESTAMP,

    -- Tag controlada
    CONSTRAINT chk_levels_tag CHECK (tag IN ('iniciante', 'intermediario', 'maximo', 'ametista')),
    -- Evita repetir o mesmo nível dentro da mesma tag
    CONSTRAINT uq_levels_tag_nivel UNIQUE (tag, nivel)
);

-- Índices úteis
CREATE INDEX IF NOT EXISTS idx_levels_tag ON levels (tag);
CREATE INDEX IF NOT EXISTS idx_levels_titulo ON levels (titulo);

INSERT INTO levels (titulo, tag, nivel, xp_min, xp_max, descricao) VALUES
  ('Explorador Júnior', 'iniciante', 1,   0,   49,  'Começando a explorar o universo de tecnologia e portfólios.'),
  ('Nível Innovator',   'iniciante', 2,  50, 149,  'Já cria soluções simples e começa a propor ideias novas.'),
  ('Desbravador',       'iniciante', 3, 150, 299,  'Vai atrás de desafios, entrega exercícios e projetos iniciais.'),
  ('Code Adventurer',   'iniciante', 4, 300, 499,  'Participa ativamente das atividades, missões e trilhas iniciais.');

INSERT INTO levels (titulo, tag, nivel, xp_min, xp_max, descricao) VALUES
  ('Problem Solver',     'intermediario', 1,  500,  899, 'Resolve problemas com autonomia e organiza bem suas entregas.'),
  ('Code Builder',       'intermediario', 2,  900, 1399, 'Constrói projetos completos e começa a integrar diferentes tecnologias.'),
  ('Team Contributor',   'intermediario', 3, 1400, 1899, 'Contribui com o time, ajuda colegas e participa de projetos em grupo.'),
  ('Innovation Hacker',  'intermediario', 4, 1900, 2499, 'Cria soluções criativas, testa hipóteses e valida ideias com dados.');

INSERT INTO levels (titulo, tag, nivel, xp_min, xp_max, descricao) VALUES
  ('Tech Specialist',      'maximo', 1, 2500, 3199, 'Demonstra domínio em uma ou mais áreas técnicas.'),
  ('Solution Architect',   'maximo', 2, 3200, 3999, 'Planeja soluções de ponta a ponta, pensando em arquitetura e qualidade.'),
  ('Code Mentor',          'maximo', 3, 4000, 4999, 'Orienta colegas, revisa código e puxa a régua para cima.'),
  ('Master Innovator',     'maximo', 4, 5000, 5999, 'Referência em inovação, impacto em sala/projetos e protagonismo.');

INSERT INTO levels (titulo, tag, nivel, xp_min, xp_max, descricao) VALUES
  ('Guardião Ametista',     'ametista', 1, 6000, 6999, 'Alcançou destaque em projetos e representa a turma/exemplo.'),
  ('Líder Ametista',        'ametista', 2, 7000, 7999, 'Assume papel de liderança em times e projetos colaborativos.'),
  ('Oráculo Ametista',      'ametista', 3, 8000, 8999, 'É referência técnica e comportamental, buscado para conselhos.'),
  ('Lendário Ametista',     'ametista', 4, 9000, NULL, 'Nível máximo, símbolo de excelência e inspiração para os demais.');
