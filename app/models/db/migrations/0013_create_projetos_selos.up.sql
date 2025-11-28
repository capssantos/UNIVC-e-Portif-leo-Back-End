-- 0012_create_usuarios_selos.up.sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS usuarios_selos (
    id_usuario_selo UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    id_usuario      UUID NOT NULL
        REFERENCES usuarios(id_usuario),

    id_selo         UUID NOT NULL
        REFERENCES selos(id_selo),

    motivo          TEXT,          -- texto livre: "projeto destaque", "ajuda a colegas", etc.
    origem          VARCHAR(50),   -- ex: "PROJETO", "ATIVIDADE", "MANUAL"
    referencia      JSONB,         -- pode guardar id_projeto, id_atividade, etc.

    habilitado      BOOLEAN NOT NULL DEFAULT TRUE,

    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP
);

-- Um mesmo selo só pode ser ganho uma vez por usuário
CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_selos_unique
    ON usuarios_selos (id_usuario, id_selo);

CREATE INDEX IF NOT EXISTS idx_usuarios_selos_usuario
    ON usuarios_selos (id_usuario);

CREATE INDEX IF NOT EXISTS idx_usuarios_selos_selo
    ON usuarios_selos (id_selo);

-- =======================================================
-- ENZO ganha selos vinculados ao projeto "API de Portfólio UNIVC"
-- =======================================================

INSERT INTO usuarios_selos (
    id_usuario, id_selo, motivo, origem, referencia, habilitado
)
SELECT 
    u.id_usuario,
    s.id_selo,
    'Entrega consistente e de alta qualidade na API principal da plataforma.',
    'PROJETO',
    jsonb_build_object(
        'id_projeto', p.id_projeto,
        'titulo_projeto', p.titulo,
        'papel', 'RESPONSAVEL'
    ),
    TRUE
FROM usuarios u
JOIN selos s   ON LOWER(s.slug) = 'excelencia_tecnica'
JOIN projetos p ON p.titulo = 'API de Portfólio UNIVC'
WHERE u.email = 'enzo@enzo.com';


INSERT INTO usuarios_selos (
    id_usuario, id_selo, motivo, origem, referencia, habilitado
)
SELECT 
    u.id_usuario,
    s.id_selo,
    'Resolveu problemas críticos de autenticação e integração no projeto de API.',
    'PROJETO',
    jsonb_build_object(
        'id_projeto', p.id_projeto,
        'titulo_projeto', p.titulo,
        'papel', 'LIDER_TECNICO'
    ),
    TRUE
FROM usuarios u
JOIN selos s   ON LOWER(s.slug) = 'resolucao_problemas'
JOIN projetos p ON p.titulo = 'API de Portfólio UNIVC'
WHERE u.email = 'enzo@enzo.com';


-- =======================================================
-- FELIPE ganha selos vinculados ao projeto "Frontend React do Sistema UNIVC"
-- =======================================================

INSERT INTO usuarios_selos (
    id_usuario, id_selo, motivo, origem, referencia, habilitado
)
SELECT 
    u.id_usuario,
    s.id_selo,
    'Criou uma interface criativa com animações e navegação inteligente.',
    'PROJETO',
    jsonb_build_object(
        'id_projeto', p.id_projeto,
        'titulo_projeto', p.titulo,
        'stack', 'React + Tailwind'
    ),
    TRUE
FROM usuarios u
JOIN selos s   ON LOWER(s.slug) = 'criatividade'
JOIN projetos p ON p.titulo = 'Frontend React do Sistema UNIVC'
WHERE u.email = 'felipe.souza@ivc.br';


INSERT INTO usuarios_selos (
    id_usuario, id_selo, motivo, origem, referencia, habilitado
)
SELECT 
    u.id_usuario,
    s.id_selo,
    'Participou ativamente das revisões e melhorias de UX no frontend.',
    'PROJETO',
    jsonb_build_object(
        'id_projeto', p.id_projeto,
        'titulo_projeto', p.titulo,
        'papel', 'UI_UX_COLABORADOR'
    ),
    TRUE
FROM usuarios u
JOIN selos s   ON LOWER(s.slug) = 'engajamento'
JOIN projetos p ON p.titulo = 'Frontend React do Sistema UNIVC'
WHERE u.email = 'felipe.souza@ivc.br';


-- =======================================================
-- LUCAS (ALUNO) ganha selo por participação em testes do projeto da API
-- =======================================================

INSERT INTO usuarios_selos (
    id_usuario, id_selo, motivo, origem, referencia, habilitado
)
SELECT 
    u.id_usuario,
    s.id_selo,
    'Executou testes de integração da API e reportou bugs importantes.',
    'PROJETO',
    jsonb_build_object(
        'id_projeto', p.id_projeto,
        'titulo_projeto', p.titulo,
        'papel', 'TESTER',
        'cenario', 'Testes de login e consumo de rotas protegidas'
    ),
    TRUE
FROM usuarios u
JOIN selos s   ON LOWER(s.slug) = 'colaboracao'
JOIN projetos p ON p.titulo = 'API de Portfólio UNIVC'
WHERE u.email = 'lucas.almeida@aluno.ivc.br';
