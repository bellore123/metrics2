from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cleaning.models import ACTIVE_STATUSES, CleaningRequest, Feedback
from notifications.services import (
    notify_roommates_request_created,
    notify_roommates_request_status_update,
)

from .forms import CleaningRequestForm, HostelAllocationForm
from .models import HostelAllocation, Room, StudentProfile




# =========================================================
# STUDENT ACCESS
# =========================================================

def student_only(user):
    return getattr(user, "role", None) == "student"


# =========================================================
# STUDENT HOME
# =========================================================

@login_required
def student_home(request):
    if not student_only(request.user):
        messages.error(
            request,
            "You are not allowed to access the student portal.",
        )
        return redirect("dashboard")

    student_profile, created = StudentProfile.objects.get_or_create(
        user=request.user,
    )

    current_allocation = HostelAllocation.objects.filter(
        student=student_profile,
        is_current=True,
    ).first()

    if current_allocation is None:
        return redirect("student_hostel_setup")

    active_room_request = None
    is_roommate_request = False

    if current_allocation.room:
        latest_requests = CleaningRequest.objects.filter(
            Q(room=current_allocation.room) | Q(student=student_profile)
        ).distinct().order_by("-created_at")[:5]

        active_room_request = CleaningRequest.objects.filter(
            room=current_allocation.room,
            status__in=ACTIVE_STATUSES,
        ).order_by("-created_at").first()

        if active_room_request and active_room_request.student != student_profile:
            is_roommate_request = True
    else:
        latest_requests = CleaningRequest.objects.filter(
            hostel_allocation=current_allocation,
        ).order_by("-created_at")[:5]

    user_notifications = request.user.notifications.all()[:10]
    unread_notifications_count = request.user.notifications.filter(is_read=False).count()

    context = {
        "student_profile": student_profile,
        "current_allocation": current_allocation,
        "latest_requests": latest_requests,
        "active_room_request": active_room_request,
        "is_roommate_request": is_roommate_request,
        "user_notifications": user_notifications,
        "unread_notifications_count": unread_notifications_count,
    }

    return render(
        request,
        "students/home.html",
        context,
    )



# =========================================================
# HOSTEL ROOM SETUP
# =========================================================

@login_required
def hostel_setup(request):
    if not student_only(request.user):
        messages.error(
            request,
            "You are not allowed to access the student portal.",
        )
        return redirect("dashboard")

    student_profile, created = StudentProfile.objects.get_or_create(
        user=request.user,
    )

    current_allocation = HostelAllocation.objects.filter(
        student=student_profile,
        is_current=True,
    ).first()

    if request.method == "POST":
        form = HostelAllocationForm(
            request.POST,
            instance=current_allocation,
        )

        if form.is_valid():
            reg_no = form.cleaned_data.get("registration_number")
            if reg_no:
                student_profile.registration_number = reg_no
                student_profile.save(update_fields=["registration_number"])

            allocation = form.save(commit=False)

            allocation.student = student_profile
            allocation.is_current = True

            allocation.save()

            messages.success(
                request,
                "Your hostel details have been saved successfully.",
            )

            return redirect("student_home")

    else:
        initial_data = {}
        if student_profile.registration_number:
            initial_data["registration_number"] = student_profile.registration_number
        else:
            initial_data["registration_number"] = student_profile.get_registration_number()

        form = HostelAllocationForm(
            instance=current_allocation,
            initial=initial_data,
        )

    context = {
        "form": form,
        "student_profile": student_profile,
        "current_allocation": current_allocation,
    }

    return render(
        request,
        "students/hostel_setup.html",
        context,
    )


# =========================================================
# CREATE CLEANING REQUEST
# =========================================================

@login_required
def create_cleaning_request(request):
    if not student_only(request.user):
        messages.error(
            request,
            "You are not allowed to access the student portal.",
        )
        return redirect("dashboard")

    student_profile, created = StudentProfile.objects.get_or_create(
        user=request.user,
    )

    current_allocation = HostelAllocation.objects.filter(
        student=student_profile,
        is_current=True,
    ).first()

    if current_allocation is None:
        messages.warning(
            request,
            "Please add your hostel details first.",
        )
        return redirect("student_hostel_setup")

    # Ensure allocation has room linked
    room = current_allocation.room
    if not room:
        room, _ = Room.objects.get_or_create(
            hostel_name=current_allocation.hostel_name or "VIT Men's Hostel",
            block=current_allocation.block,
            room_number=current_allocation.room_number.strip().upper(),
        )
        current_allocation.room = room
        current_allocation.save(update_fields=["room"])

    # Check for active cleaning request for this room
    active_request = CleaningRequest.objects.filter(
        room=room,
        status__in=ACTIVE_STATUSES,
    ).order_by("-created_at").first()

    if request.method == "POST":
        # Concurrency-safe room check under atomic transaction with lock
        with transaction.atomic():
            locked_room = Room.objects.select_for_update().get(id=room.id)
            current_active = CleaningRequest.objects.filter(
                room=locked_room,
                status__in=ACTIVE_STATUSES,
            ).order_by("-created_at").first()

            if current_active:
                error_title = "Room Cleaning Already Requested!"
                error_message = (
                    "Your roommate has already raised a room cleaning request. "
                    "Please wait until the existing request is completed."
                )
                room_display_str = f"{current_allocation.block} – {current_allocation.room_number}"

                # Handle AJAX / JSON submission
                if (
                    request.headers.get("x-requested-with") == "XMLHttpRequest"
                    or request.content_type == "application/json"
                    or request.GET.get("format") == "json"
                ):
                    return JsonResponse(
                        {
                            "status": "error",
                            "error": error_title,
                            "message": error_message,
                            "room_number": room_display_str,
                            "request_id": current_active.id,
                            "cleaning_date": str(current_active.cleaning_date),
                            "time_slot": current_active.get_time_slot_display(),
                            "current_status": current_active.get_status_display(),
                        },
                        status=409,
                    )

                messages.error(
                    request,
                    f"{error_title} {error_message}"
                )
                form = CleaningRequestForm(request.POST)
                context = {
                    "form": form,
                    "student_profile": student_profile,
                    "current_allocation": current_allocation,
                    "active_request": current_active,
                }
                return render(
                    request,
                    "students/create_request.html",
                    context,
                    status=400,
                )

            form = CleaningRequestForm(request.POST)
            if form.is_valid():
                cleaning_request = form.save(
                    commit=False,
                )

                cleaning_request.student = student_profile
                cleaning_request.hostel_allocation = current_allocation
                cleaning_request.room = locked_room
                cleaning_request.cleaning_type = "room_cleaning"
                cleaning_request.status = "pending"
                cleaning_request.assigned_cleaner = None
                cleaning_request.assigned_by = None

                try:
                    cleaning_request.save()
                except IntegrityError:
                    # Database unique constraint caught simultaneous duplicate
                    current_active = CleaningRequest.objects.filter(
                        room=locked_room,
                        status__in=ACTIVE_STATUSES,
                    ).order_by("-created_at").first()
                    error_title = "Room Cleaning Already Requested!"
                    error_message = (
                        "Your roommate has already raised a room cleaning request. "
                        "Please wait until the existing request is completed."
                    )
                    if (
                        request.headers.get("x-requested-with") == "XMLHttpRequest"
                        or request.content_type == "application/json"
                        or request.GET.get("format") == "json"
                    ):
                        return JsonResponse(
                            {
                                "status": "error",
                                "error": error_title,
                                "message": error_message,
                                "room_number": f"{current_allocation.block} – {current_allocation.room_number}",
                                "request_id": current_active.id if current_active else None,
                                "cleaning_date": str(current_active.cleaning_date) if current_active else "",
                                "time_slot": current_active.get_time_slot_display() if current_active else "",
                                "current_status": current_active.get_status_display() if current_active else "",
                            },
                            status=409,
                        )

                    messages.error(
                        request,
                        f"{error_title} {error_message}"
                    )
                    context = {
                        "form": form,
                        "student_profile": student_profile,
                        "current_allocation": current_allocation,
                        "active_request": current_active,
                    }
                    return render(
                        request,
                        "students/create_request.html",
                        context,
                        status=400,
                    )

                notify_roommates_request_created(cleaning_request)

                messages.success(
                    request,
                    (
                        "Cleaning request submitted successfully. "
                        "Your hostel warden will review the request "
                        "and assign a cleaner."
                    ),
                )

                return redirect(
                    "student_requests",
                )


    else:
        form = CleaningRequestForm()

    context = {
        "form": form,
        "student_profile": student_profile,
        "current_allocation": current_allocation,
        "active_request": active_request,
    }

    return render(
        request,
        "students/create_request.html",
        context,
    )



# =========================================================
# STUDENT REQUEST LIST
# =========================================================

@login_required
def student_requests(request):
    if not student_only(request.user):
        messages.error(
            request,
            "You are not allowed to access the student portal.",
        )
        return redirect("dashboard")

    student_profile, created = StudentProfile.objects.get_or_create(
        user=request.user,
    )

    current_allocation = HostelAllocation.objects.filter(
        student=student_profile,
        is_current=True,
    ).first()

    if current_allocation and current_allocation.room:
        cleaning_requests = CleaningRequest.objects.filter(
            Q(room=current_allocation.room) | Q(student=student_profile)
        ).distinct().order_by(
            "-created_at",
        )
    else:
        cleaning_requests = CleaningRequest.objects.filter(
            student=student_profile,
        ).order_by(
            "-created_at",
        )

    selected_status = request.GET.get(
        "status",
        "",
    ).strip()

    if selected_status:
        cleaning_requests = cleaning_requests.filter(
            status=selected_status,
        )

    context = {
        "student_profile": student_profile,
        "current_allocation": current_allocation,
        "requests": cleaning_requests,
        "selected_status": selected_status,
        "cleaning_request_statuses": (
            CleaningRequest.STATUS_CHOICES
        ),
    }

    return render(
        request,
        "students/my_requests.html",
        context,
    )


# =========================================================
# STUDENT REQUEST DETAIL
# =========================================================

@login_required
def student_request_detail(
    request,
    request_id,
):
    if not student_only(request.user):
        messages.error(
            request,
            "You are not allowed to access the student portal.",
        )
        return redirect("dashboard")

    student_profile, created = StudentProfile.objects.get_or_create(
        user=request.user,
    )

    current_allocation = HostelAllocation.objects.filter(
        student=student_profile,
        is_current=True,
    ).first()

    if current_allocation and current_allocation.room:
        cleaning_request = CleaningRequest.objects.filter(
            id=request_id
        ).filter(
            Q(room=current_allocation.room) | Q(student=student_profile)
        ).first()
    else:
        cleaning_request = CleaningRequest.objects.filter(
            id=request_id,
            student=student_profile,
        ).first()


    context = {
        "student_profile": student_profile,
        "current_allocation": current_allocation,
        "cleaning_request": cleaning_request,
    }

    return render(
        request,
        "students/request_detail.html",
        context,
    )


# =========================================================
# CANCEL REQUEST
# =========================================================

@login_required
def cancel_request(
    request,
    request_id,
):
    if not student_only(request.user):
        messages.error(
            request,
            "You are not allowed to access the student portal.",
        )
        return redirect("dashboard")

    if request.method != "POST":
        return redirect(
            "student_request_detail",
            request_id=request_id,
        )

    current_allocation = HostelAllocation.objects.filter(
        student__user=request.user,
        is_current=True,
    ).first()

    if current_allocation and current_allocation.room:
        cleaning_request = CleaningRequest.objects.filter(
            id=request_id,
            status="pending",
        ).filter(
            Q(room=current_allocation.room) | Q(student__user=request.user)
        ).first()
    else:
        cleaning_request = CleaningRequest.objects.filter(
            id=request_id,
            student__user=request.user,
            status="pending",
        ).first()

    if cleaning_request is None:
        messages.error(
            request,
            "This request cannot be cancelled.",
        )

        return redirect(
            "student_request_detail",
            request_id=request_id,
        )

    cleaning_request.status = "cancelled"

    cleaning_request.save(
        update_fields=[
            "status",
            "updated_at",
        ],
    )

    notify_roommates_request_status_update(cleaning_request, "cancelled")

    messages.success(
        request,
        "Cleaning request cancelled successfully.",
    )


    return redirect(
        "student_request_detail",
        request_id=request_id,
    )


# =========================================================
# SUBMIT FEEDBACK
# =========================================================

@login_required
def submit_feedback(
    request,
    request_id,
):
    if not student_only(request.user):
        messages.error(
            request,
            "You are not allowed to access the student portal.",
        )
        return redirect("dashboard")

    if request.method != "POST":
        return redirect(
            "student_request_detail",
            request_id=request_id,
        )

    current_allocation = HostelAllocation.objects.filter(
        student__user=request.user,
        is_current=True,
    ).first()

    if current_allocation and current_allocation.room:
        cleaning_request = CleaningRequest.objects.filter(
            id=request_id,
            status="completed",
        ).filter(
            Q(room=current_allocation.room) | Q(student__user=request.user)
        ).first()
    else:
        cleaning_request = CleaningRequest.objects.filter(
            id=request_id,
            student__user=request.user,
            status="completed",
        ).first()


    if cleaning_request is None:
        messages.error(
            request,
            "This request is not ready for feedback.",
        )

        return redirect(
            "student_requests",
        )

    room_status = request.POST.get(
        "room_status",
        "",
    ).strip()

    if room_status not in {
        "cleaned",
        "not_cleaned",
    }:
        messages.error(
            request,
            "Select the room cleaning status.",
        )

        return redirect(
            "student_request_detail",
            request_id=request_id,
        )

    rating_value = request.POST.get(
        "rating",
        "",
    ).strip()

    valid_ratings = {
        "1",
        "2",
        "3",
        "4",
        "5",
    }

    rating = (
        int(rating_value)
        if rating_value in valid_ratings
        else None
    )

    comments = request.POST.get(
        "comments",
        "",
    ).strip()

    Feedback.objects.update_or_create(
        cleaning_request=cleaning_request,
        defaults={
            "room_status": room_status,
            "rating": rating,
            "comments": comments,
        },
    )

    if room_status == "cleaned":
        cleaning_request.status = "confirmed"

        success_message = (
            "Thank you. Your room cleaning has been "
            "confirmed successfully."
        )

    else:
        cleaning_request.status = "not_cleaned"

        success_message = (
            "Your cleaning issue has been reported. "
            "The hostel warden can review and reassign "
            "the cleaning request."
        )

    cleaning_request.save(
        update_fields=[
            "status",
            "updated_at",
        ],
    )

    messages.success(
        request,
        success_message,
    )

    return redirect(
        "student_request_detail",
        request_id=request_id,
    )