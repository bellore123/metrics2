from students.models import StudentProfile
from .models import Notification


def notify_roommates_request_created(cleaning_request):
    """
    Sends notification to all roommates sharing the same room and block
    informing them that a cleaning request has been raised by their roommate,
    and that duplicate requests cannot be created until it is completed.
    """
    if not cleaning_request.room:
        return

    requester_student = cleaning_request.student
    requester_user = requester_student.user
    requester_name = requester_user.name or requester_user.email

    room = cleaning_request.room
    room_display = f"{room.block} – Room {room.room_number}"

    # Find all current allocations for this room excluding the student who raised it
    roommates = StudentProfile.objects.filter(
        allocations__room=room,
        allocations__is_current=True,
    ).exclude(
        id=requester_student.id,
    ).distinct()

    for roommate in roommates:
        Notification.objects.create(
            user=roommate.user,
            title="Room Cleaning Already Requested!",
            message=(
                f"Your roommate {requester_name} has already raised a room cleaning request "
                f"for {room_display} (Request #{cleaning_request.id} · Status: {cleaning_request.get_status_display()}). "
                f"You cannot create another request until this existing request is completed."
            ),
            notification_type="room_request",
            related_request=cleaning_request,
        )


def notify_roommates_request_status_update(cleaning_request, action_text="updated"):
    """
    Notifies all roommates when the room cleaning status changes
    (e.g. In Progress, Completed, Cancelled, Rejected).
    """
    if not cleaning_request.room:
        return

    room = cleaning_request.room
    room_display = f"{room.block} – Room {room.room_number}"

    roommates = StudentProfile.objects.filter(
        allocations__room=room,
        allocations__is_current=True,
    ).distinct()

    title = f"Room Cleaning {cleaning_request.get_status_display()}"
    status_msg = (
        f"The room cleaning request for {room_display} (Request #{cleaning_request.id}) "
        f"is now {cleaning_request.get_status_display()}."
    )

    if cleaning_request.status == "completed":
        status_msg += " Your room has been cleaned. Please verify and confirm the cleaning."
    elif cleaning_request.status in ("cancelled", "rejected"):
        status_msg += " You can now submit a new room cleaning request if needed."

    for roommate in roommates:
        Notification.objects.create(
            user=roommate.user,
            title=title,
            message=status_msg,
            notification_type="status_update",
            related_request=cleaning_request,
        )
