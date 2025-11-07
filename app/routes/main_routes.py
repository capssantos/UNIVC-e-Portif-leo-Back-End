from flask import Blueprint, jsonify
from os import getenv
from datetime import datetime

from ..models.db import one

from dotenv import load_dotenv
load_dotenv()

main_bp = Blueprint("main", __name__)

@main_bp.route("/health", methods=["GET", "POST", "PUT"])
def index():
    return jsonify({"ENV": getenv("ENV"), "time": datetime.utcnow().isoformat()})

@main_bp.get("/health/db")
def health_db():
    try:
        row = one("SELECT 1 AS ok;")
        return {"db": "ok", "result": row["ok"]}, 200
    except Exception as e:
        return {"db": "error", "detail": str(e)}, 500