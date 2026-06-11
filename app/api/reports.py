from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models import (
    User, Course, Exam, ExamAttempt, Question,
    LessonProgress, Module, Lesson, course_enrollment,
)
from app.services.utils.helpers import success, error, get_current_user

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


# ═══════════════════════════════════════════════
#  ADMIN DASHBOARD STATS
# ═══════════════════════════════════════════════

@reports_bp.get("")
@reports_bp.get("/")
@reports_bp.get("/analytics")
@jwt_required()
def analytics():
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    if user.role == "admin":
        total_exams = Exam.query.count()
        total_courses = Course.query.count()
        total_attempts = ExamAttempt.query.count()
        graded_attempts = ExamAttempt.query.filter_by(status="graded").all()
        passed_attempts = sum(1 for a in graded_attempts if a.is_passed)
        avg_score = round(
            sum(a.percentage for a in graded_attempts if a.percentage) /
            len(graded_attempts), 1
        ) if graded_attempts else 0

        return success({
            "total_users": User.query.count(),
            "total_students": User.query.filter_by(role="student").count(),
            "total_instructors": User.query.filter_by(role="instructor").count(),
            "active_users": User.query.filter_by(is_active=True).count(),
            "total_courses": total_courses,
            "published_courses": Course.query.filter_by(is_published=True).count(),
            "total_exams": total_exams,
            "published_exams": Exam.query.filter_by(is_published=True).count(),
            "total_questions": Question.query.count(),
            "total_attempts": total_attempts,
            "graded_attempts": len(graded_attempts),
            "passed_attempts": passed_attempts,
            "failed_attempts": len(graded_attempts) - passed_attempts,
            "average_score_pct": avg_score,
        })
    else:
        # Instructor sees only their own stats
        my_exams = Exam.query.filter_by(created_by=user.id).all()
        my_exam_ids = [e.id for e in my_exams]
        my_courses = Course.query.filter_by(instructor_id=user.id).all()
        my_course_ids = [c.id for c in my_courses]

        attempts = ExamAttempt.query.filter(
            ExamAttempt.exam_id.in_(my_exam_ids)
        ).all() if my_exam_ids else []

        graded = [a for a in attempts if a.status == "graded"]
        passed = sum(1 for a in graded if a.is_passed)
        avg = round(
            sum(a.percentage for a in graded if a.percentage) / len(graded), 1
        ) if graded else 0

        return success({
            "my_exams": len(my_exams),
            "my_courses": len(my_courses),
            "total_attempts": len(attempts),
            "graded_attempts": len(graded),
            "passed_attempts": passed,
            "failed_attempts": len(graded) - passed,
            "average_score_pct": avg,
        })


# ═══════════════════════════════════════════════
#  STUDENTS PERFORMANCE (NEW)
# ═══════════════════════════════════════════════

@reports_bp.get("/students-performance")
@jwt_required()
def students_performance():
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)
    
    if user.role not in ("admin", "instructor"):
        return error("Access denied.", 403)
    
    students = User.query.filter_by(role="student").all()
    result = []
    
    for student in students:
        # Get enrolled courses count
        enrolled_count = db.session.execute(
            db.select(db.func.count()).select_from(course_enrollment).where(
                course_enrollment.c.user_id == student.id
            )
        ).scalar() or 0
        
        # Get completed courses count
        completed_count = db.session.execute(
            db.select(db.func.count()).select_from(course_enrollment).where(
                course_enrollment.c.user_id == student.id,
                course_enrollment.c.completed == True
            )
        ).scalar() or 0
        
        # Get exam attempts
        attempts = ExamAttempt.query.filter_by(
            student_id=student.id, status="graded"
        ).all()
        
        total_attempts = len(attempts)
        avg_score = round(sum(a.percentage or 0 for a in attempts) / total_attempts, 1) if total_attempts else 0
        passed = sum(1 for a in attempts if a.is_passed)
        pass_rate = round(passed / total_attempts * 100, 1) if total_attempts else 0
        
        result.append({
            "student_id": student.id,
            "student_name": f"{student.first_name} {student.last_name}".strip() or student.username,
            "email": student.email,
            "enrolled_courses": enrolled_count,
            "completed_courses": completed_count,
            "total_attempts": total_attempts,
            "average_score": avg_score,
            "pass_rate": pass_rate
        })
    
    return success(result)


# ═══════════════════════════════════════════════
#  COURSES ANALYTICS (NEW)
# ═══════════════════════════════════════════════

@reports_bp.get("/courses-analytics")
@jwt_required()
def courses_analytics():
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)
    
    if user.role not in ("admin", "instructor"):
        return error("Access denied.", 403)
    
    courses = Course.query.all()
    result = []
    
    for course in courses:
        enrollments = db.session.execute(
            db.select(course_enrollment).where(course_enrollment.c.course_id == course.id)
        ).fetchall()
        
        total_enrolled = len(enrollments)
        completed = sum(1 for e in enrollments if e.completed)
        avg_progress = round(sum(e.progress_pct for e in enrollments) / total_enrolled, 1) if total_enrolled else 0
        
        result.append({
            "course_id": course.id,
            "course_title": course.title,
            "total_enrolled": total_enrolled,
            "completed_count": completed,
            "average_progress": avg_progress,
            "average_rating": course.rating or 0
        })
    
    return success(result)


# ═══════════════════════════════════════════════
#  EXAMS ANALYTICS (NEW)
# ═══════════════════════════════════════════════

@reports_bp.get("/exams-analytics")
@jwt_required()
def exams_analytics():
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)
    
    if user.role not in ("admin", "instructor"):
        return error("Access denied.", 403)
    
    exams = Exam.query.all()
    result = []
    
    for exam in exams:
        attempts = ExamAttempt.query.filter_by(exam_id=exam.id, status="graded").all()
        total_attempts = len(attempts)
        
        if total_attempts > 0:
            avg_score = round(sum(a.percentage or 0 for a in attempts) / total_attempts, 1)
            passed = sum(1 for a in attempts if a.is_passed)
            pass_rate = round(passed / total_attempts * 100, 1)
            highest_score = max((a.percentage or 0 for a in attempts), default=0)
            lowest_score = min((a.percentage or 0 for a in attempts), default=0)
        else:
            avg_score = 0
            pass_rate = 0
            highest_score = 0
            lowest_score = 0
        
        result.append({
            "exam_id": exam.id,
            "exam_title": exam.title,
            "total_attempts": total_attempts,
            "average_score": avg_score,
            "pass_rate": pass_rate,
            "highest_score": highest_score,
            "lowest_score": lowest_score
        })
    
    return success(result)


# ═══════════════════════════════════════════════
#  EXAM REPORT
# ═══════════════════════════════════════════════

@reports_bp.get("/exams/<int:exam_id>")
@jwt_required()
def exam_report(exam_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)
    
    exam = Exam.query.get_or_404(exam_id)
    graded = ExamAttempt.query.filter_by(exam_id=exam_id, status="graded").all()

    if not graded:
        return success({
            "exam_id": exam_id,
            "exam_title": exam.title,
            "message": "No graded attempts yet.",
        })

    scores = [a.percentage for a in graded if a.percentage is not None]
    passed = sum(1 for a in graded if a.is_passed)

    return success({
        "exam_id": exam_id,
        "exam_title": exam.title,
        "total_attempts": len(graded),
        "passed": passed,
        "failed": len(graded) - passed,
        "pass_rate_pct": round(passed / len(graded) * 100, 1),
        "avg_score_pct": round(sum(scores) / len(scores), 1) if scores else 0,
        "highest_score_pct": max(scores, default=0),
        "lowest_score_pct": min(scores, default=0),
    })


# ═══════════════════════════════════════════════
#  COURSE REPORT
# ═══════════════════════════════════════════════

@reports_bp.get("/courses/<int:course_id>")
@jwt_required()
def course_report(course_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)
    
    course = Course.query.get_or_404(course_id)

    enrolled_count = db.session.execute(
        db.select(db.func.count()).select_from(course_enrollment).where(
            course_enrollment.c.course_id == course_id
        )
    ).scalar()

    completed_lessons = db.session.query(LessonProgress).join(Lesson).join(Module).filter(
        Module.course_id == course_id,
        LessonProgress.is_completed.is_(True),
    ).count()

    return success({
        "course_id": course_id,
        "course_title": course.title,
        "enrolled_students": enrolled_count,
        "rating": course.rating,
        "rating_count": course.rating_count,
        "completed_lessons": completed_lessons,
    })


# ═══════════════════════════════════════════════
#  STUDENT REPORT
# ═══════════════════════════════════════════════

@reports_bp.get("/students/<int:student_id>")
@jwt_required()
def student_report(student_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)
    
    student = User.query.get_or_404(student_id)
    if student.role != "student":
        return error("User is not a student.", 400)

    attempts = ExamAttempt.query.filter_by(student_id=student_id).all()
    graded = [a for a in attempts if a.status == "graded"]
    passed = sum(1 for a in graded if a.is_passed)
    avg = round(
        sum(a.percentage for a in graded if a.percentage) / len(graded), 1
    ) if graded else 0

    enrolled_count = db.session.execute(
        db.select(db.func.count()).select_from(course_enrollment).where(
            course_enrollment.c.user_id == student_id
        )
    ).scalar()

    return success({
        "student_id": student_id,
        "student_name": f"{student.first_name} {student.last_name}".strip(),
        "email": student.email,
        "enrolled_courses": enrolled_count,
        "total_attempts": len(attempts),
        "graded_attempts": len(graded),
        "passed": passed,
        "failed": len(graded) - passed,
        "average_score_pct": avg,
    })