import os
import uuid
from flask import Blueprint, request, jsonify, g
from dotenv import load_dotenv
from ..models.db import one, run
from ..models.crypto import hash_password, check_password
from ..models.jwt_manager import create_token_pair, refresh_tokens, revoke_token
from ..models.auth import require_auth
from ..models.digitalocean import DigitalOceanSpacesUploader
from datetime import datetime
from werkzeug.utils import secure_filename

load_dotenv()
user_bp = Blueprint("user", __name__)

DO_SPACES_KEY = os.getenv("DO_SPACES_KEY")
DO_SPACES_SECRET = os.getenv("DO_SPACES_SECRET")
DO_BUCKET = os.getenv("DO_SPACES_BUCKET", "onicode")
DO_REGION = os.getenv("DO_SPACES_REGION", "nyc3")
DO_ENDPOINT = os.getenv("DO_SPACES_ENDPOINT", "https://nyc3.digitaloceanspaces.com")
DO_CDN_BASE = os.getenv("DO_SPACES_CDN_BASE", "https://onicode.nyc3.digitaloceanspaces.com")

uploader = DigitalOceanSpacesUploader(
    access_key=DO_SPACES_KEY,
    secret_key=DO_SPACES_SECRET,
    bucket=DO_BUCKET,
    region=DO_REGION,
    endpoint=DO_ENDPOINT,
    cdn_base=DO_CDN_BASE,
    public_read=True,  # deixe True se o bucket for público
)

def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("data_nascimento inválida; use 'YYYY-MM-DD'")

# ---------- Usuários ----------

@user_bp.post("/auth/register/step1")
def register_step1():
    """
    Registro de usuário - etapa 1

    Cria o usuário básico com nome, email, contato e senha, e já retorna
    um par de tokens (access e refresh) para uso imediato.

    ---
    tags:
      - Auth
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
            - nome
            - email
            - contato
            - password
          properties:
            nome:
              type: string
            email:
              type: string
            contato:
              type: string
            password:
              type: string
    responses:
      201:
        description: Usuário criado com sucesso
        schema:
          type: object
          properties:
            message:
              type: string
              example: "ok"
            user_id:
              type: string
            new:
              type: boolean
            habilitado:
              type: boolean
            validacao:
              type: boolean
            access_token:
              type: string
            refresh_token:
              type: string
            token_type:
              type: string
              example: "Bearer"
      400:
        description: Dados obrigatórios ausentes
      409:
        description: Email já cadastrado
    """
    headers_dict = dict(request.headers)
    data = request.get_json(force=True, silent=True) or {}
    print(f"[STEP1 ] - Headers: {headers_dict}")
    print(f"[STEP1 ] - Body: {data}")
    
    nome    = data.get("nome")
    email   = data.get("email")
    contato = data.get("contato")
    senha   = data.get("password")

    if not all([nome, email, senha, contato]):
        return jsonify({"error": "nome, email, contato e password são obrigatórios"}), 400

    exists = one("SELECT 1 FROM usuarios WHERE email = %(e)s", {"e": email})
    if exists:
        return jsonify({"error": "email já cadastrado"}), 409

    hashed = hash_password(senha)

    # cria usuário com new=TRUE, habilitado=TRUE, validacao=FALSE (defaults da tabela)
    row = run("""
        INSERT INTO usuarios (nome, email, contato, password)
        VALUES (%(n)s, %(e)s, %(c)s, %(pw)s)
        RETURNING id_usuario, new, habilitado, validacao
    """, {
        "n": nome,
        "e": email,
        "c": contato,
        "pw": hashed
    })

    user_id = str(row["id_usuario"])

    # dados de contexto do request
    ip  = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua  = request.headers.get("User-Agent", "")
    sid = str(uuid.uuid4())

    # gera par de tokens já vinculado ao novo usuário
    access_token, refresh_token = create_token_pair(
        user_id=user_id,
        session_id=sid,
        subject=email,   # sub = email do usuário
        ip=ip,
        user_agent=ua
    )

    return jsonify({
        "message": "ok",
        "user_id": user_id,
        "new": row["new"],                # deve ser True
        "habilitado": row["habilitado"],  # True
        "validacao": row["validacao"],    # False (ainda não validado)
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer"
    }), 201


@user_bp.post("/auth/register/step2")
@require_auth  # se ainda não tiver JWT pronto, pode remover temporariamente
def register_step2():
    """
    Registro de usuário - etapa 2

    Completa o cadastro do usuário já criado na etapa 1, preenchendo
    dados adicionais como curso, período, anos e data de nascimento.

    Requer autenticação via Bearer token.

    ---
    tags:
      - Auth
    security:
      - Bearer: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            user_id:
              type: string
              description: "Opcional se já estiver autenticado; caso contrário pode ser informado aqui"
            nome:
              type: string
            curso:
              type: string
            periodo:
              type: string
            ano_inicio:
              type: integer
            ano_fim:
              type: integer
            data_nascimento:
              type: string
              format: date
              example: "2000-01-15"
            contato:
              type: string
            email:
              type: string
            imagem:
              type: string
    responses:
      200:
        description: Cadastro complementar atualizado com sucesso
      400:
        description: Erro de validação ou dados faltando
      404:
        description: Usuário não encontrado
      409:
        description: Email já cadastrado
    """

    headers_dict = dict(request.headers)
    data = request.get_json(force=True, silent=True) or {}
    print(f"[STEP2 ] - Headers: {headers_dict}")
    print(f"[STEP2 ] - Body: {data}")

    # Identifica o usuário
    user_id = getattr(g, "user_id", None) or data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id não informado e nenhum usuário autenticado"}), 400

    # Campos permitidos para completar o cadastro
    # (SEM password)
    allowed = {
        "nome",
        "curso",
        "periodo",
        "ano_inicio",
        "ano_fim",
        "data_nascimento",
        "contato",
        "email",
        "imagem"
    }

    payload = {k: v for k, v in data.items() if k in allowed}

    if not payload:
        return jsonify({"error": "nenhum dado para atualização"}), 400

    # Conversões / validações
    if "data_nascimento" in payload:
        try:
            payload["data_nascimento"] = _parse_date(payload["data_nascimento"])
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400

    if "ano_inicio" in payload and payload["ano_inicio"] is not None:
        try:
            payload["ano_inicio"] = int(payload["ano_inicio"])
        except Exception:
            return jsonify({"error": "ano_inicio deve ser inteiro"}), 400

    if "ano_fim" in payload and payload["ano_fim"] is not None:
        try:
            payload["ano_fim"] = int(payload["ano_fim"])
        except Exception:
            return jsonify({"error": "ano_fim deve ser inteiro"}), 400

    if payload.get("ano_inicio") is not None and payload.get("ano_fim") is not None:
        if payload["ano_fim"] < payload["ano_inicio"]:
            return jsonify({"error": "ano_fim não pode ser menor que ano_inicio"}), 400

    # Garantir email único, se for alterar
    if "email" in payload and payload["email"]:
        dup = one(
            """
            SELECT 1
              FROM usuarios
             WHERE email = %(email)s
               AND id_usuario <> %(uid)s
            """,
            {"email": payload["email"], "uid": user_id}
        )
        if dup:
            return jsonify({"error": "email já cadastrado"}), 409

    # Monta UPDATE dinâmico
    set_parts = []
    params = {"uid": user_id}

    for k, v in payload.items():
        set_parts.append(f"{k} = %({k})s")
        params[k] = v

    # Conclusão do cadastro
    set_parts.append("new = FALSE")
    set_parts.append("updated_at = NOW()")

    sql = f"""
        UPDATE usuarios
           SET {", ".join(set_parts)}
         WHERE id_usuario = %(uid)s
     RETURNING id_usuario, nome, email, contato, curso, periodo,
               ano_inicio, ano_fim, data_nascimento, imagem,
               created_at, updated_at, last_signed, new, habilitado, validacao
    """

    row = run(sql, params)

    if not row:
        return jsonify({
            "error": "usuário não encontrado ou cadastro já concluído"
        }), 404

    return jsonify({
        "message": "cadastro_complementar_ok",
        "user": row
    }), 200


@user_bp.post("/users/me/avatar")
@require_auth
def upload_avatar():
    """
    Upload de avatar do usuário

    Envia uma imagem via multipart/form-data e retorna a URL pública
    no DigitalOcean Spaces. Não altera dados no banco.

    Requer autenticação via Bearer token.

    ---
    tags:
      - Upload
    security:
      - Bearer: []
    consumes:
      - multipart/form-data
    produces:
      - application/json
    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: "Token JWT no formato: Bearer <token>"
      - in: formData
        name: imagem
        type: file
        required: true
        description: "Arquivo de imagem do avatar"
    responses:
      200:
        description: Upload realizado com sucesso
        schema:
          type: object
          properties:
            message:
              type: string
              example: "upload_ok"
            url:
              type: string
              description: "URL pública da imagem"
      400:
        description: Erro de validação ou arquivo inválido
      401:
        description: Usuário não autenticado
      500:
        description: Erro interno ao fazer upload
    """
    headers_dict = dict(request.headers)
    print(f"[AVATAR] - Headers: {headers_dict}")
    
    # Confere auth
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return jsonify({"error": "nenhum usuário autenticado"}), 401

    # Confere Content-Type
    content_type = request.content_type or ""
    if "multipart/form-data" not in content_type:
        return jsonify({"error": "Content-Type deve ser multipart/form-data"}), 400

    file = request.files.get("imagem")
    if not file:
        return jsonify({"error": "campo 'imagem' é obrigatório"}), 400

    filename = secure_filename(file.filename) if file.filename else "avatar"
    print(f"[AVATAR] - Finename: {filename}")
    file_bytes = file.read()

    if not file_bytes:
        return jsonify({"error": "arquivo de imagem vazio"}), 400

    try:
        # usa o helper do uploader para gerar key e URL pública
        _, public_url = uploader.upload_file_to_path(
            base_path="UNIVC/e-Portifoleo",
            file_bytes=file_bytes,
            filename_hint=filename,
        )
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception:
        return jsonify({"error": "erro ao fazer upload da imagem"}), 500

    return jsonify({
        "message": "upload_ok",
        "url": public_url
    }), 200


@user_bp.post("/auth/login")
def login():
    """
    Login de usuário

    Valida email e senha, e retorna um par de tokens JWT
    (access_token e refresh_token) para uso na autenticação.

    ---
    tags:
      - Auth
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
            - email
            - password
          properties:
            email:
              type: string
            password:
              type: string
    responses:
      200:
        description: Login realizado com sucesso
    """
    headers_dict = dict(request.headers)
    data = request.get_json(force=True, silent=True) or {}
    print(f"[LOGIN ] - Headers: {headers_dict}")
    print(f"[LOGIN ] - Body: {data}")

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "email e password são obrigatórios"}), 400

    user = one("""
        SELECT id_usuario, password, habilitado, validacao
        FROM usuarios
        WHERE email = %(e)s
    """, {"e": email})

    if not user or not user["habilitado"]:
        return jsonify({"error": "usuário inválido ou desabilitado"}), 401

    if not check_password(password, user["password"]):
        return jsonify({"error": "credenciais inválidas"}), 401

    # Atualiza o last_signed do usuário
    run("""
        UPDATE usuarios
        SET last_signed = NOW(), updated_at = NOW()
        WHERE id_usuario = %(id)s
    """, {"id": user["id_usuario"]})

    # Coleta informações de contexto
    ip  = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua  = request.headers.get("User-Agent", "")
    sid = str(uuid.uuid4())

    # Gera os tokens JWT
    access, refresh = create_token_pair(
        user_id=str(user["id_usuario"]),
        session_id=sid,
        subject=email,
        ip=ip,
        user_agent=ua
    )

    return jsonify({
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "Bearer"
    }), 200



@user_bp.post("/auth/refresh")
def refresh():
    """
    Refresh de token

    Recebe um refresh_token válido e retorna um novo par de tokens
    (access_token e refresh_token).

    ---
    tags:
      - Auth
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
            - refresh_token
          properties:
            refresh_token:
              type: string
    responses:
      200:
        description: Tokens renovados com sucesso
        schema:
          type: object
          properties:
            access_token:
              type: string
            refresh_token:
              type: string
            token_type:
              type: string
              example: "Bearer"
      400:
        description: refresh_token não informado
      401:
        description: Refresh inválido
    """

    headers_dict = dict(request.headers)
    data = request.get_json(force=True, silent=True) or {}
    print(f"[LOGIN ] - Headers: {headers_dict}")
    print(f"[LOGIN ] - Body: {data}")

    token = data.get("refresh_token")
    if not token:
        return jsonify({"error": "refresh_token obrigatório"}), 400
    ip  = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua  = request.headers.get("User-Agent", "")
    try:
        access, refresh_tok = refresh_tokens(token, ip=ip, user_agent=ua)
        return jsonify({"access_token": access, "refresh_token": refresh_tok, "token_type": "Bearer"}), 200
    except Exception as e:
        return jsonify({"error": "refresh inválido", "detail": str(e)}), 401


@user_bp.post("/auth/logout")
def logout():
    """
    Logout

    Revoga um token (access ou refresh). O token pode ser enviado no
    body ou no header Authorization.

    ---
    tags:
      - Auth
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: header
        name: Authorization
        required: false
        description: "Bearer <token>"
        type: string
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            token:
              type: string
              description: "Token a ser revogado"
    responses:
      200:
        description: Token revogado com sucesso
        schema:
          type: object
          properties:
            revoked:
              type: boolean
      400:
        description: Token não informado ou falha ao revogar
    """
    headers_dict = dict(request.headers)
    data = request.get_json(force=True, silent=True) or {}
    print(f"[LOGOUT] - Headers: {headers_dict}")
    print(f"[LOGOUT] - Body: {data}")

    # aceita access OU refresh, e revoga
    token = (request.get_json(silent=True) or {}).get("token") or \
            request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return jsonify({"error": "informe token no body.token ou Authorization"}), 400
    ok = revoke_token(token, reason="logout")
    return jsonify({"revoked": ok}), 200 if ok else 400


# ---------- Rota protegida ----------

@user_bp.get("/users/me")
@require_auth
def get_me():
    """
    Dados do usuário logado

    Retorna os dados completos do usuário autenticado a partir do
    token JWT enviado no header Authorization.

    ---
    tags:
      - Users
    security:
      - Bearer: []
    parameters:
      - in: header
        name: Authorization
        required: true
        type: string
        description: "Token JWT no formato: Bearer <token>"
    produces:
      - application/json
    responses:
      200:
        description: Dados do usuário retornados com sucesso
        schema:
          type: object
          properties:
            user:
              type: object
      401:
        description: Usuário não autenticado
      404:
        description: Usuário não encontrado
    """
    headers_dict = dict(request.headers)
    print(f"[ME    ] - Headers: {headers_dict}")

    user_id = g.user_id
    print(f"[ME    ] - USER_ID: {user_id}")


    row = one(
        """
        SELECT
            id_usuario,
            nome,
            email,
            contato,
            curso,
            periodo,
            ano_inicio,
            ano_fim,
            data_nascimento,
            imagem,
            created_at,
            updated_at,
            last_signed,
            new,
            habilitado,
            validacao
        FROM usuarios
        WHERE id_usuario = %(uid)s
        """,
        {"uid": user_id}
    )

    if not row:
        return jsonify({"error": "usuário não encontrado"}), 404

    return jsonify({"user": row}), 200
