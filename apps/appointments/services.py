from datetime import datetime, date, time, timedelta
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from .models import Appointment
from apps.doctors.models import WorkingHours

def generate_slots(start_time, end_time):
    """
    Generates 30-minute time slots between start_time and end_time.
    Supports day shifts (e.g., 08:00 to 17:00) and night shifts (e.g., 20:00 to 06:00).
    """
    slots = []
    dummy_date = date.today()
    dt_start = datetime.combine(dummy_date, start_time)
    dt_end = datetime.combine(dummy_date, end_time)

    if dt_end <= dt_start:
        dt_end += timedelta(days=1)

    current = dt_start
    while current + timedelta(minutes=30) <= dt_end:
        slots.append(current.time())
        current += timedelta(minutes=30)

    return slots


def get_available_slots(doctor, target_date):
    """
    Returns available 30-minute slots for a doctor on target_date.
    Filters out already booked slots and slots within 1 hour of now.
    """
    day_of_week = target_date.weekday()
    try:
        wh = WorkingHours.objects.get(doctor=doctor, day_of_week=day_of_week, is_active=True)
    except WorkingHours.DoesNotExist:
        return []

    all_slots = generate_slots(wh.start_time, wh.end_time)

    # Get booked slots for scheduled appointments
    booked_slots = set(
        Appointment.objects.filter(
            doctor=doctor,
            appointment_date=target_date,
            status=Appointment.STATUS_SCHEDULED
        ).values_list('start_time', flat=True)
    )

    now = datetime.now()
    now_plus_1h = now + timedelta(hours=1)

    available = []
    for slot_time in all_slots:
        if slot_time in booked_slots:
            continue

        slot_dt = datetime.combine(target_date, slot_time)
        # Prevent bookings in the past or within 1 hour of current time
        if slot_dt < now_plus_1h:
            continue

        available.append(slot_time.strftime('%H:%M'))

    return available


def validate_and_book_appointment(patient, doctor, appointment_date, start_time_obj):
    """
    Validates and books an appointment for patient with doctor on appointment_date at start_time_obj.
    Enforces all business rules and constraints.
    """
    now = datetime.now()
    now_plus_1h = now + timedelta(hours=1)
    slot_dt = datetime.combine(appointment_date, start_time_obj)

    # Rule 1: Cannot book in past or within 1 hour of now
    if slot_dt < now_plus_1h:
        raise ValidationError("Appointments cannot be booked in the past or within 1 hour of the current time.")

    # Rule 2: 30-minute boundary check
    if start_time_obj.minute not in (0, 30) or start_time_obj.second != 0:
        raise ValidationError("Appointments must be scheduled in 30-minute slots (e.g. 09:00, 09:30).")

    # Rule 3: Doctor Working Hours check
    day_of_week = appointment_date.weekday()
    try:
        wh = WorkingHours.objects.get(doctor=doctor, day_of_week=day_of_week, is_active=True)
    except WorkingHours.DoesNotExist:
        raise ValidationError(f"Doctor does not have active working hours on {appointment_date.strftime('%A')}.")

    valid_slots = generate_slots(wh.start_time, wh.end_time)
    if start_time_obj not in valid_slots:
        raise ValidationError(f"Selected time {start_time_obj.strftime('%H:%M')} is outside the doctor's working hours.")

    # Rule 4: Patient single appointment per day check
    if Appointment.objects.filter(patient=patient, appointment_date=appointment_date, status=Appointment.STATUS_SCHEDULED).exists():
        raise ValidationError("Patient already has an active appointment scheduled on this date.")

    # Rule 5: Doctor slot availability check
    if Appointment.objects.filter(doctor=doctor, appointment_date=appointment_date, start_time=start_time_obj, status=Appointment.STATUS_SCHEDULED).exists():
        raise ValidationError("This appointment slot is already taken.")

    # Save appointment wrapped in try/except for DB race conditions
    try:
        with transaction.atomic():
            appointment = Appointment(
                patient=patient,
                doctor=doctor,
                appointment_date=appointment_date,
                start_time=start_time_obj,
                status=Appointment.STATUS_SCHEDULED
            )
            appointment.save()
            return appointment
    except Exception as e:
        raise ValidationError("This appointment slot was just taken by another patient. Please choose a different slot.")


def cancel_appointment(appointment, reason=""):
    """
    Cancels an appointment with a given reason. Slot becomes bookable again.
    """
    if appointment.status == Appointment.STATUS_CANCELLED:
        raise ValidationError("This appointment is already cancelled.")

    appointment.status = Appointment.STATUS_CANCELLED
    appointment.cancel_reason = reason or "Cancelled by patient"
    appointment.save()
    return appointment


def reschedule_appointment(appointment, new_date, new_start_time_obj):
    """
    Reschedules an appointment to a new date and time slot.
    Frees original slot and validates new slot like a fresh booking.
    """
    if appointment.status == Appointment.STATUS_CANCELLED:
        raise ValidationError("Cannot reschedule an appointment that has been cancelled.")

    now = datetime.now()
    now_plus_1h = now + timedelta(hours=1)
    slot_dt = datetime.combine(new_date, new_start_time_obj)

    if slot_dt < now_plus_1h:
        raise ValidationError("Rescheduled appointments cannot be in the past or within 1 hour of the current time.")

    if new_start_time_obj.minute not in (0, 30) or new_start_time_obj.second != 0:
        raise ValidationError("Appointments must be scheduled in 30-minute slots (e.g. 09:00, 09:30).")

    day_of_week = new_date.weekday()
    try:
        wh = WorkingHours.objects.get(doctor=appointment.doctor, day_of_week=day_of_week, is_active=True)
    except WorkingHours.DoesNotExist:
        raise ValidationError(f"Doctor does not have active working hours on {new_date.strftime('%A')}.")

    valid_slots = generate_slots(wh.start_time, wh.end_time)
    if new_start_time_obj not in valid_slots:
        raise ValidationError(f"Selected time {new_start_time_obj.strftime('%H:%M')} is outside the doctor's working hours.")

    # Check patient conflict (excluding current appointment)
    if Appointment.objects.filter(
        patient=appointment.patient,
        appointment_date=new_date,
        status=Appointment.STATUS_SCHEDULED
    ).exclude(id=appointment.id).exists():
        raise ValidationError("Patient already has an active appointment scheduled on the new date.")

    # Check doctor slot conflict (excluding current appointment)
    if Appointment.objects.filter(
        doctor=appointment.doctor,
        appointment_date=new_date,
        start_time=new_start_time_obj,
        status=Appointment.STATUS_SCHEDULED
    ).exclude(id=appointment.id).exists():
        raise ValidationError("The new appointment slot is already taken.")

    appointment.appointment_date = new_date
    appointment.start_time = new_start_time_obj
    appointment.save()
    return appointment
