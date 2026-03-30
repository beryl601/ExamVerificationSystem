from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
db = SQLAlchemy()

class Student(db.Model):
    """Stores one row per registered student."""
    id            = db.Column(db.Integer, primary_key=True)
    reg_number    = db.Column(db.String(50), unique=True, nullable=False)
    full_name     = db.Column(db.String(100), nullable=False)
    course        = db.Column(db.String(100))
    email         = db.Column(db.String(100))
    face_encoding = db.Column(db.Text)       # 128-number face signature, stored as JSON
    qr_code_path  = db.Column(db.String(200))# path to the saved QR code image
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
class Exam(db.Model):
    """Stores one row per exam unit."""
    id        = db.Column(db.Integer, primary_key=True)
    unit_code = db.Column(db.String(20),  nullable=False)
    unit_name = db.Column(db.String(100), nullable=False)
    exam_date = db.Column(db.DateTime,    nullable=False)
    venue     = db.Column(db.String(100))
class AttendanceRecord(db.Model):
    """Stores one row every time a student is verified at an exam."""
    id            = db.Column(db.Integer, primary_key=True)
    student_id    = db.Column(db.Integer, db.ForeignKey("student.id"))
    exam_id       = db.Column(db.Integer, db.ForeignKey("exam.id"))
    verified_at   = db.Column(db.DateTime, default=datetime.utcnow)
    qr_verified   = db.Column(db.Boolean, default=False)  # True = QR scanned OK
    face_verified = db.Column(db.Boolean, default=False)  # True = face matched
    status        = db.Column(db.String(20), default="pending")
                    # "present" = both passed, "failed" = face did not match
    # These let us access student/exam details from a record easily
    student = db.relationship("Student", backref="attendance_records")
    exam    = db.relationship("Exam",    backref="attendance_records")