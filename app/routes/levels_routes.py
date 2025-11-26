# app/blueprints/levels.py
from flask import Blueprint, request, jsonify, g
from ..models.db import one, many, run
from ..models.xp import adicionar_xp_usuario, recalcular_xp_e_level_por_historico
from ..models.auth import require_auth

levels_bp = Blueprint("levels", __name__, url_prefix="/levels")

@levels_bp.get("")
@require_auth
def list_levels():
    """
    Listar níveis (com filtros opcionais)

    Retorna todos os níveis cadastrados, podendo aplicar filtro por `tag`.
    Caso nenhum filtro seja informado, lista apenas níveis habilitados.

    ---
    tags:
      - Levels
    produces:
      - application/json
    parameters:
      - in: query
        name: tag
        required: false
        type: string
        description: "Filtrar níveis por categoria/tag (ex.: 'python', 'front', 'backend')"
        example: "python"
    responses:
      200:
        description: Lista de níveis
        schema:
          type: array
          items:
            type: object
            properties:
              id_level:
                type: string
                format: uuid
              titulo:
                type: string
              tag:
                type: string
              nivel:
                type: integer
                description: "Número do nível"
              xp_min:
                type: integer
                description: "XP mínimo necessário para atingir o nível"
              xp_max:
                type: integer
                description: "XP máximo permitido antes de subir para o próximo nível"
              descricao:
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
        description: Erro nos parâmetros de consulta
    """
    tag = request.args.get("tag")

    if tag:
        rows = many("""
            SELECT id_level, titulo, tag, nivel, xp_min, xp_max, descricao, habilitado,
                   created_at, updated_at
              FROM levels
             WHERE tag = %(tag)s
             ORDER BY tag, nivel
        """, {"tag": tag})
    else:
        rows = many("""
            SELECT id_level, titulo, tag, nivel, xp_min, xp_max, descricao, habilitado,
                   created_at, updated_at
              FROM levels
             WHERE habilitado = TRUE
             ORDER BY tag, nivel
        """)

    return jsonify(rows), 200

@levels_bp.get("/<uuid:id_level>")
@require_auth
def get_level(id_level):
    """
    Detalhar nível específico

    Retorna os dados completos de um nível específico a partir do seu ID.

    ---
    tags:
      - Levels
    produces:
      - application/json
    parameters:
      - in: path
        name: id_level
        required: true
        type: string
        format: uuid
        description: "ID do nível (UUID)"
    responses:
      200:
        description: "Nível encontrado"
        schema:
          type: object
          properties:
            id_level:
              type: string
              format: uuid
            titulo:
              type: string
            tag:
              type: string
              description: "Categoria/área do nível (ex.: python, backend)"
            nivel:
              type: integer
            xp_min:
              type: integer
            xp_max:
              type: integer
            descricao:
              type: string
            habilitado:
              type: boolean
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time
      404:
        description: "Nível não encontrado"
    """
    row = one("""
        SELECT id_level, titulo, tag, nivel, xp_min, xp_max, descricao, habilitado,
               created_at, updated_at
          FROM levels
         WHERE id_level = %(id)s
    """, {"id": id_level})

    if not row:
        return jsonify({"error": "Nível não encontrado"}), 404

    return jsonify(row), 200

@levels_bp.post("")
@require_auth
def create_level():
    """
    Criar novo nível

    Cria um novo nível dentro de uma categoria/tag específica.

    Body (JSON) esperado:

    {
      "titulo": "Iniciante",
      "tag": "python",
      "nivel": 1,
      "xp_min": 0,
      "xp_max": 100,
      "descricao": "Primeiro nível da trilha Python."
    }

    ---
    tags:
      - Levels
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - titulo
            - tag
            - nivel
          properties:
            titulo:
              type: string
              description: "Título exibido para o nível"
              example: "Iniciante"
            tag:
              type: string
              description: "Categoria ou trilha deste nível (ex.: python, backend)"
              example: "python"
            nivel:
              type: integer
              description: "Número do nível (ordem dentro da trilha)"
              example: 1
            xp_min:
              type: integer
              description: "XP mínimo necessário para este nível (padrão: 0)"
              example: 0
            xp_max:
              type: integer
              description: "XP máximo antes de subir para o próximo nível"
              example: 100
            descricao:
              type: string
              description: "Descrição completa do nível"
              example: "Primeiro nível da trilha Python."
    responses:
      201:
        description: "Nível criado com sucesso"
        schema:
          type: object
          properties:
            id_level:
              type: string
              format: uuid
            titulo:
              type: string
            tag:
              type: string
            nivel:
              type: integer
            xp_min:
              type: integer
            xp_max:
              type: integer
            descricao:
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
        description: "Campos obrigatórios ausentes ou inválidos"
    """
    data = request.get_json(force=True, silent=True) or {}

    titulo    = data.get("titulo")
    tag       = data.get("tag")
    nivel     = data.get("nivel")
    xp_min    = data.get("xp_min", 0)
    xp_max    = data.get("xp_max")
    descricao = data.get("descricao")

    if not all([titulo, tag, nivel is not None]):
        return jsonify({"error": "titulo, tag e nivel são obrigatórios"}), 400

    row = run("""
        INSERT INTO levels (titulo, tag, nivel, xp_min, xp_max, descricao)
        VALUES (%(t)s, %(tag)s, %(n)s, %(xpmin)s, %(xpmax)s, %(desc)s)
        RETURNING id_level, titulo, tag, nivel, xp_min, xp_max, descricao,
                  habilitado, created_at, updated_at
    """, {
        "t": titulo,
        "tag": tag,
        "n": nivel,
        "xpmin": xp_min,
        "xpmax": xp_max,
        "desc": descricao
    })

    return jsonify(row), 201

@levels_bp.put("/<uuid:id_level>")
@levels_bp.patch("/<uuid:id_level>")
@require_auth
def update_level(id_level):
    """
    Atualizar nível

    Atualiza um nível/título existente.  
    Aceita atualização parcial (PATCH) ou total (PUT).

    Campos permitidos no body (todos opcionais):

    {
      "titulo": "Novo título",
      "tag": "python",
      "nivel": 2,
      "xp_min": 100,
      "xp_max": 300,
      "descricao": "Descrição atualizada",
      "habilitado": true
    }

    ---
    tags:
      - Levels
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: path
        name: id_level
        required: true
        type: string
        format: uuid
        description: "ID do nível a ser atualizado (UUID)"

      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            titulo:
              type: string
              example: "Intermediário"
              description: "Título do nível"
            tag:
              type: string
              example: "python"
              description: "Trilha/categoria do nível"
            nivel:
              type: integer
              example: 2
            xp_min:
              type: integer
              example: 100
            xp_max:
              type: integer
              example: 300
            descricao:
              type: string
              example: "Nível para usuários com proficiência intermediária."
            habilitado:
              type: boolean
              example: true

    responses:
      200:
        description: "Nível atualizado com sucesso"
        schema:
          type: object
          properties:
            id_level:
              type: string
              format: uuid
            titulo:
              type: string
            tag:
              type: string
            nivel:
              type: integer
            xp_min:
              type: integer
            xp_max:
              type: integer
            descricao:
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
        description: "Nenhum campo enviado para atualização"

      404:
        description: "Nível não encontrado"
    """
    data = request.get_json(force=True, silent=True) or {}

    # Monta dinamicamente os campos
    campos = []
    params = {"id": id_level}

    for field in ["titulo", "tag", "nivel", "xp_min", "xp_max", "descricao", "habilitado"]:
        if field in data:
            campos.append(f"{field} = %({field})s")
            params[field] = data[field]

    if not campos:
        return jsonify({"error": "Nenhum campo enviado para atualização"}), 400

    sql = f"""
        UPDATE levels
           SET {", ".join(campos)}, updated_at = NOW()
         WHERE id_level = %(id)s
     RETURNING id_level, titulo, tag, nivel, xp_min, xp_max, descricao,
               habilitado, created_at, updated_at
    """

    row = one(sql, params)

    if not row:
        return jsonify({"error": "Nível não encontrado"}), 404

    return jsonify(row), 200

@levels_bp.delete("/<uuid:id_level>")
@require_auth
def delete_level(id_level):
    """
    Desabilitar nível (soft delete)

    Marca o nível como desabilitado (`habilitado = FALSE`), sem removê-lo
    fisicamente do banco de dados.

    ---
    tags:
      - Levels
    produces:
      - application/json
    parameters:
      - in: path
        name: id_level
        required: true
        type: string
        format: uuid
        description: "ID do nível a ser desabilitado (UUID)"
    responses:
      200:
        description: "Nível desabilitado com sucesso"
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Nível desabilitado com sucesso"
      404:
        description: "Nível não encontrado"
    """
    row = one("""
        UPDATE levels
           SET habilitado = FALSE,
               updated_at = NOW()
         WHERE id_level = %(id)s
     RETURNING id_level
    """, {"id": id_level})

    if not row:
        return jsonify({"error": "Nível não encontrado"}), 404

    return jsonify({"message": "Nível desabilitado com sucesso"}), 200

@levels_bp.post("/<uuid:id_usuario>/xp/add")
@require_auth
def add_xp_usuario(id_usuario):
    """
    Adicionar XP ao usuário e recalcular nível

    Adiciona uma quantidade de XP ao usuário, recalcula automaticamente o nível
    com base nas faixas de XP configuradas em `levels` e registra o histórico
    da operação (origem, motivo, referência, responsável).

    Body JSON esperado:

    {
      "xp": 50,
      "motivo": "atividade prática de Python",
      "origem": "ATIVIDADE",
      "referencia": {
        "id_projeto": "uuid-do-projeto",
        "id_atividade": "uuid-da-atividade"
      }
    }

    - `xp` é obrigatório e deve ser inteiro (positivo ou negativo).
    - `motivo`, `origem` e `referencia` são opcionais.
    - `referencia` é armazenado como JSONB (estrutura livre).

    ---
    tags:
      - XP
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
        name: id_usuario
        required: true
        type: string
        format: uuid
        description: "ID do usuário que receberá o XP (UUID)"
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - xp
          properties:
            xp:
              type: integer
              description: "Quantidade de XP a ser adicionada (pode ser negativa)"
              example: 50
            motivo:
              type: string
              description: "Motivo ou descrição da ação que gerou o XP"
              example: "Entrega da atividade de banco de dados"
            origem:
              type: string
              description: "Origem do XP (ADMIN, ATIVIDADE, PROJETO, SISTEMA, etc.)"
              example: "ATIVIDADE"
            referencia:
              type: object
              description: "Dados de referência relacionados ao XP (armazenado como JSONB)"
              example:
                id_projeto: "f9dfd8e4-9b51-4e66-9bf3-1b7f4f9a1234"
                id_atividade: "3a4b79ec-2f8e-4b9e-8da5-a6ce91234567"
    responses:
      200:
        description: "XP atualizado, nível recalculado e histórico registrado com sucesso"
        schema:
          type: object
          properties:
            message:
              type: string
              example: "XP atualizado, level recalculado e histórico registrado com sucesso"
            usuario:
              type: object
              description: "Dados atualizados do usuário após a mudança de XP/nível"
            level:
              type: object
              description: "Dados do nível atual do usuário após o recálculo"
      400:
        description: "Erro de validação (xp ausente ou não inteiro)"
      401:
        description: "Não autenticado"
      404:
        description: "Usuário não encontrado"
    """
    data = request.get_json(force=True, silent=True) or {}

    xp = data.get("xp")
    if xp is None:
        return jsonify({"error": "Campo 'xp' é obrigatório"}), 400

    try:
        xp = int(xp)
    except (TypeError, ValueError):
        return jsonify({"error": "Campo 'xp' deve ser inteiro"}), 400

    motivo = data.get("motivo")
    origem = data.get("origem")
    referencia = data.get("referencia")  # dict -> vai como JSONB
    id_responsavel = getattr(g, "user_id", None)

    result = adicionar_xp_usuario(
        id_usuario=id_usuario,
        delta_xp=xp,
        motivo=motivo,
        origem=origem,
        referencia=referencia,
        id_responsavel=id_responsavel,
    )

    if not result:
        return jsonify({"error": "Usuário não encontrado"}), 404

    return jsonify({
        "message": "XP atualizado, level recalculado e histórico registrado com sucesso",
        "usuario": result["usuario"],
        "level": result["level"]
    }), 200

@levels_bp.post("/<uuid:id_usuario>/level/recalc")
@require_auth
def recalc_level_usuario(id_usuario):
    """
    Recalcular XP e level do usuário a partir do histórico

    Recalcula o `xp_total` do usuário somando todos os registros do
    histórico `usuarios_xp_historico` e, em seguida, recalcula o nível
    com base nas faixas de XP configuradas na tabela `levels`.

    Útil para:
    - corrigir inconsistências de XP/level
    - reconstruir XP após ajustes manuais no histórico

    ---
    tags:
      - XP
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
        name: id_usuario
        required: true
        type: string
        format: uuid
        description: "ID do usuário que terá XP e level recalculados"
    responses:
      200:
        description: "XP recalculado a partir do histórico e level atualizado com sucesso"
        schema:
          type: object
          properties:
            message:
              type: string
              example: "XP recalculado a partir do histórico e level atualizado com sucesso"
            usuario:
              type: object
              description: "Dados atualizados do usuário após o recálculo de XP/level"
            level:
              type: object
              description: "Dados do nível atual do usuário"
      401:
        description: "Não autenticado"
      404:
        description: "Usuário não encontrado"
    """
    result = recalcular_xp_e_level_por_historico(id_usuario)

    if not result:
        return jsonify({"error": "Usuário não encontrado"}), 404

    return jsonify({
        "message": "XP recalculado a partir do histórico e level atualizado com sucesso",
        "usuario": result["usuario"],
        "level": result["level"]
    }), 200
