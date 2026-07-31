from django.core.management.base import BaseCommand
from datetime import time
from apps.doctors.models import Doctor, WorkingHours

SEED_DOCTORS = [
    {
        "first_name": "Sarah",
        "last_name": "Jenkins",
        "specialization": "General Practice & Family Medicine",
        "email": "dr.jenkins@cliniccare.com",
        "phone": "+254700000001",
        "shifts": [
            {"day": 0, "start": time(8, 0), "end": time(17, 0)}, # Mon 8am-5pm
            {"day": 1, "start": time(8, 0), "end": time(17, 0)}, # Tue
            {"day": 2, "start": time(8, 0), "end": time(17, 0)}, # Wed
            {"day": 3, "start": time(8, 0), "end": time(17, 0)}, # Thu
            {"day": 4, "start": time(8, 0), "end": time(17, 0)}, # Fri
        ]
    },
    {
        "first_name": "Michael",
        "last_name": "Ochieng",
        "specialization": "Cardiology",
        "email": "dr.ochieng@cliniccare.com",
        "phone": "+254700000002",
        "shifts": [
            {"day": 0, "start": time(8, 0), "end": time(20, 0)}, # Mon 12-hr day shift
            {"day": 2, "start": time(8, 0), "end": time(20, 0)}, # Wed 12-hr day shift
            {"day": 4, "start": time(8, 0), "end": time(20, 0)}, # Fri 12-hr day shift
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
            {"day": 5, "start": time(9, 0), "end": time(13, 0)}, # Sat half-day
        ]
    },
    {
        "first_name": "David",
        "last_name": "Kipchirchir",
        "specialization": "Emergency Medicine (Night Shift)",
        "email": "dr.david@cliniccare.com",
        "phone": "+254700000004",
        "shifts": [
            {"day": 0, "start": time(20, 0), "end": time(6, 0)}, # Mon Night shift (10 hrs)
            {"day": 1, "start": time(20, 0), "end": time(6, 0)}, # Tue Night shift
            {"day": 3, "start": time(20, 0), "end": time(6, 0)}, # Thu Night shift
            {"day": 4, "start": time(20, 0), "end": time(6, 0)}, # Fri Night shift
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

class Command(BaseCommand):
    help = "Seed initial 5 clinic doctors and their day/night working hours."

    def handle(self, *args, **options):
        self.stdout.write("Seeding 5 doctors with working hours...")
        for doc_data in SEED_DOCTORS:
            doctor, created = Doctor.objects.get_or_create(
                email=doc_data["email"],
                defaults={
                    "first_name": doc_data["first_name"],
                    "last_name": doc_data["last_name"],
                    "specialization": doc_data["specialization"],
                    "phone": doc_data["phone"],
                }
            )
            action = "Created" if created else "Found existing"
            self.stdout.write(f"{action}: {doctor.full_name}")

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
        self.stdout.write(self.style.SUCCESS("Successfully seeded 5 doctors & working hours!"))
