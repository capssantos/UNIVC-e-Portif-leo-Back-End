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
    data = request.get_json(force=True, silent=True) or {}
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
    data = request.get_json(force=True, silent=True) or {}

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
    Upload de imagem para DigitalOcean Spaces.

    - Requer autenticação (Bearer <access_token>)
    - Espera multipart/form-data com:
        - imagem: arquivo de imagem

    Retorna:
        200 + { "url": "<url_publica_da_imagem>" }

    Não altera dados no banco.
    """

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
    data = request.get_json(force=True, silent=True) or {}
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "email e password são obrigatórios"}), 400

    user = one("SELECT id_usuario, password, habilitado, validacao FROM usuarios WHERE email=%(e)s", {"e": email})
    if not user or not user["habilitado"]: # or not user["validacao"]:
        return jsonify({"error": "usuário inválido ou desabilitado"}), 401

    if not check_password(password, user["password"]):
        return jsonify({"error": "credenciais inválidas"}), 401

    ip  = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua  = request.headers.get("User-Agent", "")
    sid = str(uuid.uuid4())

    access, refresh = create_token_pair(
        user_id=str(user["id_usuario"]),
        session_id=sid,
        subject=email,
        ip=ip,
        user_agent=ua
    )
    return jsonify({"access_token": access, "refresh_token": refresh, "token_type": "Bearer"}), 200

@user_bp.post("/auth/refresh")
def refresh():
    data = request.get_json(force=True, silent=True) or {}
    token = data.get("refresh_token")
    if not token:
        return jsonify({"error": "refresh_token obrigatório"}), 400
    ip  = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua  = request.headers.get("User-Agent", "")
    try:
        access, refresh = refresh_tokens(token, ip=ip, user_agent=ua)
        return jsonify({"access_token": access, "refresh_token": refresh, "token_type": "Bearer"}), 200
    except Exception as e:
        return jsonify({"error": "refresh inválido", "detail": str(e)}), 401

@user_bp.post("/auth/logout")
def logout():
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
    user_id = g.user_id

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


