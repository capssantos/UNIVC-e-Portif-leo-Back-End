import os
from flask import Blueprint, request, jsonify, g
from dotenv import load_dotenv
from ..models.db import one, many, run
from ..models.auth import require_auth
from datetime import datetime

load_dotenv()
projetos_bp = Blueprint("projetos", __name__)

def _is_admin():
    """
    Verifica se o usuário autenticado possui permissao = 'admin'.
    """
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return False

    row = one(
        "SELECT permissao FROM usuarios WHERE id_usuario = %(id)s",
        {"id": user_id}
    )
    if not row:
        return False

    return row.get("permissao") == "ADMIN"

def _is_admin_or_professor():
    """
    Verifica se o usuário autenticado possui permissão suficiente
    para publicar projetos. Permissões válidas: ADMIN, PROFESSOR.
    """
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return False

    row = one(
        "SELECT permissao FROM usuarios WHERE id_usuario = %(id)s",
        {"id": user_id}
    )

    if not row or not row.get("permissao"):
        return False

    permissao = row["permissao"].strip().upper()
    permissoes_validas = {"ADMIN", "PROFESSOR"}

    return permissao in permissoes_validas

from datetime import datetime
from flask import Blueprint, request, jsonify, g
from ..models.db import one, many, run
from ..models.auth import require_auth

projetos_bp = Blueprint("projetos", __name__)

# Se já tiver esse helper em outro lugar, reutiliza
def _is_admin_or_professor():
    """
    Verifica se o usuário autenticado possui permissão suficiente
    para publicar projetos. Permissões válidas: ADMIN, PROFESSOR.
    """
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return False

    row = one(
        "SELECT permissao FROM usuarios WHERE id_usuario = %(id)s",
        {"id": user_id}
    )

    if not row or not row.get("permissao"):
        return False

    permissao = row["permissao"].strip().upper()
    permissoes_validas = {"ADMIN", "PROFESSOR"}

    return permissao in permissoes_validas


# --------- Listar projetos ---------
@projetos_bp.get("")
@require_auth
def list_projetos():
    """
    Listar projetos

    Retorna a lista de projetos com suporte a:

    - filtro por dono do projeto (`id_usuario`)
    - filtro por tag (`tag`)
    - filtro por habilitado (`habilitado`)
    - filtro por participação do usuário autenticado (`me`)
    - paginação (`limit`, `offset`)

    A rota possui **dois comportamentos distintos**:

    1) `me=true`  
       Lista **apenas projetos em que o usuário autenticado participa**, ignorando
       o filtro `id_usuario` (dono).  
       O resultado inclui informações da participação:

       - `id_participacao`
       - `meu_papel`
       - `meu_status`

    2) `me` ausente ou `me=false`  
       Lista projetos de forma geral (públicos do ponto de vista da API),
       respeitando os filtros `id_usuario`, `tag`, `habilitado`, `limit`, `offset`.

    Além dos campos do projeto, a API calcula e retorna sempre os campos:

    - `percentual_conclusao` (0.0 a 100.0), baseado em `data_inicio` e `data_fim`.
    - `selos`: lista de selos associados ao projeto.

    Requer autenticação via Bearer token.

    ---
    tags:
      - Projetos
    security:
      - Bearer: []
    produces:
      - application/json
    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: "Token JWT no formato Bearer <token>"

      - in: query
        name: id_usuario
        required: false
        type: string
        format: uuid
        description: >
          Filtra projetos pelo **dono do projeto** (coluna `id_usuario` da tabela `projetos`).
          Ignorado quando `me=true`.

      - in: query
        name: tag
        required: false
        type: string
        description: >
          Filtra projetos que contenham a tag informada na coluna `tags`
          (é feito um filtro `tags @> ARRAY[tag]::text[]`).
        example: "python"

      - in: query
        name: habilitado
        required: false
        type: string
        description: >
          Filtra pelo status de habilitação (`habilitado`) do projeto.
          Aceita: true/false, 1/0, t/f, sim/não, yes/no (case-insensitive).
        enum:
          - "true"
          - "false"

      - in: query
        name: me
        required: false
        type: string
        description: >
          Quando `me=true`, a rota retorna **somente projetos em que o usuário autenticado
          participa** (usa a tabela `projetos_participantes`) e **ignora** o filtro `id_usuario`.  
          Aceita: true/false, 1/0, t/f, sim/não, yes/no (case-insensitive).
        enum:
          - "true"
          - "false"

      - in: query
        name: limit
        required: false
        type: integer
        default: 20
        description: "Quantidade máxima de registros a serem retornados (>= 0)."

      - in: query
        name: offset
        required: false
        type: integer
        default: 0
        description: "Deslocamento para paginação (>= 0)."

    responses:
      200:
        description: >
          Lista de projetos retornada com sucesso.  
          Quando `me=true`, cada item inclui também os campos de participação
          (`id_participacao`, `meu_papel`, `meu_status`).
        schema:
          type: array
          items:
            type: object
            properties:
              id_projeto:
                type: string
                format: uuid
              id_usuario:
                type: string
                format: uuid
                description: "ID do dono/criador do projeto."
              titulo:
                type: string
              descricao:
                type: string
              texto:
                type: string
              imagem_atividade:
                type: string
                description: "URL da imagem de capa/ilustração do projeto."
              tags:
                type: array
                items:
                  type: string
              xp_conclusao:
                type: integer
                description: "XP concedido ao aluno ao concluir o projeto."
              data_inicio:
                type: string
                format: date-time
                nullable: true
              data_fim:
                type: string
                format: date-time
                nullable: true
              status:
                type: string
                description: "Status atual do projeto (AGUARDANDO_INICIO, EM_ANDAMENTO, PAUSADO, CANCELADO, CONCLUIDO)."
              habilitado:
                type: boolean
              created_at:
                type: string
                format: date-time
              updated_at:
                type: string
                format: date-time
              percentual_conclusao:
                type: number
                format: float
                description: >
                  Percentual estimado de conclusão baseado em `data_inicio` e `data_fim`,
                  variando de 0.0 a 100.0. Se não houver datas, retorna 0.0.
              selos:
                type: array
                description: "Selos associados ao projeto."
                items:
                  type: object
                  properties:
                    id_selo:
                      type: string
                      format: uuid
                    titulo:
                      type: string
                    slug:
                      type: string
                    descricao:
                      type: string
                    icone:
                      type: string
                    cor_inicio:
                      type: string
                    cor_fim:
                      type: string
                    tipo:
                      type: string
                    ordem:
                      type: integer
              id_participacao:
                type: string
                format: uuid
                description: >
                  **Somente quando `me=true`.** ID da participação do usuário
                  autenticado na tabela `projetos_participantes`.
              meu_papel:
                type: string
                description: >
                  **Somente quando `me=true`.** Papel do usuário autenticado no projeto
                  (ex.: ALUNO, MONITOR, MEMBRO).
              meu_status:
                type: string
                description: >
                  **Somente quando `me=true`.** Status da participação do usuário
                  (PENDENTE, APROVADO, RECUSADO, CANCELADO, CONCLUIDO).

      400:
        description: >
          Erro de validação nos parâmetros de query.  
          Exemplos:
            - `limit` ou `offset` não numéricos ou negativos
            - `me` com valor inválido
            - `habilitado` com valor inválido
        schema:
          type: object
          properties:
            error:
              type: string

      401:
        description: "Usuário não autenticado (token ausente ou inválido)."
        schema:
          type: object
          properties:
            error:
              type: string
    """
    headers_dict = dict(request.headers)
    print(f"[PROJ LIST] - Headers: {headers_dict}")
    print(f"[PROJ LIST] - Args: {dict(request.args)}")

    id_usuario = request.args.get("id_usuario")
    tag        = request.args.get("tag")
    habilitado = request.args.get("habilitado")  # 'true', 'false' ou None
    me_param   = request.args.get("me")          # 'true', 'false' ou None

    try:
        limit  = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"error": "limit e offset devem ser inteiros"}), 400

    if limit < 0 or offset < 0:
        return jsonify({"error": "limit e offset devem ser não negativos"}), 400

    # ----------- interpreta me=true|false -----------
    me_flag = False
    if me_param is not None:
        value = me_param.strip().lower()
        if value in ("true", "1", "t", "sim", "yes"):
            me_flag = True
        elif value in ("false", "0", "f", "nao", "não", "no"):
            me_flag = False
        else:
            return jsonify({
                "error": "Parâmetro 'me' deve ser true ou false"
            }), 400

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "nenhum usuário autenticado"}), 401

    # ------------------------------------------------
    # Caso 1: me=true → projetos em que EU PARTICIPO
    # (ignoramos id_usuario aqui de propósito)
    # ------------------------------------------------
    if me_flag:
        filters = ["pp.id_usuario = %(id_usuario_part)s"]
        params = {
            "limit":           limit,
            "offset":          offset,
            "id_usuario_part": user_id,
        }

        if tag:
            filters.append("p.tags @> ARRAY[%(tag)s]::text[]")
            params["tag"] = tag

        if habilitado is not None:
            value = habilitado.strip().lower()
            if value in ("true", "1", "t", "sim", "yes"):
                params["habilitado"] = True
            elif value in ("false", "0", "f", "nao", "não", "no"):
                params["habilitado"] = False
            else:
                return jsonify({
                    "error": "Parâmetro 'habilitado' deve ser true ou false"
                }), 400
            filters.append("p.habilitado = %(habilitado)s")

        where_clause = " AND ".join(filters)

        rows = many(f"""
            SELECT
                p.id_projeto,
                p.id_usuario,
                p.titulo,
                p.descricao,
                p.texto,
                p.imagem_atividade,
                p.tags,
                p.xp_conclusao,
                p.data_inicio,
                p.data_fim,
                p.status,
                p.habilitado,
                p.created_at,
                p.updated_at,
                pp.id_participacao,
                pp.papel  AS meu_papel,
                pp.status AS meu_status
            FROM projetos_participantes pp
            JOIN projetos p
              ON p.id_projeto = pp.id_projeto
            WHERE {where_clause}
            ORDER BY p.created_at DESC
            LIMIT %(limit)s
            OFFSET %(offset)s
        """, params)

    # ------------------------------------------------
    # Caso 2: me não informado ou false → lista padrão
    # (aqui sim id_usuario filtra o DONO do projeto)
    # ------------------------------------------------
    else:
        filters = []
        params = {"limit": limit, "offset": offset}

        if id_usuario:
            filters.append("id_usuario = %(id_usuario)s")
            params["id_usuario"] = id_usuario

        if tag:
            filters.append("tags @> ARRAY[%(tag)s]::text[]")
            params["tag"] = tag

        if habilitado is not None:
            value = habilitado.strip().lower()
            if value in ("true", "1", "t", "sim", "yes"):
                params["habilitado"] = True
            elif value in ("false", "0", "f", "nao", "não", "no"):
                params["habilitado"] = False
            else:
                return jsonify({
                    "error": "Parâmetro 'habilitado' deve ser true ou false"
                }), 400
            filters.append("habilitado = %(habilitado)s")

        where_clause = " AND ".join(filters) if filters else "TRUE"

        rows = many(f"""
            SELECT
                id_projeto,
                id_usuario,
                titulo,
                descricao,
                texto,
                imagem_atividade,
                tags,
                xp_conclusao,
                data_inicio,
                data_fim,
                status,
                habilitado,
                created_at,
                updated_at
            FROM projetos
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %(limit)s
            OFFSET %(offset)s
        """, params)

    # ---- cálculo da % de conclusão baseada em data_inicio / data_fim ----
    agora = datetime.utcnow()
    for row in rows:
        data_inicio = row.get("data_inicio")
        data_fim    = row.get("data_fim")

        percentual = 0.0

        if data_inicio and data_fim and data_fim > data_inicio:
            total_segundos = (data_fim - data_inicio).total_seconds()
            elapsed_segundos = (agora - data_inicio).total_seconds()

            if elapsed_segundos <= 0:
                percentual = 0.0
            elif elapsed_segundos >= total_segundos:
                percentual = 100.0
            else:
                percentual = (elapsed_segundos / total_segundos) * 100.0

        row["percentual_conclusao"] = round(percentual, 2)

    # =========================
    #   CARREGAR SELOS
    # =========================
    if not rows:
        return jsonify(rows), 200

    ids_projetos = [r["id_projeto"] for r in rows]

    selos_rows = many(
        """
        SELECT
            ps.id_projeto,
            s.id_selo,
            s.titulo,
            s.slug,
            s.descricao,
            s.icone,
            s.cor_inicio,
            s.cor_fim,
            s.tipo,
            s.ordem
        FROM projetos_selos ps
        JOIN selos s
          ON s.id_selo = ps.id_selo
        WHERE ps.id_projeto = ANY(%(ids)s)
        ORDER BY s.ordem ASC, s.titulo ASC
        """,
        {"ids": ids_projetos},
    )

    selos_por_projeto = {}
    for s in selos_rows:
        pid = s["id_projeto"]
        selo_info = {
            "id_selo": s["id_selo"],
            "titulo": s["titulo"],
            "slug": s["slug"],
            "descricao": s["descricao"],
            "icone": s["icone"],
            "cor_inicio": s["cor_inicio"],
            "cor_fim": s["cor_fim"],
            "tipo": s["tipo"],
            "ordem": s["ordem"],
        }
        selos_por_projeto.setdefault(pid, []).append(selo_info)

    for r in rows:
        r["selos"] = selos_por_projeto.get(r["id_projeto"], [])

    return jsonify(rows), 200

@projetos_bp.post("/")
@require_auth
def create_projeto():
    """
    Criar projeto

    Cria um novo projeto vinculado ao usuário autenticado.  
    Apenas usuários com permissão **ADMIN** ou **PROFESSOR** podem criar projetos.

    Body esperado (JSON):

    {
      "titulo": "Título da atividade",
      "descricao": "Breve descrição da atividade",
      "texto": "Texto completo em markdown ou HTML",
      "imagem_atividade": "URL retornada pela rota de upload",
      "tags": ["python", "flask", "backend"],
      "xp_conclusao": 100,
      "data_inicio": "2025-03-01T08:00:00",
      "data_fim": "2025-03-30T23:59:59",
      "selos": ["uuid-do-selo-1", "uuid-do-selo-2"]
    }

    Regras:
      - `titulo` e `texto` são obrigatórios.
      - `tags` deve ser uma lista de strings (se omitida, assume lista vazia).
      - `xp_conclusao`:
          - Se omitida, assume 0.
          - Deve ser inteiro >= 0.
      - `selos`:
          - Opcional.
          - Se enviado, deve ser lista de UUIDs de selos habilitados.

    Regras de status (definido automaticamente no INSERT):
      - Se `data_inicio` for nula ou futura → status = AGUARDANDO_INICIO
      - Se `data_inicio` for no passado ou agora → status = EM_ANDAMENTO

    ---
    tags:
      - Projetos
    security:
      - Bearer: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: "Token JWT no formato Bearer <token>"

      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - titulo
            - texto
          properties:
            titulo:
              type: string
              description: "Título do projeto/atividade"
              example: "Desenvolvendo uma API em Flask"
            descricao:
              type: string
              description: "Breve descrição do projeto"
              example: "Projeto prático para desenvolver uma API REST em Flask."
            texto:
              type: string
              description: "Descrição longa, podendo ser em markdown ou HTML"
              example: "Nesta atividade, o aluno irá construir endpoints de CRUD..."
            imagem_atividade:
              type: string
              description: "URL da imagem da atividade já hospedada (ex: Spaces/CDN)"
              example: "https://cdn.seuservidor.com/imagens/projetos/api-flask.png"
            tags:
              type: array
              description: "Lista de tags relacionadas ao projeto"
              items:
                type: string
              example: ["python", "flask", "backend"]
            xp_conclusao:
              type: integer
              description: "Quantidade de XP concedida ao aluno ao concluir o projeto"
              minimum: 0
              example: 100
            data_inicio:
              type: string
              format: date-time
              description: "Data/hora de início do projeto (ISO 8601)"
              example: "2025-03-01T08:00:00"
            data_fim:
              type: string
              format: date-time
              description: "Data/hora de término do projeto (ISO 8601)"
              example: "2025-03-30T23:59:59"
            selos:
              type: array
              description: "Lista de IDs de selos habilitados que serão vinculados ao projeto"
              items:
                type: string
                format: uuid
              example:
                - "11111111-2222-3333-4444-555555555555"
                - "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    responses:
      201:
        description: "Projeto criado com sucesso"
        schema:
          type: object
          properties:
            id_projeto:
              type: string
              format: uuid
            id_usuario:
              type: string
              format: uuid
            titulo:
              type: string
            descricao:
              type: string
            texto:
              type: string
            imagem_atividade:
              type: string
            tags:
              type: array
              items:
                type: string
            xp_conclusao:
              type: integer
            data_inicio:
              type: string
              format: date-time
            data_fim:
              type: string
              format: date-time
            status:
              type: string
              description: "Status inicial calculado automaticamente"
              example: "AGUARDANDO_INICIO"
            habilitado:
              type: boolean
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time
            selos:
              type: array
              description: "Lista de selos efetivamente vinculados ao projeto"
              items:
                type: string
                format: uuid

      400:
        description: |
          Erro de validação ou regra de negócio, por exemplo:
            - campos obrigatórios ausentes (titulo, texto)
            - xp_conclusao inválido ou negativo
            - tags não é lista de strings
            - selos não é lista de UUIDs
            - selos informados não existem ou estão desabilitados

      401:
        description: "Usuário não autenticado"

      403:
        description: "Permissão insuficiente (usuário não é ADMIN nem PROFESSOR)"
    """
    headers_dict = dict(request.headers)
    data = request.get_json(force=True, silent=True) or {}
    print(f"[PROJ CRIAR] - Headers: {headers_dict}")
    print(f"[PROJ CRIAR] - Body: {data}")

    if not _is_admin_or_professor():
        return jsonify({"error": "acesso restrito a administradores e professores"}), 403

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "nenhum usuário autenticado"}), 401

    titulo           = data.get("titulo")
    descricao        = data.get("descricao")
    texto            = data.get("texto")
    imagem_atividade = data.get("imagem_atividade")
    tags             = data.get("tags")
    selos            = data.get("selos")  # NOVO CAMPO

    xp_conclusao     = data.get("xp_conclusao", 0)
    data_inicio      = data.get("data_inicio") or None  # se vier string vazia, trata como None
    data_fim         = data.get("data_fim") or None

    # Se vier None, vira lista vazia
    if tags is None:
        tags = []

    # Validação tags
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        return jsonify({"error": "tags deve ser uma lista de strings"}), 400

    # Validação obrigatórios
    if not titulo or not texto:
        return jsonify({"error": "titulo e texto são obrigatórios"}), 400

    # Validação xp_conclusao
    try:
        xp_conclusao = int(xp_conclusao)
    except (TypeError, ValueError):
        return jsonify({"error": "xp_conclusao deve ser um inteiro"}), 400

    if xp_conclusao < 0:
        return jsonify({"error": "xp_conclusao não pode ser negativo"}), 400

    # ---------- Validação dos selos ----------
    if selos is None:
        selos = []
    if not isinstance(selos, list):
        return jsonify({"error": "selos deve ser uma lista de UUIDs"}), 400

    # normaliza para string e remove duplicados
    selos_str = [str(s) for s in selos]
    selos_unicos = list(dict.fromkeys(selos_str))  # preserva ordem

    selos_validos_ids = []
    if selos_unicos:
        # busca apenas selos habilitados
        rows_selos = many(
            """
            SELECT id_selo
              FROM selos
             WHERE id_selo = ANY(%(ids)s)
               AND habilitado = TRUE
            """,
            {"ids": selos_unicos},
        )
        encontrados = {str(r["id_selo"]) for r in rows_selos}
        invalidos = [s for s in selos_unicos if s not in encontrados]

        if invalidos:
            return jsonify({
                "error": "Alguns selos não existem ou estão desabilitados.",
                "selos_invalidos": invalidos
            }), 400

        selos_validos_ids = list(encontrados)

    # ---------- Criação do projeto ----------
    row = one("""
        INSERT INTO projetos
            (id_usuario, titulo, descricao, texto, imagem_atividade, tags,
             xp_conclusao, data_inicio, data_fim, status)
        VALUES
            (
                %(id_usuario)s,
                %(titulo)s,
                %(descricao)s,
                %(texto)s,
                %(imagem_atividade)s,
                %(tags)s,
                %(xp_conclusao)s,
                %(data_inicio)s,
                %(data_fim)s,
                CASE
                    WHEN %(data_inicio)s IS NULL THEN 'AGUARDANDO_INICIO'
                    WHEN %(data_inicio)s::timestamp <= NOW() THEN 'EM_ANDAMENTO'
                    ELSE 'AGUARDANDO_INICIO'
                END
            )
        RETURNING
            id_projeto,
            id_usuario,
            titulo,
            descricao,
            texto,
            imagem_atividade,
            tags,
            xp_conclusao,
            data_inicio,
            data_fim,
            status,
            habilitado,
            created_at,
            updated_at
    """, {
        "id_usuario":       user_id,
        "titulo":           titulo,
        "descricao":        descricao,
        "texto":            texto,
        "imagem_atividade": imagem_atividade,
        "tags":             tags,
        "xp_conclusao":     xp_conclusao,
        "data_inicio":      data_inicio,
        "data_fim":         data_fim,
    })

    # ---------- Vincular selos ao projeto ----------
    id_projeto = row["id_projeto"]

    for id_selo in selos_validos_ids:
        run(
            """
            INSERT INTO projetos_selos (id_projeto, id_selo)
            VALUES (%(id_projeto)s, %(id_selo)s)
            ON CONFLICT (id_projeto, id_selo) DO NOTHING
            """,
            {"id_projeto": id_projeto, "id_selo": id_selo},
        )

    row["selos"] = selos_validos_ids

    return jsonify(row), 201

# --------- Detalhar projeto ---------
@projetos_bp.get("/<uuid:id_projeto>")
@require_auth
def get_projeto(id_projeto):
    """
    Detalhar projeto

    Retorna os dados de um projeto específico pelo seu id_projeto,
    incluindo:

    - dados básicos do projeto
    - percentual_conclusao (calculado com base em data_inicio/data_fim)
    - lista de selos associados ao projeto (`selos`)

    Requer autenticação via Bearer token.

    ---
    tags:
      - Projetos
    security:
      - Bearer: []
    produces:
      - application/json
    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: "Token JWT no formato Bearer <token>"
      - in: path
        name: id_projeto
        required: true
        type: string
        format: uuid
        description: "ID do projeto (UUID)"
    responses:
      200:
        description: Projeto encontrado
        schema:
          type: object
          properties:
            id_projeto:
              type: string
              format: uuid
            id_usuario:
              type: string
              format: uuid
            titulo:
              type: string
            descricao:
              type: string
            texto:
              type: string
            imagem_atividade:
              type: string
            tags:
              type: array
              items:
                type: string
            xp_conclusao:
              type: integer
            data_inicio:
              type: string
              format: date-time
              nullable: true
            data_fim:
              type: string
              format: date-time
              nullable: true
            status:
              type: string
            percentual_conclusao:
              type: number
              format: float
            habilitado:
              type: boolean
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time
            selos:
              type: array
              description: "Selos associados a este projeto."
              items:
                type: object
                properties:
                  id_selo:
                    type: string
                    format: uuid
                  titulo:
                    type: string
                  slug:
                    type: string
                  descricao:
                    type: string
                  icone:
                    type: string
                  cor_inicio:
                    type: string
                  cor_fim:
                    type: string
                  tipo:
                    type: string
                  ordem:
                    type: integer
      401:
        description: "Não autenticado"
      404:
        description: "Projeto não encontrado"
    """
    headers_dict = dict(request.headers)
    print(f"[PROJ ID  ] - Headers: {headers_dict}")
    print(f"[PROJ ID  ] - ID_PROJETO: {id_projeto}")

    # ---- dados básicos do projeto ----
    row = one("""
        SELECT
            id_projeto,
            id_usuario,
            titulo,
            descricao,
            texto,
            imagem_atividade,
            tags,
            xp_conclusao,
            data_inicio,
            data_fim,
            status,
            habilitado,
            created_at,
            updated_at
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not row:
        return jsonify({"error": "Projeto não encontrado"}), 404

    # ---- cálculo da % de conclusão baseada em data_inicio / data_fim ----
    agora = datetime.utcnow()
    data_inicio = row.get("data_inicio")
    data_fim    = row.get("data_fim")

    percentual = 0.0

    if data_inicio and data_fim and data_fim > data_inicio:
        total_segundos = (data_fim - data_inicio).total_seconds()
        elapsed_segundos = (agora - data_inicio).total_seconds()

        if elapsed_segundos <= 0:
            percentual = 0.0
        elif elapsed_segundos >= total_segundos:
            percentual = 100.0
        else:
            percentual = (elapsed_segundos / total_segundos) * 100.0

    row["percentual_conclusao"] = round(percentual, 2)

    # ---- carregar selos associados ao projeto ----
    selos_rows = many(
        """
        SELECT
            ps.id_projeto,
            s.id_selo,
            s.titulo,
            s.slug,
            s.descricao,
            s.icone,
            s.cor_inicio,
            s.cor_fim,
            s.tipo,
            s.ordem
        FROM projetos_selos ps
        JOIN selos s
          ON s.id_selo = ps.id_selo
        WHERE ps.id_projeto = %(id_projeto)s
        ORDER BY s.ordem ASC, s.titulo ASC
        """,
        {"id_projeto": id_projeto},
    )

    selos = []
    for s in selos_rows:
        selos.append({
            "id_selo": s["id_selo"],
            "titulo": s["titulo"],
            "slug": s["slug"],
            "descricao": s["descricao"],
            "icone": s["icone"],
            "cor_inicio": s["cor_inicio"],
            "cor_fim": s["cor_fim"],
            "tipo": s["tipo"],
            "ordem": s["ordem"],
        })

    row["selos"] = selos

    return jsonify(row), 200

# --------- Atualizar projeto ---------
@projetos_bp.patch("/<uuid:id_projeto>")
@require_auth
def update_projeto(id_projeto):
    """
    Atualizar projeto

    Atualiza os dados de um projeto existente.

    Regras:
      - Apenas usuários autenticados com permissão **ADMIN** ou **PROFESSOR**.
      - O usuário precisa ser o **dono** do projeto (`id_usuario` do projeto).
      - Projetos com status **CONCLUIDO** não podem ser alterados.
      - Campo `selos`, quando enviado, substitui completamente os vínculos atuais
        de selos daquele projeto:
          - lista vazia [] remove todos os selos
          - campo ausente mantém os selos atuais

    Campos aceitos no body (todos opcionais):

    {
      "titulo": "Novo título",
      "descricao": "Resumo atualizado",
      "texto": "Descrição longa em markdown/HTML",
      "imagem_atividade": "https://cdn.../imagem.png",
      "tags": ["python", "backend"],
      "habilitado": true,
      "xp_conclusao": 100,
      "data_inicio": "2025-02-10T19:30:00Z",
      "data_fim": "2025-03-10T23:59:59Z",
      "status": "EM_ANDAMENTO",
      "selos": ["uuid-selo-1", "uuid-selo-2"]
    }

    Status possíveis:
      - AGUARDANDO_INICIO
      - EM_ANDAMENTO
      - PAUSADO
      - CANCELADO
      - CONCLUIDO

    ---
    tags:
      - Projetos
    security:
      - Bearer: []
    consumes:
      - application/json
    produces:
      - application/json

    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: "Token JWT no formato Bearer <token>"

      - in: path
        name: id_projeto
        required: true
        type: string
        format: uuid
        description: "ID do projeto a ser atualizado (UUID)"

      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            titulo:
              type: string
              description: "Novo título do projeto"
              example: "Plataforma de Portfólio Gamificada"
            descricao:
              type: string
              description: "Resumo atualizado do projeto"
            texto:
              type: string
              description: "Descrição longa em markdown/HTML"
            imagem_atividade:
              type: string
              description: "URL da imagem de capa do projeto"
              example: "https://cdn.meus-arquivos.com/projetos/capa.png"
            tags:
              type: array
              description: "Lista de tags associadas ao projeto"
              items:
                type: string
              example: ["python", "backend", "flask"]
            habilitado:
              type: boolean
              description: "Define se o projeto está habilitado/visível"
              example: true
            xp_conclusao:
              type: integer
              description: "XP concedido ao aluno quando concluir o projeto"
              example: 150
            data_inicio:
              type: string
              format: date-time
              description: "Data/hora de início previsto do projeto"
              example: "2025-02-10T19:30:00Z"
            data_fim:
              type: string
              format: date-time
              description: "Data/hora de término previsto do projeto"
              example: "2025-03-10T23:59:59Z"
            status:
              type: string
              description: "Novo status do projeto"
              enum:
                - AGUARDANDO_INICIO
                - EM_ANDAMENTO
                - PAUSADO
                - CANCELADO
                - CONCLUIDO
              example: "EM_ANDAMENTO"
            selos:
              type: array
              description: >
                Lista de IDs de selos associados ao projeto. Quando enviada,
                substitui completamente os vínculos atuais:
                - lista vazia [] remove todos os selos
                - campo ausente mantém os selos atuais
              items:
                type: string
                format: uuid
              example:
                - "11111111-1111-1111-1111-111111111111"
                - "22222222-2222-2222-2222-222222222222"

    responses:
      200:
        description: "Projeto atualizado com sucesso"
        schema:
          type: object
          properties:
            id_projeto:
              type: string
              format: uuid
            id_usuario:
              type: string
              format: uuid
            titulo:
              type: string
            descricao:
              type: string
            texto:
              type: string
            imagem_atividade:
              type: string
            tags:
              type: array
              items:
                type: string
            xp_conclusao:
              type: integer
            data_inicio:
              type: string
              format: date-time
            data_fim:
              type: string
              format: date-time
            status:
              type: string
            habilitado:
              type: boolean
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time
            selos:
              type: array
              description: "Selos associados ao projeto após a atualização."
              items:
                type: object
                properties:
                  id_selo:
                    type: string
                    format: uuid
                  titulo:
                    type: string
                  slug:
                    type: string
                  descricao:
                    type: string
                  icone:
                    type: string
                  cor_inicio:
                    type: string
                  cor_fim:
                    type: string
                  tipo:
                    type: string
                  ordem:
                    type: integer

      400:
        description: |
          Erro de validação ou regra de negócio, por exemplo:
            - xp_conclusao inválido
            - status inválido
            - nenhum campo enviado
            - projeto já está CONCLUIDO
            - selos inválidos (não existem ou estão desabilitados)

      401:
        description: "Nenhum usuário autenticado"

      403:
        description: "Usuário não é dono do projeto ou não possui permissão (não é ADMIN/PROFESSOR)"

      404:
        description: "Projeto não encontrado"
    """
    headers_dict = dict(request.headers)
    data = request.get_json(force=True, silent=True) or {}
    print(f"[PROJ UPD ] - Headers: {headers_dict}")
    print(f"[PROJ UPD ] - Body: {data}")

    if not _is_admin_or_professor():
        return jsonify({"error": "acesso restrito a administradores e professores"}), 403

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "nenhum usuário autenticado"}), 401

    # Busca dono + status atual do projeto
    projeto = one("""
        SELECT id_projeto, id_usuario, status
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not projeto:
        return jsonify({"error": "Projeto não encontrado"}), 404

    if str(projeto["id_usuario"]) != str(user_id):
        return jsonify({"error": "Você não tem permissão para editar este projeto"}), 403

    status_atual = (projeto.get("status") or "").upper()
    if status_atual == "CONCLUIDO":
        return jsonify({"error": "Projetos concluídos não podem ser alterados"}), 400

    fields = []
    params = {"id": id_projeto}

    # --------------------------
    # Campos básicos
    # --------------------------
    if "titulo" in data:
        fields.append("titulo = %(titulo)s")
        params["titulo"] = data.get("titulo")

    if "descricao" in data:
        fields.append("descricao = %(descricao)s")
        params["descricao"] = data.get("descricao")

    if "texto" in data:
        fields.append("texto = %(texto)s")
        params["texto"] = data.get("texto")

    if "imagem_atividade" in data:
        fields.append("imagem_atividade = %(imagem_atividade)s")
        params["imagem_atividade"] = data.get("imagem_atividade")

    if "tags" in data:
        tags = data.get("tags")
        if tags is None:
            tags = []

        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            return jsonify({"error": "tags deve ser uma lista de strings"}), 400

        fields.append("tags = %(tags)s")
        params["tags"] = tags

    if "habilitado" in data:
        fields.append("habilitado = %(habilitado)s")
        params["habilitado"] = bool(data.get("habilitado"))

    # --------------------------
    # XP / datas / status
    # --------------------------
    if "xp_conclusao" in data:
        try:
            xp = int(data.get("xp_conclusao"))
            if xp < 0:
                return jsonify({"error": "xp_conclusao não pode ser negativo"}), 400
        except (TypeError, ValueError):
            return jsonify({"error": "xp_conclusao deve ser um inteiro"}), 400

        fields.append("xp_conclusao = %(xp_conclusao)s")
        params["xp_conclusao"] = xp

    if "data_inicio" in data:
        fields.append("data_inicio = %(data_inicio)s")
        params["data_inicio"] = data.get("data_inicio")

    if "data_fim" in data:
        fields.append("data_fim = %(data_fim)s")
        params["data_fim"] = data.get("data_fim")

    if "status" in data:
        allowed_status = {
            "AGUARDANDO_INICIO",
            "EM_ANDAMENTO",
            "PAUSADO",
            "CANCELADO",
            "CONCLUIDO"
        }
        status_novo = str(data.get("status", "")).upper()

        if status_novo not in allowed_status:
            return jsonify({
                "error": "status inválido",
                "allowed": list(allowed_status)
            }), 400

        fields.append("status = %(status)s")
        params["status"] = status_novo

    # --------------------------
    # Selos (atualização de vínculos)
    # --------------------------
    alterar_selos = "selos" in data
    selos_validos_ids = []

    if alterar_selos:
        selos_body = data.get("selos")

        if selos_body is None:
            selos_body = []

        if not isinstance(selos_body, list):
            return jsonify({"error": "selos deve ser uma lista de UUIDs"}), 400

        selos_str = [str(s) for s in selos_body]
        selos_unicos = list(dict.fromkeys(selos_str))

        if selos_unicos:
            rows_selos = many(
                """
                SELECT id_selo
                  FROM selos
                 WHERE id_selo = ANY(%(ids)s)
                   AND habilitado = TRUE
                """,
                {"ids": selos_unicos},
            )
            encontrados = {str(r["id_selo"]) for r in rows_selos}
            invalidos = [s for s in selos_unicos if s not in encontrados]

            if invalidos:
                return jsonify({
                    "error": "Alguns selos não existem ou estão desabilitados.",
                    "selos_invalidos": invalidos
                }), 400

            selos_validos_ids = list(encontrados)

    # --------------------------
    # Nada pra atualizar?
    # --------------------------
    if not fields and not alterar_selos:
        return jsonify({"error": "nenhum campo para atualização"}), 400

    # --------------------------
    # UPDATE do projeto (se houver campos)
    # --------------------------
    if fields:
        fields.append("updated_at = NOW()")

        sql = f"""
            UPDATE projetos
               SET {", ".join(fields)}
             WHERE id_projeto = %(id)s
         RETURNING
            id_projeto,
            id_usuario,
            titulo,
            descricao,
            texto,
            imagem_atividade,
            tags,
            xp_conclusao,
            data_inicio,
            data_fim,
            status,
            habilitado,
            created_at,
            updated_at
        """

        row = one(sql, params)
        if not row:
            return jsonify({"error": "Projeto não encontrado após atualização"}), 404
    else:
        # nenhum campo de projeto foi alterado, mas vamos devolver o registro atualizado
        row = one("""
            SELECT
                id_projeto,
                id_usuario,
                titulo,
                descricao,
                texto,
                imagem_atividade,
                tags,
                xp_conclusao,
                data_inicio,
                data_fim,
                status,
                habilitado,
                created_at,
                updated_at
            FROM projetos
            WHERE id_projeto = %(id)s
        """, {"id": id_projeto})

        if not row:
            return jsonify({"error": "Projeto não encontrado"}), 404

    # --------------------------
    # Atualizar vínculos de selos
    # --------------------------
    if alterar_selos:
        # remove todos os vínculos atuais...
        run(
            "DELETE FROM projetos_selos WHERE id_projeto = %(id_projeto)s",
            {"id_projeto": id_projeto},
        )

        # ...e recria com a nova lista
        for id_selo in selos_validos_ids:
            run(
                """
                INSERT INTO projetos_selos (id_projeto, id_selo)
                VALUES (%(id_projeto)s, %(id_selo)s)
                """,
                {"id_projeto": id_projeto, "id_selo": id_selo},
            )

    # --------------------------
    # Carregar selos para o response
    # --------------------------
    selos_rows = many(
        """
        SELECT
            ps.id_projeto,
            s.id_selo,
            s.titulo,
            s.slug,
            s.descricao,
            s.icone,
            s.cor_inicio,
            s.cor_fim,
            s.tipo,
            s.ordem
        FROM projetos_selos ps
        JOIN selos s
          ON s.id_selo = ps.id_selo
        WHERE ps.id_projeto = %(id_projeto)s
        ORDER BY s.ordem ASC, s.titulo ASC
        """,
        {"id_projeto": id_projeto},
    )

    selos = []
    for s in selos_rows:
        selos.append({
            "id_selo": s["id_selo"],
            "titulo": s["titulo"],
            "slug": s["slug"],
            "descricao": s["descricao"],
            "icone": s["icone"],
            "cor_inicio": s["cor_inicio"],
            "cor_fim": s["cor_fim"],
            "tipo": s["tipo"],
            "ordem": s["ordem"],
        })

    row["selos"] = selos

    return jsonify(row), 200

# --------- Desabilitar (soft delete) projeto ---------
@projetos_bp.delete("/<uuid:id_projeto>")
@require_auth
def delete_projeto(id_projeto):
    """
    Desabilitar projeto (soft delete)

    Marca o projeto como desabilitado (habilitado = FALSE).  
    Apenas administradores ou professores que SEJAM DONOS do projeto
    podem executar esta ação (com exceção de ADMIN, que pode desabilitar qualquer projeto).

    Essa operação não apaga o projeto do banco; apenas o oculta do sistema
    (soft delete).

    Regras:
      - Apenas usuários autenticados com permissão **ADMIN** ou **PROFESSOR**.
      - ADMIN pode desabilitar qualquer projeto.
      - PROFESSOR só pode desabilitar projetos que sejam seus (`id_usuario`).
      - Se o projeto já estiver desabilitado (`habilitado = FALSE`), é retornado
        erro 400.

    ---
    tags:
      - Projetos
    security:
      - Bearer: []
    produces:
      - application/json
    parameters:
      - in: header
        name: Authorization
        type: string
        required: true
        description: "Token JWT no formato Bearer <token>"
      - in: path
        name: id_projeto
        type: string
        required: true
        format: uuid
        description: "ID do projeto a ser desabilitado"
    responses:
      200:
        description: Projeto desabilitado com sucesso
        schema:
          type: object
          properties:
            id_projeto:
              type: string
              format: uuid
            id_usuario:
              type: string
              format: uuid
            titulo:
              type: string
            descricao:
              type: string
            texto:
              type: string
            imagem_atividade:
              type: string
            tags:
              type: array
              items:
                type: string
            xp_conclusao:
              type: integer
            data_inicio:
              type: string
              format: date-time
            data_fim:
              type: string
              format: date-time
            status:
              type: string
            habilitado:
              type: boolean
              example: false
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time
      400:
        description: |
          Erro de regra de negócio, por exemplo:
            - projeto já está desabilitado
        schema:
          type: object
          properties:
            error:
              type: string
      401:
        description: "Usuário não autenticado"
        schema:
          type: object
          properties:
            error:
              type: string
      403:
        description: "Sem permissão (não admin/professor ou não dono do projeto)"
        schema:
          type: object
          properties:
            error:
              type: string
      404:
        description: "Projeto não encontrado"
        schema:
          type: object
          properties:
            error:
              type: string
    """
    headers_dict = dict(request.headers)
    print(f"[PROJ DEL ] - Headers: {headers_dict}")

    # Permissões principais
    if not _is_admin_or_professor():
        return jsonify({"error": "acesso restrito a administradores e professores"}), 403

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "nenhum usuário autenticado"}), 401

    # Verificar projeto (incluindo habilitado)
    projeto = one("""
        SELECT id_projeto, id_usuario, habilitado
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not projeto:
        return jsonify({"error": "Projeto não encontrado"}), 404

    # Se já estiver desabilitado, não faz nada e retorna 400
    if projeto.get("habilitado") is False:
        return jsonify({"error": "Projeto já está desabilitado"}), 400

    # Regras de edição/exclusão:
    # - ADMIN pode desabilitar tudo
    # - PROFESSOR só pode se for o dono
    is_admin = _is_admin()  # função auxiliar que você já tem
    is_owner = str(projeto["id_usuario"]) == str(user_id)

    if not is_admin and not is_owner:
        return jsonify({"error": "Você não tem permissão para remover este projeto"}), 403

    # Realizar soft delete
    row = one("""
        UPDATE projetos
           SET habilitado = FALSE,
               updated_at = NOW()
         WHERE id_projeto = %(id)s
     RETURNING
        id_projeto,
        id_usuario,
        titulo,
        descricao,
        texto,
        imagem_atividade,
        tags,
        xp_conclusao,
        data_inicio,
        data_fim,
        status,
        habilitado,
        created_at,
        updated_at
    """, {"id": id_projeto})

    return jsonify(row), 200

# --------- Participar de projeto ---------
@projetos_bp.post("/<uuid:id_projeto>/participar")
@require_auth
def participar_projeto(id_projeto):
    """
    Participar de projeto

    Permite que um aluno se inscreva em um projeto.  
    A inscrição recebe status inicial **PENDENTE** até aprovação do professor/dono.

    Regras:
      - Apenas usuários autenticados podem se inscrever.
      - Não permite inscrição se:
          - projeto estiver **desabilitado**
          - projeto estiver **CANCELADO**
          - projeto estiver **CONCLUIDO**
          - projeto estiver **PAUSADO** (regra opcional — incluída)
          - `data_fim` já passou
      - Não permite inscrição duplicada (PENDENTE ou APROVADO)
      - Usuário **não pode se inscrever no próprio projeto**

    Body (JSON) — opcional:

    {
      "mensagem": "Professor, gostaria de participar...",
      "papel": "ALUNO"
    }

    Se `papel` não for informado, assume "ALUNO".

    ---
    tags:
      - Projetos
    security:
      - Bearer: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: "Token JWT no formato Bearer <token>"

      - in: path
        name: id_projeto
        required: true
        type: string
        format: uuid
        description: "ID do projeto no qual o aluno deseja se inscrever"

      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            mensagem:
              type: string
              description: "Mensagem opcional enviada ao professor/dono"
              example: "Professor, gostaria de ajudar com backend."
            papel:
              type: string
              description: "Papel desejado no projeto (padrão ALUNO)"
              example: "ALUNO"

    responses:
      201:
        description: Inscrição criada com sucesso (status PENDENTE)
        schema:
          type: object
          properties:
            id_participacao:
              type: string
              format: uuid
            id_projeto:
              type: string
              format: uuid
            id_usuario:
              type: string
              format: uuid
            papel:
              type: string
            status:
              type: string
              example: "PENDENTE"
            mensagem:
              type: string
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time

      400:
        description: |
          Regra de negócio violada ou dados inválidos, exemplo:
            - projeto cancelado/pausado/concluído
            - data_fim já ultrapassada
            - usuário já inscrito
            - usuário é o dono do projeto
        schema:
          type: object
          properties:
            error:
              type: string

      401:
        description: Não autenticado
        schema:
          type: object
          properties:
            error:
              type: string

      404:
        description: Projeto não encontrado ou desabilitado
        schema:
          type: object
          properties:
            error:
              type: string
    """
    headers_dict = dict(request.headers)
    data = request.get_json(force=True, silent=True) or {}
    print(f"[PROJ PART] - Headers: {headers_dict}")
    print(f"[PROJ PART] - Body: {data}")

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "nenhum usuário autenticado"}), 401

    # Buscar projeto
    projeto = one("""
        SELECT
            id_projeto,
            id_usuario,
            habilitado,
            status,
            data_fim
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not projeto or not projeto.get("habilitado"):
        return jsonify({"error": "Projeto não encontrado ou desabilitado"}), 404

    # Dono não pode se inscrever no próprio projeto
    if str(projeto["id_usuario"]) == str(user_id):
        return jsonify({"error": "Você não pode participar do seu próprio projeto"}), 400

    status_atual = projeto.get("status", "").upper()

    # Regras de bloqueio por status
    if status_atual in ("CANCELADO", "CONCLUIDO"):
        return jsonify({
            "error": f"Não é possível participar de um projeto com status {status_atual}"
        }), 400

    # Bloqueio opcional para PAUSADO (muito recomendado)
    if status_atual == "PAUSADO":
        return jsonify({
            "error": "O projeto está PAUSADO e não aceita novas inscrições"
        }), 400

    # Verificar se data_fim já passou
    data_fim = projeto.get("data_fim")
    if data_fim is not None:
        agora = datetime.utcnow()
        if agora > data_fim:
            return jsonify({"error": "Projeto já encerrado (data_fim ultrapassada)"}), 400

    # Verificar participação existente
    existente = one("""
        SELECT id_participacao, status
        FROM projetos_participantes
        WHERE id_projeto = %(id_projeto)s
          AND id_usuario = %(id_usuario)s
    """, {
        "id_projeto": id_projeto,
        "id_usuario": user_id
    })

    if existente and existente.get("status") in ("PENDENTE", "APROVADO"):
        return jsonify({"error": "Você já possui inscrição neste projeto"}), 400

    mensagem = data.get("mensagem")

    # Papel = ALUNO por padrão
    papel = (data.get("papel") or "ALUNO").upper().strip()

    row = one("""
        INSERT INTO projetos_participantes
            (id_projeto, id_usuario, papel, status, mensagem)
        VALUES
            (%(id_projeto)s, %(id_usuario)s, %(papel)s, 'PENDENTE', %(mensagem)s)
        RETURNING
            id_participacao,
            id_projeto,
            id_usuario,
            papel,
            status,
            mensagem,
            created_at,
            updated_at
    """, {
        "id_projeto": id_projeto,
        "id_usuario": user_id,
        "papel": papel,
        "mensagem": mensagem,
    })

    return jsonify(row), 201

# --------- Listar participantes de um projeto ---------
@projetos_bp.get("/<uuid:id_projeto>/participantes")
@require_auth
def listar_participantes_projeto(id_projeto):
    """
    Listar participantes de um projeto

    Retorna todas as inscrições de participantes de um projeto específico,
    permitindo filtro opcional por status.

    Regras:
      - Apenas o **DONO** do projeto pode visualizar.
      - Usuários com permissão **ADMIN** podem visualizar qualquer projeto.
      - PROFESSOR só pode visualizar projetos de sua autoria.

    Filtro opcional:
      - `status` = PENDENTE | APROVADO | RECUSADO | CANCELADO | CONCLUIDO

    ---
    tags:
      - Projetos
    security:
      - Bearer: []
    produces:
      - application/json

    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: "Token JWT no formato Bearer <token>"

      - in: path
        name: id_projeto
        required: true
        type: string
        format: uuid
        description: "ID do projeto (UUID)"

      - in: query
        name: status
        required: false
        type: string
        enum:
          - PENDENTE
          - APROVADO
          - RECUSADO
          - CANCELADO
          - CONCLUIDO
        description: "Filtra participantes pelo status da inscrição"

    responses:
      200:
        description: Lista de participantes retornada com sucesso
        schema:
          type: array
          items:
            type: object
            properties:
              id_participacao:
                type: string
                format: uuid
              id_projeto:
                type: string
                format: uuid
              id_usuario:
                type: string
                format: uuid
              nome_usuario:
                type: string
              email_usuario:
                type: string
              avatar_usuario:
                type: string
                nullable: true
              papel:
                type: string
              status:
                type: string
                enum:
                  - PENDENTE
                  - APROVADO
                  - RECUSADO
                  - CANCELADO
                  - CONCLUIDO
              mensagem:
                type: string
                nullable: true
              created_at:
                type: string
                format: date-time
              updated_at:
                type: string
                format: date-time

      400:
        description: Status inválido informado
        schema:
          type: object
          properties:
            error:
              type: string

      401:
        description: Usuário não autenticado
        schema:
          type: object
          properties:
            error:
              type: string

      403:
        description: Usuário não é dono do projeto e não é ADMIN
        schema:
          type: object
          properties:
            error:
              type: string

      404:
        description: Projeto não encontrado
        schema:
          type: object
          properties:
            error:
              type: string
    """
    headers_dict = dict(request.headers)
    print(f"[PROJ PART LIST] - Headers: {headers_dict}")
    print(f"[PROJ PART LIST] - Args: {dict(request.args)}")

    # Permissões de base
    if not _is_admin_or_professor():
        return jsonify({"error": "acesso restrito a administradores e professores"}), 403

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "nenhum usuário autenticado"}), 401

    # Validar projeto
    projeto = one("""
        SELECT id_projeto, id_usuario
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not projeto:
        return jsonify({"error": "Projeto não encontrado"}), 404

    # Apenas o dono, exceto ADMIN
    if not _is_admin() and str(projeto["id_usuario"]) != str(user_id):
        return jsonify({"error": "Você não tem permissão para visualizar as inscrições deste projeto"}), 403

    # Filtro de status
    status = request.args.get("status")
    params = {"id_projeto": id_projeto}
    where = ["pp.id_projeto = %(id_projeto)s"]

    allowed_status = {
        "PENDENTE",
        "APROVADO",
        "RECUSADO",
        "CANCELADO",
        "CONCLUIDO"
    }

    if status:
        status_clean = status.strip().upper()

        if status_clean not in allowed_status:
            return jsonify({
                "error": "Status inválido",
                "allowed": list(allowed_status)
            }), 400

        where.append("pp.status = %(status)s")
        params["status"] = status_clean

    where_clause = " AND ".join(where)

    rows = many(f"""
        SELECT
            pp.id_participacao,
            pp.id_projeto,
            pp.id_usuario,
            u.nome        AS nome_usuario,
            u.email       AS email_usuario,
            u.imagem      AS avatar_usuario,
            pp.papel,
            pp.status,
            pp.mensagem,
            pp.created_at,
            pp.updated_at
        FROM projetos_participantes pp
        JOIN usuarios u 
          ON u.id_usuario = pp.id_usuario
        WHERE {where_clause}
        ORDER BY 
            CASE pp.status
                WHEN 'PENDENTE' THEN 1
                WHEN 'APROVADO' THEN 2
                WHEN 'CONCLUIDO' THEN 3
                WHEN 'RECUSADO' THEN 4
                WHEN 'CANCELADO' THEN 5
            END,
            pp.created_at DESC
    """, params)

    return jsonify(rows), 200

# --------- Atualizar participação em projeto ---------
@projetos_bp.patch("/<uuid:id_projeto>/participantes/<uuid:id_participacao>")
@require_auth
def atualizar_participacao_projeto(id_projeto, id_participacao):
    """
    Atualizar participação em projeto

    Permite que o DONO do projeto (professor/adm) ou um ADMIN atualizem o status
    e/ou o papel de um participante.

    Restrições:
      - Não é permitido atualizar participação em projetos:
          - DESABILITADOS
          - CANCELADOS
          - CONCLUIDOS
      - PROFESSOR só pode atualizar participações de projetos que ele é dono.
      - ADMIN pode atualizar qualquer projeto.
      - Apenas **um MONITOR APROVADO** é permitido por projeto.
      - Deve haver ao menos um campo para atualização.

    Campos aceitos no body (JSON):

    {
      "status": "PENDENTE | APROVADO | RECUSADO | CANCELADO | CONCLUIDO",
      "papel": "MEMBRO | MONITOR | ALUNO | outro papel"
    }

    ---
    tags:
      - Projetos
    security:
      - Bearer: []
    consumes:
      - application/json
    produces:
      - application/json

    parameters:
      - in: header
        name: Authorization
        required: true
        description: "Token JWT no formato Bearer <token>"
        type: string

      - in: path
        name: id_projeto
        required: true
        type: string
        format: uuid
        description: "ID do projeto"

      - in: path
        name: id_participacao
        required: true
        type: string
        format: uuid
        description: "ID da participação a ser atualizada"

      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            status:
              type: string
              description: "Novo status da participação"
              enum:
                - PENDENTE
                - APROVADO
                - RECUSADO
                - CANCELADO
                - CONCLUIDO
              example: "APROVADO"
            papel:
              type: string
              description: "Novo papel do participante"
              example: "MONITOR"

    responses:
      200:
        description: Participação atualizada com sucesso
        schema:
          type: object
          properties:
            id_participacao:
              type: string
              format: uuid
            id_projeto:
              type: string
              format: uuid
            id_usuario:
              type: string
              format: uuid
            papel:
              type: string
            status:
              type: string
            mensagem:
              type: string
              nullable: true
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time

      400:
        description: |
          Erro de validação ou regra de negócio:
            - nenhum campo enviado
            - status inválido
            - projeto desabilitado/cancelado/concluído
            - já existe MONITOR APROVADO
        schema:
          type: object
          properties:
            error:
              type: string

      401:
        description: Usuário não autenticado
        schema:
          type: object
          properties:
            error:
              type: string

      403:
        description: Usuário sem permissão (não é ADMIN ou dono)
        schema:
          type: object
          properties:
            error:
              type: string

      404:
        description: Projeto ou participação não encontrada
        schema:
          type: object
          properties:
            error:
              type: string
    """
    headers_dict = dict(request.headers)
    data = request.get_json(force=True, silent=True) or {}
    print(f"[PROJ PART UPD] - Headers: {headers_dict}")
    print(f"[PROJ PART UPD] - Body: {data}")

    # Permissões básicas
    if not _is_admin_or_professor():
        return jsonify({"error": "acesso restrito a administradores e professores"}), 403

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "nenhum usuário autenticado"}), 401

    # Buscar projeto com status/habilitado
    projeto = one("""
        SELECT id_projeto, id_usuario, status, habilitado
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not projeto:
        return jsonify({"error": "Projeto não encontrado"}), 404

    # Permissão final
    is_admin = _is_admin()
    is_owner = str(projeto["id_usuario"]) == str(user_id)

    if not is_admin and not is_owner:
        return jsonify({"error": "Você não tem permissão para gerenciar inscrições deste projeto"}), 403

    # Bloqueios por estado do projeto
    if not projeto.get("habilitado"):
        return jsonify({"error": "Projeto desabilitado — não é possível atualizar participações"}), 400

    status_proj = (projeto.get("status") or "").upper()
    if status_proj in ("CANCELADO", "CONCLUIDO"):
        return jsonify({
            "error": "Não é possível atualizar participação em um projeto cancelado ou concluído",
            "status_projeto": status_proj
        }), 400

    # Buscar a participação
    participacao = one("""
        SELECT id_participacao, id_projeto, id_usuario, status, papel, mensagem
        FROM projetos_participantes
        WHERE id_participacao = %(id_participacao)s
          AND id_projeto = %(id_projeto)s
    """, {
        "id_participacao": id_participacao,
        "id_projeto": id_projeto
    })

    if not participacao:
        return jsonify({"error": "Participação não encontrada"}), 404

    # Campos do body
    novo_status = data.get("status")
    novo_papel  = data.get("papel")

    if not novo_status and novo_papel is None:
        return jsonify({"error": "nenhum campo para atualização"}), 400

    params = {
        "id_participacao": id_participacao,
        "id_projeto": id_projeto,
    }
    fields = []

    # -------- status ----------
    status_normalizado = None
    if novo_status:
        status_normalizado = str(novo_status).strip().upper()

        status_validos = {"PENDENTE", "APROVADO", "RECUSADO", "CANCELADO", "CONCLUIDO"}
        if status_normalizado not in status_validos:
            return jsonify({
                "error": "status inválido",
                "allowed": list(status_validos)
            }), 400

        fields.append("status = %(status)s")
        params["status"] = status_normalizado

    # -------- papel ----------
    papel_normalizado = None
    if novo_papel is not None:
        papel_normalizado = str(novo_papel).strip().upper()
        fields.append("papel = %(papel)s")
        params["papel"] = papel_normalizado

    # -------- lógica final (status + papel) --------
    papel_final = (
        papel_normalizado
        if papel_normalizado is not None
        else (participacao["papel"] or "").upper()
    )

    status_final = (
        status_normalizado
        if status_normalizado is not None
        else (participacao["status"] or "").upper()
    )

    # ---------- Regras MONITOR ----------
    if papel_final == "MONITOR" and status_final == "APROVADO":
        existente_monitor = one("""
            SELECT id_participacao
            FROM projetos_participantes
            WHERE id_projeto = %(id_projeto)s
              AND id_participacao <> %(id_participacao)s
              AND UPPER(papel) = 'MONITOR'
              AND UPPER(status) = 'APROVADO'
        """, params)

        if existente_monitor:
            return jsonify({
                "error": "Já existe um monitor aprovado neste projeto. Só é permitido um monitor por projeto."
            }), 400

    # -------- realizar update --------
    fields.append("updated_at = NOW()")

    sql = f"""
        UPDATE projetos_participantes
           SET {", ".join(fields)}
         WHERE id_participacao = %(id_participacao)s
           AND id_projeto = %(id_projeto)s
     RETURNING
        id_participacao,
        id_projeto,
        id_usuario,
        papel,
        status,
        mensagem,
        created_at,
        updated_at
    """

    row = one(sql, params)

    return jsonify(row), 200

@projetos_bp.post("/<uuid:id_projeto>/participantes/adicionar")
@require_auth
def adicionar_participante_projeto(id_projeto):
    """
    Adicionar participante em projeto (pelo professor/adm)

    Permite que o **DONO** do projeto (professor/adm) ou um usuário com
    permissão **ADMIN** adicione um aluno diretamente ao projeto, definindo
    o papel e o status da participação.

    Regras principais:
      - Apenas o DONO do projeto ou um ADMIN pode adicionar.
      - Não permite adicionar participantes em projetos:
          * DESABILITADOS
          * CANCELADOS
          * CONCLUIDOS
          * Encerrados (data_fim já ultrapassada)
      - Se o papel final for MONITOR e o status final for APROVADO,
        só é permitido **um monitor aprovado por projeto**.
      - Se o aluno já tiver inscrição PENDENTE ou APROVADO no projeto,
        não é permitido criar uma nova.
      - O próprio dono do projeto não pode ser adicionado como participante.

    Body esperado (JSON):

    {
      "id_usuario": "UUID do aluno",
      "papel": "MEMBRO | MONITOR (opcional, padrão MEMBRO)",
      "status": "PENDENTE | APROVADO | RECUSADO | CANCELADO | CONCLUIDO (opcional, padrão APROVADO)",
      "mensagem": "Mensagem opcional para o aluno"
    }

    ---
    tags:
      - Projetos
    security:
      - Bearer: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: "Token JWT no formato Bearer <token>"

      - in: path
        name: id_projeto
        required: true
        type: string
        format: uuid
        description: "ID do projeto onde o aluno será adicionado"

      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - id_usuario
          properties:
            id_usuario:
              type: string
              format: uuid
              description: "ID (UUID) do aluno que será adicionado ao projeto"
              example: "552a7eb4-64e6-44b9-8207-59ad10b862a4"
            papel:
              type: string
              description: "Papel do usuário no projeto (padrão: MEMBRO)"
              example: "MEMBRO"
            status:
              type: string
              description: "Status inicial da participação (padrão: APROVADO)"
              enum:
                - PENDENTE
                - APROVADO
                - RECUSADO
                - CANCELADO
                - CONCLUIDO
              example: "APROVADO"
            mensagem:
              type: string
              description: "Mensagem opcional para o aluno sobre a participação"
              example: "Você foi adicionado como monitor do projeto X."

    responses:
      201:
        description: "Participante adicionado com sucesso ao projeto"
        schema:
          type: object
          properties:
            id_participacao:
              type: string
              format: uuid
            id_projeto:
              type: string
              format: uuid
            id_usuario:
              type: string
              format: uuid
            papel:
              type: string
              example: "MEMBRO"
            status:
              type: string
              example: "APROVADO"
            mensagem:
              type: string
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time

      400:
        description: |
          Erro de validação ou regra de negócio, por exemplo:
            - id_usuario não informado
            - status inválido
            - projeto desabilitado, cancelado, concluído ou encerrado
            - usuário já possui inscrição PENDENTE ou APROVADO
            - já existe um MONITOR aprovado no projeto
            - tentativa de adicionar o dono do projeto como participante
        schema:
          type: object
          properties:
            error:
              type: string

      401:
        description: "Usuário não autenticado"
        schema:
          type: object
          properties:
            error:
              type: string

      403:
        description: "Usuário sem permissão (não é ADMIN nem dono do projeto)"
        schema:
          type: object
          properties:
            error:
              type: string

      404:
        description: "Projeto ou usuário (aluno) não encontrados"
        schema:
          type: object
          properties:
            error:
              type: string
    """
    headers_dict = dict(request.headers)
    data = request.get_json(force=True, silent=True) or {}
    print(f"[PROJ PART ADD] - Headers: {headers_dict}")
    print(f"[PROJ PART ADD] - Body: {data}")

    # Verifica permissão global
    if not _is_admin_or_professor():
        return jsonify({"error": "acesso restrito a administradores e professores"}), 403

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "nenhum usuário autenticado"}), 401

    # Verifica se o projeto existe
    projeto = one("""
        SELECT id_projeto, id_usuario, habilitado, status, data_fim
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not projeto:
        return jsonify({"error": "Projeto não encontrado"}), 404

    # Apenas DONO do projeto, a menos que seja ADMIN
    is_admin = _is_admin()
    is_owner = str(projeto["id_usuario"]) == str(user_id)

    if not is_admin and not is_owner:
        return jsonify({"error": "Você não tem permissão para gerenciar inscrições deste projeto"}), 403

    # Projeto precisa estar habilitado
    if not projeto.get("habilitado"):
        return jsonify({"error": "Não é possível adicionar participantes em um projeto desabilitado"}), 400

    # Projeto não pode estar cancelado ou concluído
    status_projeto = (projeto.get("status") or "").upper()
    if status_projeto in ("CANCELADO", "CONCLUIDO"):
        return jsonify({
            "error": "Não é possível adicionar participantes em um projeto cancelado ou concluído",
            "status_projeto": status_projeto
        }), 400

    # Projeto não pode estar encerrado (data_fim ultrapassada, se houver)
    data_fim = projeto.get("data_fim")
    if data_fim is not None:
        agora = datetime.utcnow()
        if agora > data_fim:
            return jsonify({"error": "Projeto já encerrado (data_fim ultrapassada)"}), 400

    # Dados do body
    id_usuario_alvo = data.get("id_usuario")
    if not id_usuario_alvo:
        return jsonify({"error": "id_usuario é obrigatório"}), 400

    # Dono não pode ser adicionado como participante
    if str(id_usuario_alvo) == str(projeto["id_usuario"]):
        return jsonify({"error": "O dono do projeto não pode ser adicionado como participante"}), 400

    papel_raw = data.get("papel") or "MEMBRO"
    status_raw = data.get("status") or "APROVADO"
    mensagem = data.get("mensagem")

    papel_upper = str(papel_raw).strip().upper()
    status_normalizado = str(status_raw).strip().upper()

    status_validos = {"PENDENTE", "APROVADO", "RECUSADO", "CANCELADO", "CONCLUIDO"}
    if status_normalizado not in status_validos:
        return jsonify({
            "error": f"status inválido. Valores aceitos: {', '.join(sorted(status_validos))}"
        }), 400

    # Verifica se o aluno existe
    usuario = one("""
        SELECT id_usuario
        FROM usuarios
        WHERE id_usuario = %(id)s
    """, {"id": id_usuario_alvo})

    if not usuario:
        return jsonify({"error": "Usuário (aluno) não encontrado"}), 404

    # Evita duplicar inscrição PENDENTE/APROVADO
    existente = one("""
        SELECT id_participacao, status
        FROM projetos_participantes
        WHERE id_projeto = %(id_projeto)s
          AND id_usuario = %(id_usuario)s
    """, {
        "id_projeto": id_projeto,
        "id_usuario": id_usuario_alvo
    })

    if existente and existente.get("status") in ("PENDENTE", "APROVADO"):
        return jsonify({
            "error": "Este usuário já possui inscrição PENDENTE ou APROVADO neste projeto"
        }), 400

    # Regra: apenas 1 MONITOR APROVADO por projeto
    if papel_upper == "MONITOR" and status_normalizado == "APROVADO":
        existente_monitor = one("""
            SELECT id_participacao
            FROM projetos_participantes
            WHERE id_projeto = %(id_projeto)s
              AND UPPER(papel) = 'MONITOR'
              AND UPPER(status) = 'APROVADO'
        """, {
            "id_projeto": id_projeto,
        })

        if existente_monitor:
            return jsonify({
                "error": "Já existe um monitor aprovado neste projeto. Só é permitido um monitor por projeto."
            }), 400

    # Cria a participação
    row = one("""
        INSERT INTO projetos_participantes
            (id_projeto, id_usuario, papel, status, mensagem)
        VALUES
            (%(id_projeto)s, %(id_usuario)s, %(papel)s, %(status)s, %(mensagem)s)
        RETURNING
            id_participacao,
            id_projeto,
            id_usuario,
            papel,
            status,
            mensagem,
            created_at,
            updated_at
    """, {
        "id_projeto": id_projeto,
        "id_usuario": id_usuario_alvo,
        "papel": papel_upper,
        "status": status_normalizado,
        "mensagem": mensagem,
    })

    return jsonify(row), 201