from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from datetime import time
from apps.doctors.models import Doctor, WorkingHours
from apps.accounts.models import Patient
from apps.accounts.demo import (
    DEMO_PASSWORD,
    SEED_DEMO_PATIENTS,
    doctor_username_from_email,
)

SEED_DOCTORS = [
    {
        "first_name": "Sarah",
        "last_name": "Jenkins",
        "specialization": "General Practice & Family Medicine",
        "email": "dr.jenkins@cliniccare.com",
        "phone": "+254700000001",
        "shifts": [
            {"day": 0, "start": time(8, 0), "end": time(17, 0)},  # Mon 8am-5pm
            {"day": 1, "start": time(8, 0), "end": time(17, 0)},  # Tue
            {"day": 2, "start": time(8, 0), "end": time(17, 0)},  # Wed
            {"day": 3, "start": time(8, 0), "end": time(17, 0)},  # Thu
            {"day": 4, "start": time(8, 0), "end": time(17, 0)},  # Fri
        ]
    },
    {
        "first_name": "Michael",
        "last_name": "Ochieng",
        "specialization": "Cardiology",
        "email": "dr.ochieng@cliniccare.com",
        "phone": "+254700000002",
        "shifts": [
            {"day": 0, "start": time(8, 0), "end": time(20, 0)},  # Mon 12-hr day shift
            {"day": 2, "start": time(8, 0), "end": time(20, 0)},  # Wed 12-hr day shift
            {"day": 4, "start": time(8, 0), "end": time(20, 0)},  # Fri 12-hr day shift
        ]
    },
    {
        "first_name": "Amina",
        "last_name": "Hassan",
        "specialization": "Pediatrics",
        "email": "dr.hassan@cliniccare.com",
        "phone": "+254700000003",
        "shifts": [
            {"day": 0, "start": time(9, 0), "end": time(16, 0)},
            {"day": 1, "start": time(9, 0), "end": time(16, 0)},
            {"day": 3, "start": time(9, 0), "end": time(16, 0)},
            {"day": 4, "start": time(9, 0), "end": time(16, 0)},
            {"day": 5, "start": time(9, 0), "end": time(13, 0)},  # Sat half-day
        ]
    },
    {
        "first_name": "David",
        "last_name": "Kipchirchir",
        "specialization": "Emergency Medicine (Night Shift)",
        "email": "dr.david@cliniccare.com",
        "phone": "+254700000004",
        "shifts": [
            {"day": 0, "start": time(20, 0), "end": time(6, 0)},  # Mon Night shift (10 hrs)
            {"day": 1, "start": time(20, 0), "end": time(6, 0)},  # Tue Night shift
            {"day": 3, "start": time(20, 0), "end": time(6, 0)},  # Thu Night shift
            {"day": 4, "start": time(20, 0), "end": time(6, 0)},  # Fri Night shift
        ]
    },
    {
        "first_name": "Elena",
        "last_name": "Rostova",
        "specialization": "Dermatology",
        "email": "dr.elena@cliniccare.com",
        "phone": "+254700000005",
        "shifts": [
            {"day": 1, "start": time(10, 0), "end": time(18, 0)},
            {"day": 2, "start": time(10, 0), "end": time(18, 0)},
            {"day": 3, "start": time(10, 0), "end": time(18, 0)},
            {"day": 5, "start": time(10, 0), "end": time(16, 0)},
        ]
    }
]


def _ensure_user(username, email, first_name, last_name, password=DEMO_PASSWORD):
    """Create or update a demo User with a known password."""
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
        },
    )
    # Keep demo credentials in sync on re-seed
    user.email = email
    user.first_name = first_name
    user.last_name = last_name
    user.set_password(password)
    user.save()
    return user, created


class Command(BaseCommand):
    help = (
        "Seed clinic doctors (with login accounts), working hours, and demo patients. "
        f"All demo accounts use password: {DEMO_PASSWORD}"
    )

    def handle(self, *args, **options):
        self.stdout.write("Seeding doctors with login accounts and working hours...")
        for doc_data in SEED_DOCTORS:
            username = doctor_username_from_email(doc_data["email"])
            user, user_created = _ensure_user(
                username=username,
                email=doc_data["email"],
                first_name=doc_data["first_name"],
                last_name=doc_data["last_name"],
            )

            doctor, created = Doctor.objects.get_or_create(
                email=doc_data["email"],
                defaults={
                    "first_name": doc_data["first_name"],
                    "last_name": doc_data["last_name"],
                    "specialization": doc_data["specialization"],
                    "phone": doc_data["phone"],
                    "user": user,
                }
            )
            # Link / refresh doctor fields on re-seed
            doctor.first_name = doc_data["first_name"]
            doctor.last_name = doc_data["last_name"]
            doctor.specialization = doc_data["specialization"]
            doctor.phone = doc_data["phone"]
            doctor.user = user
            doctor.save()

            action = "Created" if created else "Updated"
            user_note = "new login" if user_created else "login refreshed"
            self.stdout.write(
                f"  {action}: {doctor.full_name} (username={username}, {user_note})"
            )

            for shift in doc_data["shifts"]:
                WorkingHours.objects.update_or_create(
                    doctor=doctor,
                    day_of_week=shift["day"],
                    defaults={
                        "start_time": shift["start"],
                        "end_time": shift["end"],
                        "is_active": True
                    }
                )

        self.stdout.write("Seeding demo patients...")
        for pdata in SEED_DEMO_PATIENTS:
            user, user_created = _ensure_user(
                username=pdata["username"],
                email=pdata["email"],
                first_name=pdata["first_name"],
                last_name=pdata["last_name"],
            )
            patient, p_created = Patient.objects.get_or_create(
                user=user,
                defaults={"phone": pdata["phone"]},
            )
            if not p_created:
                patient.phone = pdata["phone"]
                patient.save()
            action = "Created" if p_created else "Updated"
            self.stdout.write(
                f"  {action}: {patient.full_name} (username={pdata['username']})"
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete. Demo password for all accounts: {DEMO_PASSWORD}"
        ))
