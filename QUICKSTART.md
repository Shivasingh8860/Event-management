# Quick Start Guide

## Starting the Application

1. **Install Dependencies** (first time only):
   ```bash
   pip install Flask Flask-SQLAlchemy Flask-Login Werkzeug qrcode Pillow
   ```

2. **Run the Application**:
   ```bash
   python app.py
   ```

3. **Access the Application**:
   - Open your browser and navigate to: `http://localhost:5000`

## Default Admin Credentials

- **Username**: `admin`
- **Password**: `admin123`

⚠️ **Important**: Change these credentials after first login!

## Quick Tour

### For Students:
1. **Browse Events**: Click "Events" in navigation
2. **Register**: Select an event → View Details → Register Now
3. **My Events**: Enter your student ID to view registrations and attendance history

### For Administrators:
1. **Login**: Click "Admin" → Login with credentials
2. **Create Event**: Dashboard → "Create New Event"
3. **Manage**: View registrations, export attendance, check-in students
4. **QR Check-in**: Click "QR Check-in" button on dashboard

## Testing the System

### Create a Test Event:
1. Login as admin
2. Click "Create New Event"
3. Fill in details:
   - Title: "Welcome Orientation"
   - Description: "New student orientation event"
   - Date/Time: Select a future date
   - Venue: "Main Auditorium"
   - Capacity: 50
4. Click "Create Event"

### Register a Student:
1. Go to "Events" page
2. Click on your newly created event
3. Click "Register Now"
4. Fill in:
   - Name: "John Doe"
   - Email: "john@example.com"
   - Student ID: "STU001"
5. Submit (note: email won't send unless SMTP is configured)

### Check-in Process:
1. Login as admin
2. Click "QR Check-in"
3. The QR token is visible in the database or email
4. Enter the token manually to test check-in

## Email Configuration (Optional)

To enable email notifications, edit `app.py` and update:

```python
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your-app-password'
```

For Gmail:
1. Enable 2-factor authentication
2. Generate App Password: Google Account → Security → App Passwords
3. Use the generated password

## Features Overview

✅ **Implemented Features:**
- Event listing with search and filters
- Student registration with capacity limits
- Waitlist management
- QR code generation
- Email notifications (requires SMTP setup)
- Admin dashboard with CRUD operations
- Attendance tracking and check-in
- CSV export for attendance
- Student event history
- Responsive design

## Troubleshooting

**Port already in use?**
- Close other applications using port 5000
- Or change port in `app.py`: `app.run(debug=True, port=5001)`

**Database errors?**
- Delete `events.db` file and restart application

**Emails not sending?**
- This is expected if SMTP is not configured
- System works fine without email functionality

## File Structure

```
e:\mp\7\
├── app.py                  # Main application
├── requirements.txt        # Dependencies
├── README.md              # Full documentation
├── QUICKSTART.md          # This file
├── events.db              # SQLite database (created on first run)
├── templates/             # HTML templates
└── static/                # CSS, JS, images
```

## Next Steps

1. **Customize**: Modify templates and styles to match your college branding
2. **Add Events**: Create multiple events to test functionality
3. **Test Registration**: Register students and test the waitlist
4. **Try Check-in**: Use the QR check-in system
5. **Export Data**: Test the CSV export feature

## Support

- Check `README.md` for detailed documentation
- Review code comments in `app.py` for implementation details
- Test all features before production deployment

---

**Ready to get started? Run `python app.py` and visit http://localhost:5000**
