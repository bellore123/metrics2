from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    # Dashboard
    path(
        "",
        views.portal_dashboard,
        name="portal_dashboard",
    ),

    # Students
    path(
        "students/",
        views.portal_students,
        name="portal_students",
    ),
    path(
        "students/<int:user_id>/",
        views.portal_student_detail,
        name="portal_student_detail",
    ),

    # Wardens
    path(
        "wardens/",
        views.portal_wardens,
        name="portal_wardens",
    ),
    path(
        "wardens/add/",
        views.portal_add_warden,
        name="portal_add_warden",
    ),

    # Cleaners
    path(
        "cleaners/",
        views.portal_cleaners,
        name="portal_cleaners",
    ),
    path(
        "cleaners/add/",
        views.portal_add_cleaner,
        name="portal_add_cleaner",
    ),

    # Complaints
    path(
        "complaints/",
        views.portal_complaints,
        name="portal_complaints",
    ),
    path(
        "complaints/<int:request_id>/",
        views.portal_complaint_detail,
        name="portal_complaint_detail",
    ),

    # User toggle active
    path(
        "users/<int:user_id>/toggle/",
        views.portal_toggle_user,
        name="portal_toggle_user",
    ),
]
