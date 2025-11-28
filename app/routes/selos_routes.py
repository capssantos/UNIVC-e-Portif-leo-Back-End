# app/routes/selos_routes.py
import os
from flask import Blueprint, request, jsonify, g
from datetime import datetime

from ..models.db import one, many, run
from ..models.auth import require_auth

selos_bp = Blueprint("selos", __name__, url_prefix="/selos")


def _is_admin_or_professor():
    """
    Verifica se o usuário autenticado possui permissão suficiente
    para gerenciar selos. Permissões válidas: ADMIN, PROFESSOR.
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

# --------- Listar selos ---------
@selos_bp.get("/")
@require_auth
def list_selos():
    """
    Listar selos

    Retorna a lista de selos cadastrados no sistema, com suporte a filtro
    por campo `habilitado`.

    Regras de visibilidade:
      - Usuário **comum** (sem permissão ADMIN/PROFESSOR):
          - Sempre verá **apenas selos habilitados** (`habilitado = TRUE`),
            independentemente do query param.
      - Usuários com permissão **ADMIN** ou **PROFESSOR**:
          - Podem ver todos os selos.
          - Podem filtrar explicitamente por `habilitado=true|false`.

    Filtros opcionais via query params:
      - `?habilitado=true|false`

    ---
    tags:
      - Selos
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
        name: habilitado
        required: false
        type: string
        description: >
          Disponível apenas para usuários com permissão ADMIN ou PROFESSOR.  
          Quando informado, filtra os selos pelo campo `habilitado`.  
          Aceita valores: true/false, 1/0, t/f, yes/no (case-insensitive).
        enum:
          - "true"
          - "false"

    responses:
      200:
        description: Lista de selos retornada com sucesso.
        schema:
          type: array
          items:
            type: object
            properties:
              id_selo:
                type: string
                format: uuid
              titulo:
                type: string
                description: "Título do selo exibido para o usuário."
              slug:
                type: string
                description: "Identificador amigável/único do selo (ex.: 'mentor-backend')."
              descricao:
                type: string
                description: "Texto explicando o significado ou critério do selo."
              icone:
                type: string
                description: "Nome/slug de ícone ou URL de ícone associado ao selo."
              cor_inicio:
                type: string
                description: "Cor inicial (hex ou token) para gradiente/estilo do selo."
                example: "#4F46E5"
              cor_fim:
                type: string
                description: "Cor final (hex ou token) para gradiente/estilo do selo."
                example: "#22C55E"
              tipo:
                type: string
                description: "Categoria ou tipo de selo (ex.: 'CONQUISTA', 'PARTICIPACAO')."
              ordem:
                type: integer
                description: "Ordem de exibição do selo nas listagens."
              habilitado:
                type: boolean
                description: "Indica se o selo está ativo/habilitado para uso."
              created_at:
                type: string
                format: date-time
              updated_at:
                type: string
                format: date-time

      401:
        description: Usuário não autenticado (token ausente ou inválido).
        schema:
          type: object
          properties:
            error:
              type: string

    """
    is_admin_prof = _is_admin_or_professor()
    habilitado_param = request.args.get("habilitado")

    params = {}

    base_query = """
        SELECT id_selo, titulo, slug, descricao, icone,
               cor_inicio, cor_fim, tipo, ordem,
               habilitado, created_at, updated_at
          FROM selos
    """

    where_clauses = []

    if not is_admin_prof:
        # usuário comum: sempre habilitado = TRUE
        where_clauses.append("habilitado = TRUE")
    else:
        # admin/professor pode filtrar
        if habilitado_param is not None:
            valor = habilitado_param.lower() in ["true", "1", "t", "yes", "y"]
            where_clauses.append("habilitado = %(habilitado)s")
            params["habilitado"] = valor

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    base_query += " ORDER BY ordem ASC, titulo ASC"

    rows = many(base_query, params)

    return jsonify(rows), 200

# --------- Criar selo ---------
@selos_bp.post("/")
@require_auth
def create_selo():
    """
    Criar novo selo

    Cria um novo selo que poderá ser vinculado a projetos ou usado
    em gamificação do portfólio.

    Regras:
      - Apenas usuários com permissão **ADMIN** ou **PROFESSOR** podem criar selos.
      - Campo `titulo` é obrigatório.
      - Demais campos são opcionais, porém recomendados para exibição no front.

    Exemplo de body (JSON):
    {
      "titulo": "Criatividade",
      "slug": "criatividade",
      "descricao": "Reconhecimento por soluções criativas.",
      "icone": "sparkles",
      "cor_inicio": "#22c55e",
      "cor_fim": "#a3e635",
      "tipo": "CRIATIVIDADE",
      "ordem": 1
    }

    --- 
    tags:
      - Selos
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
          properties:
            titulo:
              type: string
              description: "Título do selo exibido para o usuário."
              example: "Criatividade"
            slug:
              type: string
              description: "Identificador único/amigável do selo."
              example: "criatividade"
            descricao:
              type: string
              description: "Descrição do critério ou significado do selo."
              example: "Reconhecimento por soluções criativas."
            icone:
              type: string
              description: "Nome do ícone (ex.: no front, ícone lucide/heroicons)."
              example: "sparkles"
            cor_inicio:
              type: string
              description: "Cor inicial do gradiente/estilo (hex ou token)."
              example: "#22c55e"
            cor_fim:
              type: string
              description: "Cor final do gradiente/estilo (hex ou token)."
              example: "#a3e635"
            tipo:
              type: string
              description: "Tipo/categoria do selo (ex.: CRIATIVIDADE, PARTICIPACAO, LIDERANCA)."
              example: "CRIATIVIDADE"
            ordem:
              type: integer
              description: "Ordem de exibição do selo nas listagens."
              example: 1

    responses:
      201:
        description: Selo criado com sucesso.
        schema:
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
            habilitado:
              type: boolean
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time
      400:
        description: Erro de validação (ex.: título ausente).
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Campo 'titulo' é obrigatório."
      401:
        description: Usuário não autenticado.
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Token inválido ou ausente."
      403:
        description: Permissão negada (não é ADMIN/PROFESSOR).
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Permissão negada."
    """
    if not _is_admin_or_professor():
        return jsonify({"error": "Permissão negada."}), 403

    data = request.get_json(force=True, silent=True) or {}

    titulo = (data.get("titulo") or "").strip()
    if not titulo:
        return jsonify({"error": "Campo 'titulo' é obrigatório."}), 400

    slug = (data.get("slug") or "").strip() or None
    descricao = (data.get("descricao") or "").strip() or None
    icone = (data.get("icone") or "").strip() or None
    cor_inicio = (data.get("cor_inicio") or "").strip() or None
    cor_fim = (data.get("cor_fim") or "").strip() or None
    tipo = (data.get("tipo") or "").strip() or None
    ordem = data.get("ordem", 0)

    row = one(
        """
        INSERT INTO selos (
            titulo, slug, descricao, icone,
            cor_inicio, cor_fim, tipo, ordem,
            habilitado, created_at
        )
        VALUES (
            %(titulo)s, %(slug)s, %(descricao)s, %(icone)s,
            %(cor_inicio)s, %(cor_fim)s, %(tipo)s, %(ordem)s,
            TRUE, NOW()
        )
        RETURNING id_selo, titulo, slug, descricao, icone,
                  cor_inicio, cor_fim, tipo, ordem,
                  habilitado, created_at, updated_at
        """,
        {
            "titulo": titulo,
            "slug": slug,
            "descricao": descricao,
            "icone": icone,
            "cor_inicio": cor_inicio,
            "cor_fim": cor_fim,
            "tipo": tipo,
            "ordem": ordem,
        },
    )

    return jsonify(row), 201

# --------- Detalhar selo ---------
@selos_bp.get("/<uuid:id_selo>")
@require_auth
def get_selo(id_selo):
    """
    Detalhar selo

    Retorna os dados completos de um selo específico.

    Regras de acesso:
      - Usuário comum só pode visualizar **selos habilitados**.
      - Usuários com permissão **ADMIN** ou **PROFESSOR** podem visualizar
        selos habilitados e desabilitados.

    ---
    tags:
      - Selos
    security:
      - Bearer: []
    produces:
      - application/json

    parameters:
      - in: path
        name: id_selo
        required: true
        type: string
        format: uuid
        description: "UUID do selo"

      - in: header
        name: Authorization
        required: true
        type: string
        description: "Token JWT no formato Bearer <token>"

    responses:
      200:
        description: Selo encontrado
        schema:
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
              example: "#22c55e"
            cor_fim:
              type: string
              example: "#a3e635"
            tipo:
              type: string
              example: "CRIATIVIDADE"
            ordem:
              type: integer
            habilitado:
              type: boolean
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time

      401:
        description: Não autenticado
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Usuário não autenticado."

      404:
        description: Selo não encontrado
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Selo não encontrado."
    """
    is_admin_prof = _is_admin_or_professor()

    if is_admin_prof:
        row = one(
            """
            SELECT id_selo, titulo, slug, descricao, icone,
                   cor_inicio, cor_fim, tipo, ordem,
                   habilitado, created_at, updated_at
              FROM selos
             WHERE id_selo = %(id_selo)s
            """,
            {"id_selo": id_selo},
        )
    else:
        row = one(
            """
            SELECT id_selo, titulo, slug, descricao, icone,
                   cor_inicio, cor_fim, tipo, ordem,
                   habilitado, created_at, updated_at
              FROM selos
             WHERE id_selo = %(id_selo)s
               AND habilitado = TRUE
            """,
            {"id_selo": id_selo},
        )

    if not row:
        return jsonify({"error": "Selo não encontrado."}), 404

    return jsonify(row), 200

# --------- Atualizar selo ---------
@selos_bp.patch("/<uuid:id_selo>")
@require_auth
def update_selo(id_selo):
    """
    Atualizar selo

    Atualiza os dados de um selo existente.  
    Apenas usuários com permissão **ADMIN** ou **PROFESSOR** podem alterar selos.

    Body (JSON) – todos os campos são opcionais:

    {
      "titulo": "Criatividade Avançada",
      "slug": "criatividade-avancada",
      "descricao": "Reconhecimento por soluções criativas em cenários complexos.",
      "icone": "sparkles",
      "cor_inicio": "#22c55e",
      "cor_fim": "#a3e635",
      "tipo": "CRIATIVIDADE",
      "ordem": 2,
      "habilitado": true
    }

    Regras:
      - Pelo menos um campo deve ser enviado.
      - Campos não enviados permanecem inalterados.

    ---
    tags:
      - Selos
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
        name: id_selo
        required: true
        type: string
        format: uuid
        description: "UUID do selo a ser atualizado"

      - in: body
        name: body
        required: true
        description: "Campos a serem atualizados no selo"
        schema:
          type: object
          properties:
            titulo:
              type: string
              example: "Criatividade Avançada"
            slug:
              type: string
              example: "criatividade-avancada"
            descricao:
              type: string
              example: "Reconhecimento por soluções criativas em cenários complexos."
            icone:
              type: string
              example: "sparkles"
            cor_inicio:
              type: string
              example: "#22c55e"
            cor_fim:
              type: string
              example: "#a3e635"
            tipo:
              type: string
              example: "CRIATIVIDADE"
            ordem:
              type: integer
              example: 2
            habilitado:
              type: boolean
              example: true

    responses:
      200:
        description: Selo atualizado com sucesso
        schema:
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
            habilitado:
              type: boolean
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time

      400:
        description: Nenhum campo enviado ou payload inválido
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Nenhum campo para atualizar."

      401:
        description: Não autenticado
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Usuário não autenticado."

      403:
        description: Permissão negada (não é ADMIN/PROFESSOR)
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Permissão negada."

      404:
        description: Selo não encontrado
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Selo não encontrado."
    """
    if not _is_admin_or_professor():
        return jsonify({"error": "Permissão negada."}), 403

    data = request.get_json(force=True, silent=True) or {}
    fields = []
    params = {"id_selo": id_selo}

    def set_field(field_name, db_col=None):
        nonlocal fields, params, data
        if db_col is None:
            db_col = field_name
        if field_name in data:
            fields.append(f"{db_col} = %({db_col})s")
            params[db_col] = data[field_name]

    set_field("titulo")
    set_field("slug")
    set_field("descricao")
    set_field("icone")
    set_field("cor_inicio")
    set_field("cor_fim")
    set_field("tipo")
    set_field("ordem")
    set_field("habilitado")

    if not fields:
        return jsonify({"error": "Nenhum campo para atualizar."}), 400

    fields.append("updated_at = NOW()")

    query = f"""
        UPDATE selos
           SET {", ".join(fields)}
         WHERE id_selo = %(id_selo)s
        RETURNING id_selo, titulo, slug, descricao, icone,
                  cor_inicio, cor_fim, tipo, ordem,
                  habilitado, created_at, updated_at
    """

    row = one(query, params)

    if not row:
        return jsonify({"error": "Selo não encontrado."}), 404

    return jsonify(row), 200

# --------- Desabilitar selo (soft delete) ---------
@selos_bp.patch("/<uuid:id_selo>/disable")
@require_auth
def disable_selo(id_selo):
    """
    Desabilitar selo (soft delete)

    Desabilita um selo já existente, sem removê-lo do banco de dados  
    (`habilitado = FALSE`).  
    Apenas usuários com permissão **ADMIN** ou **PROFESSOR** podem executar.

    ---
    tags:
      - Selos
    security:
      - Bearer: []
    produces:
      - application/json
    consumes:
      - application/json

    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: "Token JWT no formato Bearer <token>"

      - in: path
        name: id_selo
        required: true
        type: string
        format: uuid
        description: "ID do selo a ser desabilitado"

    responses:
      200:
        description: "Selo desabilitado com sucesso"
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Selo desabilitado com sucesso."
            id_selo:
              type: string
              format: uuid
            habilitado:
              type: boolean
              example: false

      403:
        description: "Usuário não tem permissão"
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Permissão negada."

      404:
        description: "Selo não encontrado"
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Selo não encontrado."
    """
    if not _is_admin_or_professor():
        return jsonify({"error": "Permissão negada."}), 403

    row = one(
        """
        UPDATE selos
           SET habilitado = FALSE,
               updated_at = NOW()
         WHERE id_selo = %(id_selo)s
        RETURNING id_selo, habilitado
        """,
        {"id_selo": id_selo},
    )

    if not row:
        return jsonify({"error": "Selo não encontrado."}), 404

    return jsonify({
        "message": "Selo desabilitado com sucesso.",
        **row
    }), 200

# --------- Re-habilitar selo ---------
@selos_bp.patch("/<uuid:id_selo>/enable")
@require_auth
def enable_selo(id_selo):
    """
    Reativar selo desabilitado

    Reativa um selo previamente desabilitado (`habilitado = FALSE`),  
    permitindo que ele volte a aparecer para os usuários.  

    Apenas usuários com permissão **ADMIN** ou **PROFESSOR** podem executar.

    ---
    tags:
      - Selos
    security:
      - Bearer: []
    produces:
      - application/json
    consumes:
      - application/json

    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: "Token JWT no formato Bearer <token>"

      - in: path
        name: id_selo
        required: true
        type: string
        format: uuid
        description: "ID do selo que será reativado"

    responses:
      200:
        description: "Selo habilitado com sucesso"
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Selo habilitado com sucesso."
            id_selo:
              type: string
              format: uuid
            habilitado:
              type: boolean
              example: true

      403:
        description: "Usuário não tem permissão"
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Permissão negada."

      404:
        description: "Selo não encontrado"
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Selo não encontrado."
    """
    if not _is_admin_or_professor():
        return jsonify({"error": "Permissão negada."}), 403

    row = one(
        """
        UPDATE selos
           SET habilitado = TRUE,
               updated_at = NOW()
         WHERE id_selo = %(id_selo)s
        RETURNING id_selo, habilitado
        """,
        {"id_selo": id_selo},
    )

    if not row:
        return jsonify({"error": "Selo não encontrado."}), 404

    return jsonify({
        "message": "Selo habilitado com sucesso.",
        **row
    }), 200

# -----------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------
# --------- Atribuir selo a usuário ---------
@selos_bp.post("/usuario")
@require_auth
def atribuir_selo():
    """
    Atribuir selo a usuário

    Atribui um selo a um usuário específico.  
    Apenas usuários com permissão **ADMIN** ou **PROFESSOR** podem executar.

    Body (JSON):

    {
      "id_usuario": "UUID do aluno",
      "id_selo": "UUID do selo",
      "motivo": "Aluno se destacou no projeto X",
      "origem": "PROJETO",
      "referencia": {
        "id_projeto": "...",
        "id_atividade": "..."
      }
    }

    Regras:
      - `id_usuario` e `id_selo` são obrigatórios.
      - O usuário precisa existir na tabela `usuarios`.
      - O selo precisa existir e estar `habilitado = TRUE`.
      - Não é permitido atribuir o mesmo selo duas vezes para o mesmo usuário.

    ---
    tags:
      - Selos
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
        description: "Dados para atribuição do selo ao usuário"
        schema:
          type: object
          properties:
            id_usuario:
              type: string
              format: uuid
              description: "ID do usuário (aluno) que receberá o selo"
              example: "18d7a9c4-2b0a-4f84-9b0a-2c7b0ef0a111"
            id_selo:
              type: string
              format: uuid
              description: "ID do selo a ser atribuído"
              example: "9f3b3a3e-5b7d-4f9a-8c1f-123456789abc"
            motivo:
              type: string
              description: "Motivo da atribuição do selo"
              example: "Aluno se destacou no projeto de APIs REST."
            origem:
              type: string
              description: "Origem da atribuição (PROJETO, ATIVIDADE, MANUAL, etc.)"
              example: "PROJETO"
            referencia:
              type: object
              description: "Referência opcional relacionada ao selo (projeto, atividade, etc.)"
              example:
                id_projeto: "11111111-2222-3333-4444-555555555555"
                id_atividade: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    responses:
      201:
        description: "Selo atribuído com sucesso ao usuário"
        schema:
          type: object
          properties:
            id_usuario_selo:
              type: string
              format: uuid
            id_usuario:
              type: string
              format: uuid
            id_selo:
              type: string
              format: uuid
            motivo:
              type: string
            origem:
              type: string
            referencia:
              type: object
            habilitado:
              type: boolean
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time

      400:
        description: "Erro de validação – campos obrigatórios ausentes, selo desabilitado ou selo já atribuído"
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Campos 'id_usuario' e 'id_selo' são obrigatórios."

      401:
        description: "Usuário não autenticado"
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Usuário não autenticado."

      403:
        description: "Usuário autenticado, porém sem permissão (não é ADMIN/PROFESSOR)"
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Permissão negada."

      404:
        description: "Usuário ou selo não encontrado"
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Usuário não encontrado."
    """
    if not _is_admin_or_professor():
        return jsonify({"error": "Permissão negada."}), 403

    data = request.get_json(force=True, silent=True) or {}
    id_usuario = data.get("id_usuario")
    id_selo = data.get("id_selo")

    if not id_usuario or not id_selo:
        return jsonify({
            "error": "Campos 'id_usuario' e 'id_selo' são obrigatórios."
        }), 400

    # Verifica se usuário existe
    usuario = one(
        "SELECT id_usuario FROM usuarios WHERE id_usuario = %(id)s",
        {"id": id_usuario}
    )
    if not usuario:
        return jsonify({"error": "Usuário não encontrado."}), 404

    # Verifica se selo existe e está habilitado
    selo = one(
        """
        SELECT id_selo, habilitado
          FROM selos
         WHERE id_selo = %(id)s
        """,
        {"id": id_selo}
    )
    if not selo:
        return jsonify({"error": "Selo não encontrado."}), 404
    if not selo.get("habilitado"):
        return jsonify({"error": "Selo está desabilitado."}), 400

    # Verifica se já existe vínculo (unique)
    existente = one(
        """
        SELECT id_usuario_selo
          FROM usuarios_selos
         WHERE id_usuario = %(id_usuario)s
           AND id_selo = %(id_selo)s
        """,
        {"id_usuario": id_usuario, "id_selo": id_selo}
    )
    if existente:
        return jsonify({"error": "Este usuário já possui esse selo."}), 400

    motivo = (data.get("motivo") or "").strip() or None
    origem = (data.get("origem") or "").strip() or None
    referencia = data.get("referencia")

    row = one(
        """
        INSERT INTO usuarios_selos (
            id_usuario, id_selo,
            motivo, origem, referencia,
            habilitado, created_at
        )
        VALUES (
            %(id_usuario)s, %(id_selo)s,
            %(motivo)s, %(origem)s, %(referencia)s,
            TRUE, NOW()
        )
        RETURNING id_usuario_selo, id_usuario, id_selo,
                  motivo, origem, referencia,
                  habilitado, created_at, updated_at
        """,
        {
            "id_usuario": id_usuario,
            "id_selo": id_selo,
            "motivo": motivo,
            "origem": origem,
            "referencia": referencia,
        },
    )

    return jsonify(row), 201

# --------- Listar selos de um usuário ---------
@selos_bp.get("/usuario/<uuid:id_usuario>")
@require_auth
def list_selos_usuario(id_usuario):
    """
    Listar selos de um usuário

    Lista todos os selos associados a um usuário.

    Regras de acesso:
      - Usuário comum só pode ver **os próprios** selos.
      - Usuários com permissão **ADMIN** ou **PROFESSOR** podem ver
        os selos de **qualquer** usuário.

    Retorno:
      - Informações do vínculo (usuarios_selos)
      - Metadados do selo (selos)

    ---
    tags:
      - Selos
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
        description: "ID do usuário cujos selos serão listados"

    responses:
      200:
        description: Lista de selos do usuário
        schema:
          type: array
          items:
            type: object
            properties:
              id_usuario_selo:
                type: string
                format: uuid
              id_usuario:
                type: string
                format: uuid
              id_selo:
                type: string
                format: uuid
              motivo:
                type: string
              origem:
                type: string
                description: "Origem da atribuição (PROJETO, ATIVIDADE, MANUAL, etc.)"
              referencia:
                type: object
                description: "JSON com referências adicionais (id_projeto, id_atividade, etc.)"
              habilitado:
                type: boolean
              created_at:
                type: string
                format: date-time
              updated_at:
                type: string
                format: date-time

              # Dados do selo
              titulo:
                type: string
                description: "Título do selo"
              slug:
                type: string
              selo_descricao:
                type: string
                description: "Descrição do selo"
              icone:
                type: string
                description: "Nome do ícone (frontend)"
              cor_inicio:
                type: string
                description: "Cor inicial do gradiente (ex: #22c55e)"
              cor_fim:
                type: string
                description: "Cor final do gradiente (ex: #a3e635)"
              tipo:
                type: string
              ordem:
                type: integer
                description: "Ordem de exibição do selo"

      401:
        description: "Usuário não autenticado"
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Usuário não autenticado"

      403:
        description: "Tentativa de usuário comum acessar selos de outro usuário"
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Você não pode ver selos de outro usuário."

      404:
        description: "Usuário não encontrado (se desejar validar antes)"
    """
    user_id = getattr(g, "user_id", None)
    is_admin_prof = _is_admin_or_professor()

    if not is_admin_prof and str(user_id) != str(id_usuario):
        return jsonify({"error": "Você não pode ver selos de outro usuário."}), 403

    rows = many(
        """
        SELECT us.id_usuario_selo,
               us.id_usuario,
               us.id_selo,
               us.motivo,
               us.origem,
               us.referencia,
               us.habilitado,
               us.created_at,
               us.updated_at,

               s.titulo,
               s.slug,
               s.descricao AS selo_descricao,
               s.icone,
               s.cor_inicio,
               s.cor_fim,
               s.tipo,
               s.ordem
          FROM usuarios_selos us
          JOIN selos s ON s.id_selo = us.id_selo
         WHERE us.id_usuario = %(id_usuario)s
         ORDER BY us.created_at DESC
        """,
        {"id_usuario": id_usuario},
    )

    return jsonify(rows), 200

# --------- Desabilitar (revogar) selo de um usuário ---------
@selos_bp.patch("/usuario/<uuid:id_usuario_selo>/disable")
@require_auth
def disable_usuario_selo(id_usuario_selo):
    """
    Revogar selo de um usuário

    Desabilita (revoga) um vínculo de selo atribuído a um usuário.
    O vínculo continua existindo no banco, mas marcado como `habilitado = FALSE`.

    Apenas ADMIN/PROFESSOR.

    ---
    tags:
      - Selos
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
        name: id_usuario_selo
        required: true
        type: string
        format: uuid
        description: "ID do vínculo (usuarios_selos.id_usuario_selo) a ser revogado"

    responses:
      200:
        description: "Selo revogado do usuário com sucesso"
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Selo revogado do usuário com sucesso."
            id_usuario_selo:
              type: string
              format: uuid
            id_usuario:
              type: string
              format: uuid
            id_selo:
              type: string
              format: uuid
            habilitado:
              type: boolean
              example: false

      403:
        description: "Sem permissão para revogar selo"
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Permissão negada."

      404:
        description: "Vínculo usuário-selo não encontrado"
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Vínculo usuário-selo não encontrado."
    """
    if not _is_admin_or_professor():
        return jsonify({"error": "Permissão negada."}), 403

    row = one(
        """
        UPDATE usuarios_selos
           SET habilitado = FALSE,
               updated_at = NOW()
         WHERE id_usuario_selo = %(id)s
        RETURNING id_usuario_selo, id_usuario, id_selo, habilitado
        """,
        {"id": id_usuario_selo},
    )

    if not row:
        return jsonify({"error": "Vínculo usuário-selo não encontrado."}), 404

    return jsonify({
        "message": "Selo revogado do usuário com sucesso.",
        **row
    }), 200

# -----------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------
