from flask.ext.script import Server, Manager, prompt_bool
from metropolitanweightlifting import app, db

manager = Manager(app)
manager.add_command("runserver", Server())


@manager.command
def init():
    db.create_all()


@manager.command
def init_debug():
    init()
    add_user('test', 'user', 'tuser')


@manager.command
def dropdb():
    if prompt_bool("Drop database?"):
        db.drop_all()


@manager.option('-f', '--firstname', dest='firstname', default=None)
@manager.option('-l', '--lastname', dest='lastname', default=None)
@manager.option('-u', '--username', dest='username', default=None)
def add_user(firstname, lastname, username):
    if firstname and lastname and username:
        from metropolitanweightlifting.models import User
        user = User(
            firstname,
            lastname,
            username,
            'password'
        )
        db.session.add(user)
        db.session.commit()
        print "User %s added, must change password" % username


if __name__ == "__main__":
    manager.run()
