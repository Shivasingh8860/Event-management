# College Event Management System

A comprehensive web-based event management system built with Flask, HTML, CSS, and Bootstrap. This system enables students to discover and register for college events while providing administrators with powerful tools to manage events, track attendance, and monitor registrations.

## Features

### 🎯 Core Features

1. **Event Listing Page**
   - Display all upcoming college events
   - Shows title, description, date, time, venue, and capacity
   - Responsive design with Bootstrap
   - Real-time capacity tracking

2. **Student Registration**
   - Simple registration form (name, email, student ID)
   - Automatic capacity limit enforcement
   - Waitlist management when events are full
   - Duplicate registration prevention

3. **QR Code Check-in System**
   - Unique QR code generated for each registration
   - Downloadable QR codes via email
   - Manual token entry for check-in
   - Real-time attendance tracking

4. **Email Notifications**
   - Registration confirmation emails with QR codes
   - Waitlist notifications
   - Automatic promotion emails when spots open

5. **Admin Dashboard**
   - Complete CRUD operations for events
   - View registered students and waitlist
   - Export attendance to CSV
   - Real-time statistics and analytics
   - Secure admin authentication

6. **Search & Filter**
   - Search events by title, description, or venue
   - Filter events by date
   - Clean, intuitive interface

7. **Attendance History**
   - Students can view their past events
   - Attendance rate calculation
   - Check-in status tracking

## Technology Stack

- **Backend**: Python Flask 3.0
- **Database**: SQLite (easily switchable to PostgreSQL)
- **Authentication**: Flask-Login
- **Frontend**: HTML5, CSS3, Bootstrap 5.3
- **Icons**: Font Awesome 6.4
- **QR Codes**: Python qrcode library

## Project Structure

```
college-event-management/
│
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── templates/                  # HTML templates
│   ├── base.html              # Base template with navbar
│   ├── index.html             # Homepage
│   ├── events.html            # Event listing page
│   ├── event_detail.html      # Event details
│   ├── register.html          # Registration form
│   ├── my_events.html         # Student's events & history
│   ├── admin_login.html       # Admin login page
│   ├── admin_dashboard.html   # Admin dashboard
│   ├── create_event.html      # Create event form
│   ├── edit_event.html        # Edit event form
│   ├── view_registrations.html # View event registrations
│   └── checkin.html           # QR code check-in page
│
└── static/                     # Static files
    ├── css/
    │   └── style.css          # Custom styles
    └── js/
        └── (future JS files)
```

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Configure Email (Optional)

To enable email notifications, update the email configuration in `app.py`:

```python
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your-app-password'
app.config['MAIL_USE_TLS'] = True
```

**Note**: For Gmail, you need to:
1. Enable 2-factor authentication
2. Generate an "App Password" from your Google Account settings
3. Use the app password instead of your regular password

### Step 3: Run the Application

```bash
python app.py
```

The application will:
- Create the SQLite database (`events.db`)
- Create a default admin account (username: `admin`, password: `admin123`)
- Start the development server on `http://localhost:5000`

### Step 4: Access the Application

- **Homepage**: http://localhost:5000
- **Events**: http://localhost:5000/events
- **Admin Login**: http://localhost:5000/admin/login
  - Default credentials: `admin` / `admin123`

## Usage Guide

### For Students

1. **Browse Events**
   - Navigate to "Events" page
   - Use search and filter to find events
   - Click "View Details" for more information

2. **Register for an Event**
   - Click "Register Now" on event details page
   - Fill in your name, email, and student ID
   - Submit the form
   - Check your email for confirmation and QR code

3. **View Your Events**
   - Go to "My Events" page
   - Enter your student ID
   - View upcoming events, waitlist status, and attendance history
   - Download QR codes for upcoming events

4. **Event Check-in**
   - Present your QR code at the event
   - Organizer will scan or manually enter the token

### For Administrators

1. **Login**
   - Navigate to Admin Login
   - Use credentials (default: admin/admin123)

2. **Create Events**
   - Click "Create New Event" from dashboard
   - Fill in event details
   - Set capacity and venue
   - Submit to create

3. **Manage Events**
   - View all events on dashboard
   - Edit event details
   - Delete events (with confirmation)
   - View registrations and waitlist

4. **Check-in Students**
   - Navigate to QR Check-in page
   - Scan QR codes or manually enter tokens
   - System marks attendance automatically

5. **Export Attendance**
   - Go to event registrations page
   - Click "Export Attendance"
   - Download CSV with all registration data

## Database Models

### Event
- `id`: Primary key
- `title`: Event name
- `description`: Event details
- `date`: Event date and time
- `venue`: Event location
- `capacity`: Maximum attendees
- `created_at`: Creation timestamp

### Student
- `id`: Primary key
- `name`: Student name
- `email`: Email address
- `student_id`: Unique student identifier

### Registration
- `id`: Primary key
- `event_id`: Foreign key to Event
- `student_id`: Foreign key to Student
- `registration_date`: Registration timestamp
- `qr_code_token`: Unique QR code identifier
- `checked_in`: Boolean attendance flag
- `check_in_time`: Check-in timestamp

### Waitlist
- `id`: Primary key
- `event_id`: Foreign key to Event
- `student_id`: Foreign key to Student
- `added_date`: Waitlist entry timestamp
- `position`: Waitlist position number

### Admin
- `id`: Primary key
- `username`: Admin username
- `password_hash`: Hashed password
- `email`: Admin email

## Security Features

- Password hashing with Werkzeug
- CSRF protection (Flask built-in)
- Login required decorators for admin routes
- Session management with Flask-Login
- SQL injection prevention (SQLAlchemy ORM)

## Future Enhancements

- [ ] Real-time QR code scanning with camera
- [ ] SMS notifications
- [ ] Event categories and tags
- [ ] Advanced analytics and reporting
- [ ] Calendar integration (Google Calendar, iCal)
- [ ] Social media sharing
- [ ] Multi-language support
- [ ] Mobile app (React Native/Flutter)
- [ ] Payment integration for paid events
- [ ] Event feedback and ratings

## Troubleshooting

### Email not sending
- Verify SMTP settings are correct
- For Gmail, ensure you're using an App Password
- Check firewall/antivirus settings
- Email feature works but is optional

### Database errors
- Delete `events.db` and restart the application
- This will recreate the database with fresh tables

### QR codes not generating
- Ensure Pillow library is installed
- Check file permissions in the application directory

### Port already in use
- Change the port in `app.py`: `app.run(debug=True, port=5001)`

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is open source and available for educational purposes.

## Support

For questions or issues, please open an issue on the repository or contact the development team.

---

**Developed with ❤️ for College Event Management**
