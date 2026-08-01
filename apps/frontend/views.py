from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.conf import settings
from datetime import date, datetime
from apps.doctors.models import Doctor
from apps.appointments.models import Appointment
from apps.appointments.services import get_available_slots, validate_and_book_appointment, cancel_appointment, reschedule_appointment
from apps.accounts.serializers import RegisterSerializer
from apps.accounts.demo import DEMO_PASSWORD, is_demo_username


def _post_login_redirect(user):
    """Send doctors to the doctor portal; patients to the patient dashboard."""
    if getattr(user, 'doctor_profile', None):
        return redirect('frontend-doctor-dashboard')
    return redirect('frontend-dashboard')


def _demo_accounts_context():
    """Build clickable demo account cards for the sign-in page."""
    if not getattr(settings, 'ALLOW_DEMO_LOGIN', False):
        return {'allow_demo_login': False, 'demo_patients': [], 'demo_doctors': [], 'demo_password': ''}

    demo_doctors = list(
        Doctor.objects.filter(user__isnull=False)
        .select_related('user')
        .order_by('last_name', 'first_name')
    )
    # Only show doctors whose usernames are part of the seed demo set
    demo_doctors = [d for d in demo_doctors if is_demo_username(d.user.username)]

    from apps.accounts.models import Patient
    from apps.accounts.demo import SEED_DEMO_PATIENTS

    demo_usernames = {p['username'] for p in SEED_DEMO_PATIENTS}
    demo_patients = list(
        Patient.objects.filter(user__username__in=demo_usernames)
        .select_related('user')
        .order_by('user__first_name')
    )

    return {
        'allow_demo_login': True,
        'demo_patients': demo_patients,
        'demo_doctors': demo_doctors,
        'demo_password': DEMO_PASSWORD,
    }


def index_view(request):
    if request.user.is_authenticated:
        return _post_login_redirect(request.user)
    context = _demo_accounts_context()
    return render(request, 'frontend/index.html', context)


def login_action(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            return _post_login_redirect(user)
        else:
            messages.error(request, 'Invalid username or password.')
    return redirect('frontend-index')


def demo_login_action(request):
    """One-click login for seeded demo patient/doctor accounts."""
    if not getattr(settings, 'ALLOW_DEMO_LOGIN', False):
        messages.error(request, 'Demo login is disabled.')
        return redirect('frontend-index')

    if request.method != 'POST':
        return redirect('frontend-index')

    username = (request.POST.get('username') or '').strip()
    if not username or not is_demo_username(username):
        messages.error(request, 'That account is not available for demo login.')
        return redirect('frontend-index')

    user = authenticate(request, username=username, password=DEMO_PASSWORD)
    if user is None:
        messages.error(
            request,
            'Demo account not found. Run: python manage.py seed_doctors',
        )
        return redirect('frontend-index')

    login(request, user)
    role = 'doctor' if getattr(user, 'doctor_profile', None) else 'patient'
    messages.success(request, f'Signed in as demo {role}: {user.get_full_name() or user.username}')
    return _post_login_redirect(user)


def register_action(request):
    if request.method == 'POST':
        serializer = RegisterSerializer(data=request.POST)
        if serializer.is_valid():
            patient = serializer.save()
            login(request, patient.user)
            messages.success(request, 'Account created successfully! Welcome to ClinicCare.')
            return redirect('frontend-dashboard')
        else:
            for field, errs in serializer.errors.items():
                messages.error(request, f"{field.capitalize()}: {errs[0]}")
    return redirect('frontend-index')


def logout_action(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('frontend-index')


@login_required
def dashboard_view(request):
    # Doctors land on their own portal
    if getattr(request.user, 'doctor_profile', None):
        return redirect('frontend-doctor-dashboard')

    patient = getattr(request.user, 'patient_profile', None)
    if not patient:
        messages.error(request, "Patient profile not found.")
        return redirect('frontend-index')

    upcoming = Appointment.objects.filter(
        patient=patient,
        appointment_date__gte=date.today(),
        status=Appointment.STATUS_SCHEDULED
    ).order_by('appointment_date', 'start_time')

    past_and_cancelled = Appointment.objects.filter(
        patient=patient
    ).exclude(id__in=upcoming.values_list('id', flat=True)).order_by('-appointment_date', '-start_time')

    return render(request, 'frontend/dashboard.html', {
        'patient': patient,
        'upcoming': upcoming,
        'history': past_and_cancelled,
        'today': date.today().strftime('%Y-%m-%d')
    })


@login_required
def doctor_dashboard_view(request):
    doctor = getattr(request.user, 'doctor_profile', None)
    if not doctor:
        messages.error(request, 'Doctor profile not found.')
        return redirect('frontend-index')

    upcoming = Appointment.objects.filter(
        doctor=doctor,
        appointment_date__gte=date.today(),
        status=Appointment.STATUS_SCHEDULED,
    ).select_related('patient', 'patient__user').order_by('appointment_date', 'start_time')

    history = Appointment.objects.filter(
        doctor=doctor,
    ).exclude(
        id__in=upcoming.values_list('id', flat=True)
    ).select_related('patient', 'patient__user').order_by('-appointment_date', '-start_time')[:50]

    return render(request, 'frontend/doctor_dashboard.html', {
        'doctor': doctor,
        'upcoming': upcoming,
        'history': history,
    })


@login_required
def book_view(request):
    if getattr(request.user, 'doctor_profile', None) and not getattr(request.user, 'patient_profile', None):
        messages.info(request, 'Doctors cannot book appointments as patients from this portal.')
        return redirect('frontend-doctor-dashboard')

    doctors = Doctor.objects.all()
    if request.method == 'POST':
        doctor_id = request.POST.get('doctor_id')
        appt_date_str = request.POST.get('appointment_date')
        slot_time_str = request.POST.get('slot_time')

        patient = getattr(request.user, 'patient_profile', None)
        if not patient:
            messages.error(request, 'Only registered patients can book appointments.')
            return redirect('frontend-book')

        try:
            doctor = Doctor.objects.get(id=doctor_id)
            appt_date = datetime.strptime(appt_date_str, '%Y-%m-%d').date()
            start_time_obj = datetime.strptime(slot_time_str, '%H:%M').time()

            validate_and_book_appointment(
                patient=patient,
                doctor=doctor,
                appointment_date=appt_date,
                start_time_obj=start_time_obj
            )
            messages.success(request, f"Appointment booked successfully with {doctor.full_name} on {appt_date_str} at {slot_time_str}!")
            return redirect('frontend-dashboard')
        except Exception as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            messages.error(request, f"Booking Failed: {msg}")

    return render(request, 'frontend/book.html', {
        'doctors': doctors,
        'min_date': date.today().strftime('%Y-%m-%d')
    })


def slot_picker_partial(request):
    doctor_id = request.GET.get('doctor_id')
    # Book form field is named appointment_date; accept `date` as an alias for API/tests.
    date_str = request.GET.get('appointment_date') or request.GET.get('date')

    if not doctor_id or not date_str:
        return render(request, 'frontend/partials/slots.html', {'slots': [], 'error': 'Select both doctor and date.'})

    try:
        doctor = Doctor.objects.get(id=doctor_id)
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        slots = get_available_slots(doctor, target_date)
        return render(request, 'frontend/partials/slots.html', {
            'slots': slots,
            'doctor': doctor,
            'target_date': target_date
        })
    except Exception as e:
        return render(request, 'frontend/partials/slots.html', {'slots': [], 'error': str(e)})


@login_required
def cancel_action(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, patient__user=request.user)
    if request.method == 'POST':
        reason = request.POST.get('reason', 'Cancelled via patient portal')
        try:
            cancel_appointment(appointment, reason=reason)
            messages.success(request, 'Appointment cancelled successfully.')
        except Exception as e:
            messages.error(request, f"Cancellation failed: {e}")
    return redirect('frontend-dashboard')


@login_required
def reschedule_action(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, patient__user=request.user)
    if request.method == 'POST':
        new_date_str = request.POST.get('appointment_date')
        new_time_str = request.POST.get('slot_time')
        try:
            new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
            new_time = datetime.strptime(new_time_str, '%H:%M').time()
            reschedule_appointment(appointment, new_date=new_date, new_start_time_obj=new_time)
            messages.success(request, 'Appointment rescheduled successfully!')
        except Exception as e:
            messages.error(request, f"Reschedule failed: {e}")
    return redirect('frontend-dashboard')
