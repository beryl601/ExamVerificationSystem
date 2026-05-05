# Exam Verification System

A Flask-based exam management system for Pwani University. The application supports admin registration of students and exams, invigilator face verification, student dashboard access, and QR code issuance and download.

## Features

- Admin login and dashboard
- Student registration with face encoding and QR generation
- Student login and portal access
- Invigilator login with face verification and attendance recording
- Attendance report page
- Role-based navigation and access control

## Requirements

- Python 3.10+
- Flask
- Flask-SQLAlchemy
- OpenCV
- NumPy

## Setup

1. Clone or copy the repository.
2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
3. Activate the virtual environment:
   - Windows PowerShell:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - Windows Command Prompt:
     ```cmd
     venv\Scripts\activate.bat
     ```
4. Install dependencies:
   ```bash
   pip install flask flask-sqlalchemy opencv-python numpy
   ```

## Run the application

```bash
python app.py
```

Then open `http://127.0.0.1:5000` in your browser.

## Default logins

- **Admin**
  - Username: `admin`
  - Password: `admin123`

- **Invigilator**
  - Username: `invigilator`
  - Password: `inv123`

## Project structure

- `app.py` - main Flask application
- `models.py` - SQLAlchemy models
- `qr_utils.py` - QR generation utilities
- `face_utils.py` - face encoding and verification utilities
- `templates/` - Jinja2 HTML templates
- `static/` - static assets and uploads

## Notes

- The SQLite database file is stored as `exam_system.db`.
- Uploaded student photos are stored in `static/uploads/`.
- Generated QR codes are stored in `static/qrcodes/`.
