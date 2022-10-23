from unittest import result
from flask import Flask, render_template,session, request,redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_session import Session
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
PORT = os.getenv('PORT')
DEV = os.getenv('DEV')
DATABASE_URL = os.getenv('DATABASE_URL')

app = Flask(__name__)


if DEV == 'True':
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://lgsjpdlnonitsu:af86d410492325ed8fe6cc92164f9945c08f619204bc44fcdb04283fc1086036@ec2-52-70-45-163.compute-1.amazonaws.com:5432/dcjom0hoefr7df'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = SECRET_KEY


db = SQLAlchemy(app)
db.create_all()

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

class Game(db.Model):
    __tablename__ = 'game'
    game_id = db.Column(db.String(50),primary_key=True)
    game_end = db.Column(db.Boolean , unique=False, default=False)
    date_created= db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"{self.game_id}"

class Choice(db.Model):
    __tablename__ = 'choice'
    id = db.Column(db.Integer, primary_key=True)  
    username = db.Column(db.String(200), nullable = False) 
    game_id = db.Column(db.String(50), nullable = False)
    number_chosen = db.Column(db.Integer , default = 0)

    def __repr__(self) -> str:
        return f"{self.username} - {self.game_id}"

class UserSession(db.Model):
    __tablename__ = 'usersession'
    id = db.Column(db.Integer, primary_key=True)  
    username = db.Column(db.String(200), nullable = False) 
    game_id = db.Column(db.String(50), nullable = False)

def admin_start_game(game_id):
    new_game = Game(game_id = game_id , game_end = False)
    db.session.add(new_game)
    db.session.commit()
    

def admin_end_game(game_id):
    try:
        game = Game.query.filter_by(game_id=game_id).first()
        game.game_end = True
        db.session.commit()
    except:
        return

def user_invalid_game(game_id):
    return Game.query.filter_by(game_id=game_id,game_end=False).first() is None

def user_exists_in_game(username , game_id):
    return UserSession.query.filter_by(username=username,game_id=game_id).first() is not None

def user_add_to_game(username , game_id):
    new_user = UserSession(username = username , game_id = game_id)
    db.session.add(new_user)
    db.session.commit()
    

def user_add_choice(username,game_id,number_chosen):
    if Choice.query.filter_by(username=username,game_id=game_id).first() is not None:
        return

    new_choice  = Choice(username=username,game_id=game_id,number_chosen=number_chosen)
    db.session.add(new_choice)
    db.session.commit()

def get_result(game_id):
    
    freq = dict()
    choices = Choice.query.filter_by(game_id=game_id).all()

    for choice in choices:
        freq[choice.number_chosen] = freq.get(choice.number_chosen,0) + 1

    min_freq = 1e8

    for f in freq.values():
        min_freq = min(min_freq,f)

    result = []

    for choice in choices:
        if freq[choice.number_chosen] == min_freq:
            result.append(choice.username)

    return result

@app.route("/", methods=['GET','POST'])
def public_home():
    if request.method == 'POST':
        username , email , game_id = request.form['username'] , request.form['email'] , request.form['game_id']

        if user_invalid_game(game_id) or user_exists_in_game(username,game_id): 
            return render_template('user_home.html')

        user_add_to_game(username,game_id)

        session['current_user'] = {
            'username' : username,
            'email' : email,
            'game_id' : game_id,
            'game_played' : False
        }

        session['current_game'] = {
            'game_id' : game_id,
            'game_end' : False
        }
 
        return redirect('/user/game_play')

    return render_template('user_home.html')

@app.route("/user/game_play",methods=['GET','POST'])
def user_game_play():

    try:
    
        current_game = session.get('current_game',{'game_id':-1,'game_end':True})
        current_user = session.get('current_user',{'username':'','email':'','game_id':-1,'game_played':False})

        if current_game['game_id']==-1 or current_game['game_end']==True or current_user['game_id']==-1 or current_game['game_id']!=current_user['game_id']:
                return redirect('/clear_session')

        username = current_user['username']
        game_id  = current_game['game_id']

        if current_user['game_played']==True:
            return render_template('user_game_end.html',game_id=game_id,waiting=True)

        if request.method == 'POST':
                number_chosen = request.form['number_chosen']

                user_add_choice(username,game_id,number_chosen)
                session['current_user']['game_played'] = True
                return render_template('user_game_end.html',game_id=game_id,waiting=True)
    
    except Exception as E:
        pass

    return render_template('user_game_play.html',game_id=-1,waiting=False)


@app.route("/admin", methods=['GET','POST'])
def admin_home():

    if request.method == 'POST':
        admin_username = request.form['username']
        admin_password = request.form['password']
        print(admin_username,admin_password)
        if admin_username==ADMIN_USERNAME and admin_password==ADMIN_PASSWORD:
            session['current_admin_username'] = admin_username 
            return redirect('/admin/game_start')

    return render_template('admin_home.html') 

@app.route("/admin/game_start", methods=['GET','POST'])
def admin_game_start():

    if session.get('current_admin_username','')!=ADMIN_USERNAME:
        return redirect('/')

    if request.method == 'POST':

        current_game=session.get('current_game',{'game_id':-1,'game_end':True})

        if current_game['game_id']!=-1 or current_game['game_end']==False:
            
            game_id = current_game['game_id']

            admin_end_game(game_id)
            session['current_game'] = {'game_id':-1,'game_end':True}

            return render_template('admin_game_start.html') 
        
        
        try:
            game_id = request.form['game_id']
            
            admin_start_game(game_id)
            session['current_game'] = {
                'game_id' : game_id,
                'game_end' : False
            }

            return redirect('/admin/game_play')

        except Exception as E:
            print(E)
            session['current_game'] = {
                'game_id' : -1,
                'game_end' : True
            }
        
    return render_template('admin_game_start.html') 

@app.route("/admin/game_play", methods=['GET','POST'])
def admin_game_play():

    if session.get('current_admin_username','')!=ADMIN_USERNAME:
        return redirect('/')

    current_game=session.get('current_game',{'game_id':-1,'game_end':True})
    if current_game['game_id']==-1 or current_game['game_end']==True:
        session['current_game'] = {'game_id':-1,'game_end':True}
        return redirect('/admin/game_start') 

    return render_template('admin_game_play.html',current_game=session.get('current_game',{'game_id':-1,'game_end':True}))

@app.route("/clear_session",methods=['GET','POST'])
def clear_session():

    if request.method=='POST' and session.get('current_admin_username','')==ADMIN_USERNAME:

        current_game=session.get('current_game',{'game_id':-1,'game_end':True})
        game_id = current_game['game_id']
        admin_end_game(game_id)

        session['current_admin_username'] = ""
    
    session['current_user'] = {'username':'','email':'','game_id':-1,'game_played':False}
    session['current_game'] = {'game_id':-1,'game_end':True}

    return redirect('/')

@app.route('/game_end' , methods=['GET','POST'])
def game_end():
    if request.method == 'POST':
        try:
            current_game=session.get('current_game',{'game_id':-1,'game_end':True})
            game_id = str(request.form['game_id'])


            if current_game['game_id']==game_id:
                admin_end_game(game_id)
                return "success"
        except Exception as E:
            print(E)
            pass

    return "fail"

@app.route('/result/<string:game_id>' , methods=['GET','POST'])
def show_result(game_id):

    session['current_game'] = {'game_id':-1,'game_end':True}

    result = get_result(game_id)
    return render_template('result.html',game_id=game_id,result=result)

if __name__ == "__main__":
    db.create_all()
    app.run(debug=True,port=PORT)
