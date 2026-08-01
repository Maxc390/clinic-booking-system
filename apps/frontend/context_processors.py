def role_flags(request):
    """Expose safe doctor/patient flags without raising OneToOne DoesNotExist."""
    user = getattr(request, 'user', None)
    is_doctor = False
    is_patient = False
    if user is not None and user.is_authenticated:
        is_doctor = hasattr(user, 'doctor_profile') and user.doctor_profile is not None
        is_patient = hasattr(user, 'patient_profile') and user.patient_profile is not None
    return {
        'is_doctor': is_doctor,
        'is_patient': is_patient,
    }
