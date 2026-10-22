from django.urls import path

from . import views

urlpatterns = [
    path("", views.cleaner_home, name="cleaner_home"),
    path("requests/<int:request_id>/", views.cleaner_request_detail, name="cleaner_request_detail"),
    path("requests/<int:request_id>/start/", views.start_request, name="start_request"),
    path("requests/<int:request_id>/complete/", views.complete_request, name="complete_request"),
]
