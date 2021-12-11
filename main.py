from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import BadRequestKeyError
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_gravatar import Gravatar
import json
import os

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "OIEFNOikjesmeolikmo")
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///users.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)

login_attempts = 0

gravatar = Gravatar(
                    app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None
                    )


class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False, unique=True)
    email = db.Column(db.String(250), nullable=False, unique=True)
    birthday = db.Column(db.String(500), nullable=False)
    game = db.Column(db.String(500), nullable=False)
    password = db.Column(db.String(500), nullable=True)


class Comments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False, unique=True)
    comment = db.Column(db.String(250), nullable=False, unique=True)
    rate = db.Column(db.Integer, nullable=False)


db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(user_id)


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    else:
        return redirect(url_for("welcome"))


@app.route("/sign-up", methods=["GET", "POST"])
def sign_up():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        birthday = request.form["birthday"]
        password = request.form["pass"]

        try:
            game = request.form["games"]
        except BadRequestKeyError:
            flash("Select a game")
            return redirect(url_for("sign_up"))

        all_users = db.session.query(Users).all()
        selected_users = [
            user
            for user in all_users
            if name in user.name
        ]
        if not len(selected_users) == 1:
            try:
                last_num = [int(user.name.split("(")[1].split(")")[0])
                            for user in selected_users[1:]
                            ][-1]
                name += f" ({last_num + 1})"
            except IndexError:
                pass
        else:
            name += " (1)"
        try:
            new_user = Users(
                name=name,
                email=email,
                birthday=birthday,
                game=game,
                password=generate_password_hash(
                    password=password,
                    salt_length=8
                )
            )
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError:
            flash("This email already exists.")
            return redirect(url_for("sign_up"))

        login_user(new_user)
        return redirect(url_for("home"))

    return render_template("sign-up.html")


@app.route("/sign-in", methods=["GET", "POST"])
def sign_in():
    global login_attempts

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["pass"]

        user = Users.query.filter_by(email=email).first()
        if user:
            is_correct = check_password_hash(
                pwhash=user.password,
                password=password
            )
            if is_correct:
                login_user(user)

                return redirect(url_for("dashboard"))
            else:
                flash("Wrong password.")
                login_attempts += 1
                return redirect(url_for("sign_in"))
        else:
            flash("This is email doesn't exist.")
            return redirect(url_for("sign_in"))

    return render_template("sign-in.html")


@app.route("/log-out")
@login_required
def log_out():
    logout_user()
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    all_users = db.session.query(Users).all()
    try:
        with open("survey.json") as file:
            data = json.load(file)
    except json.decoder.JSONDecodeError:
        data = {}
    return render_template("index.html", users=all_users, comments=data, length=len(data))


@app.route("/welcome")
def welcome():
    return render_template("welcome.html")


@app.route("/settings", methods=["POST", "GET"])
@login_required
def settings():
    if request.method == "POST":

        user = current_user

        if "details" in request.form:
            user.name = request.form["name"]
            user.email = request.form["email"]
            user.birthday = request.form["bday"]
            user.game = request.form["game"]

            db.session.commit()

            return redirect(url_for("settings"))

        else:

            new_pass = request.form["new_pass"]
            old_pass = request.form["old_pass"]
            confirm_pass = request.form["confirm_pass"]

            correct_password = check_password_hash(
                pwhash=user.password,
                password=old_pass,
            )
            if correct_password:
                if new_pass == confirm_pass:
                    user.password = generate_password_hash(
                        password=new_pass,
                        salt_length=8
                    )

                    db.session.commit()

                    flash("Password changed successfully!")
                    return redirect(url_for("settings"))
                else:
                    flash("Passwords doesn't match")
                    return redirect(url_for("settings"))
            else:
                flash("Wrong password")
                return redirect(url_for("settings"))

    return render_template("settings.html",
                           all_games=["8 Ball Pool",
                                      "Basketball Stars",
                                      "Carom Pool"
                                      ],
                           )


def is_admin(function):
    def wrapper(*args, **kwargs):
        if current_user.name == "Admin":
            return function(*args, **kwargs)
        else:
            return abort(403)
    return wrapper


@app.route("/delete-user", methods=["GET", "POST"])
@login_required
@is_admin
def delete():
    email = request.args.get("email")
    code = request.args.get("code")

    if code == os.environ.get("CODE"):
        user = Users.query.filter_by(email=email).first()
        if user:
            db.session.delete(user)
            db.session.commit()
        else:
            return "This email doesn't exist."
    else:
        return "Invalid confirmation code"

    return "User deleted..."


@app.route("/count")
def count_users():
    ball_pool, basket_ball, carom = 0, 0, 0

    users = db.session.query(Users).all()
    for u in users:
        if u.game == "8 Ball Pool":
            ball_pool += 1
        elif u.game == "Carom Pool":
            carom += 1
        else:
            basket_ball += 1

    return f"<p>8 Ball Pool = {ball_pool}</p>" \
           f"<p>Basket Ball Stars = {basket_ball}</p>" \
           f"<p>Carom Pool = {carom}</p>"


@app.route("/survey", methods=["GET", "POST"])
def survey():
    if request.method == "POST":
        rate = request.form["rate"]
        comment = request.form["comment"]

        if not rate:
            flash("Please select a rating from above.")
            return redirect(url_for("survey"))
        elif not comment:
            flash("Please enter a comment.")
            return redirect(url_for("survey"))

        try:
            with open("survey.json") as file:
                data = json.load(file)

            data[f"person{len(data)+1}"] = {
                "comment": comment,
                "rate": rate,
            }
        except json.decoder.JSONDecodeError:
            data = {
                "Person1": {
                    "comment": comment,
                    "rate": rate,
                }
            }

        with open("survey.json", mode="w") as file:
            json.dump(data, file)

        flash("Thank you for your feedback!")
        return render_template("survey.html")

    return render_template("survey.html")


# @app.route("/list")
# @login_required
# def count_lists():
#     user = db.session.query(Users).all()
#
#     pool_name, pool_game, pool_contact, pool_bday = [], [], [], []
#     carom_name, carom_game, carom_contact, carom_bday = [], [], [], []
#     ball_name, ball_game, ball_contact, ball_bday = [], [], [], []
#
#     for u in user:
#         if u.game == "8 Ball Pool":
#             pool_name.append(u.name)
#             pool_game.append(u.game)
#             pool_contact.append(u.email)
#             pool_bday.append(u.birthday)
#         elif u.game == "Carom Pool":
#             carom_name.append(u.name)
#             carom_game.append(u.game)
#             carom_contact.append(u.email)
#             carom_bday.append(u.birthday)
#         else:
#             ball_name.append(u.name)
#             ball_game.append(u.game)
#             ball_contact.append(u.email)
#             ball_bday.append(u.birthday)
#
#     pool = [pool_game, pool_name, pool_contact, pool_bday]
#     carom = [carom_game, carom_name, carom_contact, carom_bday]
#     ball = [ball_game, ball_name, ball_contact, ball_bday]
#
#     return render_template("event_data.html", pool=pool, carom=carom, ball=ball)


if __name__ == "__main__":
    app.run(debug=True)
