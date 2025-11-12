from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    
    CORS(app, origins=["*"])

    # Importar e registrar blueprints
    from .routes.main_routes import main_bp
    from .routes.user_routes import user_bp
    from .routes.cursos_routes import cursos_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(cursos_bp, url_prefix="/cursos")

    return app
