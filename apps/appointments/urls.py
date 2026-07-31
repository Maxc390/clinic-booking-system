from django.urls import path
from .views import (
    AppointmentListCreateView,
    AppointmentCancelView,
    AppointmentRescheduleView,
    PatientAppointmentsView
)

urlpatterns = [
    path('appointments/', AppointmentListCreateView.as_view(), name='appointment-list-create'),
    path('appointments/<uuid:pk>/cancel/', AppointmentCancelView.as_view(), name='appointment-cancel'),
    path('appointments/<uuid:pk>/reschedule/', AppointmentRescheduleView.as_view(), name='appointment-reschedule'),
    path('patients/<uuid:pk>/appointments/', PatientAppointmentsView.as_view(), name='patient-appointments'),
]
