from rest_framework import serializers
from .models import Doctor, WorkingHours

class WorkingHoursSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = WorkingHours
        fields = ['id', 'day_of_week', 'day_name', 'start_time', 'end_time', 'is_active']

class DoctorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    working_hours = WorkingHoursSerializer(many=True, read_only=True)

    class Meta:
        model = Doctor
        fields = ['id', 'first_name', 'last_name', 'full_name', 'specialization', 'email', 'phone', 'working_hours', 'created_at']
