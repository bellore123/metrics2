from django.urls import include, path

from . import views


urlpatterns = [

    # =========================================================
    # ROLE SELECTION
    # =========================================================

    path(
        "",
        views.role_selection,
        name="role_selection",
    ),

    path(
        "login/",
        views.login_view,
        name="login",
    ),

    # =========================================================
    # STUDENT
    # =========================================================

    path(
        "student/login/",
        views.student_login,
        name="student_login",
    ),

    path(
        "student/google-login/",
        views.student_google_login,
        name="student_google_login",
    ),

    # =========================================================
    # WARDEN
    # =========================================================

    path(
        "warden/login/",
        views.warden_login,
        name="warden_login",
    ),

    path(
        "warden/google-login/",
        views.warden_google_login,
        name="warden_google_login",
    ),

    # =========================================================
    # CLEANER
    # =========================================================

    path(
        "cleaner/login/",
        views.cleaner_login,
        name="cleaner_login",
    ),

    # =========================================================
    # ADMIN
    # =========================================================

    path(
        "admin-login/",
        views.admin_login,
        name="admin_login",
    ),

    # =========================================================
    # DASHBOARDS
    # =========================================================

    path(
        "dashboard/",
        views.dashboard_redirect,
        name="dashboard",
    ),

    path(
        "student-dashboard/",
        views.student_dashboard,
        name="student_dashboard",
    ),

    path(
        "warden-dashboard/",
        views.warden_dashboard,
        name="warden_dashboard",
    ),

    path(
        "cleaner-dashboard/",
        views.cleaner_dashboard,
        name="cleaner_dashboard",
    ),

    # =========================================================
    # LOGOUT
    # =========================================================

    path(
        "logout/",
        views.logout_view,
        name="logout",
    ),

    # =========================================================
    # DJANGO-ALLAUTH
    # =========================================================

    path(
        "social/",
        include("allauth.socialaccount.urls"),
    ),
]