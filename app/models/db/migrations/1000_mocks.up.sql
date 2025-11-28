-- -------------------------------------------------------
-- USUARIOS
-- -------------------------------------------------------
INSERT INTO usuarios (
    nome, password, curso, periodo, ano_inicio, ano_fim,
    data_nascimento, contato, email, imagem, permissao, new, habilitado, validacao
) VALUES
-- 1) ENZO - ADMIN
(
    'Enzo',
    '$2b$12$5HN21tQ8HWUBcnjlkphMp.nwTo0MHTubABF38lPlOCJZHY5hpCGDu',        -- substitua depois
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    '(27) 99999-1111',
    'enzo@enzo.com',
    NULL,
    'ADMIN',
    TRUE,
    TRUE,
    TRUE
),

-- 2) FELIPE SOUZA - ADMIN
(
    'Felipe Souza',
    '$2b$12$5HN21tQ8HWUBcnjlkphMp.nwTo0MHTubABF38lPlOCJZHY5hpCGDu',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    '(27) 99999-2222',
    'felipe.souza@ivc.br',
    NULL,
    'ADMIN',
    TRUE,
    TRUE,
    TRUE
),

-- 3) PROFESSOR
(
    'Mariana Ribeiro',
    '$2b$12$5HN21tQ8HWUBcnjlkphMp.nwTo0MHTubABF38lPlOCJZHY5hpCGDu',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    '(27) 99999-3333',
    'mariana.ribeiro@ivc.br',
    NULL,
    'PROFESSOR',
    TRUE,
    TRUE,
    TRUE
),

-- 4) ALUNO
(
    'Lucas Almeida',
    '$2b$12$5HN21tQ8HWUBcnjlkphMp.nwTo0MHTubABF38lPlOCJZHY5hpCGDu',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    '(27) 99999-4444',
    'lucas.almeida@aluno.ivc.br',
    NULL,
    'ALUNO',
    TRUE,
    TRUE,
    TRUE
);

-- -------------------------------------------------------
-- LEVEL
-- -------------------------------------------------------

-- =====================================================
-- ENZO (ADMIN)
-- =====================================================
UPDATE usuarios
SET 
    xp_total = 420,
    id_level_atual = (
        SELECT id_level 
        FROM levels 
        WHERE 420 BETWEEN xp_min AND xp_max
        LIMIT 1
    )
WHERE email = 'enzo@enzo.com';


-- =====================================================
-- FELIPE (ADMIN)
-- =====================================================
UPDATE usuarios
SET 
    xp_total = 180,
    id_level_atual = (
        SELECT id_level 
        FROM levels 
        WHERE 180 BETWEEN xp_min AND xp_max
        LIMIT 1
    )
WHERE email = 'felipe.souza@ivc.br';


-- =====================================================
-- MARIANA (PROFESSOR)
-- =====================================================
UPDATE usuarios
SET 
    xp_total = 600,
    id_level_atual = (
        SELECT id_level 
        FROM levels 
        WHERE 600 BETWEEN xp_min AND xp_max
        LIMIT 1
    )
WHERE email = 'mariana.ribeiro@ivc.br';


-- =====================================================
-- LUCAS (ALUNO)
-- =====================================================
UPDATE usuarios
SET 
    xp_total = 75,
    id_level_atual = (
        SELECT id_level 
        FROM levels 
        WHERE 75 BETWEEN xp_min AND xp_max
        LIMIT 1
    )
WHERE email = 'lucas.almeida@aluno.ivc.br';

-- -------------------------------------------------------
-- CURSOS
-- -------------------------------------------------------

INSERT INTO cursos (
    nome, descricao, periodo, lista_periodos, habilitado
) VALUES
-- 1) Técnico em Desenvolvimento de Sistemas
(
    'Técnico em Desenvolvimento de Sistemas',
    'Curso focado em programação, banco de dados, APIs, testes e práticas modernas de desenvolvimento.',
    4,
    ARRAY['1º período', '2º período', '3º período', '4º período'],
    TRUE
),

-- 2) Técnico em Informática
(
    'Técnico em Informática',
    'Curso voltado para montagem e manutenção de computadores, redes e fundamentos de software.',
    4,
    ARRAY['1º período', '2º período', '3º período', '4º período'],
    TRUE
),

-- 3) Análise e Desenvolvimento de Sistemas
(
    'Análise e Desenvolvimento de Sistemas',
    'Curso superior focado em engenharia de software, arquitetura de sistemas e soluções backend e frontend.',
    6,
    ARRAY['1º período', '2º período', '3º período', '4º período', '5º período', '6º período'],
    TRUE
),

-- 4) Ciência da Computação
(
    'Ciência da Computação',
    'Formação completa na área de computação, com foco em algoritmos, estruturas de dados, IA e sistemas operacionais.',
    8,
    ARRAY[
        '1º período', '2º período', '3º período', '4º período',
        '5º período', '6º período', '7º período', '8º período'
    ],
    TRUE
),

-- 5) Engenharia de Software
(
    'Engenharia de Software',
    'Curso voltado para processos, qualidade, métricas, arquitetura de software e metodologias ágeis.',
    8,
    ARRAY[
        '1º período', '2º período', '3º período', '4º período',
        '5º período', '6º período', '7º período', '8º período'
    ],
    TRUE
),

-- 6) Redes de Computadores
(
    'Redes de Computadores',
    'Curso técnico focado em infraestrutura de redes, protocolos, segurança e administração de sistemas.',
    4,
    ARRAY['1º período', '2º período', '3º período', '4º período'],
    TRUE
),

-- 7) Segurança da Informação
(
    'Segurança da Informação',
    'Curso destinado à proteção de dados, análise de vulnerabilidades, SIEM, DevSecOps e auditoria.',
    4,
    ARRAY['1º período', '2º período', '3º período', '4º período'],
    TRUE
);

-- -------------------------------------------------------
-- LEVELS
-- -------------------------------------------------------

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

-- -------------------------------------------------------
-- PROJETOS
-- -------------------------------------------------------
INSERT INTO projetos (
    id_usuario, titulo, descricao, texto, imagem_atividade,
    tags, xp_conclusao, data_inicio, data_fim, status, habilitado
) VALUES
(
    (SELECT id_usuario FROM usuarios WHERE email = 'enzo@enzo.com'),
    'API de Portfólio UNIVC',
    'Desenvolvimento da API REST da plataforma, com autenticação JWT e integração total com o Front.',
    '''
    # API Portfólio UNIVC
    A API do Portfólio UNIVC é responsável por centralizar toda a lógica de autenticação, controle de permissões, gerenciamento de alunos, professores, cursos, projetos, níveis, XP e selos. O objetivo principal é fornecer uma camada backend robusta, escalável e segura, permitindo que diversas aplicações do ecossistema UNIVC consumam os dados de forma padronizada.

    ## Objetivos da Demanda
    - Criar uma API totalmente documentada com Swagger (OpenAPI 3).
    - Implementar autenticação baseada em JWT com Bearer Token.
    - Criar rotas estruturadas em Blueprints para módulos como: **Usuários**, **Cursos**, **Projetos**, **Níveis**, **Missões**, **Selos** e **Histórico de XP**.
    - Garantir segurança com verificação de permissões (ADMIN, PROFESSOR e ALUNO).
    - Integrar com PostgreSQL utilizando camada robusta para transações e consultas.
    - Criar migrations consistentes para evolução do banco.
    - Estruturar logs e respostas padronizadas.

    ## Tecnologias e Ferramentas Utilizadas
    - **Python 3.12**
    - **Flask 3.x** com Blueprints
    - **JWT (PyJWT)** para autenticação
    - **psycopg2** para integração com PostgreSQL
    - **Flasgger / Swagger UI** para documentação
    - **PostgreSQL 15+** com uso de UUID (pgcrypto)
    - **Docker** (ambiente recomendado)
    - **Gunicorn** (produção)
    - **Render / Railway / Dokploy** (deploy opcional)

    ## Escopo Técnico
    1. **Autenticação JWT**
    - Rota de login recebe email e senha.
    - Validação via bcrypt.
    - Geração de token com validade configurável.
    - Middleware `require_auth` protege as rotas.

    2. **Gestão de Usuários**
    - Cadastro, edição e validação.
    - Controle de permissões.
    - Suporte a imagem de perfil.

    3. **Módulo de Cursos**
    - Cada curso possui períodos e lista de períodos.
    - CRUD completo.
    - Filtragem e paginação.

    4. **Módulo de Projetos**
    - API permite criar projetos com título, descrição, imagem, XP e status.
    - Status é atualizado automaticamente com base em `data_inicio` e `data_fim`.
    - Tags são armazenadas como arrays (`TEXT[]`).
    - Projeto possui relação forte com o usuário que criou.

    5. **Módulo de Selos e Gamificação**
    - CRUD de selos com gradientes de cor, ícones e tipos.
    - Relacionamento `usuarios_selos` com origem, motivo e referencia JSONB.
    - Respeita índice único (1 selo por usuário).

    6. **Sistema de Níveis e XP**
    - Cálculo automático do nível do usuário baseado em XP estendido.
    - Histórico detalhado no `usuarios_xp_historico`.

    7. **Módulo de Missões**
    - Missões com XP e ordem.
    - Preparado para exibição no front.

    ## Fluxo Real do Projeto
    - O professor/administrador cria um projeto no painel.
    - A API valida permissões e grava o registro no PostgreSQL.
    - Quando um aluno conclui o projeto, uma rota de conclusão é chamada.
    - Isso gera um evento: soma XP + atualização do nível + registro no histórico.
    - Caso aplicável, um selo é concedido automaticamente via `usuarios_selos`.
    - O front recebe todos os dados estruturados pela API.

    ## Considerações de Segurança
    - Todas as respostas seguem padrão JSON.
    - Tokens inválidos retornam HTTP 401.
    - Acesso negado retorna HTTP 403.
    - Validação de payloads é feita antes do processamento.
    - Insertions usam parâmetros para evitar SQL Injection.

    ## Conclusão
    A API Portfólio UNIVC oferece uma base sólida para toda a plataforma, garantindo organização, escalabilidade e segurança. Com módulos separados, documentação clara e integração fluida com o frontend, ela sustenta toda a camada de gamificação, progresso acadêmico e gestão educacional do ecossistema UNIVC.
    ''',
    'https://img.freepik.com/fotos-gratis/pessoas-a-trabalhar-em-equipa_23-2149136895.jpg?semt=ais_hybrid&w=740&q=80',
    ARRAY['python', 'flask', 'backend', 'api'],
    150,
    '2025-10-10 09:00:00',
    '2026-01-15 23:59:59',
    'EM_ANDAMENTO',
    TRUE
),

(
    (SELECT id_usuario FROM usuarios WHERE email = 'felipe.souza@ivc.br'),
    'Frontend React do Sistema UNIVC',
    'Interface completa com animações, chat integrado e navegação inteligente.',
    '''
## Interface do Portfólio
A Interface do Portfólio UNIVC foi desenvolvida para oferecer uma experiência moderna, interativa e fluida aos usuários. Inspirada em plataformas de IA e ambientes de aprendizado adaptativo, ela combina elementos de chat, histórico de ações, animações suaves e navegação inteligente entre módulos, proporcionando ao aluno e ao professor uma utilização simples, objetiva e visualmente atrativa.

## Objetivos da Interface
- Criar uma camada visual intuitiva para consulta e gerenciamento das informações do usuário.
- Exibir o histórico completo de interações, como evolução em cursos, XP, projetos e selos.
- Oferecer um chat lateral fixo para interação com o assistente virtual da plataforma.
- Integrar animações fluidas para transição entre páginas, melhorando a percepção de continuidade.
- Reagir dinamicamente às ações do usuário (ex.: concluir um projeto, receber um selo, responder missão).

## Principais Funcionalidades
1. **Chat Integrado**
- Sempre visível na interface.
- Exibe histórico completo da conversa.
- Responde perguntas sobre cursos, progresso, projetos, certificados, selos e XP.
- Oferece sugestões automáticas baseadas no comportamento do usuário.

2. **Histórico de Atividades**
- Exibição cronológica do que o usuário realizou.
- Filtrado por tipo: projeto, missão, nível, XP, selos.
- Atualização em tempo real após qualquer operação na API.

3. **Navegação Inteligente e Animada**
- Troca de páginas com transições suaves.
- Quando o usuário pede algo específico (ex.: “ver projetos”), a interface aciona animação de rotação ou fade para destacar a seção correspondente.
- Sessões borradas (blur) quando o usuário acessa informações protegidas ou quando não existem dados suficientes.

4. **Dashboard Personalizado**
- Cards de progresso com barras animadas.
- Níveis, XP acumulado e metas visuais.
- Lista dos últimos projetos visualizados ou concluídos.

5. **Integração Total com a API UNIVC**
- Comunicação via endpoints protegidos com JWT.
- Busca de dados do usuário, missões, selos e projetos.
- Atualização automática via chamadas periódicas ou WebSocket opcional.

## Fluxo Real de Uso
- O aluno acessa a interface e o sistema carrega seus dados por meio do JWT.
- O chat exibe sugestões baseadas no curso atual e no progresso.
- Ao solicitar “ver meus projetos”, a interface processa o comando e exibe a página com uma animação de transição.
- Caso o aluno conclua uma missão, a interface atualiza os cards e o histórico imediatamente.
- Quando novos selos são concedidos, a UI exibe uma animação de destaque.

## Considerações de UX/UI
- Foco em acessibilidade, contraste e leitura.
- Layout responsivo para desktop e mobile.
- Uso de Tailwind CSS para padronização visual.
- Componentização com React e padrões modernos (Hooks, Context, Query, Shadcn UI).

## Conclusão
A Interface do Portfólio UNIVC não é apenas uma camada visual, mas uma experiência interativa e guiada, permitindo que alunos e professores acompanhem a evolução acadêmica e de habilidades de forma clara, dinâmica e envolvente. Ela integra o poder da API com uma UI moderna, elevando o engajamento e aprendizado dentro da plataforma.
    ''',
    'https://img.freepik.com/free-photo/business-people-arranging-various-adhesive-notes-with-text-glass-office_662251-1531.jpg',
    ARRAY['react', 'tailwind', 'frontend'],
    120,
    '2026-02-05 08:00:00',
    '2026-04-01 18:00:00',
    'AGUARDANDO_INICIO',
    TRUE
);

-- -------------------------------------------------------
-- MISSÕES
-- -------------------------------------------------------

INSERT INTO missoes (
    titulo, descricao, tag, xp_reward, ordem, habilitado
) VALUES
-- 1) Missão rápida
(
    'Configurar Ambiente de Desenvolvimento',
    'Instalar Python, VSCode, Git e configurar o ambiente necessário para iniciar os projetos.',
    'RAPIDA',
    30,
    1,
    TRUE
),

-- 2) Missão rápida
(
    'Criar Primeiro Repositório no GitHub',
    'Criar um repositório público, subir um README inicial e configurar o .gitignore.',
    'RAPIDA',
    20,
    2,
    TRUE
),

-- 3) Missão desafio
(
    'Criar uma API REST Básica',
    'Desenvolver uma API simples com rotas GET/POST utilizando Flask ou FastAPI.',
    'DESAFIO',
    80,
    3,
    TRUE
),

-- 4) Missão PBL
(
    'Construir Página Inicial do Portfólio',
    'Criar o layout, containers e estrutura base do portfólio UNIVC usando React e Tailwind.',
    'PBL',
    100,
    4,
    TRUE
),

-- 5) Missão desafio
(
    'Integrar API com Banco de Dados PostgreSQL',
    'Adicionar conexão com PostgreSQL, criar tabelas e implementar operações CRUD.',
    'DESAFIO',
    120,
    5,
    TRUE
),

-- 6) Missão rápida
(
    'Criar Primeira Automação no Pipefy',
    'Configurar um fluxo simples e automatizar uma etapa via Pipefy.',
    'RAPIDA',
    40,
    6,
    TRUE
),

-- 7) Missão PBL
(
    'Implementar Sistema de Login com JWT',
    'Criar autenticação completa com criptografia de senhas, tokens JWT e middleware de proteção.',
    'PBL',
    150,
    7,
    TRUE
);

-- -------------------------------------------------------
-- SELOS
-- -------------------------------------------------------

INSERT INTO selos (
    titulo, slug, descricao, icone, cor_inicio, cor_fim, tipo, ordem, habilitado
) VALUES

-- 1) Selo Criatividade
(
    'Criatividade',
    'criatividade',
    'Reconhecimento por soluções originais e ideias inovadoras no desenvolvimento de projetos.',
    'sparkles',
    '#22c55e',
    '#a3e635',
    'CRIATIVIDADE',
    1,
    TRUE
),

-- 2) Selo Resolução de Problemas
(
    'Resolução de Problemas',
    'resolucao_problemas',
    'Concedido a quem demonstra habilidade avançada em resolver desafios técnicos complexos.',
    'lightbulb',
    '#3b82f6',
    '#60a5fa',
    'RESOLUCAO_PROBLEMAS',
    2,
    TRUE
),

-- 3) Selo Colaboração
(
    'Colaboração',
    'colaboracao',
    'Para alunos que ajudam colegas, contribuem em equipe e promovem um ambiente positivo.',
    'users',
    '#8b5cf6',
    '#c084fc',
    'COLABORACAO',
    3,
    TRUE
),

-- 4) Selo Velocidade
(
    'Velocidade',
    'velocidade',
    'Premiação para conclusão rápida e eficiente de atividades e missões.',
    'bolt',
    '#f59e0b',
    '#fcd34d',
    'DESEMPENHO',
    4,
    TRUE
),

-- 5) Selo Excelência Técnica
(
    'Excelência Técnica',
    'excelencia_tecnica',
    'Reconhecimento de domínio técnico em programação, APIs, bancos de dados e boas práticas.',
    'trophy',
    '#ef4444',
    '#fca5a5',
    'EXCELENCIA',
    5,
    TRUE
),

-- 6) Selo Engajamento
(
    'Engajamento',
    'engajamento',
    'Para quem participa ativamente das aulas, discussões, projetos e práticas.',
    'chat-bubble-left-right',
    '#06b6d4',
    '#67e8f9',
    'PARTICIPACAO',
    6,
    TRUE
),

-- 7) Selo Mentor
(
    'Mentor',
    'mentor',
    'Concedido a quem auxilia outros alunos com dúvidas, explicações e mentorias técnicas.',
    'handshake',
    '#84cc16',
    '#bef264',
    'AUXILIO',
    7,
    TRUE
);

-- -------------------------------------------------------
-- Vínculos de Selos aos Usuários
-- -------------------------------------------------------

INSERT INTO usuarios_selos (
    id_usuario, id_selo, motivo, origem, referencia, habilitado
) VALUES

-- =======================================================
-- 1) ENZO (ADMIN)
-- =======================================================
(
    (SELECT id_usuario FROM usuarios WHERE email = 'enzo@enzo.com'),
    (SELECT id_selo FROM selos WHERE slug = 'excelencia_tecnica'),
    'Desenvolveu a API principal da plataforma com excelente qualidade.',
    'PROJETO',
    jsonb_build_object('id_projeto', 'API'),
    TRUE
),

(
    (SELECT id_usuario FROM usuarios WHERE email = 'enzo@enzo.com'),
    (SELECT id_selo FROM selos WHERE slug = 'resolucao_problemas'),
    'Resolveu um bug crítico relacionado ao JWT.',
    'ATIVIDADE',
    jsonb_build_object('tarefa', 'Correção JWT'),
    TRUE
),

-- =======================================================
-- 2) FELIPE (ADMIN)
-- =======================================================
(
    (SELECT id_usuario FROM usuarios WHERE email = 'felipe.souza@ivc.br'),
    (SELECT id_selo FROM selos WHERE slug = 'colaboracao'),
    'Auxiliou no alinhamento entre times e na documentação do sistema.',
    'MANUAL',
    jsonb_build_object('observacao', 'Melhor comunicação interna'),
    TRUE
),

(
    (SELECT id_usuario FROM usuarios WHERE email = 'felipe.souza@ivc.br'),
    (SELECT id_selo FROM selos WHERE slug = 'engajamento'),
    'Participou de todas as reuniões de sprint e revisões técnicas.',
    'ATIVIDADE',
    jsonb_build_object('sprint', 'Sprint 03'),
    TRUE
),

-- =======================================================
-- 3) MARIANA (PROFESSOR)
-- =======================================================
(
    (SELECT id_usuario FROM usuarios WHERE email = 'mariana.ribeiro@ivc.br'),
    (SELECT id_selo FROM selos WHERE slug = 'mentor'),
    'Fez mentoria para alunos em dificuldades no módulo de APIs.',
    'MANUAL',
    jsonb_build_object('modulo', 'API REST'),
    TRUE
),

(
    (SELECT id_usuario FROM usuarios WHERE email = 'mariana.ribeiro@ivc.br'),
    (SELECT id_selo FROM selos WHERE slug = 'criatividade'),
    'Criou exercícios inovadores utilizando problemas reais.',
    'ATIVIDADE',
    jsonb_build_object('atividade', 'Desafio prático APIs'),
    TRUE
),

-- =======================================================
-- 4) LUCAS (ALUNO)
-- =======================================================
(
    (SELECT id_usuario FROM usuarios WHERE email = 'lucas.almeida@aluno.ivc.br'),
    (SELECT id_selo FROM selos WHERE slug = 'velocidade'),
    'Concluiu atividades antes do prazo por 3 semanas consecutivas.',
    'ATIVIDADE',
    jsonb_build_object('semanas', 3),
    TRUE
),

(
    (SELECT id_usuario FROM usuarios WHERE email = 'lucas.almeida@aluno.ivc.br'),
    (SELECT id_selo FROM selos WHERE slug = 'colaboracao'),
    'Ajudou colegas com dúvidas sobre Git e GitHub.',
    'MANUAL',
    jsonb_build_object('topico', 'Git'),
    TRUE
);