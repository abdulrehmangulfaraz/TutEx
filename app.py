from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
import sqlite3
import logging
import folium
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'
# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS student_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            area TEXT,
            board TEXT,
            subjects TEXT,
            fee INTEGER,
            accepted_by TEXT,
            status TEXT DEFAULT 'Pending Approval',
            verified INTEGER DEFAULT 0,
            tutor_approved INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/how-it-works')
def how_it_works():
    return render_template('how_it_works.html')

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    # Query database for tutors
    conn = get_db_connection()
    cursor = conn.cursor()
    tutors = cursor.execute(
        "SELECT * FROM tutors WHERE qualification LIKE ?",
        (f'%{query}%',)
    ).fetchall()
    conn.close()
    return render_template('search_results.html', tutors=tutors, query=query)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        user_type = request.form.get('user_type')
        if username and user_type in ['student', 'tutor', 'admin']:
            session['user'] = {
                'username': username,
                'user_type': user_type
            }
            flash("Logged in successfully!", "success")
            if user_type == 'student':
                return redirect(url_for('student'))
            elif user_type == 'admin':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('tutor_dashboard'))
        else:
            flash("Invalid login details.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/student', methods=['GET', 'POST'])
def student():
    if 'user' not in session or session['user']['user_type'] != 'student':
        flash("Please log in as a student to access this page.", "warning")
        return redirect(url_for('login'))
    if request.method == 'POST':
        try:
            username = session['user']['username']
            area = request.form['area']
            board = request.form['board']
            subjects = request.form.getlist('subjects')
            fee = calculate_fee(area, board, subjects)
            subjects_str = ", ".join(subjects) if isinstance(subjects, list) else subjects
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO student_leads (username, area, board, subjects, fee)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, area, board, subjects_str, fee))
            conn.commit()
            flash("Your form has been submitted successfully!", "success")
        except Exception as e:
            logger.error(f"Error submitting student lead: {str(e)}")
            flash("Error occurred. Please try again.", "danger")
        finally:
            conn.close()
        return redirect(url_for('student'))
    return render_template('student.html')

@app.route('/tutor')
def tutor():
    return render_template('tutor_dashboard.html')

@app.route('/courses')
def courses():
    return render_template('courses.html')

@app.route('/submit')
def submit():
    return render_template('submit.html')

def calculate_fee(area, board, subjects):
    # Define your fee calculation logic here
    area_fee = 2000  # Default
    if area == "DHA":
        area_fee = 8000
    elif area in ["Gulshan-e-Iqbal", "PECHS", "Saddar"]:
        area_fee = 6000

    board_fee = 2000  # Default
    if board in ["Cambridge O'Levels", "Cambridge A'Levels", "ACCA", "ICAP"]:
        board_fee = 5000

    premium_subjects = ["Mathematics", "Physics", "Chemistry", "Biology", "Audit"]
    total_fee = area_fee + board_fee  # Base fee

    for subject in subjects:
        subject_name = subject.split(' - ')[0]  # Get subject name without code
        if subject_name in premium_subjects:
            subject_fee = 8000
        else:
            subject_fee = 5000

        # Apply cap per subject
        cap = area_fee + board_fee
        if subject_fee > cap:
            subject_fee = cap

        total_fee += subject_fee

    return total_fee

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Database setup
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        user_type TEXT NOT NULL,
        email TEXT UNIQUE,
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create tutors table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tutors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        full_name TEXT NOT NULL,
        father_name TEXT,
        cnic_front TEXT,
        cnic_back TEXT,
        qualification TEXT,
        status TEXT DEFAULT 'pending',
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create students table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        full_name TEXT NOT NULL,
        relation TEXT,
        status TEXT DEFAULT 'pending',
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Helper functions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_file(file, field_name):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = str(uuid.uuid4()) + os.path.splitext(filename)[1]
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        return unique_filename
    return None

@app.route('/tutor_dashboard', methods=['GET', 'POST'])
def tutor_dashboard():
    if 'user' not in session or session['user']['user_type'] != 'tutor':
        flash('Please log in as a tutor to access the dashboard.', 'danger')
        return redirect(url_for('login'))
    leads = []
    selected_area = request.form.get('area') if request.method == 'POST' else None
    selected_board = request.form.get('board') if request.method == 'POST' else None
    selected_subject = request.form.get('subject') if request.method == 'POST' else None
    query = '''SELECT * FROM student_leads WHERE verified = 1 AND accepted_by IS NULL'''
    params = []
    if selected_area:
        query += ' AND area = ?'
        params.append(selected_area)
    if selected_board:
        query += ' AND board = ?'
        params.append(selected_board)
    if selected_subject:
        query += ' AND subjects LIKE ?'
        params.append(f'%{selected_subject}%')
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            leads = cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching leads: {str(e)}")
            flash("Error loading leads. Please try again.", "danger")
        finally:
            conn.close()
    return render_template(
        'tutor_dashboard.html',
        leads=leads,
        selected_area=selected_area,
        selected_board=selected_board,
        selected_subject=selected_subject,
        fee=request.form.get('totalfee') or 0
    )

@app.route('/accept_lead/<int:lead_id>', methods=['POST'])
def accept_lead(lead_id):
    if 'user' not in session or session['user']['user_type'] != 'tutor':
        return jsonify({"success": False, "message": "Tutor not logged in"}), 401
    tutor_username = session['user']['username']
    conn = get_db_connection()
    try:
        lead = conn.execute("SELECT * FROM student_leads WHERE id = ?", (lead_id,)).fetchone()
        if not lead:
            return jsonify({"success": False, "message": "Lead not found"}), 404
        if lead['accepted_by']:
            return jsonify({"success": False, "message": "Lead already requested or accepted"}), 400
        conn.execute(
            "UPDATE student_leads SET accepted_by = ?, status = 'Pending Admin Approval' WHERE id = ?",
            (tutor_username, lead_id)
        )
        conn.commit()
        logger.info(f"Lead {lead_id} requested by tutor {tutor_username}")
        return jsonify({"success": True, "message": "Request sent to admin"})
    except Exception as e:
        logger.error(f"Error in accept_lead: {str(e)}")
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        conn.close()

@app.route('/admin')
def admin():
    if 'user' not in session or session['user']['user_type'] != 'admin':
        flash("Please log in as a admin to access this page.", "warning")
        return redirect(url_for('login'))
    try:
        conn = get_db_connection()
        unverified_leads = conn.execute("SELECT * FROM student_leads WHERE verified = 0").fetchall()
        pending_requests = conn.execute(
            "SELECT * FROM student_leads WHERE verified = 1 AND accepted_by IS NOT NULL AND tutor_approved = 0"
        ).fetchall()
        return render_template('admin.html', unverified_leads=unverified_leads, pending_requests=pending_requests)
    except Exception as e:
        logger.error(f"Error loading admin: {str(e)}")
        flash("Error loading admin panel", "danger")
        return redirect(url_for('home'))
    finally:
        conn.close()

@app.route('/verify_lead/<int:lead_id>', methods=['POST'])
def verify_lead(lead_id):
    try:
        conn = get_db_connection()
        conn.execute("UPDATE student_leads SET verified = 1 WHERE id = ?", (lead_id,))
        conn.commit()
        flash("Tuition verified successfully!", "success")
    except Exception as e:
        logger.error(f"Error verifying lead: {str(e)}")
        flash("Error verifying tuition", "danger")
    finally:
        conn.close()
    return redirect(url_for('admin'))

@app.route('/approve_tutor_match/<int:lead_id>', methods=['POST'])
def approve_tutor_match(lead_id):
    try:
        conn = get_db_connection()
        conn.execute(
            "UPDATE student_leads SET tutor_approved = 1, status = 'Accepted' WHERE id = ?",
            (lead_id,)
        )
        conn.commit()
        flash("Tutor match approved!", "success")
    except Exception as e:
        logger.error(f"Error approving match: {str(e)}")
        flash("Error approving tutor match", "danger")
    finally:
        conn.close()
    return redirect(url_for('admin'))

@app.route('/map')
def map_view():
    map_center = [35.6762, 139.6503]
    mymap = folium.Map(location=map_center, zoom_start=16)
    folium.Marker(
        [35.6762, 139.6503],
        popup="Tokyo",
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(mymap)
    mymap.save("templates/tutor_map.html")  # Save map to template folder
    return render_template("main.html")

# Initialize DB at startup
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True)