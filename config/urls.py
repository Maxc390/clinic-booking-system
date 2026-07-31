from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include([
        path('auth/', include('apps.accounts.urls')),
        path('doctors/', include('apps.doctors.urls')),
        path('', include('apps.appointments.urls')),
    ])),
    path('', include('apps.frontend.urls')),
]
