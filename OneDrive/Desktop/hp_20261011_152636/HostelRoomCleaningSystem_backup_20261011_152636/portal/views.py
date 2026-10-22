from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from cleaning.models import CleaningRequest
from cleaners.models import CleanerProfile
from students.models import StudentProfile, HostelAllocation
from wardens.models import WardenProfile

User = get_user_model()


# ============================================================
# ACCESS CONTROL
# ============================================================

def admin_required(view_fn):
    """Decorator: allow only authenticated admins."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if getattr(request.user, "role", None) != "admin":
            return HttpResponseForbidden(
                "This page is accessible to administrators only."
            )
        return view_fn(request, *args, **kwargs)
    wrapper.__name__ = view_fn.__name__
    return wrapper


# ============================================================
# DASHBOARD
# ============================================================

@admin_required
def portal_dashboard(request):
    today = timezone.localdate()

    total_students = User.objects.filter(role="student").count()
    total_wardens  = User.objects.filter(role="warden").count()
    total_cleaners = User.objects.filter(role="cleaner").count()
    total_requests = CleaningRequest.objects.count()

    pending_requests   = CleaningRequest.objects.filter(status="pending").count()
    assigned_requests  = CleaningRequest.objects.filter(status="assigned").count()
    inprogress_requests = CleaningRequest.objects.filter(status="in_progress").count()
    completed_requests = CleaningRequest.objects.filter(
        status__in=["completed", "confirmed"]
    ).count()
    rejected_requests  = CleaningRequest.objects.filter(status="rejected").count()

    recent_requests = CleaningRequest.objects.select_related(
        "student__user",
        "hostel_allocation",
        "assigned_cleaner__user",
        "assigned_by__user",
    ).order_by("-created_at")[:10]

    today_requests = CleaningRequest.objects.filter(
        cleaning_date=today
    ).count()

    context = {
        "total_students": total_students,
        "total_wardens": total_wardens,
        "total_cleaners": total_cleaners,
        "total_requests": total_requests,
        "pending_requests": pending_requests,
        "assigned_requests": assigned_requests,
        "inprogress_requests": inprogress_requests,
        "completed_requests": completed_requests,
        "rejected_requests": rejected_requests,
        "recent_requests": recent_requests,
        "today_requests": today_requests,
        "today": today,
    }
    return render(request, "portal/dashboard.html", context)


# ============================================================
# STUDENTS
# ============================================================

@admin_required
def portal_students(request):
    query  = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()   # active / inactive

    students = User.objects.filter(role="student").select_related(
        "student_profile"
    ).prefetch_related(
        "student_profile__allocations"
    ).order_by("name")

    if query:
        students = students.filter(
            Q(name__icontains=query) | Q(email__icontains=query)
        )

    if status == "active":
        students = students.filter(is_active=True)
    elif status == "inactive":
        students = students.filter(is_active=False)

    context = {
        "students": students,
        "query": query,
        "status_filter": status,
    }
    return render(request, "portal/students.html", context)


@admin_required
def portal_student_detail(request, user_id):
    student_user = get_object_or_404(User, pk=user_id, role="student")
    profile = getattr(student_user, "student_profile", None)
    allocations = profile.allocations.all() if profile else []
    requests = CleaningRequest.objects.filter(
        student=profile
    ).select_related(
        "hostel_allocation", "assigned_cleaner__user"
    ).order_by("-created_at")[:20] if profile else []

    context = {
        "target_user": student_user,
        "profile": profile,
        "allocations": allocations,
        "requests": requests,
    }
    return render(request, "portal/student_detail.html", context)


@admin_required
def portal_toggle_user(request, user_id):
    """Toggle a user's active status (POST only)."""
    if request.method != "POST":
        return redirect("portal_dashboard")

    target = get_object_or_404(User, pk=user_id)

    if target == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("portal_dashboard")

    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])

    action = "activated" if target.is_active else "deactivated"
    messages.success(request, f"Account for {target.name or target.email} was {action}.")

    next_url = request.POST.get("next", "portal_dashboard")
    return redirect(next_url)


# ============================================================
# WARDENS
# ============================================================

@admin_required
def portal_wardens(request):
    query = request.GET.get("q", "").strip()

    wardens = User.objects.filter(role="warden").select_related(
        "warden_profile"
    ).order_by("name")

    if query:
        wardens = wardens.filter(
            Q(name__icontains=query) | Q(email__icontains=query)
        )

    context = {
        "wardens": wardens,
        "query": query,
    }
    return render(request, "portal/wardens.html", context)


@admin_required
def portal_add_warden(request):
    """Create a new warden account directly (admin only)."""
    if request.method == "POST":
        name     = request.POST.get("name", "").strip()
        email    = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "").strip()
        block    = request.POST.get("assigned_block", "").strip()
        emp_id   = request.POST.get("employee_id", "").strip()

        errors = []
        if not name:
            errors.append("Name is required.")
        if not email:
            errors.append("Email is required.")
        if not password:
            errors.append("Password is required.")
        if not emp_id:
            errors.append("Employee ID is required.")
        if User.objects.filter(email=email).exists():
            errors.append("An account with this email already exists.")
        if WardenProfile.objects.filter(employee_id=emp_id).exists():
            errors.append("Employee ID already in use.")

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            user = User.objects.create_user(
                email=email,
                name=name,
                password=password,
                role="warden",
            )
            WardenProfile.objects.create(
                user=user,
                employee_id=emp_id,
                assigned_block=block,
            )
            messages.success(request, f"Warden {name} created successfully.")
            return redirect("portal_wardens")

    from students.models import HOSTEL_BLOCK_CHOICES
    return render(request, "portal/add_warden.html", {
        "block_choices": HOSTEL_BLOCK_CHOICES,
    })


# ============================================================
# CLEANERS
# ============================================================

@admin_required
def portal_cleaners(request):
    query = request.GET.get("q", "").strip()
    block = request.GET.get("block", "").strip()

    cleaners = User.objects.filter(role="cleaner").select_related(
        "cleaner_profile"
    ).order_by("name")

    if query:
        cleaners = cleaners.filter(
            Q(name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )

    if block:
        cleaners = cleaners.filter(cleaner_profile__assigned_block=block)

    from students.models import HOSTEL_BLOCK_CHOICES
    context = {
        "cleaners": cleaners,
        "query": query,
        "block_filter": block,
        "block_choices": HOSTEL_BLOCK_CHOICES,
    }
    return render(request, "portal/cleaners.html", context)


@admin_required
def portal_add_cleaner(request):
    """Create a new cleaner account (admin only)."""
    if request.method == "POST":
        name     = request.POST.get("name", "").strip()
        phone    = request.POST.get("phone", "").strip()
        email    = request.POST.get("email", "").strip().lower() or None
        password = request.POST.get("password", "").strip()
        block    = request.POST.get("assigned_block", "").strip()
        emp_id   = request.POST.get("employee_id", "").strip()

        errors = []
        if not name:
            errors.append("Name is required.")
        if not password:
            errors.append("Password is required.")
        if not emp_id:
            errors.append("Employee ID is required.")
        if not phone and not email:
            errors.append("Phone number or email is required.")
        if CleanerProfile.objects.filter(employee_id=emp_id).exists():
            errors.append("Employee ID already in use.")
        if email and User.objects.filter(email=email).exists():
            errors.append("An account with this email already exists.")
        if phone and User.objects.filter(phone=phone).exists():
            errors.append("An account with this phone number already exists.")

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            user = User.objects.create_user(
                email=email,
                name=name,
                password=password,
                phone=phone or None,
                role="cleaner",
            )
            CleanerProfile.objects.create(
                user=user,
                employee_id=emp_id,
                assigned_block=block,
                is_available=True,
            )
            messages.success(request, f"Cleaner {name} created successfully.")
            return redirect("portal_cleaners")

    from students.models import HOSTEL_BLOCK_CHOICES
    return render(request, "portal/add_cleaner.html", {
        "block_choices": HOSTEL_BLOCK_CHOICES,
    })


# ============================================================
# COMPLAINTS / REQUESTS
# ============================================================

@admin_required
def portal_complaints(request):
    query  = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    block  = request.GET.get("block", "").strip()

    complaints = CleaningRequest.objects.select_related(
        "student__user",
        "hostel_allocation",
        "assigned_cleaner__user",
        "assigned_by__user",
    ).order_by("-created_at")

    if query:
        complaints = complaints.filter(
            Q(student__user__name__icontains=query)
            | Q(student__user__email__icontains=query)
            | Q(student__registration_number__icontains=query)
            | Q(hostel_allocation__room_number__icontains=query)
            | Q(description__icontains=query)
            | Q(remarks__icontains=query)
        )

    if status:
        complaints = complaints.filter(status=status)
    if block:
        complaints = complaints.filter(hostel_allocation__block=block)

    from students.models import HOSTEL_BLOCK_CHOICES
    context = {
        "complaints": complaints,
        "query": query,
        "status_filter": status,
        "block_filter": block,
        "status_choices": CleaningRequest.STATUS_CHOICES,
        "block_choices": HOSTEL_BLOCK_CHOICES,
    }
    return render(request, "portal/complaints.html", context)



@admin_required
def portal_complaint_detail(request, request_id):
    complaint = get_object_or_404(
        CleaningRequest.objects.select_related(
            "student__user",
            "hostel_allocation",
            "assigned_cleaner__user",
            "assigned_by__user",
        ),
        pk=request_id,
    )
    feedback = getattr(complaint, "feedback", None)
    context = {
        "complaint": complaint,
        "feedback": feedback,
    }
    return render(request, "portal/complaint_detail.html", context)
