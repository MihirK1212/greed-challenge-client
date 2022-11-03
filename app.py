from flask import Flask, jsonify, render_template, session, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_session import Session
from dotenv import load_dotenv
from os import getenv
import random
import requests
from sqlalchemy import true

load_dotenv()

ADMIN_PASSWORD = getenv("ADMIN_PASSWORD")
ADMIN_USERNAME = getenv("ADMIN_USERNAME")
DEV = getenv("DEV")
NUM_ROUNDS = int(getenv("NUM_ROUNDS"))
PORT = getenv("PORT")
SECRET_KEY = getenv("SECRET_KEY")
SERVER_URL = getenv("SERVER_URL")
RANGE = int(getenv("RANGE"))

app = Flask(__name__)
app.debug = DEV == "True"

app.secret_key = SECRET_KEY

app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def user_invalid_game_entry(game_id):
    try:
        res = (requests.get(f"{SERVER_URL}/user_invalid_game_entry" , params=dict({"game_id":game_id}))).json()
        return bool(res['flag'])
    except Exception as E:
        return True

def user_exists_in_game(username, game_id):
    try:
        res = (requests.get(f"{SERVER_URL}/user_exists_in_game" , params=dict({"username":username,"game_id":game_id}))).json()
        return bool(res['flag'])
    except Exception as E:
        return True

def user_add_to_game(username, email, game_id):
    try:
        requests.post(f"{SERVER_URL}/user_add_to_game" , json=dict({"username":username,"email":email,"game_id":game_id}))
    except Exception as E:
        return True

def user_invalid_game_play(username, game_id, round_num):
    try:
        res = (requests.get(f"{SERVER_URL}/user_invalid_game_play" , params=dict({"username":username,"game_id":game_id,"round_num":round_num}))).json()
        return bool(res['flag'])
    except Exception as E:
        return True

def user_add_choice(username, game_id, round_num, number_chosen):
    try:
        requests.post(f"{SERVER_URL}/user_add_choice" , json=dict({"username":username,"game_id":game_id,"round_num":round_num,"number_chosen":number_chosen}))   
    except Exception as E:
        print(E)

def user_valid_round_end(username, game_id, round_num):
    try:
        res = (requests.get(f"{SERVER_URL}/user_valid_round_end" , params=dict({"username":username,"game_id":game_id,"round_num":round_num}))).json()
        return bool(res['flag'])
    except Exception as E:
        return False

def admin_start_game(game_id):
    try:
        requests.post(f"{SERVER_URL}/admin_start_game" , json=dict({"game_id":game_id}))
    except Exception as E:
        print(E)

def admin_end_game(game_id):
    try:
        requests.post(f"{SERVER_URL}/admin_end_game" , json=dict({"game_id":game_id}))
    except Exception as E:
        print(E)

def admin_invalid_round_end(game_id, round_num):
    try:
        res = (requests.get(f"{SERVER_URL}/admin_invalid_round_end" , params=dict({"game_id":game_id,"round_num":round_num}))).json()
        return bool(res['flag'])
    except Exception as E:
        return True


def admin_end_round(game_id, round_num):
    try:
        requests.post(f"{SERVER_URL}/admin_end_round" , json=dict({"game_id":game_id,"round_num":round_num}))
    except Exception as E:
        print(E)

def get_result(game_id, round_num, reviewing):
    try:
        res = (requests.get(f"{SERVER_URL}/get_result" , params=dict({"game_id":game_id,"round_num":round_num,"reviewing":reviewing}))).json()
        return res['ranklist'] , res['frequency']
    except Exception as E:
        print(E)


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
        try:
            number_chosen = int(request.form["number_chosen"])
        except:
            return render_template("user_game_play.html", game_id=game_id, round_num=round_num,range=RANGE)

        if (number_chosen<1 or number_chosen>RANGE):
            return render_template("user_game_play.html", game_id=game_id, round_num=round_num,range=RANGE)

        user_add_choice(username, game_id, round_num, number_chosen)
        return redirect(f"/user/round_end")

    return render_template("user_game_play.html", game_id=game_id, round_num=round_num,range=RANGE)


@app.route("/user/round_end", methods=["GET", "POST"])
def user_round_end():

    print("in user round end:")

    current_user = session.get("current_user", {"username": "", "email": ""})
    current_game = session.get(
        "current_game", {"game_id": -1, "round_num": -1, "game_end": True}
    )

    username = current_user["username"]
    game_id = current_game["game_id"]
    round_num = current_game["round_num"]

    print("username , game_id , round_num",username , game_id , round_num)

    if game_id == -1 or round_num == -1:
        print("Clearing session due to -1 error")
        return redirect("/clear_session")

    is_last_round = round_num == NUM_ROUNDS

    print("is_last_round",is_last_round)

    if request.method == "POST":
        
        print("got post request")

        if round_num == NUM_ROUNDS:
            print("clear due to round_num == NUM_ROUNDS")
            return redirect("/clear_session")
        elif user_valid_round_end(username, game_id, round_num):
            print("user valud round end is true")
            session["current_game"] = {
                "game_id": game_id,
                "round_num": round_num + 1,
                "game_end": False,
            }
            return redirect("/user/game_play")
        else:
            print("Flash wait current round")
            flash("Please wait for current round to end!")

    print("returning render template ",game_id,round_num,is_last_round)

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

    print("in user result reviewing = ",reviewing)
    
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
