from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    # Load configuration from config.py
    app.config.from_object('app.config.Config')

    # Initialize database
    db.init_app(app)
    migrate.init_app(app, db)

    # Import  models here to make sure they are registered
    from app import models 

    # Register  blueprints
    from app.views import main_blueprint
    app.register_blueprint(main_blueprint)

    from app.api.api import api_blueprint
    print("Registering api_blueprint...")
    app.register_blueprint(api_blueprint, url_prefix='/api')
    
    return app
