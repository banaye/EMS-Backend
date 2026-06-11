# Examify - Backend API

A robust, full-featured REST API for e-learning and exam management platform built with Flask, SQLAlchemy, and JWT authentication

## Overview

Examify Backend is a comprehensive REST API that powers an e-learning platform with role-based access control for students, instructors, and administrators. The API handles user authentication, course management, exam creation and grading, question banking, and detailed analytics reporting.

## Features

### Core Features
- 🔐 JWT-based authentication (access + refresh tokens)
- 👥 Role-based access control (Admin, Instructor, Student)
- 📚 Complete course management system
- 📝 Exam creation and auto-grading
- ❓ Question bank with multiple question types
- 📊 Analytics and reporting endpoints
- 📎 File upload for course materials
- 🔔 Notification system
- 🏆 Certificate generation

### Question Types Supported
- Multiple Choice (MCQ)
- True/False
- Short Answer (with keyword auto-grading)
- Essay (with keyword auto-grading)

### Exam Features
- Timer-based exams
- Auto-submit on time expiration
- Tab-switch detection logging
- Auto-grading for objective questions
- Keyword-based scoring for subjective questions
- Manual grading override for instructors

### Security Features
- Password hashing with bcrypt
- JWT token expiration and refresh
- CORS configuration
- Input validation with Marshmallow
- SQL injection prevention via SQLAlchemy ORM

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Programming Language |
| Flask | 2.3.x | Web Framework |
| Flask-SQLAlchemy | 3.0.x | ORM |
| Flask-JWT-Extended | 4.5.x | JWT Authentication |
| Flask-Migrate | 4.0.x | Database Migrations |
| Flask-CORS | 4.0.x | CORS Handling |
| Marshmallow | 3.19.x | Serialization/Validation |
| PyMySQL | 1.0.x | MySQL Driver |
| bcrypt | 4.0.x | Password Hashing |
| Werkzeug | 2.3.x | File Upload Handling |

## Prerequisites

- Python 3.11 or higher
- MySQL 8.0 or higher
- pip (Python package manager)
- Virtual environment (recommended)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/examify-backend.git
cd examify-backend/server
