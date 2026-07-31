# ClinicCare — Clinic Booking System

A scalable, full-stack clinic appointment booking system built with **Django REST Framework (DRF)**, **PostgreSQL (Neon)**, **Tailwind CSS**, and **HTMX**, containerized and deployed on **Azure App Service** via **GitHub Actions CI/CD**.

---

## 🔗 Live Application & API

- **Deployed Application URL**: `https://clinic-booking-system.azurewebsites.net`
- **Interactive API Documentation / Endpoints**:
  - `POST /api/appointments/` — Book a 30-minute slot
  - `GET /api/doctors/{id}/availability/` — View available 30-min slots for a doctor on a date
  - `PATCH /api/appointments/{id}/cancel/` — Cancel appointment with reason
  - `PATCH /api/appointments/{id}/reschedule/` — Reschedule appointment to a new slot
  - `GET /api/patients/{id}/appointments/` — View upcoming appointments sorted by date (Bonus)

---

## 📐 SECTION 1: System Design

### 1. Architectural Overview & Domain Models

The system models a multi-doctor clinic operating with configurable shift schedules and 30-minute consultation slots.

```
       +-------------------+              +---------------------+
       |      User         | 1          1 |       Patient       |
       | (Django Auth)     |--------------| (UUID, Phone, DOB)  |
       +-------------------+              +---------------------+
                                                     | 1
                                                     |
                                                     | *
                                          +---------------------+
                                          |     Appointment     |
                                          | (Date, Start/End,   |
                                          |  Status, Reason)    |
                                          +---------------------+
                                                     | *
                                                     |
                                                     | 1
       +-------------------+ 1          * +---------------------+
       |      Doctor       |--------------|    WorkingHours     |
       | (Specialization)  |              | (DayOfWeek, Shift)  |
       +-------------------+              +---------------------+
```

### Key Models Identified
1. **Doctor**: Represents clinic doctors with specialized areas (Cardiology, Pediatrics, Emergency, etc.).
2. **WorkingHours**: Configurable shift model supporting both **day shifts** (e.g. 08:00–17:00 or 08:00–20:00 max 12 hours) and **night shifts** (e.g. 20:00–06:00).
3. **Patient**: Extends Django's built-in `User` model via a OneToOne relationship, storing health history metadata and authentication credentials.
4. **Appointment**: Represents a booked 30-minute slot between a patient and doctor on a specific calendar date.

---

### 2. Key Design Decisions & Trade-Offs

| Decision | Choice | Rationale & Trade-offs |
|---|---|---|
| **Service Layer Pattern (`services.py`)** | Business logic decoupled from Views & Serializers | Keeps Django views thin and allows isolated unit testing of validation rules without spinning up HTTP overhead. |
| **Concurrency Protection** | DB Partial Unique Index + Atomic Transactions | Avoided heavy pessimistic locking (`select_for_update`) which degrades throughput. Used Django 4.2 `UniqueConstraint` on `(doctor, appointment_date, start_time)` WHERE `status = 'scheduled'`. |
| **Patient Booking Constraint** | 1 Appointment Per Patient Per Day | Enforced via DB constraint `UniqueConstraint(fields=['patient', 'appointment_date'], condition=Q(status='scheduled'))`. Prevents hoarding slots across different doctors. |
| **Database Choice** | PostgreSQL (Neon Serverless) | Serverless PostgreSQL with auto-scaling connection pooling. Cloud-agnostic and provider-independent from Azure. |
| **Frontend Architecture** | Django Templates + Tailwind CSS + HTMX | Zero Node.js build step needed. Server-rendered HTML with HTMX provides reactive, single-page application feel for the interactive slot picker. |

---

## ⚡ SECTION 2: API Implementation & Local Setup

### Business Rules Enforced
- **30-Minute Boundary**: Slots must start at clean `:00` or `:30` marks.
- **Working Hours & Shift Limits**: Max 12 hours per shift limit. Slots must fall within the doctor's shift for that specific day of the week.
- **Past & 1-Hour Buffer**: Rejects bookings in the past or within **1 hour** of the current time.
- **Atomic Slot Reclaim**: Cancelling an appointment immediately marks it as `cancelled`, making the slot bookable by others.

### Local Setup Instructions

```bash
# 1. Clone the repository
git clone https://github.com/Maxc390/clinic-booking-system.git
cd clinic-booking-system

# 2. Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install development dependencies
pip install -r requirements/development.txt

# 4. Configure Environment Variables
cp .env.example .env
# Edit .env and paste your Neon DATABASE_URL string

# 5. Run Database Migrations
python manage.py makemigrations accounts doctors appointments
python manage.py migrate

# 6. Seed Initial 5 Doctors & Working Shift Schedules
python manage.py seed_doctors

# 7. Create Superuser (Admin Access)
python manage.py createsuperuser

# 8. Start Local Server
python manage.py runserver
```

### Running Unit Tests

```bash
# Execute unit test suite for booking, availability, cancel, and reschedule logic
python manage.py test appointments
```

---

## 🚀 SECTION 3: Deployment & CI/CD

### Deployment Architecture
- **Cloud Provider**: **Azure App Service** (Linux runtime, Python 3.10)
- **Database**: **Neon PostgreSQL** serverless instance
- **Web Server**: Gunicorn WSGI server with Whitenoise static asset compression

### CI/CD Pipeline Setup (GitHub Actions)
- **Designated Branch**: `main`
- **Workflows**:
  1. `.github/workflows/ci.yml`: Triggers on **Pull Requests** to `main`. Runs `python manage.py check` and the full Django test suite (`manage.py test appointments`). Merging is blocked if tests fail.
  2. `.github/workflows/deploy.yml`: Triggers on **Push / Merge** to `main`. Automatically deploys code to Azure App Service using Azure Publish Profile / OIDC credentials.

---

## 🤖 SECTION 4: AI Reflection

### 1. What did you use AI for across the four sections?
- **Section 1 (System Design)**: Brainstorming edge cases around shift boundary validation (handling night shifts spanning midnight) and evaluating partial unique index options in Django 4.2 versus application-level locking.
- **Section 2 (API Implementation)**: Writing boilerplate DRF serializers, setting up seed data management scripts (`seed_doctors.py`), and drafting HTML templates with Tailwind CSS layout utilities.
- **Section 3 (Deployment & CI/CD)**: Formatting GitHub Actions workflow YAML files and Whitenoise static files configuration for Azure App Service.
- **Section 4 (Reflection & Docs)**: Generating clean Markdown table layouts for the project plan and README formatting.

### 2. Give one example where an AI suggestion improved your work. What did you prompt it with?
- **Prompt**: *"How should I handle slot availability for night shifts that start at 20:00 and end at 06:00 the next day in Python without breaking datetime math?"*
- **Improvement**: AI suggested normalizing shift calculations by creating a `dummy_date` and adding `timedelta(days=1)` whenever `end_time <= start_time`. This prevented negative duration errors and allowed seamless generation of 30-minute slots across midnight boundaries.

### 3. Give one example where AI output was wrong or incomplete and how you caught it.
- **Issue**: AI initially generated a Django model `UniqueConstraint` without specifying the `condition=Q(status='scheduled')` parameter, which would have permanently blocked a patient from ever re-booking a doctor on a date where they had a previously *cancelled* appointment.
- **Detection & Fix**: I caught this during system design analysis before writing migrations, recognizing that cancelled appointments must not trigger unique key violations. I added the conditional filter `condition=Q(status='scheduled')` to both patient and doctor constraints.

### 4. Name two decisions you made without AI. Why did you trust your own judgment there?
1. **Decoupling Business Logic into `services.py`**: I decided to keep all validation rules (slot bounds, 1-hour buffer, single appointment per patient per day) in pure Python functions inside `services.py` rather than putting them in DRF Serializers or Views. I trusted my architectural experience here because keeping domain logic independent of DRF requests makes unit testing trivial and fast.
2. **Selecting HTMX + Django Templates over a React SPA**: Instead of splitting the project into a separate React frontend (which introduces CORS, dual deployments, and npm build overhead), I chose Django Templates + Tailwind CDN + HTMX. This delivered an interactive, single-page slot picker while maintaining a single lightweight deployment artifact for Azure.
