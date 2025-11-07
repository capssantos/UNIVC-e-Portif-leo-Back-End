from flask import Flask

def create_app():
    app = Flask(__name__)
    
    # Importar e registrar blueprints
    from .routes.main_routes import main_bp
    from .routes.user_routes import user_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp)

    return app
