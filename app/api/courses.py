from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from datetime import datetime
from app.extensions import db
from app.models import (
    Course, Module, Lesson, LessonProgress,
    Review, Certificate, course_enrollment, CourseResource,
)
from app.schemas import (
    course_list_schema, course_detail_schema,
    module_schema, modules_schema,
    lesson_schema, lessons_schema,
    review_schema, reviews_schema,
    certificate_schema, certificates_schema,
    lesson_progress_schema,
)
from app.services.utils.helpers import (
    success, error, paginate, get_current_user,
    unique_slug, generate_certificate_number,
)
import os
from werkzeug.utils import secure_filename
from flask import current_app

courses_bp = Blueprint("courses", __name__, url_prefix="/api/courses")


# ═══════════════════════════════════════════════
#  COURSES
# ═══════════════════════════════════════════════

@courses_bp.get("")
def list_courses():
    query = Course.query.filter_by(is_published=True)

    level = request.args.get("level")
    search = request.args.get("search")
    category_id = request.args.get("category_id", type=int)

    if level:
        query = query.filter_by(level=level)
    if category_id:
        query = query.filter_by(category_id=category_id)
    if search:
        query = query.filter(Course.title.ilike(f"%{search}%"))

    courses = query.all()
    return success(course_list_schema.dump(courses))


@courses_bp.get("/<int:course_id>")
def get_course(course_id):
    course = Course.query.get_or_404(course_id)
    return success(course_detail_schema.dump(course))


@courses_bp.post("")
@jwt_required()
def create_course():
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)
    if user.role not in ("instructor", "admin"):
        return error("Only instructors and admins can create courses.", 403)

    data = request.get_json() or {}
    if not data.get("title"):
        return error("Title is required.", 422)

    slug = unique_slug(Course, data["title"])
    course = Course(
        title=data["title"],
        slug=slug,
        short_description=data.get("short_description", ""),
        description=data.get("description", ""),
        level=data.get("level", "beginner"),
        price=data.get("price", 0.0),
        duration_hours=data.get("duration_hours", 0),
        is_published=data.get("is_published", False),
        thumbnail_url=data.get("thumbnail_url"),
        category_id=data.get("category_id"),
        instructor_id=user.id,
    )
    db.session.add(course)
    db.session.commit()
    return success(course_detail_schema.dump(course), "Course created.", 201)


@courses_bp.patch("/<int:course_id>")
@jwt_required()
def update_course(course_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    course = Course.query.get_or_404(course_id)
    if course.instructor_id != user.id and user.role != "admin":
        return error("Not authorized.", 403)

    data = request.get_json() or {}
    for field in ("title", "short_description", "description", "level",
                  "price", "duration_hours", "is_published", "thumbnail_url",
                  "category_id"):
        if field in data:
            setattr(course, field, data[field])

    if "title" in data:
        course.slug = unique_slug(Course, data["title"])

    db.session.commit()
    return success(course_detail_schema.dump(course), "Course updated.")


@courses_bp.delete("/<int:course_id>")
@jwt_required()
def delete_course(course_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    course = Course.query.get_or_404(course_id)
    if course.instructor_id != user.id and user.role != "admin":
        return error("Not authorized.", 403)

    db.session.delete(course)
    db.session.commit()
    return success(message="Course deleted.")


# ═══════════════════════════════════════════════
#  ENROLLMENT
# ═══════════════════════════════════════════════

@courses_bp.post("/<int:course_id>/enroll")
@jwt_required()
def enroll_in_course(course_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    course = Course.query.get_or_404(course_id)
    if not course.is_published:
        return error("Course is not available.", 400)

    existing = db.session.execute(
        db.select(course_enrollment).where(
            course_enrollment.c.user_id == user.id,
            course_enrollment.c.course_id == course_id,
        )
    ).first()

    if existing:
        return error("Already enrolled.", 409)

    db.session.execute(
        course_enrollment.insert().values(
            user_id=user.id,
            course_id=course_id,
        )
    )
    db.session.commit()
    return success(message="Enrolled successfully.")


@courses_bp.delete("/<int:course_id>/enroll")
@jwt_required()
def unenroll_from_course(course_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    db.session.execute(
        course_enrollment.delete().where(
            course_enrollment.c.user_id == user.id,
            course_enrollment.c.course_id == course_id,
        )
    )
    db.session.commit()
    return success(message="Unenrolled successfully.")


@courses_bp.get("/enrolled")
@jwt_required()
def my_enrolled_courses():
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    courses = (
        db.session.query(Course)
        .join(course_enrollment, Course.id == course_enrollment.c.course_id)
        .filter(course_enrollment.c.user_id == user.id)
        .all()
    )
    return success(course_list_schema.dump(courses))


# ═══════════════════════════════════════════════
#  MODULES
# ═══════════════════════════════════════════════

@courses_bp.get("/<int:course_id>/modules")
def list_modules(course_id):
    Course.query.get_or_404(course_id)
    modules = Module.query.filter_by(course_id=course_id).order_by(
        Module.order_index
    ).all()
    return success(modules_schema.dump(modules))


@courses_bp.post("/<int:course_id>/modules")
@jwt_required()
def create_module(course_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    course = Course.query.get_or_404(course_id)
    if course.instructor_id != user.id and user.role != "admin":
        return error("Not authorized.", 403)

    data = request.get_json() or {}
    if not data.get("title"):
        return error("Title is required.", 422)

    module = Module(
        title=data["title"],
        description=data.get("description", ""),
        order_index=data.get("order_index", 0),
        course_id=course_id,
    )
    db.session.add(module)
    db.session.commit()
    return success(module_schema.dump(module), "Module created.", 201)


@courses_bp.patch("/<int:course_id>/modules/<int:module_id>")
@jwt_required()
def update_module(course_id, module_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    course = Course.query.get_or_404(course_id)
    module = Module.query.filter_by(id=module_id, course_id=course_id).first_or_404()

    if course.instructor_id != user.id and user.role != "admin":
        return error("Not authorized.", 403)

    data = request.get_json() or {}
    for field in ("title", "description", "order_index"):
        if field in data:
            setattr(module, field, data[field])

    db.session.commit()
    return success(module_schema.dump(module), "Module updated.")


@courses_bp.delete("/<int:course_id>/modules/<int:module_id>")
@jwt_required()
def delete_module(course_id, module_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    course = Course.query.get_or_404(course_id)
    module = Module.query.filter_by(id=module_id, course_id=course_id).first_or_404()

    if course.instructor_id != user.id and user.role != "admin":
        return error("Not authorized.", 403)

    db.session.delete(module)
    db.session.commit()
    return success(message="Module deleted.")


# ═══════════════════════════════════════════════
#  LESSONS
# ═══════════════════════════════════════════════

@courses_bp.get("/<int:course_id>/modules/<int:module_id>/lessons")
def list_lessons(course_id, module_id):
    lessons = Lesson.query.filter_by(module_id=module_id).order_by(
        Lesson.order_index
    ).all()
    return success(lessons_schema.dump(lessons))


@courses_bp.post("/<int:course_id>/modules/<int:module_id>/lessons")
@jwt_required()
def create_lesson(course_id, module_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    course = Course.query.get_or_404(course_id)
    Module.query.filter_by(id=module_id, course_id=course_id).first_or_404()

    if course.instructor_id != user.id and user.role != "admin":
        return error("Not authorized.", 403)

    data = request.get_json() or {}
    if not data.get("title"):
        return error("Title is required.", 422)

    lesson = Lesson(
        title=data["title"],
        content=data.get("content", ""),
        lesson_type=data.get("lesson_type", "text"),
        video_url=data.get("video_url"),
        duration_minutes=data.get("duration_minutes", 0),
        order_index=data.get("order_index", 0),
        is_published=data.get("is_published", False),
        is_preview=data.get("is_preview", False),
        module_id=module_id,
    )
    db.session.add(lesson)
    db.session.commit()
    return success(lesson_schema.dump(lesson), "Lesson created.", 201)


@courses_bp.patch("/<int:course_id>/modules/<int:module_id>/lessons/<int:lesson_id>")
@jwt_required()
def update_lesson(course_id, module_id, lesson_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    course = Course.query.get_or_404(course_id)
    lesson = Lesson.query.filter_by(id=lesson_id, module_id=module_id).first_or_404()

    if course.instructor_id != user.id and user.role != "admin":
        return error("Not authorized.", 403)

    data = request.get_json() or {}
    for field in ("title", "content", "lesson_type", "video_url",
                  "duration_minutes", "order_index", "is_published", "is_preview"):
        if field in data:
            setattr(lesson, field, data[field])

    db.session.commit()
    return success(lesson_schema.dump(lesson), "Lesson updated.")


@courses_bp.delete("/<int:course_id>/modules/<int:module_id>/lessons/<int:lesson_id>")
@jwt_required()
def delete_lesson(course_id, module_id, lesson_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    course = Course.query.get_or_404(course_id)
    lesson = Lesson.query.filter_by(id=lesson_id, module_id=module_id).first_or_404()

    if course.instructor_id != user.id and user.role != "admin":
        return error("Not authorized.", 403)

    db.session.delete(lesson)
    db.session.commit()
    return success(message="Lesson deleted.")


# ═══════════════════════════════════════════════
#  LESSON PROGRESS
# ═══════════════════════════════════════════════

@courses_bp.post("/<int:course_id>/modules/<int:module_id>/lessons/<int:lesson_id>/progress")
@jwt_required()
def update_lesson_progress(course_id, module_id, lesson_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    Lesson.query.filter_by(id=lesson_id, module_id=module_id).first_or_404()
    data = request.get_json() or {}

    progress = LessonProgress.query.filter_by(
        user_id=user.id, lesson_id=lesson_id
    ).first()

    if not progress:
        progress = LessonProgress(user_id=user.id, lesson_id=lesson_id)
        db.session.add(progress)

    if "is_completed" in data:
        progress.is_completed = data["is_completed"]
    if "watch_time_seconds" in data:
        progress.watch_time_seconds = data["watch_time_seconds"]
    if "last_position_seconds" in data:
        progress.last_position_seconds = data["last_position_seconds"]

    db.session.commit()
    return success(lesson_progress_schema.dump(progress), "Progress updated.")


# ═══════════════════════════════════════════════
#  REVIEWS
# ═══════════════════════════════════════════════

@courses_bp.get("/<int:course_id>/reviews")
def list_reviews(course_id):
    Course.query.get_or_404(course_id)
    reviews = Review.query.filter_by(course_id=course_id).order_by(
        Review.created_at.desc()
    ).all()
    return success(reviews_schema.dump(reviews))


@courses_bp.post("/<int:course_id>/reviews")
@jwt_required()
def create_review(course_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    course = Course.query.get_or_404(course_id)
    data = request.get_json() or {}

    rating = data.get("rating")
    if not rating or not 1 <= int(rating) <= 5:
        return error("Rating must be between 1 and 5.", 422)

    if Review.query.filter_by(course_id=course_id, user_id=user.id).first():
        return error("You already reviewed this course.", 409)

    review = Review(
        rating=rating,
        comment=data.get("comment", ""),
        course_id=course_id,
        user_id=user.id,
    )
    db.session.add(review)

    all_reviews = Review.query.filter_by(course_id=course_id).all()
    total = sum(r.rating for r in all_reviews) + rating
    course.rating = round(total / (len(all_reviews) + 1), 2)
    course.rating_count = len(all_reviews) + 1

    db.session.commit()
    return success(review_schema.dump(review), "Review submitted.", 201)


# ═══════════════════════════════════════════════
#  CERTIFICATES
# ═══════════════════════════════════════════════

@courses_bp.get("/certificates")
@jwt_required()
def my_certificates():
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    certificates = Certificate.query.filter_by(user_id=user.id).all()
    return success(certificates_schema.dump(certificates))


@courses_bp.get("/certificates/<string:cert_number>")
def verify_certificate(cert_number):
    cert = Certificate.query.filter_by(
        certificate_number=cert_number
    ).first_or_404()
    return success(certificate_schema.dump(cert))


# ═══════════════════════════════════════════════
#  COURSE RESOURCES (File Upload)
# ═══════════════════════════════════════════════

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'mp4', 'mp3', 'zip', 'txt', 'jpg', 'png', 'pptx', 'xlsx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@courses_bp.post("/<int:course_id>/upload-resource")
@jwt_required()
def upload_course_resource(course_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)
    
    course = Course.query.get_or_404(course_id)
    
    if course.instructor_id != user.id and user.role != "admin":
        return error("Not authorized.", 403)
    
    if 'file' not in request.files:
        return error("No file provided", 400)
    
    file = request.files['file']
    if file.filename == '':
        return error("No file selected", 400)
    
    resource_type = request.form.get('resource_type', 'file')
    title = request.form.get('title', file.filename)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        
        # FIXED: Correct path to static/uploads folder
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        filepath = os.path.join(upload_dir, unique_filename)
        file.save(filepath)
        
        file_size_kb = os.path.getsize(filepath) // 1024
        file_url = f"/uploads/{unique_filename}"
        
        resource = CourseResource(
            course_id=course_id,
            title=title,
            resource_type=resource_type,
            url=file_url,
            file_size_kb=file_size_kb,
            order_index=len(course.resources)
        )
        db.session.add(resource)
        db.session.commit()
        
        return success({
            "id": resource.id,
            "title": resource.title,
            "resource_type": resource.resource_type,
            "url": resource.url,
            "file_size_kb": resource.file_size_kb
        }, "File uploaded successfully", 201)
    
    return error("File type not allowed", 400)


@courses_bp.delete("/resources/<int:resource_id>")
@jwt_required()
def delete_course_resource(resource_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)
    
    resource = CourseResource.query.get_or_404(resource_id)
    course = Course.query.get(resource.course_id)
    
    if course.instructor_id != user.id and user.role != "admin":
        return error("Not authorized.", 403)
    
    if resource.url and resource.url.startswith('/uploads/'):
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static', 'uploads')
        filename = resource.url.replace('/uploads/', '')
        filepath = os.path.join(upload_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    
    db.session.delete(resource)
    db.session.commit()
    
    return success(message="Resource deleted")


@courses_bp.get("/<int:course_id>/resources")
@jwt_required()
def get_course_resources(course_id):
    course = Course.query.get_or_404(course_id)
    user = get_current_user()
    
    if user.role == "student":
        enrollment = db.session.execute(
            db.select(course_enrollment).where(
                course_enrollment.c.user_id == user.id,
                course_enrollment.c.course_id == course_id,
            )
        ).first()
        if not enrollment:
            return error("You must be enrolled to access course materials", 403)
    
    resources = [{
        "id": r.id,
        "title": r.title,
        "resource_type": r.resource_type,
        "url": r.url,
        "file_size_kb": r.file_size_kb
    } for r in course.resources]
    
    return success(resources)