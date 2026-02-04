import base64
import email
from email.mime.text import MIMEText
from typing import List, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
import logging
import re

from .models import Email
from .auth import get_user_credentials

logger = logging.getLogger(__name__)

class GmailService:
    def __init__(self, credentials: Credentials):
        self.service = build("gmail", "v1", credentials=credentials)
    
    def _decode_body(self, payload) -> str:
        """Decode email body from payload."""
        body = ""
        
        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
        elif "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                if mime_type == "text/plain" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                    break
                elif mime_type == "text/html" and part.get("body", {}).get("data") and not body:
                    html_body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                    body = re.sub(r'<[^>]+>', '', html_body)
                elif "parts" in part:
                    body = self._decode_body(part)
                    if body:
                        break
        
        return body.strip()
    
    def _parse_sender(self, from_header: str) -> tuple:
        """Parse sender name and email from From header."""
        match = re.match(r'^"?([^"<]*)"?\s*<?([^>]*)>?$', from_header)
        if match:
            name = match.group(1).strip().strip('"')
            email_addr = match.group(2).strip() or from_header
            return name or email_addr, email_addr
        return from_header, from_header
    
    def get_emails(self, max_results: int = 5, query: str = None) -> List[Email]:
        """Fetch emails from Gmail inbox."""
        try:
            logger.info(f"Fetching {max_results} emails from Gmail")
            
            # List messages
            list_params = {
                "userId": "me",
                "maxResults": max_results,
                "labelIds": ["INBOX"]
            }
            if query:
                list_params["q"] = query
            
            results = self.service.users().messages().list(**list_params).execute()
            messages = results.get("messages", [])
            
            emails = []
            for msg in messages:
                try:
                    message = self.service.users().messages().get(
                        userId="me",
                        id=msg["id"],
                        format="full"
                    ).execute()
                    
                    headers = message.get("payload", {}).get("headers", [])
                    header_dict = {h["name"].lower(): h["value"] for h in headers}
                    
                    sender_name, sender_email = self._parse_sender(header_dict.get("from", "Unknown"))
                    
                    body = self._decode_body(message.get("payload", {}))
                    
                    email_obj = Email(
                        id=message["id"],
                        thread_id=message.get("threadId", ""),
                        sender=sender_name,
                        sender_email=sender_email,
                        subject=header_dict.get("subject", "(No Subject)"),
                        snippet=message.get("snippet", ""),
                        body=body[:5000],  # Limit body size
                        date=header_dict.get("date", "")
                    )
                    emails.append(email_obj)
                    
                except Exception as e:
                    logger.error(f"Error parsing email {msg['id']}: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(emails)} emails")
            return emails
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            if e.resp.status == 401:
                raise Exception("Gmail authentication expired. Please log in again.")
            elif e.resp.status == 403:
                raise Exception("Gmail permissions revoked. Please re-authorize the app.")
            raise Exception(f"Failed to fetch emails: {str(e)}")
    
    def send_email(self, to: str, subject: str, body: str, thread_id: str = None, reply_to_message_id: str = None) -> dict:
        """Send an email or reply to a thread."""
        try:
            logger.info(f"Sending email to {to}")
            
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject
            
            if reply_to_message_id:
                # Get original message headers for proper threading
                original = self.service.users().messages().get(
                    userId="me",
                    id=reply_to_message_id,
                    format="metadata",
                    metadataHeaders=["Message-ID", "References"]
                ).execute()
                
                headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
                if "Message-ID" in headers:
                    message["In-Reply-To"] = headers["Message-ID"]
                    message["References"] = headers.get("References", "") + " " + headers["Message-ID"]
            
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            send_params = {
                "userId": "me",
                "body": {"raw": raw}
            }
            if thread_id:
                send_params["body"]["threadId"] = thread_id
            
            result = self.service.users().messages().send(**send_params).execute()
            logger.info(f"Email sent successfully, ID: {result['id']}")
            
            return {"success": True, "message_id": result["id"]}
            
        except HttpError as e:
            logger.error(f"Failed to send email: {e}")
            raise Exception(f"Failed to send email: {str(e)}")
    
    def delete_email(self, email_id: str) -> dict:
        """Delete an email (move to trash)."""
        try:
            logger.info(f"Deleting email {email_id}")
            
            self.service.users().messages().trash(
                userId="me",
                id=email_id
            ).execute()
            
            logger.info(f"Email {email_id} moved to trash")
            return {"success": True, "message": "Email moved to trash"}
            
        except HttpError as e:
            logger.error(f"Failed to delete email: {e}")
            if e.resp.status == 404:
                raise Exception("Email not found. It may have already been deleted.")
            raise Exception(f"Failed to delete email: {str(e)}")
    
    def get_email_by_id(self, email_id: str) -> Optional[Email]:
        """Get a single email by ID."""
        try:
            message = self.service.users().messages().get(
                userId="me",
                id=email_id,
                format="full"
            ).execute()
            
            headers = message.get("payload", {}).get("headers", [])
            header_dict = {h["name"].lower(): h["value"] for h in headers}
            
            sender_name, sender_email = self._parse_sender(header_dict.get("from", "Unknown"))
            body = self._decode_body(message.get("payload", {}))
            
            return Email(
                id=message["id"],
                thread_id=message.get("threadId", ""),
                sender=sender_name,
                sender_email=sender_email,
                subject=header_dict.get("subject", "(No Subject)"),
                snippet=message.get("snippet", ""),
                body=body[:5000],
                date=header_dict.get("date", "")
            )
        except HttpError as e:
            logger.error(f"Failed to get email {email_id}: {e}")
            return None


def get_gmail_service(user_email: str) -> GmailService:
    """Get Gmail service for a user."""
    credentials = get_user_credentials(user_email)
    if not credentials:
        raise Exception("No valid credentials found. Please log in again.")
    return GmailService(credentials)
