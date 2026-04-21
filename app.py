from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import qrcode
import io
import csv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import os
import secrets
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///events.db')
# Handle Render's PostgreSQL URL (standardizing 'postgres://' to 'postgresql://')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your-app-password')
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'

# Upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# Models
class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    venue = db.Column(db.String(200), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    registrations = db.relationship('Registration', backref='event', lazy=True, cascade='all, delete-orphan')
    waitlist = db.relationship('Waitlist', backref='event', lazy=True, cascade='all, delete-orphan')
    # Add relationship to folders
    folders = db.relationship('EventFolder', backref='event', lazy=True, cascade='all, delete-orphan')
    
    def get_registered_count(self):
        return Registration.query.filter_by(event_id=self.id).count()
    
    def is_full(self):
        return self.get_registered_count() >= self.capacity
    
    def get_available_spots(self):
        return max(0, self.capacity - self.get_registered_count())

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    student_id = db.Column(db.String(50), unique=True, nullable=False)
    registrations = db.relationship('Registration', backref='student', lazy=True)
    waitlist_entries = db.relationship('Waitlist', backref='student', lazy=True)

class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    qr_code_token = db.Column(db.String(100), unique=True, nullable=False)
    checked_in = db.Column(db.Boolean, default=False)
    check_in_time = db.Column(db.DateTime, nullable=True)

class Waitlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    added_date = db.Column(db.DateTime, default=datetime.utcnow)
    position = db.Column(db.Integer, nullable=False)

class EventFolder(db.Model):
    __tablename__ = 'event_folder'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    folder_name = db.Column(db.String(200), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    # Add relationship to images
    images = db.relationship('FolderImage', backref='folder', lazy=True, cascade='all, delete-orphan')
    
class FolderImage(db.Model):
    __tablename__ = 'folder_image'
    id = db.Column(db.Integer, primary_key=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('event_folder.id'), nullable=False)
    image_path = db.Column(db.String(500), nullable=False)
    caption = db.Column(db.String(500))
    uploaded_date = db.Column(db.DateTime, default=datetime.utcnow)
    # Remove the relationship here to avoid circular dependency

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Email utility function
def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/events')
def events():
    search_query = request.args.get('search', '')
    filter_date = request.args.get('date', '')
    
    query = Event.query
    
    if search_query:
        query = query.filter(
            (Event.title.contains(search_query)) | 
            (Event.description.contains(search_query)) |
            (Event.venue.contains(search_query))
        )
    
    if filter_date:
        try:
            filter_datetime = datetime.strptime(filter_date, '%Y-%m-%d')
            query = query.filter(db.func.date(Event.date) == filter_datetime.date())
        except ValueError:
            pass
    
    events = query.filter(Event.date >= datetime.utcnow()).order_by(Event.date.asc()).all()
    return render_template('events.html', events=events, search_query=search_query, filter_date=filter_date)

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    return render_template('event_detail.html', event=event)

@app.route('/register/<int:event_id>', methods=['GET', 'POST'])
def register(event_id):
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        student_id_input = request.form.get('student_id')
        
        # Check if student exists
        student = Student.query.filter_by(student_id=student_id_input).first()
        if not student:
            student = Student(name=name, email=email, student_id=student_id_input)
            db.session.add(student)
            db.session.commit()
        
        # Check if already registered
        existing_reg = Registration.query.filter_by(event_id=event_id, student_id=student.id).first()
        existing_waitlist = Waitlist.query.filter_by(event_id=event_id, student_id=student.id).first()
        
        if existing_reg:
            flash('You are already registered for this event!', 'warning')
            return redirect(url_for('event_detail', event_id=event_id))
        
        if existing_waitlist:
            flash('You are already on the waitlist for this event!', 'warning')
            return redirect(url_for('event_detail', event_id=event_id))
        
        # Check capacity
        if event.is_full():
            # Add to waitlist
            position = Waitlist.query.filter_by(event_id=event_id).count() + 1
            waitlist_entry = Waitlist(event_id=event_id, student_id=student.id, position=position)
            db.session.add(waitlist_entry)
            db.session.commit()
            
            # Send waitlist email
            email_body = f"""
            <h2>Waitlist Confirmation</h2>
            <p>Dear {name},</p>
            <p>The event <strong>{event.title}</strong> is currently full.</p>
            <p>You have been added to the waitlist at position <strong>{position}</strong>.</p>
            <p>We will notify you if a spot becomes available.</p>
            <p>Event Details:</p>
            <ul>
                <li>Date: {event.date.strftime('%B %d, %Y at %I:%M %p')}</li>
                <li>Venue: {event.venue}</li>
            </ul>
            """
            send_email(email, f'Waitlist - {event.title}', email_body)
            
            flash(f'Event is full! You have been added to the waitlist at position {position}.', 'info')
        else:
            # Register student
            qr_token = secrets.token_urlsafe(32)
            registration = Registration(
                event_id=event_id,
                student_id=student.id,
                qr_code_token=qr_token
            )
            db.session.add(registration)
            db.session.commit()
            
            # Send confirmation email
            qr_url = url_for('generate_qr', token=qr_token, _external=True)
            email_body = f"""
            <h2>Registration Confirmed!</h2>
            <p>Dear {name},</p>
            <p>You have successfully registered for <strong>{event.title}</strong>.</p>
            <p>Event Details:</p>
            <ul>
                <li>Date: {event.date.strftime('%B %d, %Y at %I:%M %p')}</li>
                <li>Venue: {event.venue}</li>
            </ul>
            <p>Your QR Code: <a href="{qr_url}">Download QR Code</a></p>
            <p>Please present this QR code at the event for check-in.</p>
            """
            send_email(email, f'Registration Confirmed - {event.title}', email_body)
            
            flash('Registration successful! Check your email for confirmation and QR code.', 'success')
        
        return redirect(url_for('event_detail', event_id=event_id))
    
    return render_template('register.html', event=event)

@app.route('/qr/<token>')
def generate_qr(token):
    registration = Registration.query.filter_by(qr_code_token=token).first_or_404()
    
    # Generate QR code
    qr_data = f"EVENT_CHECKIN:{token}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to bytes
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png', as_attachment=True, 
                     download_name=f'event_qr_{registration.event_id}.png')

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and admin.check_password(password):
            login_user(admin)
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    events = Event.query.order_by(Event.date.desc()).all()
    upcoming_events = Event.query.filter(Event.date >= datetime.utcnow()).order_by(Event.date.asc()).all()
    past_events = Event.query.filter(Event.date < datetime.utcnow()).order_by(Event.date.desc()).all()
    total_students = Student.query.count()
    total_registrations = Registration.query.count()
    
    return render_template('admin_dashboard.html', 
                         events=events,
                         upcoming_events=upcoming_events,
                         past_events=past_events,
                         total_students=total_students,
                         total_registrations=total_registrations)

@app.route('/admin/event/create', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        date_str = request.form.get('date')
        venue = request.form.get('venue')
        capacity = request.form.get('capacity')
        
        event_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
        
        event = Event(
            title=title,
            description=description,
            date=event_date,
            venue=venue,
            capacity=int(capacity)
        )
        
        db.session.add(event)
        db.session.commit()
        
        flash('Event created successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('create_event.html')

@app.route('/admin/event/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        event.title = request.form.get('title')
        event.description = request.form.get('description')
        event.date = datetime.strptime(request.form.get('date'), '%Y-%m-%dT%H:%M')
        event.venue = request.form.get('venue')
        event.capacity = int(request.form.get('capacity'))
        
        db.session.commit()
        flash('Event updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('edit_event.html', event=event)

@app.route('/admin/event/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash('Event deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/event/<int:event_id>/registrations')
@login_required
def view_registrations(event_id):
    event = Event.query.get_or_404(event_id)
    registrations = Registration.query.filter_by(event_id=event_id).all()
    waitlist = Waitlist.query.filter_by(event_id=event_id).order_by(Waitlist.position).all()
    
    return render_template('view_registrations.html', 
                         event=event, 
                         registrations=registrations,
                         waitlist=waitlist)

@app.route('/admin/checkin', methods=['GET', 'POST'])
@login_required
def checkin():
    if request.method == 'POST':
        token = request.form.get('token')
        
        if token.startswith('EVENT_CHECKIN:'):
            token = token.replace('EVENT_CHECKIN:', '')
        
        registration = Registration.query.filter_by(qr_code_token=token).first()
        
        if registration:
            if registration.checked_in:
                return jsonify({
                    'success': False, 
                    'message': 'Already checked in!',
                    'student': registration.student.name,
                    'event': registration.event.title,
                    'check_in_time': registration.check_in_time.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            registration.checked_in = True
            registration.check_in_time = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Check-in successful!',
                'student': registration.student.name,
                'event': registration.event.title
            })
        else:
            return jsonify({'success': False, 'message': 'Invalid QR code!'})
    
    return render_template('checkin.html')

@app.route('/admin/event/<int:event_id>/export')
@login_required
def export_attendance(event_id):
    event = Event.query.get_or_404(event_id)
    registrations = Registration.query.filter_by(event_id=event_id).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student ID', 'Name', 'Email', 'Registration Date', 'Checked In', 'Check-in Time'])
    
    for reg in registrations:
        writer.writerow([
            reg.student.student_id,
            reg.student.name,
            reg.student.email,
            reg.registration_date.strftime('%Y-%m-%d %H:%M:%S'),
            'Yes' if reg.checked_in else 'No',
            reg.check_in_time.strftime('%Y-%m-%d %H:%M:%S') if reg.check_in_time else 'N/A'
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'attendance_{event.title.replace(" ", "_")}.csv'
    )

@app.route('/admin/registration/<int:reg_id>/cancel', methods=['POST'])
@login_required
def cancel_registration(reg_id):
    registration = Registration.query.get_or_404(reg_id)
    event = registration.event
    student_email = registration.student.email
    
    db.session.delete(registration)
    db.session.commit()
    
    # Check waitlist and promote first person
    waitlist_entry = Waitlist.query.filter_by(event_id=event.id).order_by(Waitlist.position).first()
    
    if waitlist_entry:
        # Promote from waitlist
        qr_token = secrets.token_urlsafe(32)
        new_registration = Registration(
            event_id=event.id,
            student_id=waitlist_entry.student_id,
            qr_code_token=qr_token
        )
        db.session.add(new_registration)
        
        # Remove from waitlist
        db.session.delete(waitlist_entry)
        
        # Update positions for remaining waitlist
        remaining_waitlist = Waitlist.query.filter_by(event_id=event.id).order_by(Waitlist.position).all()
        for idx, entry in enumerate(remaining_waitlist, 1):
            entry.position = idx
        
        db.session.commit()
        
        # Send email to promoted student
        student = waitlist_entry.student
        qr_url = url_for('generate_qr', token=qr_token, _external=True)
        email_body = f"""
        <h2>Great News!</h2>
        <p>Dear {student.name},</p>
        <p>A spot has opened up for <strong>{event.title}</strong>!</p>
        <p>You have been moved from the waitlist and are now registered for the event.</p>
        <p>Event Details:</p>
        <ul>
            <li>Date: {event.date.strftime('%B %d, %Y at %I:%M %p')}</li>
            <li>Venue: {event.venue}</li>
        </ul>
        <p>Your QR Code: <a href="{qr_url}">Download QR Code</a></p>
        """
        send_email(student.email, f'Registered - {event.title}', email_body)
    
    flash('Registration cancelled successfully!', 'success')
    return redirect(url_for('view_registrations', event_id=event.id))

@app.route('/admin/registration/<int:reg_id>/toggle-checkin', methods=['POST'])
@login_required
def toggle_checkin(reg_id):
    registration = Registration.query.get_or_404(reg_id)
    registration.checked_in = not registration.checked_in
    if registration.checked_in:
        registration.check_in_time = datetime.utcnow()
    else:
        registration.check_in_time = None
    db.session.commit()
    flash(f"{'Checked in' if registration.checked_in else 'Check-in removed'} for {registration.student.name}", 'success')
    return redirect(url_for('view_registrations', event_id=registration.event_id))

@app.route('/admin/registration/<int:reg_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_registration(reg_id):
    registration = Registration.query.get_or_404(reg_id)
    student = registration.student
    
    if request.method == 'POST':
        student.name = request.form.get('name')
        student.email = request.form.get('email')
        student.student_id = request.form.get('student_id')
        db.session.commit()
        flash('Registration details updated!', 'success')
        return redirect(url_for('view_registrations', event_id=registration.event_id))
    
    return render_template('edit_registration.html', registration=registration)

@app.route('/admin/event/<int:event_id>/add-manual', methods=['GET', 'POST'])
@login_required
def add_registration_manual(event_id):
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        student_id_input = request.form.get('student_id')
        
        student = Student.query.filter_by(student_id=student_id_input).first()
        if not student:
            student = Student(name=name, email=email, student_id=student_id_input)
            db.session.add(student)
            db.session.commit()
        
        existing_reg = Registration.query.filter_by(event_id=event_id, student_id=student.id).first()
        if existing_reg:
            flash('Student already registered!', 'warning')
            return redirect(url_for('view_registrations', event_id=event_id))
            
        qr_token = secrets.token_urlsafe(32)
        registration = Registration(
            event_id=event_id,
            student_id=student.id,
            qr_code_token=qr_token
        )
        db.session.add(registration)
        db.session.commit()
        
        flash(f'Successfully added {name} to the event!', 'success')
        return redirect(url_for('view_registrations', event_id=event_id))
        
    return render_template('add_registration_manual.html', event=event)

@app.route('/my-events')
def my_events():
    student_id = request.args.get('student_id', '')
    
    if not student_id:
        return render_template('my_events.html', student=None)
    
    student = Student.query.filter_by(student_id=student_id).first()
    
    if not student:
        flash('Student ID not found!', 'warning')
        return render_template('my_events.html', student=None)
    
    upcoming_registrations = Registration.query.join(Event).filter(
        Registration.student_id == student.id,
        Event.date >= datetime.utcnow()
    ).all()
    
    past_registrations = Registration.query.join(Event).filter(
        Registration.student_id == student.id,
        Event.date < datetime.utcnow()
    ).all()
    
    waitlist_entries = Waitlist.query.join(Event).filter(
        Waitlist.student_id == student.id,
        Event.date >= datetime.utcnow()
    ).all()
    
    return render_template('my_events.html', 
                         student=student,
                         upcoming_registrations=upcoming_registrations,
                         past_registrations=past_registrations,
                         waitlist_entries=waitlist_entries)

# Event Library Routes
@app.route('/event-library')
def event_library():
    # Get all events that have folders with images
    events_with_folders = Event.query.join(EventFolder).filter(
        Event.date < datetime.utcnow()
    ).order_by(Event.date.desc()).all()
    
    # Filter to only events that actually have folders
    events_with_folders = [event for event in events_with_folders if event.folders]
    
    return render_template('event_library.html', events=events_with_folders)

@app.route('/event-library/<int:event_id>')
def event_folders(event_id):
    event = Event.query.get_or_404(event_id)
    folders = EventFolder.query.filter_by(event_id=event_id).all()
    return render_template('event_folders.html', event=event, folders=folders)

@app.route('/event-library/<int:event_id>/folder/<int:folder_id>')
def folder_images(event_id, folder_id):
    event = Event.query.get_or_404(event_id)
    folder = EventFolder.query.get_or_404(folder_id)
    images = FolderImage.query.filter_by(folder_id=folder_id).all()
    return render_template('folder_images.html', event=event, folder=folder, images=images)

@app.route('/admin/event/<int:event_id>/create-folder', methods=['GET', 'POST'])
@login_required
def create_event_folder(event_id):
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        folder_name = request.form.get('folder_name')
        if folder_name:
            folder = EventFolder(event_id=event_id, folder_name=folder_name)
            db.session.add(folder)
            db.session.commit()
            flash(f'Folder "{folder_name}" created successfully!', 'success')
            return redirect(url_for('manage_event_folders', event_id=event_id))
        else:
            flash('Folder name is required', 'danger')
    
    return render_template('create_folder.html', event=event)

@app.route('/admin/event/<int:event_id>/manage-folders')
@login_required
def manage_event_folders(event_id):
    event = Event.query.get_or_404(event_id)
    folders = EventFolder.query.filter_by(event_id=event_id).all()
    return render_template('manage_folders.html', event=event, folders=folders)

@app.route('/admin/event/<int:event_id>/folder/<int:folder_id>/upload-images', methods=['GET', 'POST'])
@login_required
def upload_folder_images(event_id, folder_id):
    event = Event.query.get_or_404(event_id)
    folder = EventFolder.query.get_or_404(folder_id)
    
    if request.method == 'POST':
        if 'images' not in request.files:
            flash('No files selected', 'danger')
            return redirect(request.url)
        
        files = request.files.getlist('images')
        uploaded_count = 0
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp and folder ID to filename to avoid conflicts
                filename = f"{folder_id}_{int(datetime.utcnow().timestamp())}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Save to database
                caption = request.form.get(f'caption_{files.index(file)}', '')
                folder_image = FolderImage(
                    folder_id=folder_id,
                    image_path=f'uploads/{filename}',
                    caption=caption
                )
                db.session.add(folder_image)
                uploaded_count += 1
        
        if uploaded_count > 0:
            db.session.commit()
            flash(f'{uploaded_count} image(s) uploaded successfully!', 'success')
        else:
            flash('No valid images were uploaded', 'warning')
        
        return redirect(url_for('upload_folder_images', event_id=event_id, folder_id=folder_id))
    
    return render_template('upload_folder_images.html', event=event, folder=folder)

@app.route('/admin/folder/<int:folder_id>/delete', methods=['POST'])
@login_required
def delete_event_folder(folder_id):
    folder = EventFolder.query.get_or_404(folder_id)
    event_id = folder.event_id
    
    # Delete all images in the folder
    images = FolderImage.query.filter_by(folder_id=folder_id).all()
    for image in images:
        try:
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', image.image_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")
        db.session.delete(image)
    
    db.session.delete(folder)
    db.session.commit()
    
    flash('Folder and all images deleted successfully!', 'success')
    return redirect(url_for('manage_event_folders', event_id=event_id))

@app.route('/admin/folder-image/<int:image_id>/delete', methods=['POST'])
@login_required
def delete_folder_image(image_id):
    image = FolderImage.query.get_or_404(image_id)
    folder_id = image.folder_id
    folder = EventFolder.query.get_or_404(folder_id)
    event_id = folder.event_id
    
    # Delete file from filesystem
    try:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', image.image_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error deleting file: {e}")
    
    db.session.delete(image)
    db.session.commit()
    
    flash('Image deleted successfully!', 'success')
    return redirect(url_for('upload_folder_images', event_id=event_id, folder_id=folder_id))

@app.route('/download-image/<int:image_id>')
def download_image(image_id):
    image = FolderImage.query.get_or_404(image_id)
    return send_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', image.image_path), as_attachment=True)

def init_db():
    with app.app_context():
        db.create_all()
        
        # Create default admin if not exists
        admin = Admin.query.filter_by(username='admin').first()
        if not admin:
            admin = Admin(username='admin', email='admin@college.edu')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Default admin created - username: admin, password: admin123")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
