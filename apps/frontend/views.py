from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from datetime import date, datetime
from apps.doctors.models import Doctor
from apps.appointments.models import Appointment
from apps.appointments.services import get_available_slots, validate_and_book_appointment, cancel_appointment, reschedule_appointment
from apps.accounts.serializers import RegisterSerializer

def index_view(request):
    if request.user.is_authenticated:
        return redirect('frontend-dashboard')
    return render(request, 'frontend/index.html')

def login_action(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            return redirect('frontend-dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return redirect('frontend-index')

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
def book_view(request):
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
    date_str = request.GET.get('date')

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
