from flask import Blueprint, request, jsonify
from ..models.db import one, many, run

user_bp = Blueprint("user", __name__)

def atualizar_level_por_xp(id_usuario):
    """
    Busca o xp_total do usuário, encontra o level correspondente
    na tabela levels e atualiza id_level_atual em usuarios.
    Retorna um dicionário com usuario e level.
    """
    usuario = one("""
        SELECT id_usuario, nome, email, xp_total, id_level_atual
          FROM usuarios
         WHERE id_usuario = %(id)s
    """, {"id": id_usuario})

    if not usuario:
        return None  # usuário não encontrado

    xp = usuario.get("xp_total", 0)

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
