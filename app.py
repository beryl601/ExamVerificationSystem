from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from functools import wraps
from models import db, Student, Exam, AttendanceRecord
from qr_utils import generate_qr
from face_utils import encode_face, verify_face
from dotenv import load_dotenv
from flask_migrate import Migrate
import os, json, cv2, base64, numpy as np
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = "pwani_exam_secret_2026"

# Database configuration
# Use DATABASE_URL from environment (set in .env or Railway dashboard)
database_url = os.environ.get("DATABASE_URL", "sqlite:///exam_system.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 1800,
    "pool_timeout": 10,
}
app.config["UPLOAD_FOLDER"] = "static/uploads"
db.init_app(app)
migrate = Migrate(app, db)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Admin login required.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("student_logged_in"):
            flash("Student login required.", "warning")
            return redirect(url_for("student_login"))
        return f(*args, **kwargs)
    return decorated
def invigilator_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("invigilator_logged_in"):
            flash("Invigilator login required.", "warning")
            return redirect(url_for("invigilator_login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/invigilator/login", methods=["GET", "POST"])
def invigilator_login():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Check against default password or session-stored reset password
        default_password = "inv123"
        reset_password = session.get("invigilator_password")
        
        if username == "invigilator" and (password == default_password or (reset_password and password == reset_password)):
            session["invigilator_logged_in"] = True
            session["invigilator_name"] = "Invigilator"
            return redirect(url_for("invigilator_dashboard"))
        else:
            error = "Invalid invigilator credentials."

    return render_template("invigilator_login.html", error=error)


@app.route("/invigilator/logout")
def invigilator_logout():
    session.clear()
    return redirect(url_for("invigilator_login"))


@app.route("/invigilator/dashboard")
@invigilator_required
def invigilator_dashboard():
    records = AttendanceRecord.query.count()
    return render_template("invigilator_dashboard.html", attendance=records)


# ── ROUTE 1: Landing page ( / ) ───────────────────────────────────────
@app.route("/")
def index():
    """Show the landing page with Admin, Supervisor, and Student login options."""
    return render_template("landing.html")


# ── Admin login / logout ───────────────────────────────────────────────
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Check against default password or session-stored reset password
        default_password = "admin123"
        reset_password = session.get("admin_password")
        
        if username == "admin" and (password == default_password or (reset_password and password == reset_password)):
            session["admin_logged_in"] = True
            session["admin_name"] = "Administrator"
            return redirect(url_for("dashboard"))   # ← goes to dashboard, not index
        else:
            error = "Invalid admin credentials."

    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# ── ROUTE 2: Admin dashboard ( /dashboard ) ───────────────────────────
@app.route("/dashboard")
@admin_required
def dashboard():
    """Show the main dashboard with summary counts."""
    students   = Student.query.count()
    exams      = Exam.query.count()
    attendance = AttendanceRecord.query.filter_by(status="present").count()
    return render_template("index.html",
                           students=students,
                           exams=exams,
                           attendance=attendance)


# ── ROUTE 3: Register student ( /register ) ───────────────────────────
@app.route("/register", methods=["GET", "POST"])
@admin_required
def register():
    """Show the registration form (GET) or process a new student (POST)."""
    if request.method == "POST":
        reg_number = request.form["reg_number"]
        full_name  = request.form["full_name"]
        course     = request.form["course"]
        email      = request.form["email"]
        photo      = request.files["photo"]

        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        photo_path = os.path.join(
            app.config["UPLOAD_FOLDER"], f"{reg_number}.jpg")
        photo.save(photo_path)

        encoding = encode_face(photo_path)
        if encoding is None:
            return render_template("register.html",
                error="No face detected. Please upload a clear, "
                      "front-facing photo with good lighting.")

        qr_path = generate_qr(reg_number, full_name=full_name, course=course)

        student = Student(
            reg_number    = reg_number,
            full_name     = full_name,
            course        = course,
            email         = email,
            face_encoding = json.dumps(encoding),
            qr_code_path  = qr_path
        )
        db.session.add(student)
        db.session.commit()

        return redirect(url_for("student_card", reg_number=reg_number))

    return render_template("register.html")


# ── ROUTE 4: Student card with QR code ( /student/<reg> ) ─────────────
@app.route("/student/<reg_number>")
def student_card(reg_number):
    """Show a student's details and their QR code."""
    student = Student.query.filter_by(reg_number=reg_number).first_or_404()
    return render_template("student_card.html", student=student)


# ── ROUTE 5: All students list ( /students ) ──────────────────────────
@app.route("/students")
@admin_required
def students():
    """Show a table of all registered students."""
    all_students = Student.query.order_by(Student.full_name).all()
    return render_template("students.html", students=all_students)


# ── ROUTE 6: Verification page ( /verify ) ────────────────────────────
@app.route("/verify")
@invigilator_required
def verify():
    """Show the verification page with webcam and exam selector."""
    exams = Exam.query.all()
    return render_template("verify.html", exams=exams)


# ── ROUTE 7: Verification API ( /api/verify ) — called by JavaScript ──
@app.route("/api/verify", methods=["POST"])
@invigilator_required
def api_verify():
    """
    Receive reg number + webcam image from browser.
    Check face, save attendance record, return pass/fail result.
    """
    data       = request.json
    reg_number = data.get("reg_number")
    exam_id    = data.get("exam_id")
    image_data = data.get("image")

    student = Student.query.filter_by(reg_number=reg_number).first()
    if not student:
        return jsonify({"success": False,
                        "message": "Student not found in database"})

    img_bytes = base64.b64decode(image_data.split(",")[1])
    np_arr    = np.frombuffer(img_bytes, np.uint8)
    frame     = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    exam_obj = Exam.query.get(exam_id) if exam_id else None
    if not exam_obj:
        return jsonify({"success": False,
                        "message": "Exam not found. Please select a valid exam."})

    face_match = verify_face(student.face_encoding, frame)
    status = "present" if face_match else "failed"

    existing_record = AttendanceRecord.query.filter_by(
        student_id=student.id,
        exam_id=exam_id
    ).order_by(AttendanceRecord.verified_at.desc()).first()

    if existing_record:
        elapsed_seconds = (datetime.utcnow() - existing_record.verified_at).total_seconds()

        if existing_record.status == "present":
            return jsonify({
                "success":      True,
                "student_name": student.full_name,
                "reg_number":   student.reg_number,
                "photo_url":    f"/static/uploads/{student.reg_number}.jpg",
                "exam_name":    f"{exam_obj.unit_code} — {exam_obj.unit_name}",
                "message":      "Student already verified as present for this exam."
            })

        if elapsed_seconds < 60:
            return jsonify({
                "success":      existing_record.face_verified,
                "student_name": student.full_name,
                "reg_number":   student.reg_number,
                "photo_url":    f"/static/uploads/{student.reg_number}.jpg",
                "exam_name":    f"{exam_obj.unit_code} — {exam_obj.unit_name}",
                "message":      "Repeated scan ignored. Please wait a moment before retrying."
            })

        existing_record.qr_verified   = True
        existing_record.face_verified = face_match
        existing_record.status        = status
        existing_record.verified_at   = datetime.utcnow()
        db.session.commit()
    else:
        record = AttendanceRecord(
            student_id    = student.id,
            exam_id       = exam_id,
            qr_verified   = True,
            face_verified = face_match,
            status        = status
        )
        db.session.add(record)
        db.session.commit()

    return jsonify({
        "success":      face_match,
        "student_name": student.full_name,
        "reg_number":   student.reg_number,
        "photo_url":    f"/static/uploads/{student.reg_number}.jpg",
        "exam_name":    f"{exam_obj.unit_code} — {exam_obj.unit_name}",
        "message":      "Verified - Entry Allowed"
                         if face_match else
                        "Face Mismatch - Entry Denied"
    })


# ── ROUTE 8: Manage exams ( /exams ) ──────────────────────────────────
@app.route("/exams", methods=["GET", "POST"])
@admin_required
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


# ── ROUTE 8a: Edit exam ( /exam/<exam_id>/edit ) ──────────────────────
@app.route("/exam/<int:exam_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_exam(exam_id):
    """Show the edit form (GET) or update the exam (POST)."""
    exam = Exam.query.get_or_404(exam_id)
    
    if request.method == "POST":
        exam.unit_code = request.form["unit_code"]
        exam.unit_name = request.form["unit_name"]
        exam.exam_date = datetime.strptime(
                            request.form["exam_date"], "%Y-%m-%dT%H:%M")
        exam.venue = request.form["venue"]
        db.session.commit()
        flash("Exam updated successfully.", "success")
        return redirect(url_for("exams"))
    
    return render_template("edit_exam.html", exam=exam)


# ── ROUTE 8b: Delete exam ( /exam/<exam_id>/delete ) ────────────────────
@app.route("/exam/<int:exam_id>/delete", methods=["GET", "POST"])
@admin_required
def delete_exam(exam_id):
    """Delete an exam."""
    exam = Exam.query.get_or_404(exam_id)
    db.session.delete(exam)
    db.session.commit()
    flash("Exam deleted successfully.", "success")
    return redirect(url_for("exams"))


# ── ROUTE 9: Attendance report ( /attendance ) ────────────────────────
@app.route("/attendance")
@invigilator_required
def attendance():
    """Show all verification records, newest first."""
    records = AttendanceRecord.query.order_by(
                  AttendanceRecord.verified_at.desc()).all()
    return render_template("attendance.html", records=records)


# ── Student login / logout / dashboard ────────────────────────────────
@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    error = None

    if request.method == "POST":
        reg_number = request.form.get("reg_number", "").strip()
        student    = Student.query.filter_by(reg_number=reg_number).first()

        if student:
            session["student_logged_in"] = True
            session["student_reg"]       = student.reg_number
            session["student_name"]      = student.full_name
            return redirect(url_for("student_dashboard"))
        else:
            error = "Invalid registration number."

    return render_template("student_login.html", error=error)


@app.route("/student/logout")
def student_logout():
    session.clear()
    return redirect(url_for("student_login"))


@app.route("/student/dashboard")
@student_required
def student_dashboard():
    student = Student.query.filter_by(
        reg_number=session["student_reg"]
    ).first_or_404()

    exams = Exam.query.order_by(Exam.exam_date).all()

    return render_template(
        "student_dashboard.html",
        student=student,
        exams=exams
    )


# ── Student portal ( /student-portal ) ───────────────────────────────
@app.route("/student-portal", methods=["GET", "POST"])
@student_required
def student_portal():
    student = Student.query.filter_by(reg_number=session["student_reg"]).first_or_404()
    exams   = Exam.query.order_by(Exam.exam_date).all()
    error   = None

    return render_template(
        "student_portal.html",
        student=student,
        exams=exams,
        error=error
    )


# ── Supervisor login ──────────────────────────────────────────────────
@app.route("/supervisor_login")
def supervisor_login():
    return render_template("supervisor_login.html")


# ── ROUTE 10: Direct QR image download ( /download-qr/<reg> ) ─────────
@app.route("/download-qr/<path:reg_number>")
@student_required
def download_qr(reg_number):
    """Serves the QR code image as a file download."""
    from flask import send_file

    student = Student.query.filter_by(reg_number=reg_number).first_or_404()

    qr_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        student.qr_code_path
    )

    if not os.path.exists(qr_path):
        return "QR code image not found. Please contact admin.", 404

    safe_name         = reg_number.replace("/", "-").replace("\\", "-")
    download_filename = f"ExamQR_{safe_name}.png"

    return send_file(
        qr_path,
        mimetype="image/png",
        as_attachment=True,
        download_name=download_filename
    )


# ── Start the server ──────────────────────────────────────────────────
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)