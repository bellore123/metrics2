from django.test import TestCase

# Create your tests here.
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cleaners.models import CleanerProfile
from students.models import HostelAllocation, StudentProfile
from wardens.models import WardenProfile

from .models import CleaningRequest, Feedback


class CleaningWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.student_user = User.objects.create_user(
            email="workflow.ck2026@vitstudent.ac.in",
            name="Arun Student",
            password="test-password",
            role="student",
        )
        self.student = StudentProfile.objects.create(user=self.student_user)
        self.allocation = HostelAllocation.objects.create(
            student=self.student,
            block="MH Q",
            room_number="412",
            academic_year="2026-2027",
        )
        self.warden_user = User.objects.create_user(
            email="qwarden@vit.ac.in",
            name="Q Block Warden",
            password="test-password",
            role="warden",
        )
        self.warden = WardenProfile.objects.create(
            user=self.warden_user,
            employee_id="W001",
            assigned_block="MH Q",
        )
        self.cleaner_user = User.objects.create_user(
            email="cleaner@example.com",
            name="Kumar Cleaner",
            password="test-password",
            role="cleaner",
        )
        self.cleaner = CleanerProfile.objects.create(
            user=self.cleaner_user,
            employee_id="C001",
            assigned_block="MH Q",
        )
        self.cleaning_request = CleaningRequest.objects.create(
            student=self.student,
            hostel_allocation=self.allocation,
            cleaning_date=date.today() + timedelta(days=1),
            time_slot="09:00-10:00",
            cleaning_type="full",
        )

    def test_warden_assigns_cleaner(self):
        self.client.force_login(self.warden_user)
        response = self.client.post(
            reverse("assign_cleaner", args=[self.cleaning_request.id]),
            {"cleaner": self.cleaner.id},
            follow=True,
        )
        self.cleaning_request.refresh_from_db()
        self.assertEqual(self.cleaning_request.status, "assigned")
        self.assertEqual(self.cleaning_request.assigned_cleaner, self.cleaner)
        self.assertContains(response, "Kumar Cleaner")

    def test_cleaner_completes_and_student_confirms(self):
        self.cleaning_request.assigned_cleaner = self.cleaner
        self.cleaning_request.assigned_by = self.warden
        self.cleaning_request.status = "assigned"
        self.cleaning_request.save()

        self.client.force_login(self.cleaner_user)
        self.client.post(
            reverse("start_request", args=[self.cleaning_request.id])
        )
        self.client.post(
            reverse("complete_request", args=[self.cleaning_request.id])
        )

        self.client.force_login(self.student_user)
        response = self.client.post(
            reverse("submit_feedback", args=[self.cleaning_request.id]),
            {
                "room_status": "cleaned",
                "rating": "5",
                "comments": "Excellent work.",
            },
            follow=True,
        )
        self.cleaning_request.refresh_from_db()
        self.assertEqual(self.cleaning_request.status, "confirmed")
        self.assertEqual(
            Feedback.objects.get(
                cleaning_request=self.cleaning_request
            ).rating,
            5,
        )
        self.assertContains(response, "Confirmed by Student")
