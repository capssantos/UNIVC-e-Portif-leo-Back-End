from flask import Blueprint, request, jsonify
from ..models.db import run, many, one

cursos_bp = Blueprint("cursos", __name__)

def _parse_periodo(value):
    if value is None:
        return None
    try:
        v = int(value)
    except (TypeError, ValueError):
        return "INVALID"
    return v if v >= 0 else "INVALID"

@cursos_bp.post("/")
def create_curso():
    data = request.get_json(force=True, silent=True) or {}
    nome = data.get("nome")
    descricao = data.get("descricao")
    periodo = _parse_periodo(data.get("periodo"))

    if not nome:
        return jsonify({"error": "O campo 'nome' é obrigatório"}), 400
    if periodo == "INVALID":
        return jsonify({"error": "O campo 'periodo' deve ser um inteiro >= 0"}), 400

    row = run("""
        INSERT INTO cursos (nome, descricao, periodo)
        VALUES (%(n)s, %(d)s, %(p)s)
        RETURNING id_curso, nome, descricao, periodo, habilitado
    """, {"n": nome, "d": descricao, "p": periodo})

    return jsonify({"message": "Curso criado com sucesso", "curso": row}), 201


@cursos_bp.get("/")
def list_cursos():
    rows = many("""
        SELECT id_curso, nome, descricao, periodo, habilitado, created_at
        FROM cursos
        WHERE habilitado = TRUE
        ORDER BY created_at DESC
    """)

    # adiciona lista de períodos legível
    for row in rows:
        qtd = row.get("periodo")
        if isinstance(qtd, int) and qtd > 0:
            row["lista_periodos"] = [f"{i}º Período" for i in range(1, qtd + 1)]
        else:
            row["lista_periodos"] = []

    return jsonify(rows), 200



@cursos_bp.get("/<uuid:id_curso>")
def get_curso(id_curso):
    row = one("""
        SELECT id_curso, nome, descricao, periodo, habilitado, created_at, updated_at
        FROM cursos
        WHERE id_curso = %(id)s
    """, {"id": id_curso})

    if not row:
        return jsonify({"error": "Curso não encontrado"}), 404
    return jsonify(row), 200


@cursos_bp.put("/<uuid:id_curso>")
def update_curso(id_curso):
    data = request.get_json(force=True, silent=True) or {}
    nome = data.get("nome")
    descricao = data.get("descricao")
    periodo_raw = data.get("periodo")
    periodo = _parse_periodo(periodo_raw) if "periodo" in data else None
    if periodo == "INVALID":
        return jsonify({"error": "O campo 'periodo' deve ser um inteiro >= 0"}), 400

    curso = one("SELECT id_curso FROM cursos WHERE id_curso = %(id)s", {"id": id_curso})
    if not curso:
        return jsonify({"error": "Curso não encontrado"}), 404

    run("""
        UPDATE cursos
        SET nome = COALESCE(%(n)s, nome),
            descricao = COALESCE(%(d)s, descricao),
            periodo = COALESCE(%(p)s, periodo),
            updated_at = NOW()
        WHERE id_curso = %(id)s
    """, {"n": nome, "d": descricao, "p": periodo, "id": id_curso})

    return jsonify({"message": "Curso atualizado com sucesso"}), 200


@cursos_bp.put("/<uuid:id_curso>/disable")
def disable_curso(id_curso):
    curso = one("SELECT habilitado FROM cursos WHERE id_curso = %(id)s", {"id": id_curso})
    if not curso:
        return jsonify({"error": "Curso não encontrado"}), 404
    if not curso["habilitado"]:
        return jsonify({"message": "Curso já está desabilitado"}), 200

    run("""
        UPDATE cursos
        SET habilitado = FALSE, updated_at = NOW()
        WHERE id_curso = %(id)s
    """, {"id": id_curso})
    return jsonify({"message": "Curso desabilitado com sucesso"}), 200


@cursos_bp.put("/<uuid:id_curso>/enable")
def enable_curso(id_curso):
    curso = one("SELECT habilitado FROM cursos WHERE id_curso = %(id)s", {"id": id_curso})
    if not curso:
        return jsonify({"error": "Curso não encontrado"}), 404
    if curso["habilitado"]:
        return jsonify({"message": "Curso já está habilitado"}), 200

    run("""
        UPDATE cursos
        SET habilitado = TRUE, updated_at = NOW()
        WHERE id_curso = %(id)s
    """, {"id": id_curso})
    return jsonify({"message": "Curso habilitado com sucesso"}), 200
