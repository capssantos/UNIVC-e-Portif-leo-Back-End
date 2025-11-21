import os
from flask import Blueprint, request, jsonify, g
from dotenv import load_dotenv
from ..models.db import one, many, run
from ..models.auth import require_auth
from datetime import datetime

load_dotenv()
projetos_bp = Blueprint("projetos", __name__)

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

# --------- Criar projeto ---------
@projetos_bp.post("/")
@require_auth
def create_projeto():
    """
    Cria um novo projeto vinculado ao usuário autenticado.

    Body esperado (JSON):

    {
      "titulo": "Titulo da atividade",
      "descricao": "breve descrição da atividade",
      "texto": "texto completo em markdown ou html",
      "imagem_atividade": "URL já retornada pela rota de upload",
      "tags": ["python", "flask", "backend"]
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
    responses:
      201:
        description: Projeto criado com sucesso
      400:
        description: Dados inválidos
      401:
        description: Não autenticado
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

    # Se vier None, vira lista vazia
    if tags is None:
        tags = []

    # Validação simples: garantir que seja um array de strings
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        return jsonify({"error": "tags deve ser uma lista de strings"}), 400

    if not titulo or not texto:
        return jsonify({"error": "titulo e texto são obrigatórios"}), 400

    row = one("""
        INSERT INTO projetos
            (id_usuario, titulo, descricao, texto, imagem_atividade, tags)
        VALUES
            (%(id_usuario)s, %(titulo)s, %(descricao)s, %(texto)s, %(imagem_atividade)s, %(tags)s)
        RETURNING
            id_projeto,
            id_usuario,
            titulo,
            descricao,
            texto,
            imagem_atividade,
            tags,
            habilitado,
            created_at,
            updated_at
    """, {
        "id_usuario":        user_id,
        "titulo":            titulo,
        "descricao":         descricao,
        "texto":             texto,
        "imagem_atividade":  imagem_atividade,
        "tags":              tags,
    })

    return jsonify(row), 201

# --------- Listar projetos ---------
@projetos_bp.get("/")
def list_projetos():
    """
    Lista projetos.

    Filtros opcionais (query params):
      - ?id_usuario=<uuid>   -> projetos de um usuário específico
      - ?tag=python          -> projetos que contenham essa tag
      - ?limit=20
      - ?offset=0

    ---
    tags:
      - Projetos
    produces:
      - application/json
    responses:
      200:
        description: Lista de projetos
    """
    headers_dict = dict(request.headers)
    print(f"[PROJ LIST] - Headers: {headers_dict}")
    print(f"[PROJ LIST] - Args: {dict(request.args)}")

    id_usuario = request.args.get("id_usuario")
    tag        = request.args.get("tag")

    try:
        limit  = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"error": "limit e offset devem ser inteiros"}), 400

    filters = ["habilitado = TRUE"]
    params = {"limit": limit, "offset": offset}

    if id_usuario:
        filters.append("id_usuario = %(id_usuario)s")
        params["id_usuario"] = id_usuario

    if tag:
        filters.append("tags @> ARRAY[%(tag)s]::text[]")
        params["tag"] = tag

    where_clause = " AND ".join(filters)

    rows = many(f"""
        SELECT
            id_projeto,
            id_usuario,
            titulo,
            descricao,
            texto,
            imagem_atividade,
            tags,
            habilitado,
            created_at,
            updated_at
        FROM projetos
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT %(limit)s
        OFFSET %(offset)s
    """, params)

    return jsonify(rows), 200

# --------- Detalhar projeto ---------
@projetos_bp.get("/<uuid:id_projeto>")
def get_projeto(id_projeto):
    """
    Detalhes de um projeto

    Retorna os dados de um projeto específico pelo seu id_projeto.

    ---
    tags:
      - Projetos
    produces:
      - application/json
    parameters:
      - in: path
        name: id_projeto
        required: true
        type: string
        format: uuid
        description: "ID do projeto (UUID)"
    responses:
      200:
        description: Projeto encontrado
      404:
        description: Projeto não encontrado
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
            habilitado,
            created_at,
            updated_at
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not row:
        return jsonify({"error": "Projeto não encontrado"}), 404

    return jsonify(row), 200

# --------- Atualizar projeto (dono) ---------
@projetos_bp.patch("/<uuid:id_projeto>")
@require_auth
def update_projeto(id_projeto):
    """
    Atualiza um projeto.

    Apenas o DONO do projeto pode atualizar.

    Campos aceitos no body (todos opcionais):
      - titulo
      - descricao
      - texto
      - imagem_atividade
      - tags (array de strings)
      - habilitado
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

    projeto = one("""
        SELECT id_projeto, id_usuario
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not projeto:
        return jsonify({"error": "Projeto não encontrado"}), 404

    if str(projeto["id_usuario"]) != str(user_id):
        return jsonify({"error": "Você não tem permissão para editar este projeto"}), 403

    fields = []
    params = {"id": id_projeto}

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

        # Se vier None, zera as tags
        if tags is None:
            tags = []

        # Validação simples: garantir que seja um array de strings
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            return jsonify({"error": "tags deve ser uma lista de strings"}), 400

        fields.append("tags = %(tags)s")
        params["tags"] = tags

    if "habilitado" in data:
        fields.append("habilitado = %(habilitado)s")
        params["habilitado"] = bool(data.get("habilitado"))

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
        habilitado,
        created_at,
        updated_at
    """

    row = one(sql, params)

    return jsonify(row), 200

# --------- Desabilitar (soft delete) projeto ---------
@projetos_bp.delete("<uuid:id_projeto>")
@require_auth
def delete_projeto(id_projeto):
    """
    Desabilita (soft delete) um projeto.

    Apenas o DONO do projeto pode desabilitar.

    ---
    tags:
      - Projetos
    security:
      - Bearer: []
    produces:
      - application/json
    responses:
      200:
        description: Projeto desabilitado com sucesso
      401:
        description: Não autenticado
      403:
        description: Não é dono do projeto
      404:
        description: Projeto não encontrado
    """
    headers_dict = dict(request.headers)
    print(f"[PROJ DEL ] - Headers: {headers_dict}")

    if not _is_admin_or_professor():
        return jsonify({"error": "acesso restrito a administradores e professores"}), 403

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "nenhum usuário autenticado"}), 401

    projeto = one("""
        SELECT id_projeto, id_usuario
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not projeto:
        return jsonify({"error": "Projeto não encontrado"}), 404

    if str(projeto["id_usuario"]) != str(user_id):
        return jsonify({"error": "Você não tem permissão para remover este projeto"}), 403

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
        habilitado,
        created_at,
        updated_at
    """, {"id": id_projeto})

    return jsonify(row), 200
