import os, uuid, time, ipaddress
from datetime import datetime, timedelta, timezone
import jwt
from ..models.db import one, run

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALG    = os.getenv("JWT_ALG", "HS256")
JWT_ISS    = os.getenv("JWT_ISS", "univc-auth")
JWT_AUD    = os.getenv("JWT_AUD", "univc-api")
ACCESS_TTL = int(os.getenv("ACCESS_TTL", "900"))
REFRESH_TTL= int(os.getenv("REFRESH_TTL", "2592000"))

UTC = timezone.utc

def _now():
    return datetime.now(tz=UTC)

def _to_ts(dt: datetime) -> int:
    return int(dt.timestamp())

def _insert_token(*, user_id, jti, token_type, aud, iss, sub, iat, exp,
                  session_id=None, ip=None, user_agent=None, metadata=None):
    return run(
        """
        INSERT INTO jwt_tokens (
            user_id, jti, token_type, audience, issuer, subject,
            issued_at, expires_at, session_id, ip, user_agent, metadata
        )
        VALUES (
            %(user_id)s, %(jti)s, %(token_type)s, %(aud)s, %(iss)s, %(sub)s,
            %(iat)s, %(exp)s, %(session_id)s, %(ip)s, %(user_agent)s, COALESCE(%(metadata)s, '{}'::jsonb)
        )
        RETURNING id
        """,
        dict(
            user_id=user_id, jti=jti, token_type=token_type, aud=aud, iss=iss, sub=sub,
            iat=iat, exp=exp, session_id=session_id, ip=ip, user_agent=user_agent, metadata=metadata
        )
    )

def _revoke_by_jti(jti: str, reason: str|None = None, user_id=None):
    run(
        "UPDATE jwt_tokens SET revoked_at = NOW(), revoked_reason = %(reason)s WHERE jti = %(jti)s AND revoked_at IS NULL",
        {"jti": jti, "reason": reason}
    )
    run(
        "INSERT INTO jwt_revocations (jti, user_id, reason) VALUES (%(jti)s, %(user_id)s, %(reason)s)",
        {"jti": jti, "user_id": user_id, "reason": reason}
    )

def _is_revoked(jti: str) -> bool:
    row = one("SELECT revoked_at FROM jwt_tokens WHERE jti = %(jti)s", {"jti": jti})
    return bool(row and row["revoked_at"] is not None)

def _validate_common_claims(payload: dict, *, expected_typ: str):
    # valida emissor/audiência/tipo
    if payload.get("iss") != JWT_ISS:
        raise jwt.InvalidIssuerError("issuer inválido")
    aud = payload.get("aud")
    if isinstance(aud, list):
        valid_aud = JWT_AUD in aud
    else:
        valid_aud = aud == JWT_AUD
    if not valid_aud:
        raise jwt.InvalidAudienceError("audience inválida")
    if payload.get("typ") != expected_typ:
        raise jwt.InvalidTokenError("tipo de token inválido")
    # exp/iat checados pelo PyJWT ao decodificar (options default)

def create_token_pair(*, user_id: str, session_id: str|None, subject: str, ip: str|None, user_agent: str|None):
    now = _now()
    iat = now
    access_exp  = now + timedelta(seconds=ACCESS_TTL)
    refresh_exp = now + timedelta(seconds=REFRESH_TTL)

    access_jti  = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())

    access_payload = {
        "iss": JWT_ISS,
        "aud": JWT_AUD,
        "sub": subject,      # normalmente o id do usuário ou email
        "typ": "access",
        "jti": access_jti,
        "sid": session_id,
        "iat": _to_ts(iat),
        "nbf": _to_ts(iat),
        "exp": _to_ts(access_exp),
        "uid": user_id
    }
    refresh_payload = {
        "iss": JWT_ISS,
        "aud": JWT_AUD,
        "sub": subject,
        "typ": "refresh",
        "jti": refresh_jti,
        "sid": session_id,
        "iat": _to_ts(iat),
        "nbf": _to_ts(iat),
        "exp": _to_ts(refresh_exp),
        "uid": user_id
    }

    access_token  = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALG)
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALG)

    # persistência
    _insert_token(
        user_id=user_id, jti=access_jti, token_type="access", aud=JWT_AUD, iss=JWT_ISS,
        sub=subject, iat=iat, exp=access_exp, session_id=session_id, ip=ip, user_agent=user_agent
    )
    _insert_token(
        user_id=user_id, jti=refresh_jti, token_type="refresh", aud=JWT_AUD, iss=JWT_ISS,
        sub=subject, iat=iat, exp=refresh_exp, session_id=session_id, ip=ip, user_agent=user_agent
    )

    return access_token, refresh_token

def decode_and_validate(token: str, *, expected_typ: str):
    # decodifica e valida assinatura/exp/iat
    payload = jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALG],
        audience=JWT_AUD,
        options={"require": ["exp", "iat", "jti", "typ", "iss", "aud"]}
    )
    _validate_common_claims(payload, expected_typ=expected_typ)

    # checa revogação e existência no BD
    jti = payload.get("jti")
    row = one("SELECT id, user_id, revoked_at, expires_at FROM jwt_tokens WHERE jti = %(jti)s", {"jti": jti})
    if not row:
        raise jwt.InvalidTokenError("jti desconhecido")
    if row["revoked_at"] is not None:
        raise jwt.InvalidTokenError("token revogado")
    # (opcional) checa exp vs BD para evitar “replay” de payloads alterados
    return payload  # válido

def revoke_token(token: str, reason: str|None = "logout"):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG], options={"verify_aud": False})
        _revoke_by_jti(payload.get("jti"), reason=reason, user_id=payload.get("uid"))
        return True
    except Exception:
        return False

def refresh_tokens(refresh_token: str, *, ip=None, user_agent=None):
    payload = decode_and_validate(refresh_token, expected_typ="refresh")
    # Rotação de refresh: revoga o atual e emite novo par
    _revoke_by_jti(payload["jti"], reason="rotated", user_id=payload.get("uid"))

    return create_token_pair(
        user_id=payload.get("uid"),
        session_id=payload.get("sid"),
        subject=payload.get("sub"),
        ip=ip,
        user_agent=user_agent
    )
