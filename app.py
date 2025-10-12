from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = '234232sdfslkflk'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['MYSQL_HOST'] = "localhost"
app.config['MYSQL_USER'] = "root"
app.config['MYSQL_PASSWORD'] = "Kumar@123"
app.config['MYSQL_DB'] = "flask_database"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mysql = MySQL(app)
login_manage = LoginManager()
login_manage.init_app(app)
bcrypt = Bcrypt(app)


login_manage.login_view = "login"
login_manage.login_message = "Please log in to access this page."


class User(UserMixin):
    def __init__(self, user_id, name, email):
        self.id = user_id
        self.name = name
        self.email = email

    @staticmethod
    def get(user_id):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, name, email FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            return User(result[0], result[1], result[2])
        return None


@login_manage.user_loader
def load_user(user_id):
    return User.get(user_id)


@app.route("/")
def index():
    return render_template("index.html")
@app.route("/about")
def about():
    return render_template("about.html")


@app.route('/login', methods=["GET", "POST"]) 
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        
        cursor = mysql.connection.cursor() 
        cursor.execute('SELECT id, name, email, password FROM users WHERE email = %s', (email,))
        user_data = cursor.fetchone()
        cursor.close()
        
        if user_data and bcrypt.check_password_hash(user_data[3], password):
            user = User(user_data[0], user_data[1], user_data[2])
            login_user(user)

            next_page = request.args.get('next') or session.pop('next', None) 
            return redirect(next_page or url_for('recruiter'))  
    
    return render_template('login.html')




@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO users (name, email, password) VALUES (%s, %s, %s)', (name, email, hashed_password))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/dashboard')
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, job_title, description, requirements FROM jobs")
    jobs = cursor.fetchall()
    cursor.close()

    return render_template("dashboard.html", jobs=jobs)


@app.route("/application")
def application():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM jobs")
    jobs = cursor.fetchall()
    cursor.close()
    return render_template("application.html", jobs=jobs)


@app.route("/recruiter",methods = ["GET"])
@login_required  
def recruiter():
    
    return render_template('recruiter.html')





@app.route("/add_job", methods=["POST"])
@login_required
def add_job():
    job_title = request.form['job_title']
    job_description = request.form['job_description']
    requirements = request.form['requirements'] 

    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO jobs (job_title, description, requirements) VALUES (%s, %s, %s)",
                   (job_title, job_description, requirements))
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('dashboard'))  


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/apply", methods=["GET", "POST"])
@login_required
def apply():
    job_id = request.args.get('job_id')
    job_title = request.args.get('job_title')

    # Fetch job requirements (description)
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT description, requirements FROM jobs WHERE id = %s", (job_id,))
    job_data = cursor.fetchone()
    cursor.close()

    job_description = job_data[0] if job_data else "No description available"
    requirements = job_data[1] if job_data else "Not specified"

    # When page is loaded (GET)
    if request.method == "GET":
        session['job_id'] = job_id
        session['job_title'] = job_title
        session['job_description'] = job_description
        session['requirements'] = requirements
        return render_template("apply.html", job_title=job_title, requirements=requirements)

    # When form is submitted (POST)
    job_id = session.get('job_id')
    job_title = session.get('job_title')
    job_description = session.get('job_description')

    name = request.form['name']
    email = request.form['email']
    dob = request.form['dob']
    mobile = request.form['mobile']

    # Handle file upload
    if 'resume' not in request.files:
        flash("No resume file uploaded!", "danger")
        return redirect(request.url)

    file = request.files['resume']
    resume_path = None

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        resume_path = filename  

   
    cursor = mysql.connection.cursor()
    cursor.execute("""
        INSERT INTO applications 
        (user_id, job_id, name, email, dob, mobile, resume, job_title, job_description)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (current_user.id, job_id, name, email, dob, mobile, resume_path, job_title, job_description))
    mysql.connection.commit()
    cursor.close()

    flash("Your application has been submitted successfully!", "success")

    return render_template("confirmation.html", job_title=job_title, name=name, requirements=requirements)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True,port=8080)
