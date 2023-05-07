import base64
from datetime import datetime, timedelta
from io import BytesIO
from dotenv import load_dotenv
from functools import wraps
import os
import re
import jwt
import pymysql
from flask import Flask, Response, jsonify, make_response, render_template, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
from flask_cors import CORS


# Load environment variables from the .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

cors = CORS(app, resources={r"/*": {"origins": "*"}})

# Set Flask app configurations
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
app.config['VIDEO_MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = ['.pdf', '.docx']
UPLOAD_PATH = 'uploaded_resume'
app.config['UPLOAD_PATH'] = UPLOAD_PATH
app.config['VIDEO_UPLOAD_EXTENSIONS'] = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.m4v', '.3gp']
VIDEO_UPLOAD_PATH = 'uploaded_video'
app.config['VIDEO_UPLOAD_PATH'] = VIDEO_UPLOAD_PATH

# Create the UPLOAD_PATH directory if it doesn't exist
if not os.path.exists(UPLOAD_PATH):
    os.makedirs(UPLOAD_PATH)

# Initialize database connection
conn = pymysql.connect(
    host=os.environ['DB_HOST'],
    user=os.environ['DB_USER'],
    password=os.environ['DB_PASSWORD'],
    db=os.environ['DB_NAME'],
    cursorclass=pymysql.cursors.DictCursor
)

# Create a cursor object to interact with the database
cur = conn.cursor()

@app.errorhandler(404)
def page_not_found(error):
    """Handle 404 error"""
    return render_template('404.html'), 404

@app.errorhandler(401)
def unauthorized_user(error):
    """Handle 401 error"""
    return render_template('401.html'), 401

# Require a valid JWT token to access a route
def token_required(func):
    """Require a valid JWT token to access a route"""
    @wraps(func)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split()[1]
        if not token:
            return jsonify({'Forbidden!': 'Token is missing!'}), 403
        try:
            payload = jwt.decode(
                token, app.config['SECRET_KEY'], algorithms=["HS256"])
            cur.execute(
                'SELECT * FROM USERS WHERE id=%s', (payload['id']))
            current_user = cur.fetchone()
            if current_user is None:
                return jsonify({"Invalid!": "Invalid Authorization Token or Expired"}), 498
        except Exception as error:
            return jsonify({'Error!': error}), 500
        return func(current_user, *args, **kwargs)
    return decorated

# public route - home page
@app.route('/')
def home():
    """Render home page"""
    return render_template('index.html')

# public route - User registration 
@app.route('/user/register', methods=['POST'])
def register_user():
    """Endpoint for registering a user."""
    msg = ''
    if request.method == 'POST' and 'name' in request.form and 'email' in request.form and 'password' in request.form and 'is_employer' in request.form:
        # Get user registration details from the form
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        is_employer = request.form['is_employer']
        
        # Check if user with given email exists
        cur.execute('SELECT * from users WHERE email = %s', email)
        user = cur.fetchone()
        conn.commit()
        if user:
            return jsonify({'Conflict!':'Account Already Exists!'}), 409
        elif not re.match(r'^[a-zA-Z]{4,19}$', name):
            return jsonify({'Bad Request': 'Invalid Name. It should be at least 4 characters long and less than 19 characters'}), 400
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return jsonify({'Bad Request': 'Invalid Email'}), 400
        elif not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', password):
            return jsonify({'Bad Request': 'Invalid Password. Password must be at least 8 characters long, contain at least one uppercase letter, contain at least one lowercase letter, at least one digit, contains at least one Special Characters(@$!%*?&)'}), 400
        elif not re.match(r'^[01]+$', is_employer):
            return jsonify({'Bad Request': 'Invalid entry, enter 1 if employer else 0'}), 400
        else:
            # Register user in the database
            cur.execute('INSERT INTO users VALUES (NULL, %s, %s, %s, %s)',
                        (name, email, password, is_employer))
            conn.commit()
            msg = 'You have registered Successfully!'
            return jsonify({"Success":msg}),200
    elif request.method == 'POST':
        return jsonify({'Bad Request': 'Please fill out the form!'}), 400
    return render_template('register.html', msg=msg)

# public route - List of all available jobs
@app.route('/job_listings')
def get_job_listings():
    """Endpoint for getting the list of available jobs."""
    column_name = request.args.get('column_name')
    value = request.args.get('value')
    try:
        # Fetch available jobs from database
        cur.execute("SELECT * FROM JobListing")
        jobs = cur.fetchall()
        if jobs:
            if column_name is None or value is None:
                return jsonify({"Success!":jobs}), 200
            else:
                print("I am called")
                filtered_jobs = [job for job in jobs if job.get(column_name) == value]
                return jsonify({"Success!":filtered_jobs}), 200
        else:
            return jsonify({"Alert!":"No jobs found"}), 403
    except Exception as error:
        return jsonify({"Error!": str(error)}), 500    

# public route - user login
@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    """Handle user login"""
    msg = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cur.execute(
            'SELECT * from users WHERE email = %s AND password = %s', (email, password))
        conn.commit()
        user = cur.fetchone()
        if user:
            # Generate a JWT token for the user
            token = jwt.encode({
                'id': user['id'],
                'expiration': str(datetime.utcnow() + timedelta(seconds=600))
            }, app.config['SECRET_KEY'],
                algorithm="HS256")
            msg = 'Welcome {0} - {1} !'.format(user['name'], user['id'])
            return jsonify({'token': token}), 200
        else:
            return jsonify({'Bad Request': 'Incorrect email or password!'}), 403
    return render_template('login.html', msg=msg)
    
        
# private Route - Emloyers create jobs using this endpoint
@app.route('/create_jobs', methods=['POST'])
@token_required
def create_jobs(current_user):
    """Here Employers create Jobs"""
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
                return jsonify({ "message" : msg}), 200
            else:
                return jsonify({"Bad Request!":"Please fill the form"}), 409
        else:
            return jsonify({"Unauthorized!":"You are not allowed to add a job"}), 401
    except Exception as error:
        return jsonify({"Error!": str(error)}), 500


# private Route - users apply for jobs at this endpoint
@app.route('/user/apply_job', methods=['POST'])
@token_required
def apply_job(current_user):
    """User can use this api to apply for job"""
    try:
        if current_user:
            userId = current_user['id']
            print("HELLO")
            if 'job_listing_id' in request.form and 'resume' in request.files and 'video' in request.files:
                job_listing_id = request.form['job_listing_id']
                resume = request.files['resume']
                video = request.files['video']
                filename = secure_filename(resume.filename)
                video_file = secure_filename(video.filename)
                resume.save()
                video.save()
                print("I am here")
                if filename != '':
                    file_ext = os.path.splitext(filename)[1]
                    if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                        return jsonify({"Bad Request": "Please upload .pdf or .docx files only"}), 403
                    if len(resume.read()) > app.config['MAX_CONTENT_LENGTH']:
                        return jsonify({"Alert": "File too large. less than 2MB"}), 413
                    resume.save(os.path.join(
                        app.config['UPLOAD_PATH'], filename))
                if video_file != '':
                    file_ext = os.path.splitext(video_file)[1]
                    if file_ext not in app.config['VIDEO_UPLOAD_EXTENSIONS']:
                        return jsonify({"Bad Request": "Please upload .mp4 .avi .mov .wmv .flv .mkv .webm .m4v .3gp files only"}), 403
                    if len(video.read()) > app.config['VIDEO_MAX_CONTENT_LENGTH']:
                        return jsonify({"Alert": "File too large. less than 500MB"}), 413
                    video.save(os.path.join(
                        app.config['VIDEO_UPLOAD_PATH'], video_file))
                user_id = userId
                cur.execute('INSERT INTO jobapplication VALUES(NULL, %s, %s, %s, %s, %s, %s)',
                            (user_id, job_listing_id, resume, resume.read(), video, video.read()))
                conn.commit()
                return jsonify({"Success!":"Application is sent successfully"}), 200
            else:
                return jsonify({"Bad Request!":"Please enter the form details"}), 403
        else:
            return jsonify({"Unauthorized!": "Cannot apply for this job"}), 405
    except Exception as error:
        return jsonify({"Error": str(error)}), 500


# private route - user logout
@app.route('/user/logout', methods = ['POST'])
@token_required
def user_logout(current_user):
    """User Logout"""
    return jsonify({'message': 'Logged out successfully.'}), 200

@app.route('/user/get_video', methods = ['GET'])
@token_required
def get_video(current_user):
    """Video of User"""
    try:
        if current_user:
            user_id = current_user['id']
            print(user_id)
            cur.execute('SELECT video from Jobapplication WHERE user_id = %s', user_id)
            video_data = cur.fetchone()['video']
            return Response(video_data,  mimetype = 'video/avi')
        else:
            return jsonify({"Error": "User not found"}), 400
    except Exception as error:
        return jsonify({"Error": str(error)}), 500

@app.route('/user/get_resume', methods = ['GET'])
@token_required
def get_resume(current_user):
    """Resume of User"""
    try:
        if current_user:
            user_id = current_user['id']
            print(user_id)
            cur.execute('SELECT resume_data from Jobapplication WHERE user_id = %s', user_id)
            for x in cur.fetchall():
                data_v = x
                break
            return send_file(BytesIO(data_v), download_name='resume.pdf', as_attachment=True)
        else:
            return jsonify({"Error": "User not found"}), 400
    except Exception as error:
        return jsonify({"Error": str(error)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=8080)
