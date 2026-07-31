from django.urls import path
from .views import (
    index_view, login_action, demo_login_action, register_action, logout_action,
    dashboard_view, doctor_dashboard_view, book_view, slot_picker_partial,
    cancel_action, reschedule_action
)

urlpatterns = [
    path('', index_view, name='frontend-index'),
    path('auth/login/', login_action, name='frontend-login'),
    path('auth/demo-login/', demo_login_action, name='frontend-demo-login'),
    path('auth/register/', register_action, name='frontend-register'),
    path('auth/logout/', logout_action, name='frontend-logout'),
    path('dashboard/', dashboard_view, name='frontend-dashboard'),
    path('doctor/dashboard/', doctor_dashboard_view, name='frontend-doctor-dashboard'),
    path('book/', book_view, name='frontend-book'),
    path('slots-picker/', slot_picker_partial, name='frontend-slots-picker'),
    path('appointments/<uuid:pk>/cancel/', cancel_action, name='frontend-cancel'),
    path('appointments/<uuid:pk>/reschedule/', reschedule_action, name='frontend-reschedule'),
]
