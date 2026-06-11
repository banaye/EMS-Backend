"""
Seed the database with realistic demo data.
Run:  python seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.extensions import db, bcrypt
from app.models import (
    User, Category, Course, Module, Lesson, LessonResource,
    Question, QuestionOption, Exam, ExamAttempt, AttemptAnswer,
    Notification, exam_question, course_enrollment, CourseResource,
)
from app.services.utils.helpers import unique_slug, generate_certificate_number
from datetime import datetime, timezone, timedelta
import random

app = create_app("development")

CATEGORIES = [
    {"name": "Programming", "slug": "programming", "icon": "💻", "color": "#6366f1"},
    {"name": "Data Science", "slug": "data-science", "icon": "📊", "color": "#0ea5e9"},
    {"name": "Web Development", "slug": "web-development", "icon": "🌐", "color": "#10b981"},
    {"name": "Cybersecurity", "slug": "cybersecurity", "icon": "🔐", "color": "#f59e0b"},
    {"name": "Mathematics", "slug": "mathematics", "icon": "🔢", "color": "#ec4899"},
]

def seed_course_resources():
    """Seed course resources for download/open buttons"""
    courses = Course.query.all()
    
    # Sample resources for courses
    resources_templates = [
        [
            {"title": "Course Syllabus & Guide.pdf", "type": "pdf", "url": "/static/syllabus.pdf", "size": 1024},
            {"title": "Supplementary Reading Materials", "type": "link", "url": "https://example.com/reading", "size": 0},
            {"title": "Practice Exercises", "type": "pdf", "url": "/static/exercises.pdf", "size": 512},
            {"title": "Video Tutorial: Getting Started", "type": "video", "url": "/static/getting-started.mp4", "size": 15000},
        ],
        [
            {"title": "Lecture Slides - Complete Set", "type": "pdf", "url": "/static/slides-complete.pdf", "size": 2048},
            {"title": "GitHub Repository", "type": "link", "url": "https://github.com/example/repo", "size": 0},
            {"title": "Data Files for Practice", "type": "file", "url": "/static/data-files.zip", "size": 5000},
            {"title": "Video: Advanced Concepts", "type": "video", "url": "/static/advanced-concepts.mp4", "size": 25000},
        ],
        [
            {"title": "Quick Reference Guide.pdf", "type": "pdf", "url": "/static/reference.pdf", "size": 256},
            {"title": "Community Discussion Forum", "type": "link", "url": "https://example.com/forum", "size": 0},
            {"title": "Sample Projects", "type": "file", "url": "/static/projects.zip", "size": 8000},
        ],
    ]
    
    for idx, course in enumerate(courses):
        template = resources_templates[idx % len(resources_templates)]
        for i, res in enumerate(template):
            existing = CourseResource.query.filter_by(
                course_id=course.id, 
                title=res["title"]
            ).first()
            if not existing:
                resource = CourseResource(
                    course_id=course.id,
                    title=res["title"],
                    resource_type=res["type"],
                    url=res["url"],
                    file_size_kb=res["size"],
                    order_index=i
                )
                db.session.add(resource)
    
    db.session.commit()
    print("  ✓ Course resources seeded")

with app.app_context():
    db.drop_all()
    db.create_all()
    print("✓ Tables created")

    # ── Admin ─────────────────────────────────────
    admin = User(
        username="admin",
        email="admin@examify.dev",
        password_hash=bcrypt.generate_password_hash("Admin1234!").decode(),
        first_name="Platform",
        last_name="Admin",
        role="admin",
        is_active=True,
        is_verified=True,
    )
    db.session.add(admin)

    # ── Instructors ───────────────────────────────
    instructors = []
    instructor_data = [
        ("alice_teach", "alice@examify.dev", "Alice", "Chen"),
        ("bob_prof", "bob@examify.dev", "Bob", "Martinez"),
    ]
    for uname, email, first, last in instructor_data:
        u = User(
            username=uname,
            email=email,
            password_hash=bcrypt.generate_password_hash("Pass1234!").decode(),
            first_name=first,
            last_name=last,
            role="instructor",
            is_active=True,
            is_verified=True,
            bio=f"Experienced instructor specializing in technology education.",
        )
        db.session.add(u)
        instructors.append(u)

    # ── Students ──────────────────────────────────
    students = []
    student_data = [
        ("student_jane", "jane@examify.dev", "Jane", "Smith"),
        ("student_mike", "mike@examify.dev", "Mike", "Johnson"),
        ("student_sara", "sara@examify.dev", "Sara", "Lee"),
    ]
    for uname, email, first, last in student_data:
        u = User(
            username=uname,
            email=email,
            password_hash=bcrypt.generate_password_hash("Pass1234!").decode(),
            first_name=first,
            last_name=last,
            role="student",
            is_active=True,
            is_verified=True,
        )
        db.session.add(u)
        students.append(u)

    db.session.flush()
    print("✓ Users created")

    # ── Categories ────────────────────────────────
    cats = {}
    for c in CATEGORIES:
        cat = Category(**c)
        db.session.add(cat)
        db.session.flush()
        cats[c["slug"]] = cat
    print("✓ Categories created")

    # ── Courses ───────────────────────────────────
    course_specs = [
        {
            "title": "Python for Beginners",
            "short_description": "Learn Python from scratch with hands-on projects.",
            "level": "beginner",
            "price": 0.0,
            "category": "programming",
            "instructor": instructors[0],
            "modules": [
                ("Introduction to Python", [
                    ("What is Python?", "text", 5),
                    ("Installing Python & VS Code", "video", 12),
                    ("Your First Python Script", "video", 15),
                ]),
                ("Variables & Data Types", [
                    ("Numbers, Strings, Booleans", "text", 8),
                    ("Lists and Tuples", "video", 20),
                    ("Dictionaries", "video", 18),
                ]),
                ("Control Flow", [
                    ("If / Elif / Else", "video", 14),
                    ("For and While Loops", "video", 22),
                ]),
            ],
        },
        {
            "title": "Data Science Fundamentals",
            "short_description": "Master pandas, NumPy and basic ML concepts.",
            "level": "intermediate",
            "price": 49.99,
            "category": "data-science",
            "instructor": instructors[1],
            "modules": [
                ("NumPy Essentials", [
                    ("Arrays and Operations", "video", 25),
                    ("Broadcasting", "video", 20),
                ]),
                ("Pandas Deep Dive", [
                    ("DataFrames & Series", "video", 30),
                    ("Data Cleaning", "video", 35),
                    ("Merging & Groupby", "video", 28),
                ]),
            ],
        },
        {
            "title": "Web Development with React",
            "short_description": "Build modern web applications with React.",
            "level": "intermediate",
            "price": 79.99,
            "category": "web-development",
            "instructor": instructors[0],
            "modules": [
                ("React Basics", [
                    ("Components & Props", "video", 20),
                    ("State & Lifecycle", "video", 25),
                ]),
                ("Advanced React", [
                    ("Hooks Deep Dive", "video", 30),
                    ("Context API", "video", 22),
                ]),
            ],
        },
    ]

    created_courses = []
    for spec in course_specs:
        slug = unique_slug(Course, spec["title"])
        course = Course(
            title=spec["title"],
            slug=slug,
            description=spec["short_description"] + " " + spec["short_description"],
            short_description=spec["short_description"],
            level=spec["level"],
            price=spec["price"],
            is_published=True,
            duration_hours=round(random.uniform(4, 20), 1),
            rating=round(random.uniform(3.8, 5.0), 1),
            rating_count=random.randint(5, 120),
            instructor_id=spec["instructor"].id,
            category_id=cats[spec["category"]].id,
        )
        db.session.add(course)
        db.session.flush()

        for m_idx, (m_title, lessons_spec) in enumerate(spec["modules"]):
            module = Module(title=m_title, order_index=m_idx, course_id=course.id)
            db.session.add(module)
            db.session.flush()

            for l_idx, (l_title, l_type, l_dur) in enumerate(lessons_spec):
                lesson = Lesson(
                    title=l_title,
                    lesson_type=l_type,
                    duration_minutes=l_dur,
                    order_index=l_idx,
                    is_published=True,
                    is_preview=(l_idx == 0),
                    content=f"<p>This lesson covers <strong>{l_title}</strong>.</p>",
                    video_url=f"https://example.com/videos/{slug}-{l_idx}.mp4" if l_type == "video" else None,
                    module_id=module.id,
                )
                db.session.add(lesson)

        created_courses.append(course)

    db.session.flush()
    print("✓ Courses & lessons created")

    # ── Seed Course Resources (Download/Open buttons) ──
    seed_course_resources()

    # ── Enroll students ───────────────────────────
    for student in students:
        for course in created_courses:
            stmt = course_enrollment.insert().values(
                user_id=student.id, course_id=course.id
            )
            db.session.execute(stmt)

    db.session.flush()
    print("✓ Enrollments created")

    # ── Questions ─────────────────────────────────
    q_data = [
        {
            "text": "What does 'PEP' stand for in Python?",
            "question_type": "mcq",
            "difficulty": "easy",
            "topic_tag": "python-basics",
            "options": [
                ("Python Enhancement Proposal", True),
                ("Python Extended Protocol", False),
                ("Program Execution Plan", False),
                ("Python Encoding Practice", False),
            ],
            "explanation": "PEP stands for Python Enhancement Proposal.",
        },
        {
            "text": "Which data structure uses key-value pairs?",
            "question_type": "mcq",
            "difficulty": "easy",
            "topic_tag": "python-basics",
            "options": [
                ("List", False),
                ("Tuple", False),
                ("Dictionary", True),
                ("Set", False),
            ],
            "explanation": "Dictionaries store data as key-value pairs.",
        },
        {
            "text": "Python is an interpreted language.",
            "question_type": "true_false",
            "difficulty": "easy",
            "topic_tag": "python-basics",
            "options": [("True", True), ("False", False)],
            "explanation": "Python code is executed line-by-line by the Python interpreter.",
        },
        {
            "text": "What is the time complexity of accessing a dictionary element?",
            "question_type": "mcq",
            "difficulty": "medium",
            "topic_tag": "algorithms",
            "options": [
                ("O(n)", False),
                ("O(log n)", False),
                ("O(1)", True),
                ("O(n²)", False),
            ],
            "explanation": "Dictionary lookup is O(1) average-case due to hashing.",
        },
        {
            "text": "Which NumPy function creates an array of zeros?",
            "question_type": "mcq",
            "difficulty": "easy",
            "topic_tag": "numpy",
            "options": [
                ("np.empty()", False),
                ("np.zeros()", True),
                ("np.null()", False),
                ("np.blank()", False),
            ],
            "explanation": "np.zeros() creates an array filled with zeros.",
        },
        {
            "text": "Describe the difference between a list and a tuple in Python.",
            "question_type": "short_answer",
            "difficulty": "medium",
            "topic_tag": "python-basics",
            "options": [],
            "explanation": "Lists are mutable; tuples are immutable.",
        },
    ]

    questions = []
    for qd in q_data:
        q = Question(
            text=qd["text"],
            question_type=qd["question_type"],
            difficulty=qd["difficulty"],
            topic_tag=qd["topic_tag"],
            explanation=qd["explanation"],
            created_by=instructors[0].id,
        )
        db.session.add(q)
        db.session.flush()

        for i, (opt_text, is_correct) in enumerate(qd["options"]):
            opt = QuestionOption(
                question_id=q.id,
                text=opt_text,
                is_correct=is_correct,
                order_index=i,
            )
            db.session.add(opt)

        questions.append(q)

    db.session.flush()
    print("✓ Questions created")

    # ── Exam ──────────────────────────────────────
    exam = Exam(
        title="Python Fundamentals Quiz",
        description="Test your knowledge of Python basics.",
        instructions="Read each question carefully. You have 30 minutes.",
        exam_type="quiz",
        duration_minutes=30,
        total_marks=float(len(questions)),
        passing_marks=float(len(questions)) * 0.6,
        max_attempts=3,
        shuffle_questions=True,
        shuffle_options=True,
        show_results_immediately=True,
        is_published=True,
        course_id=created_courses[0].id,
        created_by=instructors[0].id,
    )
    db.session.add(exam)
    db.session.flush()

    for i, q in enumerate(questions):
        stmt = exam_question.insert().values(
            exam_id=exam.id, question_id=q.id, order_index=i, marks=1.0
        )
        db.session.execute(stmt)

    db.session.flush()
    print("✓ Exam created")

    # ── Demo attempt by first student ─────────────
    now = datetime.now(timezone.utc)
    attempt = ExamAttempt(
        exam_id=exam.id,
        student_id=students[0].id,
        status="graded",
        started_at=now - timedelta(minutes=25),
        submitted_at=now - timedelta(minutes=5),
        graded_at=now - timedelta(minutes=5),
        time_spent_seconds=1200,
        ip_address="127.0.0.1",
    )
    db.session.add(attempt)
    db.session.flush()

    score = 0.0
    for q in questions:
        correct_opt = next((o for o in q.options if o.is_correct), None)
        is_correct = random.random() > 0.3  # 70% chance of correct
        chosen = correct_opt if is_correct else (
            q.options[0] if q.options and not q.options[0].is_correct else None
        )
        marks = 1.0 if (is_correct and chosen) else 0.0
        score += marks

        ans = AttemptAnswer(
            attempt_id=attempt.id,
            question_id=q.id,
            selected_option_id=chosen.id if chosen else None,
            is_correct=is_correct if chosen else None,
            marks_awarded=marks,
        )
        db.session.add(ans)

    attempt.score = score
    attempt.percentage = round(score / exam.total_marks * 100, 2)
    attempt.is_passed = attempt.score >= exam.passing_marks

    # ── Welcome notification ───────────────────────
    for s in students:
        notif = Notification(
            user_id=s.id,
            title="Welcome to Examify! 🎉",
            message="You're all set. Explore your courses and start learning.",
            notification_type="success",
        )
        db.session.add(notif)

    db.session.commit()
    print("✓ Attempt & notifications created")
    print("\n🎓  Seed complete!")
    print("─" * 40)
    print("Admin :  admin@examify.dev  / Admin1234!")
    print("Instructor: alice@examify.dev / Pass1234!")
    print("Student: jane@examify.dev   / Pass1234!")