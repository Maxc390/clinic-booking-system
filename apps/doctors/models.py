import uuid
from django.db import models
from django.core.exceptions import ValidationError

DAY_CHOICES = [
    (0, 'Monday'),
    (1, 'Tuesday'),
    (2, 'Wednesday'),
    (3, 'Thursday'),
    (4, 'Friday'),
    (5, 'Saturday'),
    (6, 'Sunday'),
]

class Doctor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    specialization = models.CharField(max_length=200, default='General Practice')
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"Dr. {self.first_name} {self.last_name} ({self.specialization})"

    @property
    def full_name(self):
        return f"Dr. {self.first_name} {self.last_name}"


class WorkingHours(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='working_hours')
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['day_of_week', 'start_time']
        unique_together = ['doctor', 'day_of_week']

    def __str__(self):
        day_name = dict(DAY_CHOICES).get(self.day_of_week, 'Unknown')
        return f"{self.doctor.full_name} - {day_name}: {self.start_time.strftime('%H:%M')} to {self.end_time.strftime('%H:%M')}"

    def clean(self):
        # Validation for maximum 12 hours shift limit requirement
        from datetime import datetime, timedelta
        dummy_date = datetime.now().date()
        dt_start = datetime.combine(dummy_date, self.start_time)
        dt_end = datetime.combine(dummy_date, self.end_time)
        if dt_end <= dt_start:
            dt_end += timedelta(days=1)
        duration_hours = (dt_end - dt_start).total_seconds() / 3600.0
        if duration_hours > 12.0:
            raise ValidationError({'end_time': f"Working shift cannot exceed 12 hours (currently {duration_hours:.1f} hours)."})
