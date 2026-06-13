from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from datetime import datetime, timezone
import random
import re

from app.extensions import db
from app.models import (
    Exam, Question, QuestionOption, ExamAttempt, AttemptAnswer,
    QuestionBank, QuestionBankEntry, exam_question,
)
from app.schemas import (
    exam_schema, exams_schema,
    question_schema, questions_schema,
    question_public_schema, questions_public_schema,
    question_option_schema, question_bank_schema, question_banks_schema,
    attempt_schema, attempts_schema,
    answer_schema, answers_schema,
)
from app.services.utils.helpers import (
    success, error, paginate, get_current_user, roles_required,
)

exams_bp = Blueprint("exams", __name__, url_prefix="/api/exams")
questions_bp = Blueprint("questions", __name__, url_prefix="/api/questions")
banks_bp = Blueprint("banks", __name__, url_prefix="/api/question-banks")


# ═══════════════════════════════════════════════
#  QUESTION BANKS
# ═══════════════════════════════════════════════

@banks_bp.get("")
@jwt_required()
@roles_required("instructor", "admin")
def list_banks():
    user = get_current_user()
    if user.role == "admin":
        query = QuestionBank.query
    else:
        query = QuestionBank.query.filter_by(created_by=user.id)
    return paginate(query, question_banks_schema)


@banks_bp.post("")
@jwt_required()
@roles_required("instructor", "admin")
def create_bank():
    user = get_current_user()
    data = request.get_json() or {}
    if not data.get("name"):
        return error("Name is required.", 422)

    bank = QuestionBank(
        name=data["name"],
        description=data.get("description"),
        category=data.get("category"),
        created_by=user.id,
    )
    db.session.add(bank)
    db.session.commit()
    return success(question_bank_schema.dump(bank), "Question bank created.", 201)


@banks_bp.post("/<int:bank_id>/questions/<int:question_id>")
@jwt_required()
@roles_required("instructor", "admin")
def add_to_bank(bank_id, question_id):
    QuestionBank.query.get_or_404(bank_id)
    Question.query.get_or_404(question_id)

    existing = QuestionBankEntry.query.filter_by(
        bank_id=bank_id, question_id=question_id
    ).first()
    if existing:
        return error("Question already in bank.", 409)

    entry = QuestionBankEntry(bank_id=bank_id, question_id=question_id)
    db.session.add(entry)
    db.session.commit()
    return success(message="Question added to bank.")


# ═══════════════════════════════════════════════
#  QUESTIONS
# ═══════════════════════════════════════════════

@questions_bp.get("")
@jwt_required()
@roles_required("instructor", "admin")
def list_questions():
    user = get_current_user()
    query = Question.query if user.role == "admin" else Question.query.filter_by(created_by=user.id)

    if topic := request.args.get("topic"):
        query = query.filter(Question.topic_tag.ilike(f"%{topic}%"))
    if q_type := request.args.get("type"):
        query = query.filter_by(question_type=q_type)
    if difficulty := request.args.get("difficulty"):
        query = query.filter_by(difficulty=difficulty)

    return paginate(query, questions_schema)


@questions_bp.post("")
@jwt_required()
@roles_required("instructor", "admin")
def create_question():
    user = get_current_user()
    data = request.get_json() or {}

    if not data.get("text"):
        return error("Question text is required.", 422)

    question = Question(
        text=data["text"],
        question_type=data.get("question_type", "mcq"),
        difficulty=data.get("difficulty", "medium"),
        explanation=data.get("explanation"),
        image_url=data.get("image_url"),
        topic_tag=data.get("topic_tag"),
        keywords=data.get("keywords"),
        created_by=user.id,
    )
    db.session.add(question)
    db.session.flush()

    for i, opt in enumerate(data.get("options", [])):
        db.session.add(QuestionOption(
            question_id=question.id,
            text=opt["text"],
            is_correct=opt.get("is_correct", False),
            order_index=i,
        ))

    db.session.commit()
    return success(question_schema.dump(question), "Question created.", 201)


@questions_bp.get("/<int:question_id>")
@jwt_required()
@roles_required("instructor", "admin")
def get_question(question_id):
    q = Question.query.get_or_404(question_id)
    return success(question_schema.dump(q))


@questions_bp.patch("/<int:question_id>")
@jwt_required()
@roles_required("instructor", "admin")
def update_question(question_id):
    user = get_current_user()
    q = Question.query.get_or_404(question_id)

    if q.created_by != user.id and user.role != "admin":
        return error("Not authorized.", 403)

    data = request.get_json() or {}
    for f in ("text", "question_type", "difficulty", "explanation",
              "image_url", "topic_tag", "keywords"):
        if f in data:
            setattr(q, f, data[f])

    if "options" in data:
        QuestionOption.query.filter_by(question_id=q.id).delete()
        for i, opt in enumerate(data["options"]):
            db.session.add(QuestionOption(
                question_id=q.id,
                text=opt["text"],
                is_correct=opt.get("is_correct", False),
                order_index=i,
            ))

    db.session.commit()
    return success(question_schema.dump(q), "Question updated.")


@questions_bp.delete("/<int:question_id>")
@jwt_required()
@roles_required("instructor", "admin")
def delete_question(question_id):
    user = get_current_user()
    q = Question.query.get_or_404(question_id)

    if q.created_by != user.id and user.role != "admin":
        return error("Not authorized.", 403)

    db.session.delete(q)
    db.session.commit()
    return success(message="Question deleted.")


# ═══════════════════════════════════════════════
#  EXAMS
# ═══════════════════════════════════════════════

@exams_bp.get("")
@jwt_required()
def list_exams():
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    if user.role == "admin":
        query = Exam.query
    elif user.role == "instructor":
        query = Exam.query.filter_by(created_by=user.id)
    else:
        query = Exam.query.filter_by(is_published=True)

    if course_id := request.args.get("course_id", type=int):
        query = query.filter_by(course_id=course_id)

    return paginate(query, exams_schema)


@exams_bp.post("")
@jwt_required()
@roles_required("instructor", "admin")
def create_exam():
    user = get_current_user()
    data = request.get_json() or {}

    if not data.get("title"):
        return error("Title is required.", 422)

    exam = Exam(
        title=data["title"],
        description=data.get("description"),
        instructions=data.get("instructions"),
        exam_type=data.get("exam_type", "quiz"),
        duration_minutes=data.get("duration_minutes", 60),
        total_marks=data.get("total_marks", 100.0),
        passing_marks=data.get("passing_marks", 40.0),
        max_attempts=data.get("max_attempts", 1),
        shuffle_questions=data.get("shuffle_questions", False),
        shuffle_options=data.get("shuffle_options", False),
        show_results_immediately=data.get("show_results_immediately", True),
        is_proctored=data.get("is_proctored", False),
        is_published=data.get("is_published", False),
        start_time=_parse_dt(data.get("start_time")),
        end_time=_parse_dt(data.get("end_time")),
        course_id=data.get("course_id"),
        created_by=user.id,
    )
    db.session.add(exam)
    db.session.commit()
    return success(exam_schema.dump(exam), "Exam created.", 201)


@exams_bp.get("/<int:exam_id>")
@jwt_required()
def get_exam(exam_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    exam = Exam.query.get_or_404(exam_id)
    if not exam.is_published and user.role not in ("instructor", "admin"):
        return error("Exam not available.", 403)

    return success(exam_schema.dump(exam))


@exams_bp.patch("/<int:exam_id>")
@jwt_required()
@roles_required("instructor", "admin")
def update_exam(exam_id):
    user = get_current_user()
    exam = Exam.query.get_or_404(exam_id)

    if exam.created_by != user.id and user.role != "admin":
        return error("Not authorized.", 403)

    data = request.get_json() or {}
    for f in ("title", "description", "instructions", "exam_type", "duration_minutes",
              "total_marks", "passing_marks", "max_attempts", "shuffle_questions",
              "shuffle_options", "show_results_immediately", "is_published",
              "is_proctored", "course_id"):
        if f in data:
            setattr(exam, f, data[f])

    if "start_time" in data:
        exam.start_time = _parse_dt(data["start_time"])
    if "end_time" in data:
        exam.end_time = _parse_dt(data["end_time"])

    db.session.commit()
    return success(exam_schema.dump(exam), "Exam updated.")


@exams_bp.delete("/<int:exam_id>")
@jwt_required()
@roles_required("instructor", "admin")
def delete_exam(exam_id):
    user = get_current_user()
    exam = Exam.query.get_or_404(exam_id)

    if exam.created_by != user.id and user.role != "admin":
        return error("Not authorized.", 403)

    db.session.delete(exam)
    db.session.commit()
    return success(message="Exam deleted.")


# ─────────────────────────────────────────────
#  Exam ↔ Question management
# ─────────────────────────────────────────────

@exams_bp.post("/<int:exam_id>/questions")
@jwt_required()
@roles_required("instructor", "admin")
def add_question_to_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    data = request.get_json() or {}
    question_id = data.get("question_id")
    if not question_id:
        return error("question_id is required.", 422)

    question = Question.query.get_or_404(question_id)
    if question in exam.questions:
        return error("Question already in exam.", 409)

    db.session.execute(
        exam_question.insert().values(
            exam_id=exam_id,
            question_id=question_id,
            order_index=data.get("order_index", len(exam.questions)),
            marks=data.get("marks", 1.0),
        )
    )
    db.session.commit()
    return success(message="Question added to exam.")


@exams_bp.delete("/<int:exam_id>/questions/<int:question_id>")
@jwt_required()
@roles_required("instructor", "admin")
def remove_question_from_exam(exam_id, question_id):
    Exam.query.get_or_404(exam_id)
    db.session.execute(
        exam_question.delete().where(
            exam_question.c.exam_id == exam_id,
            exam_question.c.question_id == question_id,
        )
    )
    db.session.commit()
    return success(message="Question removed from exam.")


@exams_bp.get("/<int:exam_id>/questions")
@jwt_required()
def get_exam_questions(exam_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    exam = Exam.query.get_or_404(exam_id)
    questions = list(exam.questions)

    if exam.shuffle_questions:
        random.shuffle(questions)

    if user.role == "student":
        return success(questions_public_schema.dump(questions))
    return success(questions_schema.dump(questions))


# ═══════════════════════════════════════════════
#  ATTEMPTS
# ═══════════════════════════════════════════════

@exams_bp.post("/<int:exam_id>/attempts")
@jwt_required()
def start_attempt(exam_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    exam = Exam.query.get_or_404(exam_id)

    if not exam.is_published:
        return error("Exam is not available.", 400)

    now = datetime.now(timezone.utc)
    if exam.start_time and now < exam.start_time:
        return error("Exam has not started yet.", 400)
    if exam.end_time and now > exam.end_time:
        return error("Exam has ended.", 400)

    # SECURITY: Check for any completed/submitted attempt
    completed_attempt = ExamAttempt.query.filter(
        ExamAttempt.exam_id == exam_id,
        ExamAttempt.student_id == user.id,
        ExamAttempt.status.in_(["graded", "submitted"])
    ).first()
    
    if completed_attempt:
        return error("You have already completed this exam. Cannot start new attempt.", 400)

    previous_count = ExamAttempt.query.filter_by(
        exam_id=exam_id, student_id=user.id
    ).count()
    if exam.max_attempts and previous_count >= exam.max_attempts:
        return error(f"Maximum attempts ({exam.max_attempts}) reached.", 400)

    in_progress = ExamAttempt.query.filter_by(
        exam_id=exam_id, student_id=user.id, status="in_progress"
    ).first()
    if in_progress:
        return success(attempt_schema.dump(in_progress), "Resuming existing attempt.")

    attempt = ExamAttempt(
        exam_id=exam_id,
        student_id=user.id,
        status="in_progress",
        started_at=now,
        ip_address=request.remote_addr,
    )
    db.session.add(attempt)
    db.session.commit()
    return success(attempt_schema.dump(attempt), "Attempt started.", 201)


@exams_bp.post("/<int:exam_id>/attempts/<int:attempt_id>/answers")
@jwt_required()
def submit_answer(exam_id, attempt_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    attempt = ExamAttempt.query.filter_by(
        id=attempt_id, exam_id=exam_id, student_id=user.id
    ).first_or_404()

    # SECURITY: Prevent answers after submission
    if attempt.status != "in_progress":
        return error("Exam already submitted. Cannot save answers.", 400)

    data = request.get_json() or {}
    question_id = data.get("question_id")
    if not question_id:
        return error("question_id is required.", 422)

    question = Question.query.get_or_404(question_id)

    answer = AttemptAnswer.query.filter_by(
        attempt_id=attempt_id, question_id=question_id
    ).first()
    if not answer:
        answer = AttemptAnswer(attempt_id=attempt_id, question_id=question_id)
        db.session.add(answer)

    answer.selected_option_id = data.get("selected_option_id")
    answer.text_answer = data.get("text_answer")
    answer.answered_at = datetime.now(timezone.utc)

    if question.question_type in ("mcq", "true_false") and answer.selected_option_id:
        option = QuestionOption.query.get(answer.selected_option_id)
        if option:
            answer.is_correct = option.is_correct
            eq = db.session.execute(
                db.select(exam_question).where(
                    exam_question.c.exam_id == exam_id,
                    exam_question.c.question_id == question_id,
                )
            ).first()
            answer.marks_awarded = (eq.marks if eq else 1.0) if answer.is_correct else 0.0

    db.session.commit()
    return success(answer_schema.dump(answer), "Answer saved.")


@exams_bp.post("/<int:exam_id>/attempts/<int:attempt_id>/submit")
@jwt_required()
def submit_attempt(exam_id, attempt_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    attempt = ExamAttempt.query.filter_by(
        id=attempt_id, exam_id=exam_id, student_id=user.id
    ).first_or_404()

    # SECURITY: Prevent double submission
    if attempt.status != "in_progress":
        return error("Exam already submitted.", 400)

    now = datetime.now(timezone.utc)
    attempt.submitted_at = now

    if attempt.started_at:
        started = attempt.started_at.replace(tzinfo=timezone.utc) \
            if attempt.started_at.tzinfo is None else attempt.started_at
        attempt.time_spent_seconds = int((now - started).total_seconds())

    # ── Grade each answer ──────────────────────
    for answer in attempt.answers:
        question = answer.question
        if not question:
            continue

        if question.question_type in ("mcq", "true_false"):
            # Already graded when answer was submitted
            continue

        if question.question_type in ("short_answer", "essay"):
            if not answer.text_answer:
                answer.marks_awarded = 0.0
                answer.feedback = "No answer provided."
                answer.is_correct = False
                continue

            # Get marks for this question from exam_question pivot
            eq = db.session.execute(
                db.select(exam_question).where(
                    exam_question.c.exam_id == exam_id,
                    exam_question.c.question_id == question.id,
                )
            ).first()
            max_marks = eq.marks if eq else 1.0

            # Use instructor-defined keywords
            keywords = []
            if question.keywords:
                keywords = [
                    k.strip().lower()
                    for k in question.keywords.split(",")
                    if k.strip()
                ]

            if not keywords:
                # No keywords defined — give partial credit pending review
                answer.marks_awarded = round(max_marks * 0.5, 2)
                answer.feedback = "Answer received. No keywords defined — pending instructor review."
                answer.is_correct = None
                continue

            # Score based on keyword matches
            student_answer = answer.text_answer.lower()
            matched = [kw for kw in keywords if kw in student_answer]
            match_ratio = len(matched) / len(keywords)

            if match_ratio >= 0.7:
                answer.marks_awarded = max_marks
                answer.is_correct = True
                answer.feedback = (
                    f"Excellent! Covered {len(matched)}/{len(keywords)} "
                    f"key concepts: {', '.join(matched)}."
                )
            elif match_ratio >= 0.4:
                answer.marks_awarded = round(max_marks * 0.6, 2)
                answer.is_correct = None
                answer.feedback = (
                    f"Partial credit. Covered {len(matched)}/{len(keywords)} "
                    f"key concepts: {', '.join(matched)}."
                )
            else:
                answer.marks_awarded = round(max_marks * 0.2, 2)
                answer.is_correct = False
                answer.feedback = (
                    f"Needs improvement. Only matched "
                    f"{len(matched)}/{len(keywords)} keywords."
                )

    # ── Compute total score ────────────────────
    score = sum(a.marks_awarded or 0.0 for a in attempt.answers)
    attempt.score = score
    attempt.percentage = round((score / attempt.exam.total_marks) * 100, 2) \
        if attempt.exam.total_marks else 0.0
    attempt.is_passed = attempt.score >= attempt.exam.passing_marks
    attempt.status = "graded"
    attempt.graded_at = now

    db.session.commit()

    result = attempt_schema.dump(attempt)
    if attempt.exam.show_results_immediately:
        result["answers"] = answers_schema.dump(attempt.answers)

    return success(result, "Exam submitted and graded.")


@exams_bp.get("/<int:exam_id>/attempts")
@jwt_required()
def list_attempts(exam_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    Exam.query.get_or_404(exam_id)

    if user.role in ("instructor", "admin"):
        query = ExamAttempt.query.filter_by(exam_id=exam_id)
    else:
        query = ExamAttempt.query.filter_by(exam_id=exam_id, student_id=user.id)

    return paginate(query, attempts_schema)


# GET - View specific attempt
@exams_bp.get("/<int:exam_id>/attempts/<int:attempt_id>")
@jwt_required()
def get_attempt(exam_id, attempt_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)

    attempt = ExamAttempt.query.filter_by(
        id=attempt_id, exam_id=exam_id
    ).first_or_404()

    if attempt.student_id != user.id and user.role not in ("instructor", "admin"):
        return error("Not authorized.", 403)

    result = attempt_schema.dump(attempt)
    if attempt.status == "graded" and (
        attempt.exam.show_results_immediately or user.role in ("instructor", "admin")
    ):
        result["answers"] = answers_schema.dump(attempt.answers)

    return success(result)


# DELETE - Delete specific attempt (separate route)
@exams_bp.delete("/<int:exam_id>/attempts/<int:attempt_id>/delete")
@jwt_required()
@roles_required("instructor", "admin")
def delete_attempt(exam_id, attempt_id):
    user = get_current_user()
    if not user:
        return error("Unauthorized.", 401)
    
    attempt = ExamAttempt.query.filter_by(
        id=attempt_id, exam_id=exam_id
    ).first_or_404()
    
    # Delete answers first (child records)
    AttemptAnswer.query.filter_by(attempt_id=attempt_id).delete()
    
    # Then delete the attempt
    db.session.delete(attempt)
    db.session.commit()
    
    return success(message="Attempt deleted successfully")


@exams_bp.patch("/<int:exam_id>/attempts/<int:attempt_id>/grade")
@jwt_required()
@roles_required("instructor", "admin")
def manual_grade(exam_id, attempt_id):
    attempt = ExamAttempt.query.filter_by(
        id=attempt_id, exam_id=exam_id
    ).first_or_404()
    data = request.get_json() or {}

    for g in data.get("grades", []):
        answer = AttemptAnswer.query.filter_by(
            id=g["answer_id"], attempt_id=attempt_id
        ).first()
        if answer:
            answer.marks_awarded = g.get("marks_awarded", 0.0)
            answer.feedback = g.get("feedback")
            answer.is_correct = answer.marks_awarded > 0

    attempt.score = sum(a.marks_awarded or 0.0 for a in attempt.answers)
    attempt.percentage = round(
        (attempt.score / attempt.exam.total_marks) * 100, 2
    ) if attempt.exam.total_marks else 0.0
    attempt.is_passed = attempt.score >= attempt.exam.passing_marks
    attempt.status = "graded"
    attempt.graded_at = datetime.now(timezone.utc)

    db.session.commit()
    return success(attempt_schema.dump(attempt), "Attempt graded.")


@exams_bp.get("/<int:exam_id>/results/summary")
@jwt_required()
@roles_required("instructor", "admin")
def exam_summary(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    graded = ExamAttempt.query.filter_by(exam_id=exam_id, status="graded").all()

    if not graded:
        return success({"message": "No graded attempts yet."})

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


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None