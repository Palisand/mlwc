# Development environment enable (for manage.py::runserver)
DEFAULT = None

# Application directory
import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Database
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'app.db')
DATABASE_CONNECT_OPTIONS = {}

# Secret key TODO: this should probably be an environment variable
SECRET_KEY = "^Kr\x8d`\xab\x15\xb9\xe4\xdc\xf0\xb3\xaa\xa1A\xcf\x8d'\xfe\xb1\xe2\x19\xe1m"

# Upload folders / directories
ATHLETE_IMAGE_UPLOAD_DIR = 'metropolitanweightlifting/static/image/athletes'
ATHLETE_IMAGE_UPLOAD_FOLDER = os.path.join(BASE_DIR, ATHLETE_IMAGE_UPLOAD_DIR)
ARTICLE_IMAGE_UPLOAD_DIR = 'metropolitanweightlifting/static/image/articles'
ARTICLE_IMAGE_UPLOAD_FOLDER = os.path.join(BASE_DIR, ARTICLE_IMAGE_UPLOAD_DIR)
PDF_UPLOAD_DIR = 'metropolitanweightlifting/static/pdf'
PDF_UPLOAD_FOLDER = os.path.join(BASE_DIR, PDF_UPLOAD_DIR)
