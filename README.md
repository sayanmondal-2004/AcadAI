# AI Academic Advisor

An AI-powered academic assistance platform designed to help students manage their academic information, understand their performance, create study plans, practice through AI-generated quizzes, communicate with an AI academic advisor, and receive important notifications.

---

## Overview

AI Academic Advisor is a full-stack academic support platform that combines student academic data with AI-powered assistance.

The platform provides students with a centralized dashboard where they can:

- View academic information
- Track attendance
- Review academic performance
- Generate personalized study plans
- Chat with an AI academic advisor
- Generate topic-based quizzes using AI
- Receive instant quiz results and correct answers
- Receive academic notifications
- Submit and view feedback
- Manage their academic profile
- Upload a profile picture
- Reset their password securely through email verification

The system is designed to provide academic assistance while keeping student information organized and accessible.

---

## Key Features

### Student Dashboard

A centralized dashboard providing access to:

- Academic overview
- Attendance
- Study plan
- Academic performance
- Notifications
- AI chatbot
- AI quizzes
- Academic profile

---

### Academic Profile

Students can maintain their academic information, including:

- Personal academic details
- Subjects
- Semester information
- Academic history

Academic profile data can be retrieved and updated through the backend API.

---

### Attendance Tracking

Students can view their attendance information and monitor their academic attendance.

---

### AI Study Plan

The system provides study-plan functionality to help students organize their academic preparation.

---

### AI Academic Advisor

Students can interact with an AI-powered chatbot for academic assistance.

The advisor can be used for questions related to:

- Subjects
- Study preparation
- Academic concepts
- Learning guidance
- General academic assistance

---

### AI Quiz Generator

Students can enter a subject or topic they currently find difficult.

The system then generates a 10-question quiz based on the provided topic.

Quiz workflow:

1. Student selects **Quiz**
2. Student enters the subject/topic
3. AI generates 10 questions
4. Student answers the questions
5. Student submits the quiz
6. Score is calculated instantly
7. Correct answers are displayed
8. Results are shown immediately

Quiz marks are intentionally **not stored in the database**.

This keeps the quiz feature as an instant self-assessment tool rather than an academic grading system.

> **Academic Integrity Declaration:**  
> Students are encouraged to attempt quizzes independently without using AI or external assistance. The purpose of the quiz is self-assessment, identifying knowledge gaps, and improving learning. Using AI to obtain answers defeats the purpose of the assessment and ultimately harms the student's own learning and academic growth.

---

### Notification System

The backend supports:

- Individual student notifications
- Broadcast notifications
- Notification retrieval
- Marking notifications as read

Administrators can send notifications through the backend API.

---

### Feedback System

Students can submit feedback through the platform.

The system supports:

- Feedback submission
- Student feedback retrieval
- Email notification functionality

---

### Password Reset

The authentication system supports password recovery through email verification.

Password reset flow:

```text
Forgot Password
       ↓
Enter Registered Email
       ↓
Reset Code Sent to Email
       ↓
Enter 6-Digit Code
       ↓
Verify Code
       ↓
Set New Password
```

SMTP credentials are stored securely as environment variables.

# Technology Stack

### Frontend
- HTML5
- CSS3
- JavaScript
- Responsive design
- Mobile-friendly interface

### Backend
- Python
- FastAPI
- Uvicorn
- Pydantic
  
### Database
- PostgreSQL
  
### AI
- OpenRouter API
- Configurable AI model

### Email
- SMTP
- Gmail App Password
  
### API Documentation
- Swagger UI
- OpenAPI
## Development Tools
- Git
- GitHub
- Python Virtual Environment
- REST APIs

# Environment Variables
Create a .env file locally.
```
DATABASE_URL=your_database_url

OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=your_model

SMTP_EMAIL=your_email@gmail.com
SMTP_APP_PASSWORD=your_google_app_password

ADMIN_NOTIFICATION_KEY=your_admin_key
```
# Local Development
## 1. Clone the repository
```
git clone https://github.com/YOUR_USERNAME/AI-Academic-Advisor.git
cd AI-Academic-Advisor
```
## 2. Create a virtual environment
```
python -m venv .venv
```
#### macOS / Linux
```
source .venv/bin/activate
```
#### Windows
```
.venv\Scripts\activate
```
## 3. Install dependencies
```
pip install -r requirements.txt
```
## 4. Configure environment variables
Create:
```
.env
```
and add the required variables.
## 5. Start the backend
```
python -m uvicorn backend.main:app --reload
```
The API will be available at:
```
http://127.0.0.1:8000
```
# API Documentation
FastAPI automatically generates interactive API documentation.
Swagger UI:
```
/docs
```
# Database Design
The application stores student-related information in structured database tables.
Major data areas include:
```
Users
 ├── Academic Profiles
 ├── Academic Subjects
 ├── Academic Semesters
 ├── Notifications
 ├── Feedback
 ├── Email Verifications
 └── Profile Pictures
```
Quiz scores are not persisted in the database.

# Privacy & Security
The project follows several security principles:
- Sensitive credentials are stored in environment variables.
- API keys are not hard-coded into source files.
- Gmail App Passwords are used for SMTP authentication.
- Password reset codes are sent through registered email addresses.
- Password recovery uses verification codes.
- Quiz scores are not permanently stored.
- Administrative notification endpoints use a dedicated admin key.
- ```.env``` files are excluded from version control.

> **Important:** Never publish API keys, database credentials, SMTP passwords, or administrative keys in a public GitHub repository.

Production environment variables should be configured directly in the deployment platform.
# Current Features
## Implemented
- Student authentication
- Login and signup
- Password reset
- Email verification/reset codes
- Student profile
- Profile picture
- Academic profile
- Academic records
- Academic analysis
- Attendance
- Study plan
- AI chatbot
- AI quiz generation
- Instant quiz scoring
- Feedback system
- Notification system
- Responsive/mobile dashboard
- PostgreSQL integration

# Disclaimer
AI Academic Advisor is an academic assistance project.

AI-generated recommendations, study plans, explanations, and quiz questions should be treated as assistance rather than a replacement for teachers, academic advisors, official university information, or independent learning.

Students should verify important academic information through official sources.
# Author
### Sayan Mondal
```Computer Science / Engineering Student```

GitHub: ```https://github.com/sayanX9889```

# License
This project is currently intended for educational and development purposes.
See the [LICENSE](LICENSE) file for details.
