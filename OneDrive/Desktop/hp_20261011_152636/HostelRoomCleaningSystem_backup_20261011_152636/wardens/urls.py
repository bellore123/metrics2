from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.warden_home,
        name="warden_home",
    ),

    path(
        "requests/<int:request_id>/",
        views.warden_request_detail,
        name="warden_request_detail",
    ),

    path(
        "requests/<int:request_id>/assign/",
        views.assign_cleaner,
        name="assign_cleaner",
    ),

    path(
        "requests/<int:request_id>/reject/",
        views.reject_request,
        name="reject_request",
    ),

    path(
        "requests/<int:request_id>/status/",
        views.update_request_status,
        name="update_request_status",
    ),
]