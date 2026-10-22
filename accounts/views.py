from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import EmailOrPhoneLoginForm


# =========================================================
# ROLE SELECTION
# =========================================================

def role_selection(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    return render(
        request,
        "accounts/role_selection.html",
    )


# =========================================================
# OLD LOGIN REDIRECT
# =========================================================

def login_view(request):
    return redirect("role_selection")


# =========================================================
# STUDENT LOGIN PAGE
# =========================================================

def student_login(request):
    if request.user.is_authenticated:
        if request.user.role == "student":
            return redirect("student_home")

        return redirect("dashboard")

    return render(
        request,
        "accounts/student_login.html",
    )


# =========================================================
# START STUDENT GOOGLE LOGIN
# =========================================================

def student_google_login(request):
    if request.user.is_authenticated:
        if request.user.role == "student":
            return redirect("student_home")

        messages.error(
            request,
            "You are already signed in with another role.",
        )
        return redirect("dashboard")

    request.session["google_login_role"] = "student"
    request.session.modified = True
    request.session.save()

    google_login_url = reverse("google_login")

    return redirect(
        f"{google_login_url}?process=login"
    )


# =========================================================
# WARDEN LOGIN PAGE
# =========================================================

def warden_login(request):
    if request.user.is_authenticated:
        if request.user.role == "warden":
            return redirect("warden_home")

        return redirect("dashboard")

    return render(
        request,
        "accounts/warden_login.html",
    )


# =========================================================
# START WARDEN GOOGLE LOGIN
# =========================================================

def warden_google_login(request):
    if request.user.is_authenticated:
        if request.user.role == "warden":
            return redirect("warden_home")

        messages.error(
            request,
            "You are already signed in with another role.",
        )
        return redirect("dashboard")

    request.session["google_login_role"] = "warden"
    request.session.modified = True
    request.session.save()

    google_login_url = reverse("google_login")

    return redirect(
        f"{google_login_url}?process=login"
    )


# =========================================================
# CLEANER LOGIN
# =========================================================

def cleaner_login(request):
    if request.user.is_authenticated:
        if request.user.role == "cleaner":
            return redirect("cleaner_home")

        return redirect("dashboard")

    form = EmailOrPhoneLoginForm(
        request=request,
        data=request.POST or None,
    )

    if request.method == "POST" and form.is_valid():
        user = form.get_user()

        if user.role != "cleaner":
            messages.error(
                request,
                "This login page is available only for cleaners.",
            )

            return render(
                request,
                "accounts/cleaner_login.html",
                {
                    "form": form,
                },
            )

        login(
            request,
            user,
            backend="accounts.backend.EmailOrPhoneBackend",
        )

        messages.success(
            request,
            f"Welcome, {user.name or 'Cleaner'}.",
        )

        return redirect("cleaner_home")

    return render(
        request,
        "accounts/cleaner_login.html",
        {
            "form": form,
        },
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

def admin_login(request):
    if request.user.is_authenticated:
        if request.user.role == "admin":
            return redirect("portal:portal_dashboard")

        return redirect("dashboard")

    form = EmailOrPhoneLoginForm(
        request=request,
        data=request.POST or None,
    )

    if request.method == "POST" and form.is_valid():
        user = form.get_user()

        if user.role != "admin":
            messages.error(
                request,
                "This login page is available only for administrators.",
            )

            return render(
                request,
                "accounts/admin_login.html",
                {
                    "form": form,
                },
            )

        login(
            request,
            user,
            backend="accounts.backend.EmailOrPhoneBackend",
        )

        messages.success(
            request,
            f"Welcome, {user.name or 'Administrator'}.",
        )

        return redirect("portal:portal_dashboard")

    return render(
        request,
        "accounts/admin_login.html",
        {
            "form": form,
        },
    )


# =========================================================
# ROLE-BASED DASHBOARD REDIRECT
# =========================================================

@login_required
def dashboard_redirect(request):
    role = request.user.role

    if role == "student":
        return redirect("student_home")

    if role == "warden":
        return redirect("warden_home")

    if role == "cleaner":
        return redirect("cleaner_home")

    if role == "admin":
        return redirect("portal:portal_dashboard")

    messages.error(
        request,
        "Your account does not have a valid role.",
    )

    logout(request)

    return redirect("role_selection")


# =========================================================
# STUDENT DASHBOARD REDIRECT
# =========================================================

@login_required
def student_dashboard(request):
    if request.user.role != "student":
        return HttpResponse(
            "You are not allowed to access the Student portal.",
            status=403,
        )

    return redirect("student_home")


# =========================================================
# WARDEN DASHBOARD REDIRECT
# =========================================================

@login_required
def warden_dashboard(request):
    if request.user.role != "warden":
        return HttpResponse(
            "You are not allowed to access the Warden portal.",
            status=403,
        )

    return redirect("warden_home")


# =========================================================
# TEMPORARY CLEANER DASHBOARD
# =========================================================

@login_required
def cleaner_dashboard(request):
    """Redirects authenticated cleaners to the real cleaner portal."""

    if request.user.role != "cleaner":
        return HttpResponse(
            "You are not allowed to access the Cleaner portal.",
            status=403,
        )

    return redirect("cleaner_home")


# =========================================================
# LOGOUT
# =========================================================

@login_required
def logout_view(request):
    request.session.pop(
        "google_login_role",
        None,
    )

    logout(request)

    messages.success(
        request,
        "You have been logged out successfully.",
    )

    return redirect("role_selection")