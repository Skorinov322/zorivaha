"""
Management command: send_test_email

Sends a test email to verify SMTP configuration.

Usage:
    python manage.py send_test_email --to admin@example.com
    python manage.py send_test_email --to admin@example.com --type booking_created
    python manage.py send_test_email --to admin@example.com --booking ZV-XXXXXXXX

Email types:
    booking_created        — бронь создана
    booking_confirmed      — бронь подтверждена
    booking_cancelled      — бронь отменена вручную
    booking_auto_cancelled — автоматическая отмена
    checkin_reminder       — напоминание о заезде
    no_show                — незаезд
    plain                  — простое тестовое письмо (без брони)
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = "Send a test email to verify SMTP configuration"

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            required=True,
            help="Recipient email address",
        )
        parser.add_argument(
            "--type",
            default="plain",
            choices=[
                "plain",
                "booking_created",
                "booking_confirmed",
                "booking_cancelled",
                "booking_auto_cancelled",
                "checkin_reminder",
                "no_show",
            ],
            help="Email template type to test (default: plain)",
        )
        parser.add_argument(
            "--booking",
            default=None,
            help="Confirmation number of an existing booking (e.g. ZV-ABCD1234)",
        )

    def handle(self, *args, **options):
        to_email   = options["to"]
        email_type = options["type"]
        booking_cn = options["booking"]

        self.stdout.write(f"\n📧 Sending test email ({email_type}) → {to_email}")
        self.stdout.write(f"   SMTP host : {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
        self.stdout.write(f"   From      : {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"   TLS       : {settings.EMAIL_USE_TLS}")
        self.stdout.write("")

        if email_type == "plain":
            self._send_plain(to_email)
        else:
            booking = self._get_booking(booking_cn)
            self._send_template(email_type, to_email, booking)

    # ----------------------------------------------------------------

    def _send_plain(self, to_email: str):
        """Send a simple plain-text email — no templates, no DB."""
        try:
            send_mail(
                subject="[Зори Ваха] Тестовое письмо — SMTP работает",
                message=(
                    "Это тестовое письмо от системы управления гостиницей «Зори Ваха».\n\n"
                    "Если вы получили это письмо — SMTP настроен корректно.\n\n"
                    f"Хост: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}\n"
                    f"От: {settings.DEFAULT_FROM_EMAIL}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Plain email sent to {to_email}"))
        except Exception as exc:
            raise CommandError(f"❌ Failed to send email: {exc}") from exc

    def _get_booking(self, confirmation_number: str):
        """Load a booking by confirmation number, or create a fake one."""
        from apps.bookings.models import Booking

        if confirmation_number:
            try:
                booking = Booking.objects.select_related(
                    "guest", "room_category"
                ).get(confirmation_number=confirmation_number)
                self.stdout.write(f"   Booking   : {booking.confirmation_number}")
                return booking
            except Booking.DoesNotExist:
                raise CommandError(
                    f"Booking with confirmation number '{confirmation_number}' not found."
                )

        # No booking specified — use the most recent one
        booking = (
            Booking.objects.select_related("guest", "room_category")
            .order_by("-created_at")
            .first()
        )
        if not booking:
            raise CommandError(
                "No bookings found in the database. "
                "Create a booking first or use --booking to specify one."
            )
        self.stdout.write(f"   Booking   : {booking.confirmation_number} (most recent)")
        return booking

    def _send_template(self, email_type: str, to_email: str, booking):
        """Render and send a template email synchronously (no Celery)."""
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags

        template_map = {
            "booking_created":        "notifications/email/booking_created.html",
            "booking_confirmed":      "notifications/email/booking_confirmation.html",
            "booking_cancelled":      "notifications/email/booking_cancelled.html",
            "booking_auto_cancelled": "notifications/email/booking_auto_cancelled.html",
            "checkin_reminder":       "notifications/email/checkin_reminder.html",
            "no_show":                "notifications/email/no_show.html",
        }
        subject_map = {
            "booking_created":        f"[TEST] Заявка #{booking.confirmation_number} принята",
            "booking_confirmed":      f"[TEST] Бронь #{booking.confirmation_number} подтверждена",
            "booking_cancelled":      f"[TEST] Бронь #{booking.confirmation_number} отменена",
            "booking_auto_cancelled": f"[TEST] Бронь #{booking.confirmation_number} автоматически отменена",
            "checkin_reminder":       f"[TEST] Напоминание о заезде — {booking.confirmation_number}",
            "no_show":                f"[TEST] Незаезд — {booking.confirmation_number}",
        }

        template = template_map[email_type]
        subject  = subject_map[email_type]
        context  = {
            "booking": booking,
            "CONTACT_PHONE": settings.CONTACT_PHONE,
            "CONTACT_PHONE_SECOND": settings.CONTACT_PHONE_SECOND,
            "CONTACT_EMAIL": settings.CONTACT_EMAIL,
        }

        try:
            html_content = render_to_string(template, context)
            text_content = strip_tags(html_content)

            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to_email],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            self.stdout.write(self.style.SUCCESS(
                f"✅ Template email '{email_type}' sent to {to_email}"
            ))
            self.stdout.write(f"   Template  : {template}")
            self.stdout.write(f"   Subject   : {subject}")

        except Exception as exc:
            raise CommandError(f"❌ Failed to send email: {exc}") from exc
