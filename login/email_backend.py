import requests

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):
    api_url = "https://api.resend.com/emails"

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, "RESEND_API_KEY", "")
        if not api_key:
            raise ImproperlyConfigured("Configure RESEND_API_KEY to send email.")

        sent_count = 0
        for message in email_messages:
            recipients = message.recipients()
            if not recipients:
                continue
            if message.attachments:
                raise NotImplementedError(
                    "The Resend email backend does not support attachments."
                )

            payload = {
                "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
                "to": recipients,
                "subject": message.subject,
                "text": message.body,
            }
            if message.cc:
                payload["cc"] = message.cc
            if message.bcc:
                payload["bcc"] = message.bcc
            if message.reply_to:
                payload["reply_to"] = message.reply_to
            for content, mimetype in getattr(message, "alternatives", []):
                if mimetype == "text/html":
                    payload["html"] = content

            try:
                response = requests.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10,
                )
                response.raise_for_status()
            except requests.RequestException:
                if not self.fail_silently:
                    raise
                continue

            sent_count += 1

        return sent_count
