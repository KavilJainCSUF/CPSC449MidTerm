from datetime import timedelta
import re
from flask import Flask, redirect, render_template, request, session, url_for
# from flask_restful import Api, Resource
# from flask_swagger import swagger
# from flask_swagger_ui import get_swaggerui_blueprint
import pymysql

app = Flask(__name__)

app.secret_key = 'midterm'

app.permanent_session_lifetime = timedelta(seconds=100)

conn = pymysql.connect(
    host='localhost',
    user='root',
    password='Kavil@514',
    db='job_board',
    cursorclass=pymysql.cursors.DictCursor
)

cur = conn.cursor()


@app.route('/')
def index():
    """Home Page"""
    return render_template("index.html")


@app.route('/user/login', methods=['GET','POST'])
def user_login():
    """User Login"""
    msg=''
    if request.method=='POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cur.execute(
            'SELECT * from users WHERE email = %s AND password = %s', (email, password))
        conn.commit()
        user = cur.fetchone()
        if user:
            session.permanent = True
            session['loggedin'] = True
            session['id'] = user['id']
            session['username'] = user['name']
            msg = 'Welcome {0} - {1} !'.format(user['name'], user['id'])
            return render_template('index.html', msg=msg)
        else:
            msg = 'Incorrect email or password!'
    return render_template('login.html', msg=msg)


@app.route('/user/logout')
def user_logout():
    """User Logout"""
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('user_login'))


@app.route('/user/register', methods=['POST'])
def register_user():
    """Register a user"""
    msg = ''
    if request.method == 'POST' and 'name' in request.form and 'email' in request.form and 'password' in request.form and 'is_employer' in request.form:
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        is_employer = request.form['is_employer']
        cur.execute('SELECT * from users WHERE name = %s', name)
        user = cur.fetchone()
        conn.commit()
        if user:
            msg = 'Account Already Exists!'
        elif not re.match(r'^[a-zA-Z]{4,19}$', name):
            msg = 'Invalid Name. It should be at least 4 characters long and less than 19 characters.'
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            msg = 'Invalid Email Address'
        elif not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', password):
            msg = 'Invalid Password. Password must be at least 8 characters long, contain at least one uppercase letter, contain at least one lowercase letter, at least one digit, can contain Special Characters(@$!%*?&)'
        elif not re.match(r'^[01]+$', is_employer):
            msg = 'Press 1 if an employer or press 0.'
        else:
            cur.execute('INSERT INTO users VALUES (NULL, %s, %s, %s, %s)',
                        (name, email, password, is_employer))
            conn.commit()
            msg = 'You have registered Successfully!'
            return render_template('login.html', msg=msg)
    elif request.method == 'POST':
        msg = 'Please fill out the form!'
    return render_template('register.html', msg=msg)


if __name__ == "__main__":
    app.run(host="localhost", port=int("5000"))
