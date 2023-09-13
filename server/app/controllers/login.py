from flask import render_template, request, flash, redirect, url_for
from app import app
from flask_wtf import FlaskForm
from flask_login import current_user, login_user, logout_user, UserMixin, LoginManager

from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import InputRequired, Length
from werkzeug.urls import url_parse
from werkzeug.security import check_password_hash

from app.repository import Repository, UserRole


class LoginForm(FlaskForm):
    username = StringField("Your login name", validators=[InputRequired(), Length(min=3, max=20)])
    password = PasswordField("Your password", validators=[InputRequired(), Length(min=5, max=80)])
    remember = BooleanField("Remember me")

    submit = SubmitField("Sign In")


class ApplicationUser(UserMixin):

    # The following fields are useful for Flask-login
    # It's basically a reimplementation of UserMixin

    def __init__(self, user):
        # Copy id, username, digest, email, role fields
        for key, value in user.items():
            setattr(self, key, value)
        self.auth = False

    def check_digest(self, digest: str):
        """This compares hashes. It's almost useless (except perhaps for testing) as the hashes
        are salted. So they're almost always different. This sets the auth field (true if provided
        password is correct)."""
        self.auth = self.digest == digest
        return self.auth

    def check_password(self, passwd: str):
        return check_password_hash(self.digest, passwd)

    def is_authenticated(self):
        return self.auth

    def is_anonymous(self):
        return not self.auth

    def get_id(self):
        return self.id


@app.route("/login", methods=["GET", "POST"])
def login():

    repository = Repository()

    if current_user.is_authenticated:
        stations = repository.owned_stations(current_user.get_id())

        # list of stations
        owned_stations = " ".join(f"{s['name']}({s['station_id']})" for s in stations)
        app.logger.info("Authenticated user %s, owner of %s" % (current_user.username, owned_stations))

        return render_template("login.html", user=current_user, stations=stations)

    form = LoginForm()

    if form.validate_on_submit():
        app.logger.info("Login requested for user %s, pass=%s, remember_me=%s" % (form.username.data, form.password.data, form.remember.data))

        user = repository.read_user(user=form.username.data)

        if user is None:
            app.logger.info("Login failed: invalid username: %s" % form.username.data)
            flash("Invalid username.")
            return redirect(url_for("login"))

        u = ApplicationUser(user)
        if not u.check_password(form.password.data):
            app.logger.info("Login failed: invalid password %s for user %s" % (form.password.data, form.username.data))
            flash("Invalid password.")
            return redirect(url_for("login"))

        if u.role == UserRole.BANNED:
            app.logger.info("Login failed: attempt to login into disabled account %s" % form.username.data)
            flash("Account disabled.")
            return redirect(url_for("login"))

        app.logger.info("Login successful for user %s" % form.username.data)
        login_user(u, remember=form.remember.data)

        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("index")
        return redirect(next_page)

    return render_template("login.html", form=form)


lm = LoginManager(app)


@lm.user_loader
def load_user(user_id):
    rep = Repository()
    u = rep.read_user(user=user_id)
    if u:
        return ApplicationUser(u)
    return None


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))
