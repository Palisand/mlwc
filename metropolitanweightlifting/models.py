from metropolitanweightlifting import db, admin  # bcrypt
from werkzeug.security import generate_password_hash
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.login import current_user
from flask import url_for, redirect
import datetime

# TODO: install and use alembic to deal with migrations involving a lot of data


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum('text_only', 'images', 'video', 'pdf'), nullable=False)
    title = db.Column(db.String, nullable=False)
    body = db.Column(db.Text)
    video_src = db.Column(db.String)
    pdf_src = db.Column(db.String)
    wrap_text = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now())

    def __init__(self, type, title, body, video_src, pdf_src, wrap_text):
        self.type = type
        self.title = title
        self.body = body
        self.video_src = video_src
        self.pdf_src = pdf_src
        self.wrap_text = wrap_text

    def __repr__(self):
        return '<Article %r>' % self.title


class ArticleImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    src = db.Column(db.String, nullable=False)
    caption = db.Column(db.String)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    # TODO (if requested): location/order in carousel

    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), index=True)
    article = db.relationship('Article', backref=db.backref('images', lazy='dynamic'))

    def __init__(self, src, caption, width, height, article_id):
        self.src = src
        self.caption = caption
        self.width = width
        self.height = height
        self.article_id = article_id

    def __repr__(self):
        return '<ArticleImage %r: %r>' % (self.id, self.src)


class Athlete(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # USA Weightlifting ID
    gender = db.Column(db.Enum('m', 'f'), nullable=False)
    firstname = db.Column(db.String, nullable=False)
    lastname = db.Column(db.String, nullable=False)
    body_weight = db.Column(db.Float)
    weight_class = db.Column(db.Enum(
        '56', '62', '69', '77', '85', '94', '105', '105+',
        '48', '53', '58', '63', '69', '75', '90', '90+'
    ), nullable=False)
    snatch = db.Column(db.Integer, nullable=False)
    clean_jerk = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    has_photo = db.Column(db.Boolean)

    def __init__(self,
                 id,
                 gender,
                 firstname,
                 lastname,
                 body_weight,
                 weight_class,
                 snatch,
                 clean_jerk,
                 description,
                 has_photo):
        self.id = id
        self.gender = gender
        self.firstname = firstname
        self.lastname = lastname
        self.body_weight = body_weight
        self.weight_class = weight_class
        self.snatch = snatch
        self.clean_jerk = clean_jerk
        self.description = description
        self.has_photo = has_photo

    def __repr__(self):
        return '<Athlete %r %r (%r)>' % (self.firstname, self.lastname, self.id)


class Meet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sanction_number = db.Column(db.String(20), nullable=False)  # this should be UNIQUE!?
    name = db.Column(db.String, nullable=False)
    date = db.Column(db.Date, nullable=False)
    city = db.Column(db.String)
    state = db.Column(db.String)

    def __init__(self, sanction_number, name, date, city, state):
        self.sanction_number = sanction_number
        self.name = name
        self.date = date
        self.city = city
        self.state = state

    def __repr__(self):
        return '<Meet %r>' % self.sanction_number


class MeetResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gender = db.Column(db.Enum('m', 'f'), nullable=False)
    member_id = db.Column(db.Integer, nullable=False)
    weight_class = db.Column(db.Enum(
        '56', '62', '69', '77', '85', '94', '105', '105+',
        '48', '53', '58', '63', '69', '75', '75+', '90', '90+'  # 75+ for old meet results
    ), nullable=False)
    place = db.Column(db.Integer)
    name = db.Column(db.String)
    body_weight = db.Column(db.Float)
    snatch_1 = db.Column(db.Integer)
    snatch_2 = db.Column(db.Integer)
    snatch_3 = db.Column(db.Integer)
    snatch_best = db.Column(db.Integer)
    clean_jerk_1 = db.Column(db.Integer)
    clean_jerk_2 = db.Column(db.Integer)
    clean_jerk_3 = db.Column(db.Integer)
    clean_jerk_best = db.Column(db.Integer)
    total = db.Column(db.Integer)

    meet_id = db.Column(db.Integer, db.ForeignKey('meet.id'))
    meet = db.relationship('Meet', backref=db.backref('results', lazy='dynamic'))

    def __init__(self,
                 gender,
                 member_id,
                 weight_class,
                 place,
                 name,
                 body_weight,
                 snatch_1,
                 snatch_2,
                 snatch_3,
                 snatch_best,
                 clean_jerk_1,
                 clean_jerk_2,
                 clean_jerk_3,
                 clean_jerk_best,
                 total,
                 meet_id):
        self.gender = gender
        self.member_id = member_id
        self.weight_class = weight_class
        self.place = place
        self.name = name
        self.body_weight = body_weight
        self.snatch_1 = snatch_1
        self.snatch_2 = snatch_2
        self.snatch_3 = snatch_3
        self.snatch_best = snatch_best
        self.clean_jerk_1 = clean_jerk_1
        self.clean_jerk_2 = clean_jerk_2
        self.clean_jerk_3 = clean_jerk_3
        self.clean_jerk_best = clean_jerk_best
        self.total = total
        self.meet_id = meet_id

    def __repr__(self):
        return '<MeetResult %r:%r>' % (self.weight_class, self.place)


class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    pdf_src = db.Column(db.String, nullable=False)

    def __init__(self, date, pdf_src):
        self.date = date
        self.pdf_src = pdf_src

    def __repr__(self):
        return '<MeetingMinutes %r>' % self.date


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String, nullable=False)
    lastname = db.Column(db.String, nullable=False)
    username = db.Column(db.String, unique=True, index=True, nullable=False)
    password = db.Column(db.String, nullable=False)

    def __init__(self, firstname, lastname, username, password):
        self.firstname = firstname
        self.lastname = lastname
        self.username = username
        # self.password = bcrypt.generate_password_hash(password)
        self.password = generate_password_hash(password)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<User %r>' % self.username


# Flask-Admin

class AuthModelView(ModelView):

    can_create = False

    def is_accessible(self):
        return current_user.is_authenticated()

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))


admin.add_view(AuthModelView(User, db.session))
admin.add_view(AuthModelView(Athlete, db.session))
admin.add_view(AuthModelView(Article, db.session))
admin.add_view(AuthModelView(ArticleImage, db.session))
admin.add_view(AuthModelView(Meet, db.session))
admin.add_view(AuthModelView(MeetResult, db.session))
admin.add_view(AuthModelView(Meeting, db.session))

