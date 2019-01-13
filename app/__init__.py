from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow
from flask_login import LoginManager
from flask_httpauth import HTTPBasicAuth
from flask_bootstrap import Bootstrap


app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)

ma = Marshmallow(app)

migrate = Migrate(app, db)

login = LoginManager(app)
login.login_view = 'login'

auth = HTTPBasicAuth()

bootstrap = Bootstrap(app)



from app import routes, models, errors