"""
Gmail API Client

Reads unread emails from a specific sender using the Gmail API with
a service account and domain-wide delegation.

Usage:
    client = GmailClient(credentials_path, delegate_email)
    emails = client.get_unread_emails("info@wexfordstables.co.nz")
    for email in emails:
        # process...
        client.mark_read(email["message_id"])
"""

import base64
import logging
from email.utils import parsedate_to_datetime
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Gmail API scopes needed
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailClient:
    """Reads and manages emails via Gmail API with service account delegation."""

    def __init__(self, credentials_path: str, delegate_email: str):
        """
        Args:
            credentials_path: Path to the service account JSON key file.
            delegate_email: The mailbox to access (e.g. info@wexfordstables.co.nz).
        """
        self.delegate_email = delegate_email
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=SCOPES,
            subject=delegate_email,  # Domain-wide delegation
        )
        self.service = build("gmail", "v1", credentials=self.credentials)
        logger.info(f"GmailClient initialized for {delegate_email}")

    def get_unread_emails(self, from_address: str, max_results: int = 10) -> list[dict]:
        """
        Fetch unread emails from a specific sender.

        Returns list of dicts with keys:
            message_id, thread_id, subject, from_address, date_received,
            body_text, body_html, has_attachments, attachment_ids
        """
        query = f"from:{from_address} is:unread"
        logger.info(f"Searching Gmail: {query}")

        try:
            results = self.service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_results,
            ).execute()
        except Exception as e:
            logger.error(f"Gmail list failed: {e}")
            raise

        messages = results.get("messages", [])
        if not messages:
            logger.info("No unread emails found")
            return []

        logger.info(f"Found {len(messages)} unread email(s)")

        emails = []
        for msg in messages:
            try:
                email_data = self._get_message(msg["id"])
                if email_data:
                    emails.append(email_data)
            except Exception as e:
                logger.warning(f"Failed to fetch message {msg['id']}: {e}")
                continue

        return emails

    def _get_message(self, message_id: str) -> Optional[dict]:
        """Fetch full message details by ID."""
        result = self.service.users().messages().get(
            userId="me",
            id=message_id,
            format="full",
        ).execute()

        headers = {}
        for header in result.get("payload", {}).get("headers", []):
            headers[header["name"].lower()] = header["value"]

        # Extract body
        body_text = ""
        body_html = ""
        attachment_ids = []

        payload = result.get("payload", {})
        parts = payload.get("parts", [])

        if parts:
            for part in parts:
                mime_type = part.get("mimeType", "")
                filename = part.get("filename", "")

                if filename:
                    # This is an attachment
                    body_attachment = part.get("body", {})
                    attachment_id = body_attachment.get("attachmentId")
                    if attachment_id:
                        attachment_ids.append({
                            "attachment_id": attachment_id,
                            "filename": filename,
                            "mime_type": mime_type,
                        })
                elif mime_type == "text/plain":
                    body_text = self._decode_body(part.get("body", {}))
                elif mime_type == "text/html":
                    body_html = self._decode_body(part.get("body", {}))
        else:
            # No parts — body is directly in payload
            body_data = payload.get("body", {}).get("data", "")
            if body_data:
                decoded = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
                body_html = decoded
                body_text = decoded

        # If we have HTML but no text, strip tags for text fallback
        if not body_text and body_html:
            import re
            body_text = re.sub(r"<[^>]*>", " ", body_html)
            body_text = re.sub(r"\s+", " ", body_text).strip()

        date_str = headers.get("date", "")
        try:
            date_received = parsedate_to_datetime(date_str)
        except Exception:
            from datetime import datetime, timezone
            date_received = datetime.now(timezone.utc)

        return {
            "message_id": result["id"],
            "thread_id": result.get("threadId", ""),
            "subject": headers.get("subject", "No Subject"),
            "from_address": headers.get("from", "Unknown"),
            "date_received": date_received,
            "body_text": body_text[:50000],
            "body_html": body_html[:100000],
            "has_attachments": len(attachment_ids) > 0,
            "attachment_ids": attachment_ids,
        }

    def _decode_body(self, body: dict) -> str:
        """Decode base64-encoded email body."""
        data = body.get("data", "")
        if not data:
            return ""
        try:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        except Exception:
            return ""

    def mark_read(self, message_id: str) -> bool:
        """Remove UNREAD label from a message."""
        try:
            self.service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            logger.info(f"Marked {message_id} as read")
            return True
        except Exception as e:
            logger.error(f"Failed to mark {message_id} as read: {e}")
            return False

    def download_attachment(self, message_id: str, attachment_id: str) -> Optional[bytes]:
        """Download an attachment by ID. Returns raw bytes."""
        try:
            attachment = self.service.users().messages().attachments().get(
                userId="me",
                messageId=message_id,
                id=attachment_id,
            ).execute()
            data = attachment.get("data", "")
            if data:
                return base64.urlsafe_b64decode(data)
            return None
        except Exception as e:
            logger.error(f"Failed to download attachment {attachment_id}: {e}")
            return None
