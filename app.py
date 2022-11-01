from pickle import TRUE
from flask import Flask, render_template, session, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_session import Session
from dotenv import load_dotenv
from os import getenv
import random
import requests

load_dotenv()

SECRET_KEY = getenv("SECRET_KEY")
ADMIN_USERNAME = getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = getenv("ADMIN_PASSWORD")
PORT = getenv("PORT")
DEV = getenv("DEV")
DATABASE_URI = getenv("DATABASE_URI")
NUM_ROUNDS = 5
SERVER_URL = getenv("SERVER_URL")

app = Flask(__name__)
app.debug = DEV == "True"

app.secret_key = SECRET_KEY

app.config["SESSION_PERMANENT"] = TRUE
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def user_invalid_game_entry(game_id):
    res = requests.get(f"{SERVER_URL}/user_invalid_game_entry" , params=dict({"game_id":game_id})).json()
    return res['flag']

def user_exists_in_game(username, game_id):
    res = (requests.get(f"{SERVER_URL}/user_invalid_game_entry" , params=dict({"game_id":game_id}))).json()
    return res['flag']


def user_add_to_game(username, email, game_id):
    new_user = UserSession(username=username, email=email, game_id=game_id, points=0.0)
    db.session.add(new_user)
    db.session.commit()


def user_invalid_game_play(username, game_id, round_num):
    res = (requests.get(f"{SERVER_URL}/user_invalid_game_play" , params=dict({"username":username,"game_id":game_id,"round_num":round_num}))).json()
    return res['flag']


def user_add_choice(username, game_id, round_num, number_chosen):

    if (
        Choice.query.filter_by(
            username=username, game_id=game_id, round_num=round_num
        ).first()
        is not None
    ):
        return

    new_choice = Choice(
        username=username,
        game_id=game_id,
        round_num=round_num,
        number_chosen=number_chosen,
    )
    db.session.add(new_choice)
    db.session.commit()


def user_valid_round_end(username, game_id, round_num):
    res = (requests.get(f"{SERVER_URL}/user_invalid_game_play" , params=dict({"username":username,"game_id":game_id,"round_num":round_num}))).json()
    return res['flag']


def admin_start_game(game_id):
    new_game = Game(game_id=game_id, round_num=1, game_end=False)
    db.session.add(new_game)
    db.session.commit()


def admin_end_game(game_id):
    try:
        game = Game.query.filter_by(game_id=game_id).first()
        game.game_end = True
        db.session.commit()
    except:
        return


def admin_invalid_round_end(game_id, round_num):
    return (
        Game.query.filter_by(
            game_id=game_id, round_num=round_num, game_end=False
        ).first()
        is None
    )


def admin_end_round(game_id, round_num):
    try:
        game = Game.query.filter_by(game_id=game_id).first()

        if round_num == NUM_ROUNDS:
            game.game_end = True
            db.session.commit()
        else:
            game.round_num = round_num + 1
            db.session.commit()

    except:
        return


def get_result(game_id, round_num, reviewing):

    freq = dict()
    choices = Choice.query.filter_by(game_id=game_id, round_num=round_num).all()
    for choice in choices:
        freq[choice.number_chosen] = freq.get(choice.number_chosen, 0) + 1

    if not reviewing:
        for choice in choices:

            username = choice.username
            number_chosen = choice.number_chosen
            f = freq[number_chosen]

            user = UserSession.query.filter_by(
                username=username, game_id=game_id
            ).first()
            user.points = user.points + ((float(number_chosen)) / (float(f)))
            db.session.commit()

    frequency = dict()

    for i in range(1, 101):
        frequency[i] = freq.get(i, 0) + random.randint(0, 10)

    userlist = UserSession.query.filter_by(game_id=game_id).all()
    ranklist = []

    for user in userlist:
        ranklist.append(user.__dict__)

    ranklist = sorted(ranklist, key=lambda d: d["points"], reverse=True)

    return ranklist[:10], frequency


@app.route("/", methods=["GET", "POST"])
def user_home():
    if request.method == "POST":
        username, email, game_id = (
            request.form["username"],
            request.form["email"],
            request.form["game_id"],
        )

        if user_invalid_game_entry(game_id):
            return redirect("/clear_session")

        if user_exists_in_game(username, game_id):
            return redirect(f"/user/game_play")

        user_add_to_game(username, email, game_id)

        session["current_user"] = {"username": username, "email": email}

        session["current_game"] = {
            "game_id": game_id,
            "round_num": 1,
            "game_end": False,
        }

        return redirect("/user/game_play")

    return render_template("user_home.html")


@app.route("/user/game_play", methods=["GET", "POST"])
def user_game_play():

    current_user = session.get("current_user", {"username": "", "email": ""})
    current_game = session.get(
        "current_game", {"game_id": -1, "round_num": -1, "game_end": True}
    )

    if current_game["game_id"] == -1 or current_game["game_end"] == True:
        return redirect("/clear_session")

    username = current_user["username"]
    game_id = current_game["game_id"]
    round_num = current_game["round_num"]

    if user_invalid_game_play(username, game_id, round_num):
        return redirect("/clear_session")

    if request.method == "POST":
        number_chosen = request.form["number_chosen"]

        user_add_choice(username, game_id, round_num, number_chosen)
        return redirect(f"/user/round_end")

    return render_template("user_game_play.html", game_id=game_id, round_num=round_num)


@app.route("/user/round_end", methods=["GET", "POST"])
def user_round_end():

    current_user = session.get("current_user", {"username": "", "email": ""})
    current_game = session.get(
        "current_game", {"game_id": -1, "round_num": -1, "game_end": True}
    )

    username = current_user["username"]
    game_id = current_game["game_id"]
    round_num = current_game["round_num"]

    if game_id == -1 or round_num == -1:
        return redirect("/clear_session")

    is_last_round = round_num == NUM_ROUNDS

    if request.method == "POST":
        if round_num == NUM_ROUNDS:
            return redirect("/clear_session")
        elif user_valid_round_end(username, game_id, round_num):
            session["current_game"] = {
                "game_id": game_id,
                "round_num": round_num + 1,
                "game_end": False,
            }
            return redirect("/user/game_play")
        else:
            flash("Please wait for current round to end!")

    return render_template(
        "user_round_end.html",
        game_id=game_id,
        round_num=round_num,
        is_last_round=is_last_round,
    )


@app.route("/admin", methods=["GET", "POST"])
def admin_home():

    if request.method == "POST":
        admin_username = request.form["username"]
        admin_password = request.form["password"]
        if admin_username == ADMIN_USERNAME and admin_password == ADMIN_PASSWORD:
            session["current_admin_username"] = admin_username
            return redirect("/admin/game_start")

    return render_template("admin_home.html")


@app.route("/admin/game_start", methods=["GET", "POST"])
def admin_game_start():

    if session.get("current_admin_username", "") != ADMIN_USERNAME:
        return redirect("/clear_session")

    if request.method == "POST":

        current_game = session.get(
            "current_game", {"game_id": -1, "round_num": -1, "game_end": True}
        )

        if (
            current_game["game_id"] != -1
            or current_game["round_num"] != -1
            or current_game["game_end"] == False
        ):

            game_id = current_game["game_id"]

            admin_end_game(game_id)
            session["current_game"] = {"game_id": -1, "round_num": -1, "game_end": True}

            return render_template("admin_game_start.html")

        try:
            game_id = request.form["game_id"]

            admin_start_game(game_id)
            session["current_game"] = {
                "game_id": game_id,
                "round_num": 1,
                "game_end": False,
            }

            return redirect("/admin/game_play")

        except Exception as E:
            print(E)
            session["current_game"] = {"game_id": -1, "round_num": -1, "game_end": True}

    return render_template("admin_game_start.html")


@app.route("/admin/game_play", methods=["GET", "POST"])
def admin_game_play():

    if session.get("current_admin_username", "") != ADMIN_USERNAME:
        return redirect("/clear_session")

    current_game = session.get(
        "current_game", {"game_id": -1, "round_num": -1, "game_end": True}
    )

    if current_game["game_id"] == -1 or current_game["game_end"] == True:
        session["current_game"] = {"game_id": -1, "round_num": -1, "game_end": True}
        return redirect("/clear_session")

    current_game = session.get(
        "current_game", {"game_id": -1, "round_num": -1, "game_end": True}
    )

    return render_template("admin_game_play.html", current_game=current_game)


@app.route("/admin/round_end", methods=["GET", "POST"])
def andmin_round_end():
    if request.method == "POST":
        try:
            current_game = session.get(
                "current_game", {"game_id": -1, "round_num": -1, "game_end": True}
            )
            game_id = request.form["game_id"]
            round_num = int(request.form["round_num"])

            if (
                current_game["game_id"] == game_id
                and current_game["round_num"] == round_num
            ):
                print("redirecting to result")
                return redirect(f"/admin/result/{game_id}/{round_num}")

        except Exception as E:
            print(E)

    return redirect("/clear_session")


@app.route("/admin/result/<string:game_id>/<int:round_num>", methods=["GET", "POST"])
def admin_result(game_id, round_num):

    reviewing = admin_invalid_round_end(game_id, round_num)

    if not reviewing:
        admin_end_round(game_id, round_num)

    is_last_round = round_num == NUM_ROUNDS

    if is_last_round == True:
        session["current_game"] = {"game_id": -1, "round_num": -1, "game_end": True}
    else:
        session["current_game"] = {
            "game_id": game_id,
            "round_num": round_num + 1,
            "game_end": False,
        }

    result, frequency = get_result(game_id, round_num, reviewing)
    return render_template(
        "admin_result.html",
        game_id=game_id,
        round_num=round_num,
        result=result,
        frequency=frequency,
        is_last_round=is_last_round,
    )


@app.route("/clear_session", methods=["GET", "POST"])
def clear_session():

    if session.get("current_admin_username", "") == ADMIN_USERNAME:

        current_game = session.get(
            "current_game", {"game_id": -1, "round_num": -1, "game_end": True}
        )
        game_id = current_game["game_id"]

        admin_end_game(game_id)

        session["current_admin_username"] = ""

    session["current_user"] = {
        "username": "",
        "email": "",
        "game_id": -1,
        "game_played": False,
    }
    session["current_game"] = {"game_id": -1, "round_num": -1, "game_end": True}

    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True, port=PORT)
