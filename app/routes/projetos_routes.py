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

@projetos_bp.post("/")
@require_auth
def create_projeto():
    """
    Criar projeto

    Cria um novo projeto vinculado ao usuário autenticado.  
    Apenas usuários com permissao de administrador ou professor podem criar projetos.

    Body esperado (JSON):

    {
      "titulo": "Titulo da atividade",
      "descricao": "Breve descricao da atividade",
      "texto": "Texto completo em markdown ou HTML",
      "imagem_atividade": "URL retornada pela rota de upload",
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
              description: "Titulo da atividade ou projeto"
              example: "API de Portifoleo UNIVC com Flask"
            descricao:
              type: string
              description: "Resumo curto sobre o projeto"
              example: "API backend em Flask para gerenciar projetos e atividades dos alunos"
            texto:
              type: string
              description: "Texto completo em markdown ou HTML descrevendo o projeto"
              example: "## Objetivo do projeto..."
            imagem_atividade:
              type: string
              description: "URL publica da imagem da atividade retornada pela rota de upload"
              example: "https://onicode.nyc3.digitaloceanspaces.com/UNIVC/e-Portifoleo/projetos/img123.png"
            tags:
              type: array
              description: "Lista de tags relacionadas ao projeto"
              items:
                type: string
              example: ["python", "flask", "backend", "api"]
    responses:
      201:
        description: Projeto criado com sucesso
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
            habilitado:
              type: boolean
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time
      400:
        description: Erro de validacao, campos obrigatorios ausentes ou tags invalidas
      401:
        description: Nao autenticado, token ausente ou invalido
      403:
        description: Usuario autenticado sem permissao para criar projeto
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
    Atualizar projeto (dono)

    Atualiza um projeto existente.  
    Apenas usuários autenticados com permissão de administrador ou professor
    que sejam donos do projeto podem editar.

    Campos aceitos no body (todos opcionais):
      - titulo
      - descricao
      - texto
      - imagem_atividade
      - tags (array de strings)
      - habilitado

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
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            titulo:
              type: string
              description: "Novo título do projeto"
              example: "API de Portifoleo UNIVC - v2"
            descricao:
              type: string
              description: "Nova descrição resumida do projeto"
              example: "Atualização com novos endpoints e melhorias de segurança"
            texto:
              type: string
              description: "Texto completo em markdown ou HTML"
              example: "## Novas funcionalidades..."
            imagem_atividade:
              type: string
              description: "URL pública da nova imagem da atividade"
              example: "https://onicode.nyc3.digitaloceanspaces.com/UNIVC/e-Portifoleo/projetos/img456.png"
            tags:
              type: array
              description: "Lista de tags relacionadas ao projeto"
              items:
                type: string
              example: ["python", "flask", "api", "update"]
            habilitado:
              type: boolean
              description: "Define se o projeto está habilitado para exibição"
              example: true
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
            habilitado:
              type: boolean
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time
      400:
        description: "Erro de validação (tags inválidas ou nenhum campo para atualização)"
      401:
        description: "Não autenticado"
      403:
        description: "Sem permissão para editar (não admin/professor ou não dono do projeto)"
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

    # permissões
    if not _is_admin_or_professor():
        return jsonify({"error": "acesso restrito a administradores e professores"}), 403

    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "nenhum usuário autenticado"}), 401

    # verificar projeto
    projeto = one("""
        SELECT id_projeto, id_usuario
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not projeto:
        return jsonify({"error": "Projeto não encontrado"}), 404

    if not _is_admin() and (str(projeto["id_usuario"]) != str(user_id)):
        return jsonify({"error": "Você não tem permissão para remover este projeto"}), 403

    # soft delete
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
              example: "MEMBRO"
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
        description: "Dados inválidos ou inscrição já existente (PENDENTE ou APROVADO)"
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
        SELECT id_projeto, id_usuario, habilitado
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not projeto or not projeto.get("habilitado"):
        return jsonify({"error": "Projeto não encontrado ou desabilitado"}), 404

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
    papel = data.get("papel") or "MEMBRO"

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
    Apenas o DONO do projeto (professor/adm) pode visualizar as inscrições.

    Filtro opcional via query param:
      - ?status=PENDENTE|APROVADO|RECUSADO|CANCELADO

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
        description: "Filtra inscrições por status"
        enum:
          - PENDENTE
          - APROVADO
          - RECUSADO
          - CANCELADO
    responses:
      200:
        description: "Lista de participações do projeto"
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
      401:
        description: "Não autenticado"
      403:
        description: "Sem permissão (não admin/professor ou não dono do projeto)"
      404:
        description: "Projeto não encontrado"
    """
    headers_dict = dict(request.headers)
    print(f"[PROJ PART LIST] - Headers: {headers_dict}")
    print(f"[PROJ PART LIST] - Args: {dict(request.args)}")

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

    # Apenas DONO do projeto
    if str(projeto["id_usuario"]) != str(user_id):
        return jsonify({"error": "Você não tem permissão para visualizar as inscrições deste projeto"}), 403

    status = request.args.get("status")
    params = {"id_projeto": id_projeto}
    where = ["pp.id_projeto = %(id_projeto)s"]

    if status:
        where.append("pp.status = %(status)s")
        params["status"] = status.strip().upper()

    where_clause = " AND ".join(where)

    rows = many(f"""
        SELECT
            pp.id_participacao,
            pp.id_projeto,
            pp.id_usuario,
            u.nome        AS nome_usuario,
            u.email       AS email_usuario,
            pp.papel,
            pp.status,
            pp.mensagem,
            pp.created_at,
            pp.updated_at
        FROM projetos_participantes pp
        JOIN usuarios u ON u.id_usuario = pp.id_usuario
        WHERE {where_clause}
        ORDER BY pp.created_at DESC
    """, params)

    return jsonify(rows), 200

@projetos_bp.patch("/<uuid:id_projeto>/participantes/<uuid:id_participacao>")
@require_auth
def atualizar_participacao_projeto(id_projeto, id_participacao):
    """
    Atualizar participação em projeto

    Atualiza o status e/ou o papel de um participante em um projeto.  
    Apenas o DONO do projeto (professor/adm) pode aprovar, recusar, cancelar
    ou ajustar o papel do participante.

    Body (JSON):

    {
      "status": "PENDENTE | APROVADO | RECUSADO | CANCELADO",
      "papel": "MEMBRO | MONITOR (1) | outro papel"
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
        description: "ID do projeto (UUID)"
      - in: path
        name: id_participacao
        required: true
        type: string
        format: uuid
        description: "ID da participação (UUID)"
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            status:
              type: string
              description: "Novo status da participação. Valores aceitos: PENDENTE, APROVADO, RECUSADO, CANCELADO"
              example: "APROVADO"
            papel:
              type: string
              description: "Novo papel do participante no projeto (exemplo: MEMBRO, MONITOR)"
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
        description: "Dados inválidos (nenhum campo informado ou status inválido)"
      401:
        description: "Não autenticado"
      403:
        description: "Sem permissão (não admin/professor ou não dono do projeto)"
      404:
        description: "Projeto ou participação não encontrada"
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

    projeto = one("""
        SELECT id_projeto, id_usuario
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not projeto:
        return jsonify({"error": "Projeto não encontrado"}), 404

    # Apenas DONO do projeto
    if str(projeto["id_usuario"]) != str(user_id):
        return jsonify({"error": "Você não tem permissão para gerenciar inscrições deste projeto"}), 403

    participacao = one("""
        SELECT id_participacao, id_projeto, id_usuario, status, papel
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
        status_normalizado = novo_status.strip().upper()
        status_validos = {"PENDENTE", "APROVADO", "RECUSADO", "CANCELADO"}
        if status_normalizado not in status_validos:
            return jsonify({"error": f"status inválido. Valores aceitos: {', '.join(status_validos)}"}), 400

        fields.append("status = %(status)s")
        params["status"] = status_normalizado

    if novo_papel is not None:
        fields.append("papel = %(papel)s")
        params["papel"] = novo_papel

    # ---------- Regra de apenas 1 MONITOR APROVADO por projeto ----------
    # Descobre como ficará o papel e o status DEPOIS da atualização
    papel_final = (novo_papel if novo_papel is not None else participacao["papel"]) or ""
    papel_final = papel_final.strip().upper()

    status_final = (status_normalizado if status_normalizado is not None else participacao["status"]) or ""
    status_final = status_final.strip().upper()

    # Se esse registro vai virar (ou continuar sendo) MONITOR APROVADO,
    # verifica se já existe outro monitor aprovado no mesmo projeto.
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

    Permite que o DONO do projeto (professor/adm) adicione um aluno diretamente
    ao projeto, definindo o papel e o status da participação.

    Body (JSON):

    {
      "id_usuario": "UUID do aluno",
      "papel": "MEMBRO | MONITOR | (opcional, padrão MEMBRO)",
      "status": "PENDENTE | APROVADO | RECUSADO | CANCELADO (opcional, padrão APROVADO)",
      "mensagem": "Mensagem opcional para o aluno"
    }

    Regras:
    - Apenas o DONO do projeto (professor/adm) pode adicionar.
    - Se o papel final for MONITOR e o status final for APROVADO,
      só é permitido um monitor aprovado por projeto.
    - Se o aluno já tiver inscrição PENDENTE ou APROVADO no projeto,
      não é permitido criar uma nova.

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
        description: "ID do projeto (UUID) onde o aluno será adicionado"
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
              description: "ID do aluno a ser adicionado ao projeto"
              example: "8b7b8e2a-7e1c-4b46-9c23-9f5a0e3d1234"
            papel:
              type: string
              description: "Papel do usuário no projeto. Padrão MEMBRO"
              example: "MEMBRO"
            status:
              type: string
              description: "Status inicial da participação. Padrão APROVADO"
              enum:
                - PENDENTE
                - APROVADO
                - RECUSADO
                - CANCELADO
              example: "APROVADO"
            mensagem:
              type: string
              description: "Mensagem opcional para o aluno sobre a participação"
              example: "Você foi adicionado como monitor deste projeto."
    responses:
      201:
        description: "Participação criada com sucesso"
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
        description: "Erro de validação (id_usuario ausente, status inválido ou já possui inscrição PENDENTE/APROVADO)"
      401:
        description: "Não autenticado"
      403:
        description: "Sem permissão (não admin/professor ou não dono do projeto)"
      404:
        description: "Projeto ou usuário (aluno) não encontrado"
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

    # Verifica se o projeto existe e se o usuário é o DONO
    projeto = one("""
        SELECT id_projeto, id_usuario
        FROM projetos
        WHERE id_projeto = %(id)s
    """, {"id": id_projeto})

    if not projeto:
        return jsonify({"error": "Projeto não encontrado"}), 404

    if str(projeto["id_usuario"]) != str(user_id):
        return jsonify({"error": "Você não tem permissão para gerenciar inscrições deste projeto"}), 403

    # Dados do body
    id_usuario_alvo = data.get("id_usuario")
    if not id_usuario_alvo:
        return jsonify({"error": "id_usuario é obrigatório"}), 400

    papel = data.get("papel") or "MEMBRO"
    status = data.get("status") or "APROVADO"
    mensagem = data.get("mensagem")

    status_normalizado = status.strip().upper()
    status_validos = {"PENDENTE", "APROVADO", "RECUSADO", "CANCELADO"}
    if status_normalizado not in status_validos:
        return jsonify({"error": f"status inválido. Valores aceitos: {', '.join(status_validos)}"}), 400

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
    papel_final_upper = (papel or "").strip().upper()
    status_final_upper = status_normalizado

    if papel_final_upper == "MONITOR" and status_final_upper == "APROVADO":
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
        "papel": papel,
        "status": status_normalizado,
        "mensagem": mensagem,
    })

    return jsonify(row), 201
