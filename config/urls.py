from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),

    path(
        "accounts/",
        include("allauth.urls"),
    ),

    path(
        "student/",
        include("students.urls"),
    ),

    path(
        "warden/",
        include("wardens.urls"),
    ),

    path(
        "cleaner/",
        include("cleaners.urls"),
    ),

    path(
        "portal/",
        include("portal.urls"),
    ),

    path(
        "",
        include("accounts.urls"),
    ),
]