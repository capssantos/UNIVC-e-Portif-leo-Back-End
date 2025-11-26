# app/routes/missoes_routes.py
import os
from flask import Blueprint, request, jsonify, g
from dotenv import load_dotenv
from ..models.db import one, many, run
from ..models.auth import require_auth
from ..models.xp import adicionar_xp_usuario

load_dotenv()

missoes_bp = Blueprint("missoes", __name__, url_prefix="/missoes")

def _is_admin_or_professor():
    """
    Verifica se o usuário autenticado possui permissão suficiente
    para gerenciar missões. Permissões válidas: ADMIN, PROFESSOR.
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

@missoes_bp.get("")
@require_auth
def list_missoes():
    """
    Listar missões

    Retorna a lista de missões cadastradas, com suporte a filtros por tag
    e opção para exibir missões desabilitadas.

    Query params opcionais:
      - tag=RAPIDA
      - include_disabled=true

    ---
    tags:
      - Missões
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
        name: tag
        required: false
        type: string
        description: "Filtra missões por tag (ex.: RAPIDA, DIARIA, SEMANAL)"

      - in: query
        name: include_disabled
        required: false
        type: boolean
        default: false
        description: "Se true, retorna também missões desabilitadas (habilitado = FALSE)"

    responses:
      200:
        description: Lista de missões encontradas
        schema:
          type: array
          items:
            type: object
            properties:
              id_missao:
                type: string
                format: uuid
              titulo:
                type: string
              descricao:
                type: string
              tag:
                type: string
                example: "RAPIDA"
              xp_reward:
                type: integer
                example: 50
              ordem:
                type: integer
                example: 1
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
    """
    tag = request.args.get("tag")
    include_disabled = request.args.get("include_disabled", "false").lower() == "true"

    params = {}
    where_clauses = []

    if tag:
        where_clauses.append("tag = %(tag)s")
        params["tag"] = tag

    if not include_disabled:
        where_clauses.append("habilitado = TRUE")

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    rows = many(f"""
        SELECT id_missao, titulo, descricao, tag, xp_reward, ordem,
               habilitado, created_at, updated_at
          FROM missoes
          {where_sql}
         ORDER BY COALESCE(ordem, 9999), created_at
    """, params)

    return jsonify(rows), 200

@missoes_bp.get("/<uuid:id_missao>")
@require_auth
def get_missao(id_missao):
    """
    Detalhar missão específica

    Retorna todos os dados de uma missão a partir do seu ID.

    ---
    tags:
      - Missões
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
        name: id_missao
        required: true
        type: string
        format: uuid
        description: "ID da missão (UUID)"

    responses:
      200:
        description: "Missão encontrada com sucesso"
        schema:
          type: object
          properties:
            id_missao:
              type: string
              format: uuid
            titulo:
              type: string
            descricao:
              type: string
            tag:
              type: string
              example: "RAPIDA"
            xp_reward:
              type: integer
              example: 50
            ordem:
              type: integer
              description: "Ordem de exibição (para ordenação no front)"
            habilitado:
              type: boolean
              example: true
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time

      404:
        description: "Missão não encontrada"

      401:
        description: "Não autenticado"
    """
    row = one("""
        SELECT id_missao, titulo, descricao, tag, xp_reward, ordem,
               habilitado, created_at, updated_at
          FROM missoes
         WHERE id_missao = %(id)s
    """, {"id": id_missao})

    if not row:
        return jsonify({"error": "Missão não encontrada"}), 404

    return jsonify(row), 200

@missoes_bp.post("")
@require_auth
def create_missao():
    """
    Criar nova missão

    Cria uma nova missão no sistema.  
    Apenas usuários com permissão **ADMIN** ou **PROFESSOR** podem criar missões.

    Exemplo de body (JSON):
    {
      "titulo": "Registrar reflexão (3-5 linhas)",
      "descricao": "Aluno registra uma reflexão curta sobre a aula de hoje.",
      "tag": "RAPIDA",
      "xp_reward": 20,
      "ordem": 1
    }

    Regras:
      - `titulo` e `xp_reward` são obrigatórios.
      - `tag` pode ser usada para categorizar missões (RAPIDA, DIARIA, SEMANAL, etc.)
      - `ordem` define posição na lista (para exibição no front).

    ---
    tags:
      - Missões
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
            - xp_reward
          properties:
            titulo:
              type: string
              example: "Registrar reflexão (3-5 linhas)"
            descricao:
              type: string
              example: "Aluno registra uma reflexão curta sobre o conteúdo da aula."
            tag:
              type: string
              example: "RAPIDA"
              description: "Categoria da missão (ex.: RAPIDA, DIARIA, SEMANAL)"
            xp_reward:
              type: integer
              example: 20
              description: "Quantidade de XP atribuída ao concluir a missão"
            ordem:
              type: integer
              example: 1
              description: "Define a ordem de exibição"

    responses:
      201:
        description: "Missão criada com sucesso"
        schema:
          type: object
          properties:
            id_missao:
              type: string
              format: uuid
            titulo:
              type: string
            descricao:
              type: string
            tag:
              type: string
            xp_reward:
              type: integer
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
        description: "Erro de validação (faltando campos obrigatórios)"

      403:
        description: "Usuário não possui permissão para criar missões"
    """
    if not _is_admin_or_professor():
        return jsonify({"error": "Permissão insuficiente"}), 403

    data = request.get_json() or {}

    titulo = (data.get("titulo") or "").strip()
    xp_reward = data.get("xp_reward")

    if not titulo or xp_reward is None:
        return jsonify({
            "error": "Campos obrigatórios: titulo, xp_reward"
        }), 400

    descricao = data.get("descricao")
    tag = data.get("tag")
    ordem = data.get("ordem")

    row = one("""
        INSERT INTO missoes (titulo, descricao, tag, xp_reward, ordem)
        VALUES (%(titulo)s, %(descricao)s, %(tag)s, %(xp_reward)s, %(ordem)s)
        RETURNING id_missao, titulo, descricao, tag, xp_reward, ordem,
                  habilitado, created_at, updated_at
    """, {
        "titulo": titulo,
        "descricao": descricao,
        "tag": tag,
        "xp_reward": xp_reward,
        "ordem": ordem
    })

    return jsonify(row), 201

@missoes_bp.patch("/<uuid:id_missao>")
@require_auth
def update_missao(id_missao):
    """
    Atualizar missão

    Atualiza os dados de uma missão existente.  
    Apenas usuários com permissão **ADMIN** ou **PROFESSOR** podem alterar missões.

    Body (JSON) – todos os campos são opcionais:

    {
      "titulo": "Nova descrição curta",
      "descricao": "Texto completo explicando a missão",
      "tag": "RAPIDA",
      "xp_reward": 25,
      "ordem": 2,
      "habilitado": true
    }

    ---
    tags:
      - Missões
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
        name: id_missao
        required: true
        type: string
        format: uuid
        description: "ID da missão a ser atualizada (UUID)"

      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            titulo:
              type: string
              description: "Novo título da missão"
              example: "Registrar insight sobre a aula"
            descricao:
              type: string
              description: "Descrição detalhada da missão"
              example: "Aluno deve registrar um insight sobre o conteúdo estudado hoje."
            tag:
              type: string
              description: "Categoria da missão (ex.: RAPIDA, DIARIA, SEMANAL)"
              example: "RAPIDA"
            xp_reward:
              type: integer
              description: "XP concedido ao concluir esta missão"
              example: 25
            ordem:
              type: integer
              description: "Ordem de exibição da missão na lista"
              example: 2
            habilitado:
              type: boolean
              description: "Define se a missão está ativa/visível"
              example: true

    responses:
      200:
        description: "Missão atualizada com sucesso"
        schema:
          type: object
          properties:
            id_missao:
              type: string
              format: uuid
            titulo:
              type: string
            descricao:
              type: string
            tag:
              type: string
            xp_reward:
              type: integer
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
        description: "Nenhum campo para atualizar"

      401:
        description: "Não autenticado"

      403:
        description: "Permissão insuficiente (não ADMIN/PROFESSOR)"

      404:
        description: "Missão não encontrada"
    """
    if not _is_admin_or_professor():
        return jsonify({"error": "Permissão insuficiente"}), 403

    data = request.get_json() or {}

    campos = []
    params = {"id": id_missao}

    if "titulo" in data:
        campos.append("titulo = %(titulo)s")
        params["titulo"] = data.get("titulo")
    if "descricao" in data:
        campos.append("descricao = %(descricao)s")
        params["descricao"] = data.get("descricao")
    if "tag" in data:
        campos.append("tag = %(tag)s")
        params["tag"] = data.get("tag")
    if "xp_reward" in data:
        campos.append("xp_reward = %(xp_reward)s")
        params["xp_reward"] = data.get("xp_reward")
    if "ordem" in data:
        campos.append("ordem = %(ordem)s")
        params["ordem"] = data.get("ordem")
    if "habilitado" in data:
        campos.append("habilitado = %(habilitado)s")
        params["habilitado"] = bool(data.get("habilitado"))

    if not campos:
        return jsonify({"error": "Nenhum campo para atualizar"}), 400

    campos.append("updated_at = NOW()")

    row = one(f"""
        UPDATE missoes
           SET {", ".join(campos)}
         WHERE id_missao = %(id)s
        RETURNING id_missao, titulo, descricao, tag, xp_reward, ordem,
                  habilitado, created_at, updated_at
    """, params)

    if not row:
        return jsonify({"error": "Missão não encontrada"}), 404

    return jsonify(row), 200

@missoes_bp.patch("/<uuid:id_missao>/toggle")
@require_auth
def toggle_missao(id_missao):
    """
    Alternar estado da missão (habilitar/desabilitar)

    Alterna automaticamente o campo `habilitado` de uma missão:
    - Se estiver habilitada → será desabilitada  
    - Se estiver desabilitada → será habilitada  

    Apenas usuários com permissão **ADMIN** ou **PROFESSOR** podem executar esta ação.

    ---
    tags:
      - Missões
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
        name: id_missao
        required: true
        type: string
        format: uuid
        description: "ID da missão (UUID)"

    responses:
      200:
        description: "Estado da missão alterado com sucesso"
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Missão habilitada com sucesso."
            missao:
              type: object
              properties:
                id_missao:
                  type: string
                  format: uuid
                titulo:
                  type: string
                descricao:
                  type: string
                tag:
                  type: string
                xp_reward:
                  type: integer
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
        description: "Não autenticado"

      403:
        description: "Permissão insuficiente (não ADMIN/PROFESSOR)"

      404:
        description: "Missão não encontrada"
    """
    if not _is_admin_or_professor():
        return jsonify({"error": "Permissão insuficiente"}), 403

    row = one("""
        UPDATE missoes
           SET habilitado = NOT habilitado,
               updated_at = NOW()
         WHERE id_missao = %(id)s
        RETURNING id_missao, titulo, descricao, tag, xp_reward, ordem,
                  habilitado, created_at, updated_at
    """, {"id": id_missao})

    if not row:
        return jsonify({"error": "Missão não encontrada"}), 404

    estado = "habilitada" if row["habilitado"] else "desabilitada"

    return jsonify({
        "message": f"Missão {estado} com sucesso.",
        "missao": row
    }), 200

@missoes_bp.post("/<uuid:id_missao>/concluir")
@require_auth
def concluir_missao(id_missao):
    """
    Concluir missão para o usuário autenticado

    Marca uma missão como concluída para o usuário autenticado, registra
    a conclusão em `missoes_usuarios` e utiliza `adicionar_xp_usuario`
    para somar XP, registrar histórico e recalcular o nível do usuário.

    Regras:
      - Usuário precisa estar autenticado.
      - A missão deve existir e estar habilitada.
      - Uma missão só pode ser concluída uma vez por usuário
        (se já concluída, retorna 409).

    ---
    tags:
      - Missões
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
        name: id_missao
        required: true
        type: string
        format: uuid
        description: "ID da missão a ser concluída (UUID)"

    responses:
      201:
        description: "Missão concluída, XP somado e nível recalculado com sucesso"
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Missão concluída, XP somado e nível recalculado com sucesso."
            missao:
              type: object
              properties:
                id_missao:
                  type: string
                  format: uuid
                titulo:
                  type: string
                xp_reward:
                  type: integer
                  example: 20
            registro_missao:
              type: object
              description: "Registro na tabela missoes_usuarios"
              properties:
                id_missao_usuario:
                  type: string
                  format: uuid
                id_missao:
                  type: string
                  format: uuid
                id_usuario:
                  type: string
                  format: uuid
                concluida_em:
                  type: string
                  format: date-time
            usuario:
              type: object
              description: "Dados atualizados do usuário após a conclusão da missão"
            level:
              type: object
              description: "Level atual do usuário após o recálculo"

      400:
        description: "Missão desabilitada ou erro de regra de negócio"

      401:
        description: "Usuário não autenticado"

      404:
        description: "Missão não encontrada"

      409:
        description: "Missão já foi concluída anteriormente por este usuário"

      500:
        description: "Erro ao atualizar XP do usuário"
    """
    id_usuario = getattr(g, "user_id", None)
    if not id_usuario:
        return jsonify({"error": "Usuário não autenticado"}), 401

    # 1) Buscar missão
    missao = one("""
        SELECT id_missao, titulo, xp_reward, habilitado
          FROM missoes
         WHERE id_missao = %(id)s
    """, {"id": id_missao})

    if not missao:
        return jsonify({"error": "Missão não encontrada"}), 404

    if not missao["habilitado"]:
        return jsonify({"error": "Missão desabilitada"}), 400

    # 2) Verificar se usuário já concluiu
    ja_concluida = one("""
        SELECT id_missao_usuario, concluida_em
          FROM missoes_usuarios
         WHERE id_missao = %(id_missao)s
           AND id_usuario = %(id_usuario)s
    """, {"id_missao": id_missao, "id_usuario": id_usuario})

    if ja_concluida:
        return jsonify({
            "message": "Missão já foi concluída anteriormente.",
            "concluida_em": ja_concluida["concluida_em"]
        }), 409

    # 3) Registrar conclusão da missão
    registro = one("""
        INSERT INTO missoes_usuarios (id_missao, id_usuario)
        VALUES (%(id_missao)s, %(id_usuario)s)
        RETURNING id_missao_usuario, id_missao, id_usuario, concluida_em
    """, {"id_missao": id_missao, "id_usuario": id_usuario})

    # 4) Somar XP + registrar histórico + recalcular level
    result_xp = adicionar_xp_usuario(
        id_usuario=id_usuario,
        delta_xp=missao["xp_reward"],
        motivo=f"Conclusão da missão: {missao['titulo']}",
        origem="MISSAO",
        referencia={
            "id_missao": str(missao["id_missao"]),
            "titulo_missao": missao["titulo"]
        },
        # se quiser registrar quem deu o XP:
        id_responsavel=id_usuario  # ou None se preferir “sistema”
    )

    if not result_xp:
        # em teoria só cai aqui se o usuário tiver sido apagado no meio do caminho
        return jsonify({"error": "Não foi possível atualizar XP do usuário"}), 500

    return jsonify({
        "message": "Missão concluída, XP somado e nível recalculado com sucesso.",
        "missao": {
            "id_missao": missao["id_missao"],
            "titulo": missao["titulo"],
            "xp_reward": missao["xp_reward"],
        },
        "registro_missao": registro,
        "usuario": result_xp["usuario"],
        "level": result_xp["level"]
    }), 201

@missoes_bp.get("/minhas")
@require_auth
def minhas_missoes():
    """
    Listar missões do usuário autenticado

    Retorna as missões disponíveis para o usuário autenticado, indicando
    se já foram concluídas ou não.

    Por padrão, **não** traz missões já concluídas.  
    Use o query param `show_completed=true` para incluí-las.

    Exemplo de uso:
      - `GET /missoes/minhas`
      - `GET /missoes/minhas?show_completed=true`

    ---
    tags:
      - Missões
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
        name: show_completed
        required: false
        type: boolean
        default: false
        description: >
          Se true, inclui missões já concluídas pelo usuário.
          Se false (padrão), retorna apenas missões ainda não concluídas.

    responses:
      200:
        description: "Lista de missões do usuário autenticado, com status de conclusão"
        schema:
          type: array
          items:
            type: object
            properties:
              id_missao:
                type: string
                format: uuid
              titulo:
                type: string
              descricao:
                type: string
              tag:
                type: string
                example: "RAPIDA"
              xp_reward:
                type: integer
                example: 20
              ordem:
                type: integer
                example: 1
              habilitado:
                type: boolean
              created_at:
                type: string
                format: date-time
              updated_at:
                type: string
                format: date-time
              concluida:
                type: boolean
                description: "Indica se o usuário já concluiu esta missão"
                example: false
              concluida_em:
                type: string
                format: date-time
                nullable: true
                description: "Data/hora de conclusão da missão (se concluída)"
      401:
        description: "Usuário não autenticado"
    """
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "Usuário não autenticado"}), 401

    show_completed = request.args.get("show_completed", "false").lower() == "true"

    params = {"id_usuario": user_id}
    where_extra = "WHERE m.habilitado = TRUE"

    if not show_completed:
        # esconde concluídas
        where_extra += " AND mu.id_missao_usuario IS NULL"

    rows = many(f"""
        SELECT
            m.id_missao,
            m.titulo,
            m.descricao,
            m.tag,
            m.xp_reward,
            m.ordem,
            m.habilitado,
            m.created_at,
            m.updated_at,
            (mu.id_missao_usuario IS NOT NULL) AS concluida,
            mu.concluida_em
        FROM missoes m
        LEFT JOIN missoes_usuarios mu
               ON mu.id_missao = m.id_missao
              AND mu.id_usuario = %(id_usuario)s
        {where_extra}
        ORDER BY COALESCE(m.ordem, 9999), m.created_at
    """, params)

    return jsonify(rows), 200

@missoes_bp.get("/<uuid:id_missao>/relatorio")
@require_auth
def relatorio_missao(id_missao):
    """
    Relatório de usuários que concluíram uma missão

    Retorna os dados da missão e a lista de usuários que já concluíram
    essa missão, com data/hora de conclusão.

    Apenas usuários com permissão **ADMIN** ou **PROFESSOR** podem acessar
    este relatório.

    ---
    tags:
      - Missões
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
        name: id_missao
        required: true
        type: string
        format: uuid
        description: "ID da missão (UUID) a ser consultada"

    responses:
      200:
        description: "Relatório de usuários que concluíram a missão"
        schema:
          type: object
          properties:
            missao:
              type: object
              properties:
                id_missao:
                  type: string
                  format: uuid
                titulo:
                  type: string
                xp_reward:
                  type: integer
            total_concluida:
              type: integer
              description: "Quantidade total de usuários que concluíram a missão"
              example: 12
            usuarios:
              type: array
              description: "Lista de usuários que concluíram a missão"
              items:
                type: object
                properties:
                  id_usuario:
                    type: string
                    format: uuid
                  nome:
                    type: string
                  email:
                    type: string
                  concluida_em:
                    type: string
                    format: date-time
      401:
        description: "Não autenticado"
      403:
        description: "Permissão insuficiente (não ADMIN/PROFESSOR)"
      404:
        description: "Missão não encontrada"
    """
    if not _is_admin_or_professor():
        return jsonify({"error": "Permissão insuficiente"}), 403

    missao = one("""
        SELECT id_missao, titulo, xp_reward
          FROM missoes
         WHERE id_missao = %(id)s
    """, {"id": id_missao})

    if not missao:
        return jsonify({"error": "Missão não encontrada"}), 404

    rows = many("""
        SELECT
            u.id_usuario,
            u.nome,
            u.email,
            mu.concluida_em
        FROM missoes_usuarios mu
        JOIN usuarios u ON u.id_usuario = mu.id_usuario
        WHERE mu.id_missao = %(id_missao)s
        ORDER BY mu.concluida_em ASC
    """, {"id_missao": id_missao})

    return jsonify({
        "missao": missao,
        "total_concluida": len(rows),
        "usuarios": rows
    }), 200
