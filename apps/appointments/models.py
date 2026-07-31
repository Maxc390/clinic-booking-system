import uuid
from datetime import datetime, timedelta
from django.db import models
from apps.accounts.models import Patient
from apps.doctors.models import Doctor

class Appointment(models.Model):
    STATUS_SCHEDULED = 'scheduled'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = [
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, related_name='appointments')
    appointment_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)
    cancel_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['appointment_date', 'start_time']
        constraints = [
            # Doctor cannot have two scheduled appointments at the exact same date & start_time
            models.UniqueConstraint(
                fields=['doctor', 'appointment_date', 'start_time'],
                condition=models.Q(status='scheduled'),
                name='unique_doctor_slot_per_time'
            ),
            # Patient cannot have more than 1 scheduled appointment per day across any doctor
            models.UniqueConstraint(
                fields=['patient', 'appointment_date'],
                condition=models.Q(status='scheduled'),
                name='unique_patient_appointment_per_day'
            )
        ]

    def __str__(self):
        return f"{self.patient.full_name} with {self.doctor.full_name} on {self.appointment_date} at {self.start_time.strftime('%H:%M')} [{self.status}]"

    def save(self, *args, **kwargs):
        # Auto-compute 30-minute slot end_time if not set
        if self.start_time and not self.end_time:
            dummy_dt = datetime.combine(datetime.today(), self.start_time)
            self.end_time = (dummy_dt + timedelta(minutes=30)).time()
        super().save(*args, **kwargs)
