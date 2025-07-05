from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
import logging
import folium
import os
import uuid
from werkzeug.utils import secure_filename
from config import Config
from models import db, User, Tutor, Student, StudentLead

app = Flask(__name__)
app.config.from_object(Config)  # Load configuration from config.py
db.init_app(app)  # Initialize SQLAlchemy with the app

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/how-it-works')
def how_it_works():
    return render_template('how_it_works.html')

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    tutors = Tutor.query.filter(Tutor.qualification.ilike(f'%{query}%')).all()
    return render_template('search_results.html', tutors=tutors, query=query)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        user_type = request.form.get('user_type')
        user = User.query.filter_by(username=username).first()
        if user and user.user_type == user_type:
            # Note: Add password hashing check here (e.g., using werkzeug.security)
            session['user'] = {'username': username, 'user_type': user_type}
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
            new_lead = StudentLead(username=username, area=area, board=board, subjects=subjects_str, fee=fee)
            db.session.add(new_lead)
            db.session.commit()
            flash("Your form has been submitted successfully!", "success")
        except Exception as e:
            logger.error(f"Error submitting student lead: {str(e)}")
            db.session.rollback()
            flash("Error occurred. Please try again.", "danger")
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

        cap = area_fee + board_fee
        if subject_fee > cap:
            subject_fee = cap

        total_fee += subject_fee

    return total_fee

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

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
    query = StudentLead.query.filter_by(verified=1, accepted_by=None)
    if selected_area:
        query = query.filter_by(area=selected_area)
    if selected_board:
        query = query.filter_by(board=selected_board)
    if selected_subject:
        query = query.filter(StudentLead.subjects.ilike(f'%{selected_subject}%'))
    if request.method == 'POST':
        try:
            leads = query.all()
        except Exception as e:
            logger.error(f"Error fetching leads: {str(e)}")
            flash("Error loading leads. Please try again.", "danger")
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
    try:
        lead = StudentLead.query.get_or_404(lead_id)
        if lead.accepted_by:
            return jsonify({"success": False, "message": "Lead already requested or accepted"}), 400
        lead.accepted_by = tutor_username
        lead.status = 'Pending Admin Approval'
        db.session.commit()
        logger.info(f"Lead {lead_id} requested by tutor {tutor_username}")
        return jsonify({"success": True, "message": "Request sent to admin"})
    except Exception as e:
        logger.error(f"Error in accept_lead: {str(e)}")
        db.session.rollback()
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route('/admin')
def admin():
    if 'user' not in session or session['user']['user_type'] != 'admin':
        flash("Please log in as a admin to access this page.", "warning")
        return redirect(url_for('login'))
    try:
        unverified_leads = StudentLead.query.filter_by(verified=0).all()
        pending_requests = StudentLead.query.filter_by(verified=1, accepted_by=None, tutor_approved=0).all()
        return render_template('admin.html', unverified_leads=unverified_leads, pending_requests=pending_requests)
    except Exception as e:
        logger.error(f"Error loading admin: {str(e)}")
        flash("Error loading admin panel", "danger")
        return redirect(url_for('home'))

@app.route('/verify_lead/<int:lead_id>', methods=['POST'])
def verify_lead(lead_id):
    try:
        lead = StudentLead.query.get_or_404(lead_id)
        lead.verified = 1
        db.session.commit()
        flash("Tuition verified successfully!", "success")
    except Exception as e:
        logger.error(f"Error verifying lead: {str(e)}")
        db.session.rollback()
        flash("Error verifying tuition", "danger")
    return redirect(url_for('admin'))

@app.route('/approve_tutor_match/<int:lead_id>', methods=['POST'])
def approve_tutor_match(lead_id):
    try:
        lead = StudentLead.query.get_or_404(lead_id)
        lead.tutor_approved = 1
        lead.status = 'Accepted'
        db.session.commit()
        flash("Tutor match approved!", "success")
    except Exception as e:
        logger.error(f"Error approving match: {str(e)}")
        db.session.rollback()
        flash("Error approving tutor match", "danger")
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
    mymap.save("templates/tutor_map.html")
    return render_template("main.html")

if __name__ == '__main__':
    app.run(debug=True)