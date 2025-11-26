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

# --------- Listar projetos ---------
@projetos_bp.get("")
@require_auth
def list_projetos():
    """
    Listar projetos

    Retorna a lista de projetos, com suporte a filtros por usuário,
    tag, habilitado e paginação (limit/offset).

    Filtros opcionais via query params:
      - ?id_usuario=<uuid>        -> projetos de um usuário específico
      - ?tag=python               -> projetos que contenham essa tag
      - ?habilitado=true|false    -> filtra por status de habilitação
      - ?limit=20                 -> quantidade máxima de registros
      - ?offset=0                 -> deslocamento para paginação

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
        description: "Filtra projetos de um usuário específico"
      - in: query
        name: tag
        required: false
        type: string
        description: "Filtra projetos que contenham essa tag na lista de tags"
      - in: query
        name: habilitado
        required: false
        type: boolean
        description: "Filtra projetos habilitados (true) ou desabilitados (false)"
      - in: query
        name: limit
        required: false
        type: integer
        description: "Quantidade máxima de registros retornados (padrão 20)"
        default: 20
      - in: query
        name: offset
        required: false
        type: integer
        description: "Deslocamento para paginação (padrão 0)"
        default: 0
    responses:
      200:
        description: Lista de projetos encontrados
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
      400:
        description: "Erro de validação nos parâmetros"
      401:
        description: "Não autenticado"
    """
    headers_dict = dict(request.headers)
    print(f"[PROJ LIST] - Headers: {headers_dict}")
    print(f"[PROJ LIST] - Args: {dict(request.args)}")

    id_usuario = request.args.get("id_usuario")
    tag        = request.args.get("tag")
    habilitado = request.args.get("habilitado")  # 'true', 'false' ou None

    try:
        limit  = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"error": "limit e offset devem ser inteiros"}), 400

    if limit < 0 or offset < 0:
        return jsonify({"error": "limit e offset devem ser não negativos"}), 400

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
            # Garantir que estamos comparando datetimes compatíveis
            total_segundos = (data_fim - data_inicio).total_seconds()
            elapsed_segundos = (agora - data_inicio).total_seconds()

            if elapsed_segundos <= 0:
                percentual = 0.0
            elif elapsed_segundos >= total_segundos:
                percentual = 100.0
            else:
                percentual = (elapsed_segundos / total_segundos) * 100.0

        # Arredonda para 2 casas decimais
        row["percentual_conclusao"] = round(percentual, 2)

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
      "data_fim": "2025-03-30T23:59:59"
    }

    Regras:
      - `titulo` e `texto` são obrigatórios.
      - `tags` deve ser uma lista de strings (se omitida, assume lista vazia).
      - `xp_conclusao`:
          - Se omitida, assume 0.
          - Deve ser inteiro >= 0.

    Regras de status (definido automaticamente no INSERT):
      - Se `data_inicio` for **nula** ou **futura** → `status = AGUARDANDO_INICIO`
      - Se `data_inicio` for **no passado** ou **agora** → `status = EM_ANDAMENTO`

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
              description: "Título do projeto"
              example: "Plataforma de Portfólio Gamificado em Flask + React"
            descricao:
              type: string
              description: "Breve descrição/resumo do projeto"
              example: "Projeto para alunos cadastrarem atividades, projetos e conquistarem XP."
            texto:
              type: string
              description: "Descrição detalhada do projeto (markdown/HTML)"
            imagem_atividade:
              type: string
              description: "URL da imagem de capa do projeto"
              example: "https://cdn.meus-arquivos.com/projetos/portifoleo-capa.png"
            tags:
              type: array
              description: "Lista de tags associadas ao projeto"
              items:
                type: string
              example: ["python", "backend", "flask"]
            xp_conclusao:
              type: integer
              description: "Quantidade de XP dada ao aluno ao concluir o projeto"
              example: 100
            data_inicio:
              type: string
              format: date-time
              description: "Data/hora de início previsto do projeto"
              example: "2025-03-01T08:00:00"
            data_fim:
              type: string
              format: date-time
              description: "Data/hora de término previsto do projeto"
              example: "2025-03-30T23:59:59"

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
              nullable: true
            data_fim:
              type: string
              format: date-time
              nullable: true
            status:
              type: string
              description: "Status inicial calculado automaticamente"
              enum:
                - AGUARDANDO_INICIO
                - EM_ANDAMENTO
                - PAUSADO
                - CANCELADO
            habilitado:
              type: boolean
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time

      400:
        description: "Erro de validação (ex.: tags inválidas, xp_conclusao negativo, campos obrigatórios ausentes)"

      401:
        description: "Nenhum usuário autenticado"

      403:
        description: "Usuário autenticado não possui permissão (não é ADMIN/PROFESSOR)"
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

    xp_conclusao     = data.get("xp_conclusao", 0)
    # se vier string vazia, trata como None
    data_inicio      = data.get("data_inicio") or None
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

    # status é calculado no próprio SQL via CASE
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

    return jsonify(row), 201

# --------- Detalhar projeto ---------
@projetos_bp.get("/<uuid:id_projeto>")
@require_auth
def get_projeto(id_projeto):
    """
    Detalhar projeto

    Retorna os dados de um projeto específico pelo seu id_projeto.
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
            data_fim:
              type: string
              format: date-time
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
      401:
        description: "Não autenticado"
      404:
        description: "Projeto não encontrado"
    """
    headers_dict = dict(request.headers)
    print(f"[PROJ ID  ] - Headers: {headers_dict}")
    print(f"[PROJ ID  ] - ID_PROJETO: {id_projeto}")

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

    # cálculo da % de conclusão baseada em data_inicio / data_fim
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

    return jsonify(row), 200

# --------- Atualizar projeto (dono) ---------
@projetos_bp.patch("/<uuid:id_projeto>")
@require_auth
def update_projeto(id_projeto):
    """
    Atualizar projeto (dono)

    Atualiza os dados de um projeto existente.

    Regras:
      - Apenas usuários autenticados com permissão **ADMIN** ou **PROFESSOR**.
      - O usuário precisa ser o **dono** do projeto (`id_usuario` do projeto).
      - Projetos com status **CONCLUIDO** não podem ser alterados.

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
      "status": "EM_ANDAMENTO"
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

      400:
        description: |
          Erro de validação ou regra de negócio, por exemplo:
            - xp_conclusao inválido
            - status inválido
            - nenhum campo enviado
            - projeto já está CONCLUIDO

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

    # Agora buscamos também o status atual do projeto
    projeto = one("""
        SELECT id_projeto, id_usuario, status
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not projeto:
        return jsonify({"error": "Projeto não encontrado"}), 404

    if str(projeto["id_usuario"]) != str(user_id):
        return jsonify({"error": "Você não tem permissão para editar este projeto"}), 403

    # Bloqueio: projeto já concluído não pode ser alterado
    status_atual = (projeto.get("status") or "").upper()
    if status_atual == "CONCLUIDO":
        return jsonify({"error": "Projetos concluídos não podem ser alterados"}), 400

    fields = []
    params = {"id": id_projeto}

    # --------------------------
    # Campos básicos existentes
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
    # NOVOS CAMPOS
    # --------------------------

    # xp_conclusao (int >= 0)
    if "xp_conclusao" in data:
        try:
            xp = int(data.get("xp_conclusao"))
            if xp < 0:
                return jsonify({"error": "xp_conclusao não pode ser negativo"}), 400
        except (TypeError, ValueError):
            return jsonify({"error": "xp_conclusao deve ser um inteiro"}), 400

        fields.append("xp_conclusao = %(xp_conclusao)s")
        params["xp_conclusao"] = xp

    # data_inicio
    if "data_inicio" in data:
        fields.append("data_inicio = %(data_inicio)s")
        params["data_inicio"] = data.get("data_inicio")

    # data_fim
    if "data_fim" in data:
        fields.append("data_fim = %(data_fim)s")
        params["data_fim"] = data.get("data_fim")

    # status
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
    # Nada pra atualizar?
    # --------------------------
    if not fields:
        return jsonify({"error": "nenhum campo para atualização"}), 400

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

    return jsonify(row), 200

# --------- Desabilitar (soft delete) projeto ---------
@projetos_bp.delete("/<uuid:id_projeto>")
@require_auth
def delete_projeto(id_projeto):
    """
    Desabilitar projeto (soft delete)

    Marca o projeto como desabilitado (habilitado = FALSE).  
    Apenas administradores ou professores que SEJAM DONOS do projeto
    podem executar esta ação.

    Essa operação não apaga o projeto do banco; apenas o oculta do sistema.

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
      401:
        description: "Usuário não autenticado"
      403:
        description: "Sem permissão (não admin/professor ou não dono do projeto)"
      404:
        description: "Projeto não encontrado"
    """
    headers_dict = dict(request.headers)
    print(f"[PROJ DEL ] - Headers: {headers_dict}")

    # Permissões principais
    if not _is_admin_or_professor():
        return jsonify({"error": "acesso restrito a administradores e professores"}), 403

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "nenhum usuário autenticado"}), 401

    # Verificar projeto
    projeto = one("""
        SELECT id_projeto, id_usuario
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not projeto:
        return jsonify({"error": "Projeto não encontrado"}), 404

    # Regras de edição/exclusão:
    # - ADMIN pode deletar tudo
    # - PROFESSOR só pode se for o dono
    is_admin = _is_admin()  # função que você já tem
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

@projetos_bp.post("/<uuid:id_projeto>/participar")
@require_auth
def participar_projeto(id_projeto):
    """
    Participar de projeto

    Aluno se inscreve em um projeto.  
    A inscrição fica com status inicial 'PENDENTE' até o professor/aplicador aprovar.

    Body esperado (JSON) – opcional:

    {
      "mensagem": "Professor, queria participar porque...",
      "papel": "ALUNO"
    }

    Se 'papel' não for informado, o padrão é "ALUNO".

    Regras adicionais:
      - Não permite inscrição em projetos desabilitados.
      - Não permite inscrição em projetos CANCELADOS.
      - Não permite inscrição em projetos CONCLUIDOS.
      - Não permite inscrição em projetos cuja data_fim já foi atingida (se definida).

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
              description: "Mensagem opcional para o professor explicando o interesse"
              example: "Professor, queria participar porque gosto de backend e APIs."
            papel:
              type: string
              description: "Papel desejado no projeto (padrão ALUNO)"
              example: "ALUNO"
    responses:
      201:
        description: "Inscrição criada com sucesso (pendente de aprovação)"
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
              example: "ALUNO"
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
          Dados inválidos ou regra de negócio violada, por exemplo:
            - inscrição já existente (PENDENTE/APROVADO)
            - projeto cancelado
            - projeto concluído
            - projeto encerrado (data_fim ultrapassada)
      401:
        description: "Não autenticado"
      404:
        description: "Projeto não encontrado ou desabilitado"
    """
    headers_dict = dict(request.headers)
    data = request.get_json(force=True, silent=True) or {}
    print(f"[PROJ PART] - Headers: {headers_dict}")
    print(f"[PROJ PART] - Body: {data}")

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "nenhum usuário autenticado"}), 401

    # Verifica se o projeto existe e está habilitado
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

    status_atual = projeto.get("status")

    # Bloqueia inscrição em projetos cancelados ou concluídos
    if status_atual in ("CANCELADO", "CONCLUIDO"):
        return jsonify({
            "error": "Não é possível participar de um projeto com status CANCELADO ou CONCLUIDO"
        }), 400

    # Bloqueia inscrição em projetos já encerrados (se tiver data_fim)
    data_fim = projeto.get("data_fim")
    if data_fim is not None:
        agora = datetime.utcnow()
        if agora > data_fim:
            return jsonify({"error": "Projeto já encerrado (data_fim ultrapassada)"}), 400

    # Evita duplicar inscrição (PENDENTE/APROVADO)
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

    # Padrão de papel = ALUNO
    papel = data.get("papel") or "ALUNO"
    papel = str(papel).upper().strip()

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

@projetos_bp.get("/<uuid:id_projeto>/participantes")
@require_auth
def listar_participantes_projeto(id_projeto):
    """
    Listar participantes de um projeto

    Lista as participações (inscrições) de um projeto.

    Regras:
      - Apenas o **DONO** do projeto (professor/adm) pode visualizar as inscrições.
      - Usuários com permissão **ADMIN** podem visualizar qualquer projeto.

    Filtro opcional via query param:
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
        description: "Filtra participantes por status da participação"
        enum:
          - PENDENTE
          - APROVADO
          - RECUSADO
          - CANCELADO
          - CONCLUIDO

    responses:
      200:
        description: "Lista de participantes do projeto"
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
                description: "Nome do aluno/participante"
              email_usuario:
                type: string
                description: "Email do aluno/participante"
              avatar_usuario:
                type: string
                nullable: true
                description: "URL do avatar do usuário (se existir)"
              papel:
                type: string
                description: "Papel no projeto (ex.: ALUNO, MONITOR)"
              status:
                type: string
                description: "Status da participação"
                enum:
                  - PENDENTE
                  - APROVADO
                  - RECUSADO
                  - CANCELADO
                  - CONCLUIDO
              mensagem:
                type: string
                nullable: true
                description: "Mensagem enviada pelo aluno ao se inscrever (se houver)"
              created_at:
                type: string
                format: date-time
              updated_at:
                type: string
                format: date-time

      400:
        description: "Status inválido informado no filtro"

      401:
        description: "Nenhum usuário autenticado"

      403:
        description: "Acesso restrito: usuário não é dono do projeto e não é ADMIN"

      404:
        description: "Projeto não encontrado"
    """
    headers_dict = dict(request.headers)
    print(f"[PROJ PART LIST] - Headers: {headers_dict}")
    print(f"[PROJ PART LIST] - Args: {dict(request.args)}")

    # Permissão principal
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

    # Apenas dono do projeto, a menos que seja admin
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
            u.avatar_url  AS avatar_usuario,   -- opcional
            pp.papel,
            pp.status,
            pp.mensagem,
            pp.created_at,
            pp.updated_at
        FROM projetos_participantes pp
        JOIN usuarios u ON u.id_usuario = pp.id_usuario
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

@projetos_bp.patch("/<uuid:id_projeto>/participantes/<uuid:id_participacao>")
@require_auth
def atualizar_participacao_projeto(id_projeto, id_participacao):
    """
    Atualizar participação em projeto

    Atualiza o status e/ou o papel de um participante em um projeto.  
    Apenas o DONO do projeto (professor/adm) ou um ADMIN podem aprovar, recusar,
    cancelar, concluir ou ajustar o papel do participante.

    Restrições:
      - Não é permitido atualizar participação em projetos DESABILITADOS.
      - Não é permitido atualizar participação em projetos CANCELADOS.
      - Não é permitido atualizar participação em projetos CONCLUIDOS.

    Campos aceitos no body (JSON):

    {
      "status": "PENDENTE | APROVADO | RECUSADO | CANCELADO | CONCLUIDO",
      "papel": "MEMBRO | MONITOR | ALUNO | outro papel"
    }

    Regras de negócio adicionais:
      - Se o papel final for MONITOR e o status final for APROVADO,
        só é permitido um monitor aprovado por projeto.
      - ADMIN pode gerenciar qualquer projeto.
      - PROFESSOR só pode gerenciar inscrições dos projetos onde ele é o dono (`id_usuario`).

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
        description: "ID do projeto (UUID)"

      - in: path
        name: id_participacao
        required: true
        type: string
        format: uuid
        description: "ID da participação (UUID) a ser atualizada"

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
              description: "Novo papel do participante no projeto"
              example: "MONITOR"

    responses:
      200:
        description: "Participação atualizada com sucesso"
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
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time

      400:
        description: |
          Erro de validação ou regra de negócio, por exemplo:
            - nenhum campo para atualização
            - status inválido
            - já existe outro MONITOR com status APROVADO
            - projeto desabilitado, cancelado ou concluído

      401:
        description: "Nenhum usuário autenticado"

      403:
        description: "Usuário sem permissão (não é ADMIN nem dono do projeto)"

      404:
        description: "Projeto ou participação não encontrados"
    """
    headers_dict = dict(request.headers)
    data = request.get_json(force=True, silent=True) or {}
    print(f"[PROJ PART UPD] - Headers: {headers_dict}")
    print(f"[PROJ PART UPD] - Body: {data}")

    if not _is_admin_or_professor():
        return jsonify({"error": "acesso restrito a administradores e professores"}), 403

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "nenhum usuário autenticado"}), 401

    # Agora buscamos também status e habilitado
    projeto = one("""
        SELECT id_projeto, id_usuario, status, habilitado
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not projeto:
        return jsonify({"error": "Projeto não encontrado"}), 404

    # ADMIN pode gerenciar qualquer projeto, PROFESSOR só se for dono
    is_admin = _is_admin()
    is_owner = str(projeto["id_usuario"]) == str(user_id)

    if not is_admin and not is_owner:
        return jsonify({"error": "Você não tem permissão para gerenciar inscrições deste projeto"}), 403

    # Bloqueios de estado do projeto
    if not projeto.get("habilitado"):
        return jsonify({"error": "Não é possível atualizar participação em um projeto desabilitado"}), 400

    status_projeto = (projeto.get("status") or "").upper()
    if status_projeto in ("CANCELADO", "CONCLUIDO"):
        return jsonify({
            "error": "Não é possível atualizar participação em um projeto cancelado ou concluído",
            "status_projeto": status_projeto
        }), 400

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

    novo_status = data.get("status")
    novo_papel  = data.get("papel")

    if not novo_status and novo_papel is None:
        return jsonify({"error": "nenhum campo para atualização"}), 400

    fields = []
    params = {
        "id_participacao": id_participacao,
        "id_projeto": id_projeto,
    }

    status_normalizado = None
    if novo_status:
        status_normalizado = str(novo_status).strip().upper()
        status_validos = {"PENDENTE", "APROVADO", "RECUSADO", "CANCELADO", "CONCLUIDO"}
        if status_normalizado not in status_validos:
            return jsonify({
                "error": f"status inválido. Valores aceitos: {', '.join(sorted(status_validos))}"
            }), 400

        fields.append("status = %(status)s")
        params["status"] = status_normalizado

    if novo_papel is not None:
        papel_norm = str(novo_papel).strip().upper()
        fields.append("papel = %(papel)s")
        params["papel"] = papel_norm

    # ---------- Regra de apenas 1 MONITOR APROVADO por projeto ----------
    papel_final = (
        str(novo_papel).strip().upper()
        if novo_papel is not None
        else (participacao["papel"] or "").strip().upper()
    )

    status_final = (
        status_normalizado
        if status_normalizado is not None
        else (participacao["status"] or "").strip().upper()
    )

    if papel_final == "MONITOR" and status_final == "APROVADO":
        existente_monitor = one("""
            SELECT id_participacao
            FROM projetos_participantes
            WHERE id_projeto = %(id_projeto)s
              AND id_participacao <> %(id_participacao)s
              AND UPPER(papel) = 'MONITOR'
              AND UPPER(status) = 'APROVADO'
        """, {
            "id_projeto": id_projeto,
            "id_participacao": id_participacao,
        })

        if existente_monitor:
            return jsonify({
                "error": "Já existe um monitor aprovado neste projeto. Só é permitido um monitor por projeto."
            }), 400
    # -------------------------------------------------------------------

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
      - Apenas o DONO do projeto (professor/adm) ou um ADMIN pode adicionar.
      - Não permite adicionar participantes em projetos:
          * DESABILITADOS
          * CANCELADOS
          * CONCLUIDOS
          * ou já encerrados (`data_fim` passada).
      - Se o papel final for MONITOR e o status final for APROVADO,
        só é permitido **um monitor aprovado por projeto**.
      - Se o aluno já tiver inscrição PENDENTE ou APROVADO no projeto,
        não é permitido criar uma nova.

    Body esperado (JSON):

    {
      "id_usuario": "UUID do aluno",
      "papel": "MEMBRO | MONITOR | (opcional, padrão MEMBRO)",
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

      401:
        description: "Usuário não autenticado"

      403:
        description: "Usuário sem permissão (não é ADMIN nem dono do projeto)"

      404:
        description: "Projeto ou usuário (aluno) não encontrados"
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

    papel_raw = data.get("papel") or "MEMBRO"
    status_raw = data.get("status") or "APROVADO"
    mensagem = data.get("mensagem")

    papel_upper = str(papel_raw).strip().upper()
    status_normalizado = str(status_raw).strip().upper()

    status_validos = {"PENDENTE", "APROVADO", "RECUSADO", "CANCELADO", "CONCLUIDO"}
    if status_normalizado not in status_validos:
        return jsonify({"error": f"status inválido. Valores aceitos: {', '.join(sorted(status_validos))}"}), 400

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
