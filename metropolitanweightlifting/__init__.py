from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.admin import Admin
from flask.ext.login import LoginManager
# from flask.ext.bcrypt import Bcrypt

app = Flask(__name__)
app.config.from_object('config')

db = SQLAlchemy(app)

admin = Admin(app, name='MLCW Admin', template_mode='bootstrap3')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = u'This page can only be accessed by site admins.'

# bcrypt = Bcrypt(app)

import metropolitanweightlifting.views
import metropolitanweightlifting.util.jinja_filters
