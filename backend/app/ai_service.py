from groq import Groq
from typing import List, Optional, Tuple
import logging
import json
import re

from .config import settings
from .models import Email, ChatMessage

logger = logging.getLogger(__name__)

client = Groq(api_key=settings.groq_api_key)

SYSTEM_PROMPT = """You are an intelligent email assistant. You help users manage their Gmail inbox through natural conversation.

You can:
1. **Read emails**: Show the user their recent emails with AI-generated summaries
2. **Reply to emails**: Generate professional, context-aware replies
3. **Delete emails**: Help users delete specific emails by sender, subject, or reference number

When the user asks to perform an action, respond with a JSON action block that the system will execute.

Available actions and their JSON format:
- Read emails: {"action": "read_emails", "count": 5, "query": "optional search query"}
- Generate reply: {"action": "generate_reply", "email_index": 1, "custom_instruction": "optional user instruction"}
- Send reply: {"action": "send_reply", "email_index": 1, "reply_text": "the reply content"}
- Delete email: {"action": "delete_email", "email_index": 1} OR {"action": "delete_email", "by_sender": "sender@email.com"} OR {"action": "delete_email", "by_subject": "keyword"}
- Confirm action: {"action": "confirm", "confirmed": true/false, "pending_action": "the action being confirmed"}

IMPORTANT RULES:
1. For deletion, ALWAYS ask for confirmation first. Only include the actual delete action after user confirms.
2. When referencing emails, use 1-based indexing (Email 1, Email 2, etc.)
3. If the user's intent is unclear, ask for clarification.
4. Be conversational and helpful, not robotic.
5. When generating replies, match the tone of the original email.

If no action is needed (general chat), just respond naturally without a JSON block.
"""

def parse_action_from_response(response: str) -> Tuple[str, Optional[dict]]:
    """Extract action JSON from AI response if present."""
    # Look for JSON block in response
    json_pattern = r'\{[^{}]*"action"[^{}]*\}'
    matches = re.findall(json_pattern, response, re.DOTALL)
    
    if matches:
        try:
            action_data = json.loads(matches[-1])  # Take the last JSON block
            # Remove JSON from display message
            clean_message = re.sub(json_pattern, '', response).strip()
            return clean_message, action_data
        except json.JSONDecodeError:
            pass
    
    return response, None


async def process_chat_message(
    user_message: str,
    user_name: str,
    conversation_history: List[ChatMessage],
    emails_context: List[Email] = None,
    pending_action: dict = None
) -> Tuple[str, Optional[dict]]:
    """Process a chat message and return response with optional action."""
    
    try:
        # Build messages for OpenAI
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add context about available emails if any
        if emails_context:
            email_context_str = "Current emails in context:\n"
            for i, email in enumerate(emails_context, 1):
                email_context_str += f"\nEmail {i}:\n"
                email_context_str += f"  From: {email.sender} <{email.sender_email}>\n"
                email_context_str += f"  Subject: {email.subject}\n"
                email_context_str += f"  Date: {email.date}\n"
                if email.summary:
                    email_context_str += f"  Summary: {email.summary}\n"
            messages.append({"role": "system", "content": email_context_str})
        
        # Add pending action context
        if pending_action:
            messages.append({
                "role": "system", 
                "content": f"PENDING ACTION AWAITING CONFIRMATION: {json.dumps(pending_action)}\nIf user confirms, proceed. If user denies, cancel."
            })
        
        # Add conversation history
        for msg in conversation_history[-10:]:  # Keep last 10 messages for context
            messages.append({"role": msg.role, "content": msg.content})
        
        # Add current user message
        messages.append({"role": "user", "content": f"User ({user_name}): {user_message}"})
        
        logger.info(f"Sending chat request to Groq")
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        ai_response = response.choices[0].message.content
        logger.info(f"Received AI response")
        
        # Parse for actions
        clean_message, action = parse_action_from_response(ai_response)
        
        return clean_message or ai_response, action
        
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        raise Exception(f"Failed to process message: {str(e)}")


async def summarize_email(email: Email) -> str:
    """Generate a concise summary of an email."""
    try:
        prompt = f"""Summarize this email in 1-2 sentences. Be concise and capture the key point.

From: {email.sender} <{email.sender_email}>
Subject: {email.subject}
Content: {email.body[:2000]}

Summary:"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Failed to summarize email: {e}")
        return email.snippet[:200] + "..." if len(email.snippet) > 200 else email.snippet


async def generate_email_reply(email: Email, custom_instruction: str = None) -> str:
    """Generate a professional reply to an email."""
    try:
        instruction = custom_instruction or "Write a professional and helpful reply."
        
        prompt = f"""Generate a reply to this email. {instruction}

Original Email:
From: {email.sender} <{email.sender_email}>
Subject: {email.subject}
Content: {email.body[:3000]}

Requirements:
- Be professional and courteous
- Address the main points of the email
- Keep it concise but complete
- Match the tone of the original (formal/casual)
- Do not include subject line, just the body

Reply:"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Failed to generate reply: {e}")
        raise Exception("Failed to generate reply. Please try again.")


async def categorize_emails(emails: List[Email]) -> dict:
    """Categorize emails into groups (bonus feature)."""
    try:
        email_summaries = []
        for i, email in enumerate(emails, 1):
            email_summaries.append(f"{i}. From: {email.sender}, Subject: {email.subject}")
        
        prompt = f"""Categorize these emails into groups: Work, Personal, Promotions, Urgent, Other.

Emails:
{chr(10).join(email_summaries)}

Return a JSON object with category names as keys and arrays of email numbers as values.
Example: {{"Work": [1, 3], "Promotions": [2], "Personal": [4, 5]}}

Categories:"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )
        
        result = response.choices[0].message.content.strip()
        # Extract JSON from response
        json_match = re.search(r'\{[^{}]+\}', result)
        if json_match:
            return json.loads(json_match.group())
        return {}
        
    except Exception as e:
        logger.error(f"Failed to categorize emails: {e}")
        return {}


async def generate_daily_digest(emails: List[Email]) -> str:
    """Generate a daily digest summary of emails (bonus feature)."""
    try:
        email_info = []
        for email in emails:
            email_info.append(f"- From: {email.sender}\n  Subject: {email.subject}\n  Preview: {email.snippet[:100]}")
        
        prompt = f"""Create a concise daily email digest from these emails. Include:
1. A brief overview of email activity
2. Key emails that need attention
3. Suggested actions or follow-ups

Emails:
{chr(10).join(email_info)}

Daily Digest:"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=600
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Failed to generate digest: {e}")
        raise Exception("Failed to generate daily digest. Please try again.")
