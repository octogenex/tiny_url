from flask import Flask
from flask import Blueprint, render_template, request, redirect
from datetime import datetime
import string
from random import choices
from flask_sqlalchemy import SQLAlchemy
import os
from functools import wraps
from flask import request, Response, current_app

db = SQLAlchemy()

short = Blueprint('short', __name__)

SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
SQLALCHEMY_TRACK_MODIFICATIONS = False

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')


def create_app(config_file='settings.py'):
    app = Flask(__name__)

    app.config.from_pyfile(config_file)

    db.init_app(app)

    app.register_blueprint(short)

    return app



class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.String(512))
    short_url = db.Column(db.String(5), unique=True)
    visits = db.Column(db.Integer, default=0)
    date_created = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.short_url = self.generate_short_link()

    def generate_short_link(self):
        characters = string.digits + string.ascii_letters + string.punctuation
        short_url = ''.join(choices(characters, k=5))

        link = self.query.filter_by(short_url=short_url).first()

        if link:
            return self.generate_short_link()

        return short_url

def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == current_app.config['ADMIN_USERNAME'] \
        and password == current_app.config['ADMIN_PASSWORD']

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


@short.route('/<short_url>')
def redirect_to_url(short_url):
    link = Link.query.filter_by(short_url=short_url).first_or_404()

    link.visits = link.visits + 1
    db.session.commit()

    return redirect(link.original_url)


@short.route('/')
@requires_auth
def index():
    return render_template('index.html')


@short.route('/add_link', methods=['POST'])
def add_link():
    original_url = request.form['original_url']
    link = Link(original_url=original_url)
    db.session.add(link)
    db.session.commit()

    return render_template('link_added.html',
                           new_url=link.short_url, original_url=link.original_url)


@short.route('/stats')
def stats():
    links = Link.query.all()

    return render_template('stats.html', links=links)


@short.errorhandler(404)
def page_not_found(e):
    return render_template('404.html')
