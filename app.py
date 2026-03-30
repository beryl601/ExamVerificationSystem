from flask import Flask, render_template, request, jsonify, redirect, url_for
from models import db, Student, Exam, AttendanceRecord
from qr_utils import generate_qr
from face_utils import encode_face, verify_face
import os, json, cv2, base64, numpy as np
from datetime import datetime
app = Flask(__name__)
# Database configuration — SQLite file stored in the project folder
app.config["SQLALCHEMY_DATABASE_URI"]     = "sqlite:///exam_system.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"]              = "static/uploads"
db.init_app(app)
# Create all database tables when the app starts (only runs if tables do not exist)
with app.app_context():
    db.create_all()
# ROUTE 1: Dashboard ( / ) 
@app.route("/")
def index():
    """Show the main dashboard with summary counts."""
    students   = Student.query.count()
    exams      = Exam.query.count()
    attendance = AttendanceRecord.query.filter_by(status="present").count()
    return render_template("index.html",
                           students=students,
                           exams=exams,
                           attendance=attendance)
# ROUTE 2: Register student ( /register ) 
@app.route("/register", methods=["GET", "POST"])
def register():
    """Show the registration form (GET) or process a new student (POST)."""
    if request.method == "POST":
        # Collect form data
        reg_number = request.form["reg_number"]
        full_name  = request.form["full_name"]
        course     = request.form["course"]
        email      = request.form["email"]
        photo      = request.files["photo"]
        # Save the uploaded photo to static/uploads/
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        photo_path = os.path.join(
            app.config["UPLOAD_FOLDER"], f"{reg_number}.jpg")
        photo.save(photo_path)
        # Try to detect and encode the face in the photo
        encoding = encode_face(photo_path)
        if encoding is None:
            # No face found — show error and ask user to try again
            return render_template("register.html",
                error="No face detected. Please upload a clear, "
                      "front-facing photo with good lighting.")
        # Generate the QR code image for this student
        qr_path = generate_qr(reg_number)
        # Save student record to the database
        student = Student(
            reg_number    = reg_number,
            full_name     = full_name,
            course        = course,
            email         = email,
            face_encoding = json.dumps(encoding),  # Store as JSON text
            qr_code_path  = qr_path
        )
        db.session.add(student)
        db.session.commit()
        # Redirect to the student card page to show the QR code
        return redirect(url_for("student_card", reg_number=reg_number))
    # GET request: just show the empty registration form
    return render_template("register.html")
# ROUTE 3: Student card with QR code ( /student/<reg> ) 
@app.route("/student/<reg_number>")
def student_card(reg_number):
    """Show a student's details and their QR code."""
    student = Student.query.filter_by(
        reg_number=reg_number).first_or_404()
    return render_template("student_card.html", student=student)
# ROUTE 4: All students list ( /students ) 
@app.route("/students")
def students():
    """Show a table of all registered students."""
    all_students = Student.query.order_by(Student.full_name).all()
    return render_template("students.html", students=all_students)
# ROUTE 5: Verification page ( /verify ) 
@app.route("/verify")
def verify():
    """Show the verification page with webcam and exam selector."""
    exams = Exam.query.all()
    return render_template("verify.html", exams=exams)
# ROUTE 6: Verification API ( /api/verify ) — called by JavaScript 
@app.route("/api/verify", methods=["POST"])
def api_verify():
    """
    Receive reg number + webcam image from browser.
    Check face, save attendance record, return pass/fail result.
    """
    data       = request.json
    reg_number = data.get("reg_number")
    exam_id    = data.get("exam_id")
    image_data = data.get("image")   # base64-encoded JPEG from browser webcam
    # Look up the student in the database
    student = Student.query.filter_by(reg_number=reg_number).first()
    if not student:
        return jsonify({"success": False,
                        "message": "Student not found in database"})
    # Decode the base64 webcam image into an OpenCV image array
    img_bytes = base64.b64decode(image_data.split(",")[1])
    np_arr    = np.frombuffer(img_bytes, np.uint8)
    frame     = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    # Run face verification
    face_match = verify_face(student.face_encoding, frame)
    # Save the attendance record to the database
    status = "present" if face_match else "failed"
    record = AttendanceRecord(
        student_id    = student.id,
        exam_id       = exam_id,
        qr_verified   = True,
        face_verified = face_match,
        status        = status
    )
    db.session.add(record)
    db.session.commit()
    # Return the result to the browser as JSON
    return jsonify({
        "success":      face_match,
        "student_name": student.full_name,
        "reg_number":   student.reg_number,
        "message":      "Verified - Entry Allowed"
                         if face_match else
                        "Face Mismatch - Entry Denied"
    })
# ROUTE 7: Manage exams ( /exams )
@app.route("/exams", methods=["GET", "POST"])
def exams():
    """Show the exam list (GET) or add a new exam (POST)."""
    if request.method == "POST":
        exam = Exam(
            unit_code = request.form["unit_code"],
            unit_name = request.form["unit_name"],
            exam_date = datetime.strptime(
                            request.form["exam_date"], "%Y-%m-%dT%H:%M"),
            venue     = request.form["venue"]
        )
        db.session.add(exam)
        db.session.commit()
        return redirect(url_for("exams"))
    all_exams = Exam.query.order_by(Exam.exam_date).all()
    return render_template("exams.html", exams=all_exams)
# ROUTE 8: Attendance report ( /attendance ) 
@app.route("/attendance")
def attendance():
    """Show all verification records, newest first."""
    records = AttendanceRecord.query.order_by(
                  AttendanceRecord.verified_at.desc()).all()
    return render_template("attendance.html", records=records)
# Start the server 
if __name__ == "__main__":
    app.run(debug=True)  # debug=True shows errors in browser during development