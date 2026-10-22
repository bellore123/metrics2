from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from cleaning.models import CleaningRequest
from cleaners.models import CleanerProfile

from .models import WardenProfile


# =========================================================
# ACCESS CONTROL
# =========================================================

def is_warden(user):
    return getattr(user, "role", None) == "warden"


def get_warden_block(user):
    block = getattr(user, "warden_block", None)
    if not block:
        profile = getattr(user, "warden_profile", None)
        if profile and profile.assigned_block:
            block = profile.assigned_block
    return block


# =========================================================
# WARDEN PROFILE
# =========================================================

def get_or_create_warden_profile(user):
    assigned_block = get_warden_block(user)
    employee_id = f"WARDEN-{user.pk:04d}"

    profile, created = WardenProfile.objects.get_or_create(
        user=user,
        defaults={
            "employee_id": employee_id,
            "assigned_block": assigned_block or "",
        },
    )

    fields_to_update = []

    if profile.assigned_block != (assigned_block or ""):
        profile.assigned_block = assigned_block or ""
        fields_to_update.append("assigned_block")

    if not profile.employee_id:
        profile.employee_id = employee_id
        fields_to_update.append("employee_id")

    if fields_to_update:
        profile.save(
            update_fields=fields_to_update,
        )

    return profile


# =========================================================
# BLOCK REQUEST QUERY
# =========================================================

def get_block_requests(assigned_block):
    return CleaningRequest.objects.filter(
        hostel_allocation__block=assigned_block,
    ).select_related(
        "student__user",
        "hostel_allocation",
        "assigned_cleaner__user",
        "assigned_by__user",
    )


# =========================================================
# WARDEN DASHBOARD
# =========================================================

@login_required
def warden_home(request):
    if not is_warden(request.user):
        messages.error(
            request,
            "You are not allowed to access the warden portal.",
        )
        return redirect("dashboard")

    assigned_block = get_warden_block(
        request.user,
    )

    if not assigned_block:
        messages.error(
            request,
            "No hostel block is assigned to this warden account.",
        )
        return redirect("role_selection")

    warden_profile = get_or_create_warden_profile(
        request.user,
    )

    today = timezone.localdate()

    block_requests = get_block_requests(
        assigned_block,
    )

    # ── Filters ──────────────────────────────────────────────
    selected_status = request.GET.get("status", "").strip()
    search_query    = request.GET.get("q", "").strip()

    filtered_requests = block_requests

    if selected_status:
        filtered_requests = filtered_requests.filter(
            status=selected_status,
        )
    if search_query:
        from django.db.models import Q
        filtered_requests = filtered_requests.filter(
            Q(student__user__name__icontains=search_query)
            | Q(student__user__email__icontains=search_query)
            | Q(student__registration_number__icontains=search_query)
            | Q(hostel_allocation__room_number__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(remarks__icontains=search_query)
        )

    recent_requests = filtered_requests.order_by(
        "-created_at",
    )[:50]


    pending_count = block_requests.filter(
        status="pending",
    ).count()

    assigned_count = block_requests.filter(
        status="assigned",
    ).count()

    in_progress_count = block_requests.filter(
        status="in_progress",
    ).count()

    not_cleaned_count = block_requests.filter(
        status="not_cleaned",
    ).count()

    completed_today_count = block_requests.filter(
        status__in=[
            "completed",
            "confirmed",
        ],
        updated_at__date=today,
    ).count()

    today_requests_count = block_requests.filter(
        cleaning_date=today,
    ).count()

    available_cleaners_count = CleanerProfile.objects.filter(
        assigned_block=assigned_block,
        is_available=True,
        user__role="cleaner",
        user__is_active=True,
    ).count()

    context = {
        "warden_profile": warden_profile,
        "assigned_block": assigned_block,
        "today": today,
        "recent_requests": recent_requests,
        "selected_status": selected_status,
        "search_query": search_query,
        "status_choices": CleaningRequest.STATUS_CHOICES,
        "pending_count": pending_count,
        "assigned_count": assigned_count,
        "in_progress_count": in_progress_count,
        "not_cleaned_count": not_cleaned_count,
        "completed_today_count": completed_today_count,
        "today_requests_count": today_requests_count,
        "available_cleaners_count": available_cleaners_count,
    }

    return render(
        request,
        "wardens/dashboard.html",
        context,
    )



# =========================================================
# WARDEN REQUEST DETAIL
# =========================================================

@login_required
def warden_request_detail(request, request_id):
    if not is_warden(request.user):
        messages.error(
            request,
            "You are not allowed to access the warden portal.",
        )
        return redirect("dashboard")

    assigned_block = get_warden_block(
        request.user,
    )

    if not assigned_block:
        messages.error(
            request,
            "No hostel block is assigned to this account.",
        )
        return redirect("warden_home")

    warden_profile = get_or_create_warden_profile(
        request.user,
    )

    cleaning_request = get_object_or_404(
        get_block_requests(assigned_block),
        id=request_id,
    )

    available_cleaners = CleanerProfile.objects.filter(
        assigned_block=assigned_block,
        is_available=True,
        user__role="cleaner",
        user__is_active=True,
    ).select_related(
        "user",
    ).order_by(
        "user__name",
    )

    context = {
        "warden_profile": warden_profile,
        "assigned_block": assigned_block,
        "cleaning_request": cleaning_request,
        "available_cleaners": available_cleaners,
    }

    return render(
        request,
        "wardens/request_detail.html",
        context,
    )


# =========================================================
# ASSIGN CLEANER
# =========================================================

@login_required
@transaction.atomic
def assign_cleaner(request, request_id):
    if not is_warden(request.user):
        messages.error(
            request,
            "You are not allowed to assign cleaners.",
        )
        return redirect("dashboard")

    if request.method != "POST":
        return redirect(
            "warden_request_detail",
            request_id=request_id,
        )

    assigned_block = get_warden_block(
        request.user,
    )

    if not assigned_block:
        messages.error(
            request,
            "No hostel block is assigned to this account.",
        )
        return redirect("warden_home")

    warden_profile = get_or_create_warden_profile(
        request.user,
    )

    cleaning_request = get_object_or_404(
        get_block_requests(assigned_block),
        id=request_id,
    )

    if cleaning_request.status not in {
        "pending",
        "assigned",
        "in_progress",
        "not_cleaned",
    }:
        messages.error(
            request,
            "A cleaner cannot be assigned at the current request stage.",
        )
        return redirect(
            "warden_request_detail",
            request_id=request_id,
        )

    cleaner_id = request.POST.get(
        "cleaner_id",
        "",
    ).strip()

    if not cleaner_id:
        messages.error(
            request,
            "Select a cleaner before assigning the request.",
        )
        return redirect(
            "warden_request_detail",
            request_id=request_id,
        )

    cleaner = CleanerProfile.objects.filter(
        id=cleaner_id,
        assigned_block=assigned_block,
        user__role="cleaner",
        user__is_active=True,
    ).select_related(
        "user",
    ).first()

    if cleaner is None:
        messages.error(
            request,
            (
                "The selected cleaner is unavailable "
                "or belongs to another block."
            ),
        )
        return redirect(
            "warden_request_detail",
            request_id=request_id,
        )

    old_cleaner = cleaning_request.assigned_cleaner
    cleaning_request.assigned_cleaner = cleaner
    cleaning_request.assigned_by = warden_profile
    cleaning_request.status = "assigned"

    cleaning_request.save(
        update_fields=[
            "assigned_cleaner",
            "assigned_by",
            "status",
            "updated_at",
        ],
    )

    if old_cleaner and old_cleaner != cleaner:
        has_other = CleaningRequest.objects.filter(
            assigned_cleaner=old_cleaner,
            status="in_progress",
        ).exclude(
            id=cleaning_request.id,
        ).exists()
        old_cleaner.is_available = not has_other
        old_cleaner.save(update_fields=["is_available"])

    messages.success(
        request,
        (
            f"{cleaner.user.name or 'Cleaner'} was assigned "
            f"to Room "
            f"{cleaning_request.hostel_allocation.room_number}."
        ),
    )

    from notifications.services import notify_roommates_request_status_update
    notify_roommates_request_status_update(cleaning_request, "assigned")

    return redirect(
        "warden_request_detail",
        request_id=request_id,
    )



# =========================================================
# REJECT REQUEST
# =========================================================

@login_required
@transaction.atomic
def reject_request(request, request_id):
    if not is_warden(request.user):
        messages.error(
            request,
            "You are not allowed to reject requests.",
        )
        return redirect("dashboard")

    if request.method != "POST":
        return redirect(
            "warden_request_detail",
            request_id=request_id,
        )

    assigned_block = get_warden_block(
        request.user,
    )

    if not assigned_block:
        messages.error(
            request,
            "No hostel block is assigned to this account.",
        )
        return redirect("warden_home")

    cleaning_request = get_object_or_404(
        get_block_requests(assigned_block),
        id=request_id,
    )

    if cleaning_request.status != "pending":
        messages.error(
            request,
            "Only pending requests can be rejected.",
        )
        return redirect(
            "warden_request_detail",
            request_id=request_id,
        )

    cleaning_request.status = "rejected"
    cleaning_request.assigned_cleaner = None

    cleaning_request.save(
        update_fields=[
            "status",
            "assigned_cleaner",
            "updated_at",
        ],
    )

    from notifications.services import notify_roommates_request_status_update
    notify_roommates_request_status_update(cleaning_request, "rejected")

    messages.success(
        request,
        "The cleaning request was rejected.",
    )


    return redirect(
        "warden_request_detail",
        request_id=request_id,
    )


# =========================================================
# UPDATE REQUEST STATUS DIRECTLY (WARDEN)
# =========================================================

@login_required
@transaction.atomic
def update_request_status(request, request_id):
    if not is_warden(request.user):
        messages.error(
            request,
            "You are not allowed to update request status.",
        )
        return redirect("dashboard")

    if request.method != "POST":
        return redirect(
            "warden_request_detail",
            request_id=request_id,
        )

    assigned_block = get_warden_block(
        request.user,
    )

    if not assigned_block:
        messages.error(
            request,
            "No hostel block is assigned to this account.",
        )
        return redirect("warden_home")

    cleaning_request = get_object_or_404(
        get_block_requests(assigned_block),
        id=request_id,
    )

    new_status = request.POST.get("status", "").strip()
    valid_statuses = dict(CleaningRequest.STATUS_CHOICES)

    if new_status not in valid_statuses:
        messages.error(
            request,
            "Invalid status selected.",
        )
        return redirect(
            "warden_request_detail",
            request_id=request_id,
        )

    update_fields = ["status", "updated_at"]
    cleaning_request.status = new_status

    if new_status == "completed" and not cleaning_request.completion_date:
        cleaning_request.completion_date = timezone.localdate()
        update_fields.append("completion_date")

    if new_status in {"pending", "rejected", "cancelled"}:
        if cleaning_request.assigned_cleaner:
            cleaner = cleaning_request.assigned_cleaner
            cleaning_request.assigned_cleaner = None
            update_fields.append("assigned_cleaner")

            has_other = CleaningRequest.objects.filter(
                assigned_cleaner=cleaner,
                status="in_progress",
            ).exclude(
                id=cleaning_request.id,
            ).exists()
            cleaner.is_available = not has_other
            cleaner.save(update_fields=["is_available"])

    cleaning_request.save(update_fields=update_fields)

    from notifications.services import notify_roommates_request_status_update
    notify_roommates_request_status_update(cleaning_request, new_status)

    messages.success(
        request,
        f"Request status successfully updated to '{valid_statuses[new_status]}'.",
    )


    return redirect(
        "warden_request_detail",
        request_id=request_id,
    )