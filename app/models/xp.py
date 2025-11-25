# app/models/xp.py
from ..models.db import one, run
from psycopg2.extras import Json

def registrar_historico_xp(
    id_usuario,
    delta_xp,
    xp_antes,
    xp_depois,
    motivo=None,
    origem=None,
    referencia=None,
    id_responsavel=None,
):
    """
    Registra uma linha na tabela usuarios_xp_historico.
    referencia pode ser dict, será salva como JSONB.
    """
    referencia_db = Json(referencia) if referencia is not None else None

    run("""
        INSERT INTO usuarios_xp_historico (
            id_usuario,
            delta_xp,
            xp_antes,
            xp_depois,
            motivo,
            origem,
            referencia,
            id_responsavel
        )
        VALUES (
            %(id_usuario)s,
            %(delta_xp)s,
            %(xp_antes)s,
            %(xp_depois)s,
            %(motivo)s,
            %(origem)s,
            %(referencia)s,
            %(id_responsavel)s
        )
    """, {
        "id_usuario": id_usuario,
        "delta_xp": delta_xp,
        "xp_antes": xp_antes,
        "xp_depois": xp_depois,
        "motivo": motivo,
        "origem": origem,
        "referencia": referencia_db,
        "id_responsavel": id_responsavel,
    })

def atualizar_level_por_xp(id_usuario):
    """
    Calcula o level do usuário com base em xp_total e atualiza id_level_atual.
    Retorna um dicionário { "usuario": ..., "level": ... }.
    """
    usuario = one("""
        SELECT id_usuario, nome, email, xp_total, id_level_atual
          FROM usuarios
         WHERE id_usuario = %(id)s
    """, {"id": id_usuario})

    if not usuario:
        return None  # usuário não encontrado

    xp = usuario.get("xp_total") or 0

    level = one("""
        SELECT id_level, titulo, tag, nivel, xp_min, xp_max, descricao
          FROM levels
         WHERE xp_min <= %(xp)s
           AND (xp_max IS NULL OR xp_max >= %(xp)s)
           AND habilitado = TRUE
         ORDER BY xp_min DESC
         LIMIT 1
    """, {"xp": xp})

    # Se não encontrou nenhum nível compatível, zera o id_level_atual
    if not level:
        updated_user = one("""
            UPDATE usuarios
               SET id_level_atual = NULL,
                   updated_at     = NOW()
             WHERE id_usuario = %(id)s
         RETURNING id_usuario, nome, email, xp_total, id_level_atual
        """, {"id": id_usuario})

        return {
            "usuario": updated_user,
            "level": None
        }

    # Atualiza o usuário com o nível encontrado
    updated_user = one("""
        UPDATE usuarios
           SET id_level_atual = %(id_level)s,
               updated_at     = NOW()
         WHERE id_usuario = %(id)s
     RETURNING id_usuario, nome, email, xp_total, id_level_atual
    """, {
        "id": id_usuario,
        "id_level": level["id_level"]
    })

    return {
        "usuario": updated_user,
        "level": level
    }

def definir_xp_usuario(
    id_usuario,
    novo_xp,
    motivo=None,
    origem=None,
    referencia=None,
    id_responsavel=None,
):
    """
    Define o xp_total do usuário com um valor específico
    e já recalcula o level, registrando histórico.
    """
    # Busca XP atual para poder salvar xp_antes
    usuario = one("""
        SELECT xp_total
          FROM usuarios
         WHERE id_usuario = %(id)s
    """, {"id": id_usuario})

    if not usuario:
        return None

    xp_antes = usuario.get("xp_total") or 0
    xp_depois = int(novo_xp)
    delta_xp = xp_depois - xp_antes

    row = one("""
        UPDATE usuarios
           SET xp_total  = %(xp)s,
               updated_at = NOW()
         WHERE id_usuario = %(id)s
     RETURNING id_usuario
    """, {
        "xp": xp_depois,
        "id": id_usuario
    })

    if not row:
        return None

    # registra histórico
    registrar_historico_xp(
        id_usuario=id_usuario,
        delta_xp=delta_xp,
        xp_antes=xp_antes,
        xp_depois=xp_depois,
        motivo=motivo,
        origem=origem,
        referencia=referencia,
        id_responsavel=id_responsavel,
    )

    return atualizar_level_por_xp(id_usuario)

def adicionar_xp_usuario(
    id_usuario,
    delta_xp,
    motivo=None,
    origem=None,
    referencia=None,
    id_responsavel=None,
):
    """
    Soma delta_xp ao xp_total do usuário e recalcula o level.
    Aceita valores positivos (ganho de XP) e negativos (perda).
    Também registra histórico.
    """
    # Primeiro pega o XP atual
    usuario = one("""
        SELECT xp_total
          FROM usuarios
         WHERE id_usuario = %(id)s
    """, {"id": id_usuario})

    if not usuario:
        return None

    xp_antes = usuario.get("xp_total") or 0
    delta_xp = int(delta_xp)
    xp_depois = xp_antes + delta_xp

    row = one("""
        UPDATE usuarios
           SET xp_total  = %(xp)s,
               updated_at = NOW()
         WHERE id_usuario = %(id)s
     RETURNING id_usuario, xp_total
    """, {
        "xp": xp_depois,
        "id": id_usuario
    })

    if not row:
        return None

    # registra histórico
    registrar_historico_xp(
        id_usuario=id_usuario,
        delta_xp=delta_xp,
        xp_antes=xp_antes,
        xp_depois=xp_depois,
        motivo=motivo,
        origem=origem,
        referencia=referencia,
        id_responsavel=id_responsavel,
    )

    return atualizar_level_por_xp(id_usuario)

def recalcular_xp_e_level_por_historico(id_usuario):
    """
    Recalcula o xp_total do usuário com base no histórico (usuarios_xp_historico)
    e, em seguida, recalcula e atualiza o level.

    Retorna o mesmo formato de atualizar_level_por_xp:
    {
      "usuario": { ... },
      "level": { ... } ou None
    }
    """
    # Verifica se o usuário existe
    usuario = one("""
        SELECT id_usuario
          FROM usuarios
         WHERE id_usuario = %(id)s
    """, {"id": id_usuario})

    if not usuario:
        return None

    # Soma todo o delta_xp do histórico
    row = one("""
        SELECT COALESCE(SUM(delta_xp), 0) AS xp_total
          FROM usuarios_xp_historico
         WHERE id_usuario = %(id)s
    """, {"id": id_usuario})

    novo_xp = (row or {}).get("xp_total", 0) or 0

    # Atualiza o xp_total do usuário sem registrar novo histórico
    run("""
        UPDATE usuarios
           SET xp_total  = %(xp)s,
               updated_at = NOW()
         WHERE id_usuario = %(id)s
    """, {
        "xp": novo_xp,
        "id": id_usuario
    })

    # Agora recalcula o level normalmente
    return atualizar_level_por_xp(id_usuario)
