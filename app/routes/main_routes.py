# routes/main_routes.py
from flask import Blueprint, jsonify
from os import getenv
from datetime import datetime

from ..models.db import one

from dotenv import load_dotenv
load_dotenv()

main_bp = Blueprint("main", __name__)

@main_bp.route("/health", methods=["GET", "POST", "PUT"])
def index():
    """
    Health Check da API
    ---
    tags:
      - Health
    consumes:
      - application/json
    produces:
      - application/json
    responses:
      200:
        description: Retorna o ambiente e a hora atual no servidor
        schema:
          type: object
          properties:
            ENV:
              type: string
              description: "Nome do ambiente (ex.: dev, prod)"
            time:
              type: string
              format: date-time
              description: "Horário UTC ISO8601"
    """
    return jsonify({"ENV": getenv("ENV"), "time": datetime.utcnow().isoformat()})

@main_bp.get("/health/db")
def health_db():
    """
    Verifica conexão com o banco de dados
    ---
    tags:
      - Health
    responses:
      200:
        description: Conexão com banco ok
        schema:
          type: object
          properties:
            db:
              type: string
              example: "ok"
            result:
              type: integer
              example: 1
      500:
        description: Erro ao conectar no banco
        schema:
          type: object
          properties:
            db:
              type: string
              example: "error"
            detail:
              type: string
              description: "Detalhe do erro"
    """
    try:
        row = one("SELECT 1 AS ok;")
        return {"db": "ok", "result": row["ok"]}, 200
    except Exception as e:
        return {"db": "error", "detail": str(e)}, 500
