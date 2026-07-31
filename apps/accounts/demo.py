"""
Shared demo-account definitions used by seed data and the click-to-login UI.

All demo users share DEMO_PASSWORD so visitors can one-click sign in without
typing credentials. Only usernames listed here are eligible for demo login.
"""

DEMO_PASSWORD = 'demo1234'

# Doctor usernames are derived from the seed email local-part (e.g. dr.jenkins).
SEED_DEMO_PATIENTS = [
    {
        'username': 'patient.alice',
        'email': 'alice.wanjiku@example.com',
        'first_name': 'Alice',
        'last_name': 'Wanjiku',
        'phone': '+254711000001',
    },
    {
        'username': 'patient.john',
        'email': 'john.kamau@example.com',
        'first_name': 'John',
        'last_name': 'Kamau',
        'phone': '+254711000002',
    },
    {
        'username': 'patient.grace',
        'email': 'grace.njeri@example.com',
        'first_name': 'Grace',
        'last_name': 'Njeri',
        'phone': '+254711000003',
    },
]


def doctor_username_from_email(email: str) -> str:
    """Map seed doctor email → login username (local part before @)."""
    return email.split('@', 1)[0]


def is_demo_username(username: str) -> bool:
    from apps.doctors.management.commands.seed_doctors import SEED_DOCTORS

    patient_names = {p['username'] for p in SEED_DEMO_PATIENTS}
    doctor_names = {doctor_username_from_email(d['email']) for d in SEED_DOCTORS}
    return username in patient_names or username in doctor_names
