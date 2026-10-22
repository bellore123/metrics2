from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from cleaning.models import CleaningRequest

from .models import CleanerProfile


# =========================================================
# CLEANER ACCESS CONTROL
# =========================================================

def cleaner_required(view_function):
    @wraps(view_function)
    @login_required
    def wrapper(request, *args, **kwargs):
        if getattr(request.user, "role", None) != "cleaner":
            return HttpResponseForbidden(
                "Cleaner access only."
            )

        return view_function(
            request,
            *args,
            **kwargs,
        )

    return wrapper


# =========================================================
# CLEANER PROFILE
# =========================================================

def get_cleaner(user):
    return get_object_or_404(
        CleanerProfile.objects.select_related("user"),
        user=user,
    )


# =========================================================
# CLEANER DASHBOARD
# =========================================================

@cleaner_required
def cleaner_home(request):
    cleaner = get_cleaner(request.user)
    today = timezone.localdate()

    all_requests = CleaningRequest.objects.filter(
        assigned_cleaner=cleaner,
    ).select_related(
        "student__user",
        "hostel_allocation",
        "assigned_by__user",
    )

    selected_status = request.GET.get(
        "status",
        "",
    ).strip()

    displayed_requests = all_requests

    if selected_status:
        displayed_requests = displayed_requests.filter(
            status=selected_status,
        )

    displayed_requests = displayed_requests.order_by(
        "cleaning_date",
        "time_slot",
        "-created_at",
    )

    assigned_count = all_requests.filter(
        status="assigned",
    ).count()

    in_progress_count = all_requests.filter(
        status="in_progress",
    ).count()

    completed_count = all_requests.filter(
        status__in=[
            "completed",
            "confirmed",
        ],
    ).count()

    today_count = all_requests.filter(
        cleaning_date=today,
        status__in=[
            "assigned",
            "in_progress",
        ],
    ).count()

    context = {
        "cleaner": cleaner,
        "requests": displayed_requests,
        "today": today,
        "selected_status": selected_status,
        "status_choices": CleaningRequest.STATUS_CHOICES,
        "assigned_count": assigned_count,
        "in_progress_count": in_progress_count,
        "active_count": assigned_count + in_progress_count,
        "completed_count": completed_count,
        "today_count": today_count,
    }

    return render(
        request,
        "cleaners/home.html",
        context,
    )


# =========================================================
# CLEANER REQUEST DETAILS
# =========================================================

@cleaner_required
def cleaner_request_detail(request, request_id):
    cleaner = get_cleaner(request.user)

    cleaning_request = get_object_or_404(
        CleaningRequest.objects.select_related(
            "student__user",
            "hostel_allocation",
            "assigned_by__user",
            "assigned_cleaner__user",
        ),
        id=request_id,
        assigned_cleaner=cleaner,
    )

    context = {
        "cleaner": cleaner,
        "cleaning_request": cleaning_request,
    }

    return render(
        request,
        "cleaners/request_detail.html",
        context,
    )


# =========================================================
# START CLEANING
# =========================================================

@cleaner_required
@require_POST
def start_request(request, request_id):
    cleaner = get_cleaner(request.user)

    cleaning_request = get_object_or_404(
        CleaningRequest,
        id=request_id,
        assigned_cleaner=cleaner,
        status="assigned",
    )

    cleaning_request.status = "in_progress"

    cleaning_request.save(
        update_fields=[
            "status",
            "updated_at",
        ],
    )

    from notifications.services import notify_roommates_request_status_update
    notify_roommates_request_status_update(cleaning_request, "in_progress")

    cleaner.is_available = False

    cleaner.save(
        update_fields=[
            "is_available",
        ],
    )

    messages.success(
        request,
        "Cleaning started successfully.",
    )

    return redirect(
        "cleaner_request_detail",
        request_id=request_id,
    )


# =========================================================
# COMPLETE CLEANING
# =========================================================

@cleaner_required
@require_POST
def complete_request(request, request_id):
    cleaner = get_cleaner(request.user)

    cleaning_request = get_object_or_404(
        CleaningRequest,
        id=request_id,
        assigned_cleaner=cleaner,
        status="in_progress",
    )

    cleaning_request.status = "completed"
    cleaning_request.completion_date = timezone.localdate()

    cleaning_request.save(
        update_fields=[
            "status",
            "completion_date",
            "updated_at",
        ],
    )

    from notifications.services import notify_roommates_request_status_update
    notify_roommates_request_status_update(cleaning_request, "completed")



    has_other_active_requests = CleaningRequest.objects.filter(
        assigned_cleaner=cleaner,
        status="in_progress",
    ).exclude(
        id=cleaning_request.id,
    ).exists()

    cleaner.is_available = not has_other_active_requests

    cleaner.save(
        update_fields=[
            "is_available",
        ],
    )

    messages.success(
        request,
        "Cleaning marked as completed.",
    )

    return redirect(
        "cleaner_request_detail",
        request_id=request_id,
    )