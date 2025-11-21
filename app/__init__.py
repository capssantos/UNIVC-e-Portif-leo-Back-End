# __init__.py
from flask import Flask
from flask_cors import CORS
from flasgger import Swagger

def create_app():
    app = Flask(__name__)

    # Libera explicitamente o front
    CORS(
        app,
        resources={r"/*": {
            "origins": [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "https://apiunivc.carlosp.dev",  # se quiser que o Swagger continue funcionando bonitinho
            ]
        }}
    )

    app.config["SWAGGER"] = {
        "title": "API Portifoleo UNIVC",
        "uiversion": 3,
    }

    Swagger(app)

    from .routes.main_routes import main_bp
    from .routes.user_routes import user_bp
    from .routes.cursos_routes import cursos_bp
    from .routes.levels_routes import levels_bp
    from .routes.projetos_routes import projetos_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(cursos_bp, url_prefix="/cursos")
    app.register_blueprint(levels_bp, url_prefix="/levels")
    app.register_blueprint(projetos_bp, url_prefix="/projetos")

    return app
