# app/blueprints/levels.py
from flask import Blueprint, request, jsonify
from ..models.db import one, many, run

levels_bp = Blueprint("levels", __name__, url_prefix="/levels")

@levels_bp.get("/")
def list_levels():
    """
    Lista todos os níveis (com filtros opcionais por tag).
    """
    tag = request.args.get("tag")

    if tag:
        rows = many("""
            SELECT id_level, titulo, tag, nivel, xp_min, xp_max, descricao, habilitado,
                   created_at, updated_at
              FROM levels
             WHERE tag = %(tag)s
             ORDER BY tag, nivel
        """, {"tag": tag})
    else:
        rows = many("""
            SELECT id_level, titulo, tag, nivel, xp_min, xp_max, descricao, habilitado,
                   created_at, updated_at
              FROM levels
             WHERE habilitado = TRUE
             ORDER BY tag, nivel
        """)

    return jsonify(rows), 200


@levels_bp.get("/<uuid:id_level>")
def get_level(id_level):
    """
    Detalhes de um nível específico.
    """
    row = one("""
        SELECT id_level, titulo, tag, nivel, xp_min, xp_max, descricao, habilitado,
               created_at, updated_at
          FROM levels
         WHERE id_level = %(id)s
    """, {"id": id_level})

    if not row:
        return jsonify({"error": "Nível não encontrado"}), 404

    return jsonify(row), 200


@levels_bp.post("/")
def create_level():
    """
    Cria um novo nível/título.
    """
    data = request.get_json(force=True, silent=True) or {}

    titulo    = data.get("titulo")
    tag       = data.get("tag")
    nivel     = data.get("nivel")
    xp_min    = data.get("xp_min", 0)
    xp_max    = data.get("xp_max")
    descricao = data.get("descricao")

    if not all([titulo, tag, nivel is not None]):
        return jsonify({"error": "titulo, tag e nivel são obrigatórios"}), 400

    row = run("""
        INSERT INTO levels (titulo, tag, nivel, xp_min, xp_max, descricao)
        VALUES (%(t)s, %(tag)s, %(n)s, %(xpmin)s, %(xpmax)s, %(desc)s)
        RETURNING id_level, titulo, tag, nivel, xp_min, xp_max, descricao,
                  habilitado, created_at, updated_at
    """, {
        "t": titulo,
        "tag": tag,
        "n": nivel,
        "xpmin": xp_min,
        "xpmax": xp_max,
        "desc": descricao
    })

    return jsonify(row), 201


@levels_bp.put("/<uuid:id_level>")
@levels_bp.patch("/<uuid:id_level>")
def update_level(id_level):
    """
    Atualiza um nível/título.
    """
    data = request.get_json(force=True, silent=True) or {}

    # Monta dinamicamente os campos
    campos = []
    params = {"id": id_level}

    for field in ["titulo", "tag", "nivel", "xp_min", "xp_max", "descricao", "habilitado"]:
        if field in data:
            campos.append(f"{field} = %({field})s")
            params[field] = data[field]

    if not campos:
        return jsonify({"error": "Nenhum campo enviado para atualização"}), 400

    sql = f"""
        UPDATE levels
           SET {", ".join(campos)}, updated_at = NOW()
         WHERE id_level = %(id)s
     RETURNING id_level, titulo, tag, nivel, xp_min, xp_max, descricao,
               habilitado, created_at, updated_at
    """

    row = one(sql, params)

    if not row:
        return jsonify({"error": "Nível não encontrado"}), 404

    return jsonify(row), 200


@levels_bp.delete("/<uuid:id_level>")
def delete_level(id_level):
    """
    Desabilita (soft delete) um nível.
    """
    row = one("""
        UPDATE levels
           SET habilitado = FALSE,
               updated_at = NOW()
         WHERE id_level = %(id)s
     RETURNING id_level
    """, {"id": id_level})

    if not row:
        return jsonify({"error": "Nível não encontrado"}), 404

    return jsonify({"message": "Nível desabilitado com sucesso"}), 200
