from flask import Blueprint, request, jsonify, g
from ..models.db import run, many, one
from ..models.auth import require_auth

cursos_bp = Blueprint("cursos", __name__)


def _parse_periodo(value):
    if value is None:
        return None
    try:
        v = int(value)
    except (TypeError, ValueError):
        return "INVALID"
    return v if v >= 0 else "INVALID"


def _parse_lista_periodos(value):
    """
    Valida/normaliza lista_periodos vinda do JSON.
    Esperado: list de strings. Se None, retorna None.
    """
    if value is None:
        return None
    if not isinstance(value, list):
        return "INVALID"
    # Garante que tudo é string
    return [str(item) for item in value]


def _generate_lista_periodos_from_int(qtd):
    """
    Gera ["1º Período", "2º Período", ..., "Nº Período"] a partir de um inteiro.
    """
    if not isinstance(qtd, int) or qtd <= 0:
        return []
    return [f"{i}º Período" for i in range(1, qtd + 1)]


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


@cursos_bp.post("/")
@require_auth
def create_curso():
    """
    Criação de curso

    Cria um novo curso com nome, descrição, quantidade de períodos e/ou lista de períodos.
    Requer usuário com permissao 'admin'.

    ---
    tags:
      - Cursos
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
        description: "Token JWT no formato: Bearer <token>"
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - nome
          properties:
            nome:
              type: string
              description: "Nome do curso"
            descricao:
              type: string
              description: "Descrição do curso"
            periodo:
              type: integer
              description: "Quantidade de períodos (inteiro >= 0). Se enviado sem lista_periodos, será usada para gerar a lista automaticamente."
            lista_periodos:
              type: array
              items:
                type: string
              description: "Lista de períodos, ex.: ['1º Período', '2º Período', ...]. Se enviada, sobrescreve a quantidade em 'periodo'."
    responses:
      201:
        description: Curso criado com sucesso
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Curso criado com sucesso"
            curso:
              type: object
      400:
        description: Erro de validação (nome ausente ou período/lista inválidos)
      401:
        description: Não autenticado
      403:
        description: Usuário sem permissão de admin
    """
    if not _is_admin():
        return jsonify({"error": "acesso restrito a administradores"}), 403

    data = request.get_json(force=True, silent=True) or {}

    nome = data.get("nome")
    descricao = data.get("descricao")

    periodo = _parse_periodo(data.get("periodo"))
    if periodo == "INVALID":
        return jsonify({"error": "O campo 'periodo' deve ser um inteiro >= 0"}), 400

    lista_periodos_raw = data.get("lista_periodos")
    if "lista_periodos" in data:
        if not isinstance(lista_periodos_raw, list):
            return jsonify({"error": "O campo 'lista_periodos' deve ser uma lista"}), 400
        lista_periodos = [str(x) for x in lista_periodos_raw]
    else:
        lista_periodos = None

    if not nome:
        return jsonify({"error": "O campo 'nome' é obrigatório"}), 400

    existe = one(
        "SELECT id_curso FROM cursos WHERE LOWER(nome) = LOWER(%(n)s)",
        {"n": nome}
    )
    if existe:
        return jsonify({"error": "Já existe um curso cadastrado com esse nome"}), 409

    if lista_periodos is not None:
        periodo = len(lista_periodos)
    elif periodo is not None:
        lista_periodos = [f"{i}º Período" for i in range(1, periodo + 1)]
    else:
        periodo = 0
        lista_periodos = []

    row = run(
        """
        INSERT INTO cursos (nome, descricao, periodo, lista_periodos)
        VALUES (%(n)s, %(d)s, %(p)s, %(lp)s)
        RETURNING id_curso, nome, descricao, periodo, lista_periodos, habilitado
        """,
        {
            "n": nome,
            "d": descricao,
            "p": periodo,
            "lp": lista_periodos,
        }
    )

    return jsonify({"message": "Curso criado com sucesso", "curso": row}), 201

@cursos_bp.get("/")
def list_cursos():
    """
    Listagem de cursos

    Retorna todos os cursos habilitados, incluindo uma lista legível de períodos.

    ---
    tags:
      - Cursos
    produces:
      - application/json
    responses:
      200:
        description: Lista de cursos habilitados
        schema:
          type: array
          items:
            type: object
            properties:
              id_curso:
                type: string
                format: uuid
              nome:
                type: string
              descricao:
                type: string
              periodo:
                type: integer
              lista_periodos:
                type: array
                items:
                  type: string
                description: "Lista com textos como '1º Período', '2º Período', etc."
              habilitado:
                type: boolean
              created_at:
                type: string
                format: date-time
    """
    headers_dict = dict(request.headers)
    print(f"[CURSOS] - Headers: {headers_dict}")

    rows = many(
        """
        SELECT id_curso, nome, descricao, periodo, lista_periodos, habilitado, created_at
        FROM cursos
        WHERE habilitado = TRUE
        ORDER BY created_at DESC
        """
    )

    # Garante lista_periodos sempre preenchida na resposta
    for row in rows:
        qtd = row.get("periodo")
        lp = row.get("lista_periodos")

        if lp is None or len(lp) == 0:
            row["lista_periodos"] = _generate_lista_periodos_from_int(qtd if isinstance(qtd, int) else 0)

    return jsonify(rows), 200


@cursos_bp.get("/<uuid:id_curso>")
def get_curso(id_curso):
    """
    Detalhes de um curso

    Retorna os dados de um curso específico pelo seu id_curso.

    ---
    tags:
      - Cursos
    produces:
      - application/json
    parameters:
      - in: path
        name: id_curso
        required: true
        type: string
        format: uuid
        description: "ID do curso (UUID)"
    responses:
      200:
        description: Curso encontrado
        schema:
          type: object
      404:
        description: Curso não encontrado
    """

    headers_dict = dict(request.headers)
    print(f"[CURSOS][ID] - Headers: {headers_dict}")
    print(f"[CURSOS][ID] - ID_CURSO: {id_curso}")

    id_str = str(id_curso)

    row = one(
        """
        SELECT id_curso, nome, descricao, periodo, lista_periodos, habilitado, created_at, updated_at
        FROM cursos
        WHERE id_curso = %(id)s
        """,
        {"id": id_str}
    )

    if not row:
        return jsonify({"error": "Curso não encontrado"}), 404

    qtd = row.get("periodo")
    lp = row.get("lista_periodos")
    if lp is None or len(lp) == 0:
        row["lista_periodos"] = _generate_lista_periodos_from_int(qtd if isinstance(qtd, int) else 0)

    return jsonify(row), 200


@cursos_bp.put("/<uuid:id_curso>")
@require_auth
def update_curso(id_curso):
    """
    Atualização de curso

    Atualiza dados de um curso (nome, descrição, periodo e/ou lista_periodos).
    Requer usuário com permissao 'admin'.

    ---
    tags:
      - Cursos
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
        description: "Token JWT no formato: Bearer <token>"
      - in: path
        name: id_curso
        required: true
        type: string
        format: uuid
        description: "ID do curso (UUID)"
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            nome:
              type: string
            descricao:
              type: string
            periodo:
              type: integer
              description: "Quantidade de períodos (inteiro >= 0). Se enviado sem lista_periodos, será usada para gerar a lista automaticamente."
            lista_periodos:
              type: array
              items:
                type: string
              description: "Lista de períodos, ex.: ['1º Período', '2º Período', ...]. Se enviada, define o valor de 'periodo' como o tamanho da lista."
    responses:
      200:
        description: Curso atualizado com sucesso
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Curso atualizado com sucesso"
      400:
        description: Período ou lista de períodos inválidos
      401:
        description: Não autenticado
      403:
        description: Usuário sem permissão de admin
      404:
        description: Curso não encontrado
    """
    if not _is_admin():
        return jsonify({"error": "acesso restrito a administradores"}), 403

    data = request.get_json(force=True, silent=True) or {}
    nome = data.get("nome")
    descricao = data.get("descricao")

    periodo = None
    lista_periodos = None

    # periodo (se foi enviado no body)
    if "periodo" in data:
        periodo = _parse_periodo(data.get("periodo"))
        if periodo == "INVALID":
            return jsonify({"error": "O campo 'periodo' deve ser um inteiro >= 0"}), 400

    # lista_periodos (se foi enviado no body)
    if "lista_periodos" in data:
        lista_periodos_raw = data.get("lista_periodos")
        lista_periodos = _parse_lista_periodos(lista_periodos_raw)
        if lista_periodos == "INVALID":
            return jsonify({"error": "O campo 'lista_periodos' deve ser uma lista de strings"}), 400

    # Regras de consistência na atualização:
    # - Se vier lista_periodos: periodo := len(lista_periodos)
    # - Se vier só periodo: lista_periodos := gerada
    # - Se não vier nenhum dos dois: ambos ficam None (não altera esses campos)
    if lista_periodos is not None:
        periodo = len(lista_periodos)
    elif periodo is not None:
        lista_periodos = _generate_lista_periodos_from_int(periodo)

    id_str = str(id_curso)

    curso = one(
        "SELECT id_curso FROM cursos WHERE id_curso = %(id)s",
        {"id": id_str}
    )
    if not curso:
        return jsonify({"error": "Curso não encontrado"}), 404

    run(
        """
        UPDATE cursos
           SET nome           = COALESCE(%(n)s, nome),
               descricao      = COALESCE(%(d)s, descricao),
               periodo        = COALESCE(%(p)s, periodo),
               lista_periodos = COALESCE(%(lp)s, lista_periodos),
               updated_at     = NOW()
         WHERE id_curso = %(id)s
        """,
        {
            "n": nome,
            "d": descricao,
            "p": periodo,
            "lp": lista_periodos,
            "id": id_str,
        }
    )

    return jsonify({"message": "Curso atualizado com sucesso"}), 200


@cursos_bp.put("/<uuid:id_curso>/disable")
@require_auth
def disable_curso(id_curso):
    """
    Desabilitar curso

    Marca um curso como desabilitado (habilitado = FALSE).
    Requer usuário com permissao 'admin'.

    ---
    tags:
      - Cursos
    security:
      - Bearer: []
    produces:
      - application/json
    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: "Token JWT no formato: Bearer <token>"
      - in: path
        name: id_curso
        required: true
        type: string
        format: uuid
        description: "ID do curso (UUID)"
    responses:
      200:
        description: Curso desabilitado com sucesso ou já desabilitado
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Curso desabilitado com sucesso"
      401:
        description: Não autenticado
      403:
        description: Usuário sem permissão de admin
      404:
        description: Curso não encontrado
    """
    if not _is_admin():
        return jsonify({"error": "acesso restrito a administradores"}), 403

    id_str = str(id_curso)

    curso = one(
        "SELECT habilitado FROM cursos WHERE id_curso = %(id)s",
        {"id": id_str}
    )

    if not curso:
        return jsonify({"error": "Curso não encontrado"}), 404

    run(
        """
        UPDATE cursos
           SET habilitado = FALSE,
               updated_at = NOW()
         WHERE id_curso = %(id)s
        """,
        {"id": id_str}
    )

    return jsonify({"message": "Curso desabilitado com sucesso"}), 200


@cursos_bp.put("/<uuid:id_curso>/enable")
@require_auth
def enable_curso(id_curso):
    """
    Habilitar curso

    Marca um curso como habilitado (habilitado = TRUE).
    Requer usuário com permissao 'admin'.

    ---
    tags:
      - Cursos
    security:
      - Bearer: []
    produces:
      - application/json
    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: "Token JWT no formato: Bearer <token>"
      - in: path
        name: id_curso
        required: true
        type: string
        format: uuid
        description: "ID do curso (UUID)"
    responses:
      200:
        description: Curso habilitado com sucesso ou já habilitado
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Curso habilitado com sucesso"
      401:
        description: Não autenticado
      403:
        description: Usuário sem permissão de admin
      404:
        description: Curso não encontrado
    """
    if not _is_admin():
        return jsonify({"error": "acesso restrito a administradores"}), 403

    id_str = str(id_curso)

    curso = one(
        "SELECT habilitado FROM cursos WHERE id_curso = %(id)s",
        {"id": id_str}
    )

    if not curso:
        return jsonify({"error": "Curso não encontrado"}), 404

    if curso["habilitado"]:
        return jsonify({"message": "Curso já está habilitado"}), 200

    run(
        """
        UPDATE cursos
           SET habilitado = TRUE,
               updated_at = NOW()
         WHERE id_curso = %(id)s
        """,
        {"id": id_str}
    )

    return jsonify({"message": "Curso habilitado com sucesso"}), 200
