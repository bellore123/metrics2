from django.test import TestCase

# Create your tests here.
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cleaning.models import CleaningRequest

from .models import HostelAllocation, StudentProfile


class StudentFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="student.ck2026@vitstudent.ac.in",
            name="Test Student",
            password="test-password",
            role="student",
        )
        self.client.force_login(self.user)

    def test_first_login_redirects_to_hostel_setup(self):
        response = self.client.get(reverse("student_home"))

        self.assertRedirects(
            response,
            reverse("student_hostel_setup"),
        )
        self.assertTrue(
            StudentProfile.objects.filter(user=self.user).exists()
        )

    def test_hostel_setup_then_home_page(self):
        response = self.client.post(
            reverse("student_hostel_setup"),
            {
                "block": "MH Q",
                "room_number": "412",
                "academic_year": "2026-2027",
            },
            follow=True,
        )

        self.assertContains(response, "MH Q")
        self.assertContains(response, "412")
        self.assertTemplateUsed(response, "students/home.html")

    def test_create_and_view_cleaning_request(self):
        student = StudentProfile.objects.create(user=self.user)
        allocation = HostelAllocation.objects.create(
            student=student,
            block="MH Q",
            room_number="412",
            academic_year="2026-2027",
        )
        cleaning_date = date.today() + timedelta(days=1)

        response = self.client.post(
            reverse("create_cleaning_request"),
            {
                "cleaning_date": cleaning_date.isoformat(),
                "time_slot": "09:00-10:00",
                "cleaning_type": "full",
                "remarks": "Please clean the bathroom too.",
            },
            follow=True,
        )

        cleaning_request = CleaningRequest.objects.get()
        self.assertEqual(cleaning_request.student, student)
        self.assertEqual(cleaning_request.hostel_allocation, allocation)
        self.assertEqual(cleaning_request.status, "pending")
        self.assertContains(response, "Full Cleaning")
        self.assertIn(self.user.email, str(cleaning_request))

    def test_only_one_allocation_remains_current(self):
        student = StudentProfile.objects.create(user=self.user)
        old_allocation = HostelAllocation.objects.create(
            student=student,
            block="MH N",
            room_number="210",
            academic_year="2025-2026",
        )
        HostelAllocation.objects.create(
            student=student,
            block="MH Q",
            room_number="412",
            academic_year="2026-2027",
        )

        old_allocation.refresh_from_db()
        self.assertFalse(old_allocation.is_current)
        self.assertEqual(
            student.allocations.filter(is_current=True).count(),
            1,
        )
