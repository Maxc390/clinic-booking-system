from django.urls import path
from .views import DoctorListView, DoctorDetailView, DoctorAvailabilityView

urlpatterns = [
    path('', DoctorListView.as_view(), name='doctor-list'),
    path('<uuid:pk>/', DoctorDetailView.as_view(), name='doctor-detail'),
    path('<uuid:pk>/availability/', DoctorAvailabilityView.as_view(), name='doctor-availability'),
]
