from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.student_home,
        name="student_home"
    ),

    path(
        "hostel-details/",
        views.hostel_setup,
        name="student_hostel_setup"
    ),

    path(
        "create-request/",
        views.create_cleaning_request,
        name="create_cleaning_request"
    ),

    path(
        "my-requests/",
        views.student_requests,
        name="student_requests"
    ),

    path(
        "request/<int:request_id>/",
        views.student_request_detail,
        name="student_request_detail"
    ),
    path(
        "request/<int:request_id>/cancel/",
        views.cancel_request,
        name="cancel_request"
    ),
    path(
        "request/<int:request_id>/feedback/",
        views.submit_feedback,
        name="submit_feedback"
    ),
]
