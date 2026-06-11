from app.extensions import ma
from app.models import (
    User, Category, Course, Module, Lesson, LessonResource,
    LessonProgress, Review, Question, QuestionOption, QuestionBank,
    QuestionBankEntry, Exam, ExamAttempt, AttemptAnswer, Certificate, Notification,
)
from marshmallow import fields, validates, ValidationError
import re


# ─────────────────────────────────────────────
#  User Schemas
# ─────────────────────────────────────────────

class UserPublicSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "role",
                  "avatar_url", "bio", "created_at")
        dump_only = ("id", "created_at")


class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role",
                  "avatar_url", "bio", "is_active", "is_verified",
                  "last_login", "created_at", "updated_at")
        dump_only = ("id", "is_verified", "last_login", "created_at", "updated_at")

    full_name = fields.Method("get_full_name")

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class UserRegisterSchema(ma.Schema):
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    role = fields.Str(load_default="student")

    @validates("username")
    def validate_username(self, value):
        if len(value) < 3:
            raise ValidationError("Username must be at least 3 characters.")
        if not re.match(r"^[a-zA-Z0-9_]+$", value):
            raise ValidationError("Username may only contain letters, numbers, and underscores.")

    @validates("password")
    def validate_password(self, value):
        if len(value) < 6:
            raise ValidationError("Password must be at least 6 characters.")

    @validates("role")
    def validate_role(self, value):
        if value not in ("student", "instructor", "admin"):
            raise ValidationError("Invalid role.")


class UserLoginSchema(ma.Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)


# ─────────────────────────────────────────────
#  Category & Course Schemas
# ─────────────────────────────────────────────

class CategorySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "icon", "color", "created_at")
        dump_only = ("id", "created_at")


class CourseListSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Course
        fields = ("id", "title", "slug", "short_description", "thumbnail_url",
                  "level", "language", "price", "is_published", "is_featured",
                  "duration_hours", "rating", "rating_count", "created_at",
                  "enrolled_count")
        dump_only = ("id", "rating", "rating_count", "created_at")

    instructor = fields.Nested(UserPublicSchema, dump_only=True)
    category = fields.Nested(CategorySchema, dump_only=True)
    enrolled_count = fields.Method("get_enrolled_count")
    resources = fields.Method("get_resources")

    def get_enrolled_count(self, obj):
        return obj.enrolled_count
    def get_resources(self, obj):
        return [r.to_dict() for r in obj.resources]


class ModuleSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Module
        include_fk = True
        fields = ("id", "title", "description", "order_index", "course_id", "created_at")
        dump_only = ("id", "created_at")


class LessonResourceSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = LessonResource
        fields = ("id", "title", "resource_type", "url", "file_size_kb", "created_at")
        dump_only = ("id", "created_at")


class LessonSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Lesson
        include_fk = True
        fields = ("id", "title", "content", "lesson_type", "video_url",
                  "duration_minutes", "order_index", "is_preview", "is_published",
                  "module_id", "created_at", "updated_at")
        dump_only = ("id", "created_at", "updated_at")

    resources = fields.List(fields.Nested(LessonResourceSchema), dump_only=True)


class CourseDetailSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Course
        fields = ("id", "title", "slug", "description", "short_description",
                  "thumbnail_url", "level", "language", "price", "is_published",
                  "is_featured", "duration_hours", "rating", "rating_count",
                  "created_at", "updated_at", "enrolled_count")
        dump_only = ("id", "rating", "rating_count", "created_at", "updated_at")

    instructor = fields.Nested(UserPublicSchema, dump_only=True)
    category = fields.Nested(CategorySchema, dump_only=True)
    modules = fields.List(fields.Nested(ModuleSchema), dump_only=True)
    enrolled_count = fields.Method("get_enrolled_count")
    resources = fields.Method("get_resources") 

    def get_enrolled_count(self, obj):
        return obj.enrolled_count
    def get_resources(self, obj):
        return [r.to_dict() for r in obj.resources]


class LessonProgressSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = LessonProgress
        include_fk = True
        fields = ("id", "user_id", "lesson_id", "is_completed",
                  "watch_time_seconds", "last_position_seconds",
                  "completed_at", "updated_at")
        dump_only = ("id", "updated_at")


class ReviewSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Review
        include_fk = True
        fields = ("id", "rating", "comment", "course_id", "user_id", "created_at")
        dump_only = ("id", "created_at")

    user = fields.Nested(UserPublicSchema, dump_only=True)

    @validates("rating")
    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise ValidationError("Rating must be between 1 and 5.")


# ─────────────────────────────────────────────
#  Question & Exam Schemas
# ─────────────────────────────────────────────

class QuestionOptionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = QuestionOption
        fields = ("id", "text", "is_correct", "order_index")
        dump_only = ("id",)


class QuestionOptionPublicSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = QuestionOption
        fields = ("id", "text", "order_index")
        dump_only = ("id",)


class QuestionSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Question
        include_fk = True
        fields = ("id", "text", "question_type", "difficulty", "explanation",
                  "image_url", "topic_tag", "created_by", "created_at", "updated_at")
        dump_only = ("id", "created_at", "updated_at")

    options = fields.List(fields.Nested(QuestionOptionSchema), dump_only=True)


class QuestionPublicSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Question
        fields = ("id", "text", "question_type", "difficulty", "options",
                  "image_url", "topic_tag", "created_at")
        dump_only = ("id", "created_at")

    options = fields.List(fields.Nested(QuestionOptionPublicSchema), dump_only=True)


class QuestionBankSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = QuestionBank
        include_fk = True
        fields = ("id", "name", "description", "category", "created_by", "created_at")
        dump_only = ("id", "created_at")


class QuestionBankEntrySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = QuestionBankEntry
        include_fk = True
        fields = ("id", "bank_id", "question_id")
        dump_only = ("id",)


class ExamSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Exam
        include_fk = True
        fields = ("id", "title", "description", "instructions", "exam_type",
                  "duration_minutes", "total_marks", "passing_marks", "max_attempts",
                  "shuffle_questions", "shuffle_options", "show_results_immediately",
                  "is_published", "is_proctored", "start_time", "end_time",
                  "course_id", "created_by", "created_at", "updated_at",
                  "question_count")
        dump_only = ("id", "created_at", "updated_at")

    question_count = fields.Method("get_question_count")

    def get_question_count(self, obj):
        return obj.question_count


class ExamAttemptSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ExamAttempt
        include_fk = True
        fields = ("id", "exam_id", "student_id", "status", "score",
                  "percentage", "is_passed", "started_at", "submitted_at",
                  "graded_at", "time_spent_seconds","student_name", "created_at")
        dump_only = ("id", "score", "percentage", "is_passed",
                     "graded_at", "created_at")
        
    student_name = fields.Method("get_student_name")

    def get_student_name(self, obj):
        if obj.student:
            return f"{obj.student.first_name} {obj.student.last_name}".strip()
        return "Unknown"


class AttemptAnswerSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = AttemptAnswer
        include_fk = True
        fields = ("id", "attempt_id", "question_id", "selected_option_id",
                  "text_answer", "is_correct", "marks_awarded", "feedback",
                  "answered_at")
        dump_only = ("id", "is_correct", "marks_awarded", "feedback", "answered_at")


class CertificateSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Certificate
        include_fk = True
        fields = ("id", "user_id", "course_id", "certificate_number",
                  "issued_at", "valid_until", "pdf_url")
        dump_only = ("id", "certificate_number", "issued_at")


class NotificationSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Notification
        include_fk = True
        fields = ("id", "user_id", "title", "message", "notification_type",
                  "is_read", "action_url", "created_at")
        dump_only = ("id", "created_at")


# ─────────────────────────────────────────────
#  Singletons
# ─────────────────────────────────────────────

user_schema = UserSchema()
users_schema = UserSchema(many=True)
user_public_schema = UserPublicSchema()
users_public_schema = UserPublicSchema(many=True)
register_schema = UserRegisterSchema()
login_schema = UserLoginSchema()

category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)

course_list_schema = CourseListSchema(many=True)
course_detail_schema = CourseDetailSchema()

module_schema = ModuleSchema()
modules_schema = ModuleSchema(many=True)
lesson_schema = LessonSchema()
lessons_schema = LessonSchema(many=True)
lesson_resource_schema = LessonResourceSchema()
lesson_progress_schema = LessonProgressSchema()
lesson_progress_list_schema = LessonProgressSchema(many=True)

review_schema = ReviewSchema()
reviews_schema = ReviewSchema(many=True)

question_schema = QuestionSchema()
questions_schema = QuestionSchema(many=True)
question_public_schema = QuestionPublicSchema()
questions_public_schema = QuestionPublicSchema(many=True)
question_option_schema = QuestionOptionSchema()
question_bank_schema = QuestionBankSchema()
question_banks_schema = QuestionBankSchema(many=True)
question_bank_entry_schema = QuestionBankEntrySchema()
question_bank_entries_schema = QuestionBankEntrySchema(many=True)

exam_schema = ExamSchema()
exams_schema = ExamSchema(many=True)
attempt_schema = ExamAttemptSchema()
attempts_schema = ExamAttemptSchema(many=True)
answer_schema = AttemptAnswerSchema()
answers_schema = AttemptAnswerSchema(many=True)

certificate_schema = CertificateSchema()
certificates_schema = CertificateSchema(many=True)

notification_schema = NotificationSchema()
notifications_schema = NotificationSchema(many=True)