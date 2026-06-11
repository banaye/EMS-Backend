from datetime import datetime, timezone
from app.extensions import db, bcrypt


# ─────────────────────────────────────────────
#  Association / pivot tables
# ─────────────────────────────────────────────

course_enrollment = db.Table(
    "course_enrollment",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("course_id", db.Integer, db.ForeignKey("courses.id"), primary_key=True),
    db.Column("enrolled_at", db.DateTime, default=lambda: datetime.now(timezone.utc)),
    db.Column("completed", db.Boolean, default=False),
    db.Column("progress_pct", db.Float, default=0.0),
)

exam_question = db.Table(
    "exam_question",
    db.Column("exam_id", db.Integer, db.ForeignKey("exams.id"), primary_key=True),
    db.Column("question_id", db.Integer, db.ForeignKey("questions.id"), primary_key=True),
    db.Column("order_index", db.Integer, default=0),
    db.Column("marks", db.Float, default=1.0),
)


# ─────────────────────────────────────────────
#  User
# ─────────────────────────────────────────────

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(60), nullable=False)
    last_name = db.Column(db.String(60), nullable=False)
    role = db.Column(db.Enum("student", "instructor", "admin", name="user_role"),
                     default="student", nullable=False)
    avatar_url = db.Column(db.String(500))
    bio = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    courses_created = db.relationship("Course", back_populates="instructor",
                                      foreign_keys="Course.instructor_id")
    enrolled_courses = db.relationship("Course", secondary=course_enrollment,
                                       back_populates="students")
    attempts = db.relationship("ExamAttempt", back_populates="student",
                               cascade="all, delete-orphan")
    notifications = db.relationship("Notification", back_populates="user",
                                    cascade="all, delete-orphan")
    progress_records = db.relationship("LessonProgress", back_populates="user",
                                       cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        if not self.password_hash:
            return False
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


# ─────────────────────────────────────────────
#  Course & Learning
# ─────────────────────────────────────────────

class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))
    color = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    courses = db.relationship("Course", back_populates="category")


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    description = db.Column(db.Text)
    short_description = db.Column(db.String(300))
    thumbnail_url = db.Column(db.String(500))
    level = db.Column(db.Enum("beginner", "intermediate", "advanced", name="course_level"),
                      default="beginner")
    language = db.Column(db.String(30), default="English")
    price = db.Column(db.Float, default=0.0)
    is_published = db.Column(db.Boolean, default=False)
    is_featured = db.Column(db.Boolean, default=False)
    duration_hours = db.Column(db.Float, default=0.0)
    rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    instructor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    instructor = db.relationship("User", back_populates="courses_created",
                                 foreign_keys=[instructor_id])
    category = db.relationship("Category", back_populates="courses")
    students = db.relationship("User", secondary=course_enrollment,
                               back_populates="enrolled_courses")
    modules = db.relationship("Module", back_populates="course",
                              cascade="all, delete-orphan", order_by="Module.order_index")
    exams = db.relationship("Exam", back_populates="course")
    reviews = db.relationship("Review", back_populates="course", cascade="all, delete-orphan")
    resources = db.relationship("CourseResource", back_populates="course", cascade="all, delete-orphan")

    @property
    def enrolled_count(self):
        return len(self.students)


class Module(db.Model):
    __tablename__ = "modules"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    order_index = db.Column(db.Integer, default=0)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    course = db.relationship("Course", back_populates="modules")
    lessons = db.relationship("Lesson", back_populates="module",
                              cascade="all, delete-orphan", order_by="Lesson.order_index")


class Lesson(db.Model):
    __tablename__ = "lessons"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    lesson_type = db.Column(db.Enum("video", "text", "quiz", "assignment", name="lesson_type"),
                            default="text")
    video_url = db.Column(db.String(500))
    duration_minutes = db.Column(db.Integer, default=0)
    order_index = db.Column(db.Integer, default=0)
    is_preview = db.Column(db.Boolean, default=False)
    is_published = db.Column(db.Boolean, default=True)
    module_id = db.Column(db.Integer, db.ForeignKey("modules.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    module = db.relationship("Module", back_populates="lessons")
    progress_records = db.relationship("LessonProgress", back_populates="lesson",
                                       cascade="all, delete-orphan")
    resources = db.relationship("LessonResource", back_populates="lesson",
                                cascade="all, delete-orphan")


class LessonResource(db.Model):
    __tablename__ = "lesson_resources"

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    resource_type = db.Column(db.Enum("pdf", "link", "file", "code", name="resource_type"),
                               default="link")
    url = db.Column(db.String(500))
    file_size_kb = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    lesson = db.relationship("Lesson", back_populates="resources")


class LessonProgress(db.Model):
    __tablename__ = "lesson_progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    watch_time_seconds = db.Column(db.Integer, default=0)
    last_position_seconds = db.Column(db.Integer, default=0)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint("user_id", "lesson_id"),)

    user = db.relationship("User", back_populates="progress_records")
    lesson = db.relationship("Lesson", back_populates="progress_records")


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint("course_id", "user_id"),)

    course = db.relationship("Course", back_populates="reviews")
    user = db.relationship("User")
    
class CourseResource(db.Model):
    __tablename__ = "course_resources"
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    resource_type = db.Column(db.Enum("pdf", "link", "file", "video", name="resource_type_enum"), default="pdf")
    url = db.Column(db.String(500), nullable=False)
    file_size_kb = db.Column(db.Integer, default=0)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    course = db.relationship("Course", back_populates="resources")
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "resource_type": self.resource_type,
            "url": self.url,
            "file_size_kb": self.file_size_kb,
            "order_index": self.order_index
        }


# ─────────────────────────────────────────────
#  Examination
# ─────────────────────────────────────────────

class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    keywords = db.Column(db.Text)  
    text = db.Column(db.Text, nullable=False)
    question_type = db.Column(
        db.Enum("mcq", "true_false", "short_answer", "essay", "fill_blank",
                name="question_type"),
        default="mcq", nullable=False,
    )
    difficulty = db.Column(db.Enum("easy", "medium", "hard", name="difficulty"),
                           default="medium")
    explanation = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    topic_tag = db.Column(db.String(100))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    author = db.relationship("User")
    options = db.relationship("QuestionOption", back_populates="question",
                              cascade="all, delete-orphan")
    exams = db.relationship("Exam", secondary=exam_question, back_populates="questions")
    answers = db.relationship("AttemptAnswer", back_populates="question")


class QuestionOption(db.Model):
    __tablename__ = "question_options"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    order_index = db.Column(db.Integer, default=0)

    question = db.relationship("Question", back_populates="options")


class QuestionBank(db.Model):
    __tablename__ = "question_banks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    author = db.relationship("User")
    question_entries = db.relationship("QuestionBankEntry", back_populates="bank",
                                       cascade="all, delete-orphan")


class QuestionBankEntry(db.Model):
    __tablename__ = "question_bank_entries"

    id = db.Column(db.Integer, primary_key=True)
    bank_id = db.Column(db.Integer, db.ForeignKey("question_banks.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    added_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    bank = db.relationship("QuestionBank", back_populates="question_entries")
    question = db.relationship("Question")


class Exam(db.Model):
    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    instructions = db.Column(db.Text)
    exam_type = db.Column(
        db.Enum("quiz", "midterm", "final", "practice", "assignment", name="exam_type"),
        default="quiz",
    )
    duration_minutes = db.Column(db.Integer, default=60)
    total_marks = db.Column(db.Float, default=100.0)
    passing_marks = db.Column(db.Float, default=40.0)
    max_attempts = db.Column(db.Integer, default=1)
    shuffle_questions = db.Column(db.Boolean, default=False)
    shuffle_options = db.Column(db.Boolean, default=False)
    show_results_immediately = db.Column(db.Boolean, default=True)
    is_published = db.Column(db.Boolean, default=False)
    is_proctored = db.Column(db.Boolean, default=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    course = db.relationship("Course", back_populates="exams")
    author = db.relationship("User")
    questions = db.relationship("Question", secondary=exam_question, back_populates="exams")
    attempts = db.relationship("ExamAttempt", back_populates="exam",
                               cascade="all, delete-orphan")

    @property
    def question_count(self):
        return len(self.questions)


class ExamAttempt(db.Model):
    __tablename__ = "exam_attempts"

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(
        db.Enum("not_started", "in_progress", "submitted", "graded", "timed_out",
                name="attempt_status"),
        default="not_started",
    )
    score = db.Column(db.Float)
    percentage = db.Column(db.Float)
    is_passed = db.Column(db.Boolean)
    started_at = db.Column(db.DateTime)
    submitted_at = db.Column(db.DateTime)
    graded_at = db.Column(db.DateTime)
    time_spent_seconds = db.Column(db.Integer, default=0)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    exam = db.relationship("Exam", back_populates="attempts")
    student = db.relationship("User", back_populates="attempts")
    answers = db.relationship("AttemptAnswer", back_populates="attempt",
                              cascade="all, delete-orphan")

    @property
    def attempt_number(self):
        previous = ExamAttempt.query.filter_by(
            exam_id=self.exam_id, student_id=self.student_id
        ).filter(ExamAttempt.id <= self.id).count()
        return previous


class AttemptAnswer(db.Model):
    __tablename__ = "attempt_answers"

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("exam_attempts.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey("question_options.id"))
    text_answer = db.Column(db.Text)
    is_correct = db.Column(db.Boolean)
    marks_awarded = db.Column(db.Float, default=0.0)
    feedback = db.Column(db.Text)
    answered_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    attempt = db.relationship("ExamAttempt", back_populates="answers")
    question = db.relationship("Question", back_populates="answers")
    selected_option = db.relationship("QuestionOption")


class Certificate(db.Model):
    __tablename__ = "certificates"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    certificate_number = db.Column(db.String(50), unique=True, nullable=False)
    issued_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    valid_until = db.Column(db.DateTime)
    pdf_url = db.Column(db.String(500))

    user = db.relationship("User")
    course = db.relationship("Course")


# ─────────────────────────────────────────────
#  Notifications
# ─────────────────────────────────────────────

class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(
        db.Enum("info", "success", "warning", "error", name="notif_type"),
        default="info",
    )
    is_read = db.Column(db.Boolean, default=False)
    action_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="notifications")