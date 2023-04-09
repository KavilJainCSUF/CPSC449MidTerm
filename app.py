from datetime import datetime, timedelta
from functools import wraps
import os
from werkzeug.utils import secure_filename
import re
import jwt
from flask import Flask, abort, jsonify, redirect, render_template, request, url_for
# from flask_restful import Api, Resource
# from flask_swagger import swagger
# from flask_swagger_ui import get_swaggerui_blueprint
import pymysql

app = Flask(__name__)

app.config['secret_key'] = 'midterm'
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = ['.pdf', '.docx']
UPLOAD_PATH = 'uploaded_resume'
app.config['UPLOAD_PATH'] = UPLOAD_PATH
if not os.path.exists(UPLOAD_PATH):
    os.makedirs(UPLOAD_PATH)


conn = pymysql.connect(
    host='localhost',
    user='root',
    password='Kavil@514',
    db='job_board',
    cursorclass=pymysql.cursors.DictCursor
)

cur = conn.cursor()


def token_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split()[1]
        if not token:
            return jsonify({'Alert!': 'Token is missing!'}), 401
        try:
            payload = jwt.decode(
                token, app.config['secret_key'], algorithms=["HS256"])
            print(payload)
            cur.execute(
                'SELECT * FROM USERS WHERE id=%s', (payload['id']))
            current_user = cur.fetchone()
            print(current_user)
            if current_user is None:
                return jsonify({"Alert!": "Invalid Authorization Token"}), 402
        except Exception as error:
            print("{0}", error)
            return jsonify({'Alert!': 'Something went wrong !'}), 500
        return func(current_user, *args, **kwargs)
    return decorated



@app.route('/')
def index():
    """Home Page"""
    return render_template('index.html')

@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    """User Login"""
    msg = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cur.execute(
            'SELECT * from users WHERE email = %s AND password = %s', (email, password))
        conn.commit()
        user = cur.fetchone()
        if user:
            token = jwt.encode({
                'id': user['id'],
                'expiration': str(datetime.utcnow() + timedelta(seconds=600))
            }, app.config['secret_key'],
                algorithm="HS256")
            msg = 'Welcome {0} - {1} !'.format(user['name'], user['id'])
            # return render_template('index.html', msg=msg)
            return jsonify({'token': token})
        else:
            msg = 'Incorrect email or password!'
    return render_template('login.html', msg=msg)


@app.route('/user/logout', methods = ['POST'])
@token_required
def user_logout(current_user):
    """User Logout"""
    print(current_user)
    return jsonify({'message': 'Logged out successfully.'}), 200


@app.route('/user/register', methods=['POST'])
def register_user():
    """Register a user"""
    msg = ''
    if request.method == 'POST' and 'name' in request.form and 'email' in request.form and 'password' in request.form and 'is_employer' in request.form:
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        is_employer = request.form['is_employer']
        cur.execute('SELECT * from users WHERE email = %s', email)
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


@app.route('/job_listings')
def get_job_listings():
    """List of available Jobs"""
    try:
        cur.execute("SELECT * FROM JobListing")
        jobs = cur.fetchall()
        if jobs:
            return jsonify(jobs)
        else:
            abort(404)
    except Exception as e:
        abort(500, e)


@app.route('/create_jobs', methods=['POST'])
@token_required
def create_jobs(current_user):
    """Here Employers create Jobs"""
    msg = ''
    try:
        if current_user['is_employer'] == 1:
            employerId = current_user['id']
            if 'company_name' in request.form and 'company_description' in request.form and 'title' in request.form and 'title_description' in request.form and 'location' in request.form and 'salary' in request.form:
                company_name = request.form['company_name']
                company_description = request.form['company_description']
                title = request.form.get('title')
                # title = request.form['title']
                title_description = request.form['title_description']
                location = request.form['location']
                salary = request.form['salary']
                employer_id = employerId
                cur.execute('INSERT INTO joblisting VALUES (NULL, %s, %s, %s, %s, %s, %s, %s)', (
                    company_name, company_description, title, title_description, location, salary, employer_id))
                conn.commit()
                msg = 'Job is Successfully added'
                return jsonify({ "message" : msg})
            else:
                return jsonify({"Alert!":"Please fill the form"}), 401
        else:
            return jsonify({"Alert!":"You are not allowed to add a job"}), 402
    except Exception as e:
        abort(500, e)


@app.route('/user/apply_job', methods=['POST'])
@token_required
def apply_job(current_user):
    """User can use this api to apply for job"""
    msg = ''
    try:
        if current_user:
            userId = current_user['id']
            if 'job_listing_id' in request.form and 'cover_letter' in request.form and 'resume' in request.files:
                job_listing_id = request.form['job_listing_id']
                cover_letter = request.form['cover_letter']
                resume = request.files['resume']
                filename = secure_filename(resume.filename)
                if filename != '':
                    file_ext = os.path.splitext(filename)[1]
                    if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                        abort(400)
                    resume.save(os.path.join(
                        app.config['UPLOAD_PATH'], filename))
                user_id = userId
                cur.execute('INSERT INTO jobapplication VALUES(NULL, %s, %s, %s, %s)',
                            (user_id, job_listing_id, cover_letter, resume))
                conn.commit()
                msg = 'Application is sent successfully'
                return render_template('index.html', msg=msg)
            else:
                abort(410)
        else:
            msg = 'Please Login'
            return redirect(url_for('user_login'))
    except Exception as e:
        abort(500, e)


if __name__ == "__main__":
    app.run(host="localhost", port=int("5000"))
