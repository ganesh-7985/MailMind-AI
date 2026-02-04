from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
import logging
from datetime import datetime
from typing import List, Optional

from .config import settings
from .models import (
    TokenResponse, UserInfo, ChatRequest, ChatResponse, 
    SendEmailRequest, DeleteEmailRequest, Email, ChatMessage
)
from .auth import (
    create_oauth_flow, create_jwt_token, get_current_user,
    store_user_credentials, get_user_credentials, remove_user_credentials,
    get_user_info
)
from .gmail_service import get_gmail_service, GmailService
from .ai_service import (
    process_chat_message, summarize_email, generate_email_reply,
    categorize_emails, generate_daily_digest
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MailMind AI API",
    description="AI-powered email assistant with Gmail integration",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://*.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for email context per user session
user_email_context = {}
user_pending_actions = {}


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "MailMind AI API", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.environment
    }


# ============== Authentication Routes ==============

@app.get("/auth/login")
async def login():
    """Initiate Google OAuth login flow."""
    try:
        logger.info("Initiating OAuth login flow")
        flow = create_oauth_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        logger.info(f"Generated auth URL, redirecting...")
        return {"auth_url": authorization_url}
    except Exception as e:
        logger.error(f"Login initiation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate login. Please try again."
        )


@app.get("/auth/callback")
async def auth_callback(code: str = None, error: str = None):
    """Handle OAuth callback from Google."""
    if error:
        logger.error(f"OAuth error: {error}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error={error}"
        )
    
    if not code:
        logger.error("No authorization code received")
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=no_code"
        )
    
    try:
        logger.info("Processing OAuth callback")
        flow = create_oauth_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get user info
        user_info = get_user_info(credentials)
        user_email = user_info["email"]
        user_name = user_info["name"]
        picture = user_info.get("picture", "")
        
        # Store credentials
        store_user_credentials(user_email, credentials)
        
        # Create JWT token
        token = create_jwt_token(user_email, user_name, picture)
        
        logger.info(f"User {user_email} authenticated successfully")
        
        # Redirect to frontend with token
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/success?token={token}&name={user_name}&email={user_email}&picture={picture}"
        )
        
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=auth_failed"
        )


@app.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    return UserInfo(
        email=current_user["email"],
        name=current_user["name"],
        picture=current_user.get("picture")
    )


@app.post("/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Log out user and clear session."""
    try:
        user_email = current_user["email"]
        remove_user_credentials(user_email)
        
        # Clear user context
        if user_email in user_email_context:
            del user_email_context[user_email]
        if user_email in user_pending_actions:
            del user_pending_actions[user_email]
        
        logger.info(f"User {user_email} logged out")
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


# ============== Email Routes ==============

@app.get("/emails", response_model=List[Email])
async def get_emails(
    count: int = 5,
    query: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Fetch emails from user's Gmail inbox."""
    try:
        logger.info(f"Fetching {count} emails for {current_user['email']}")
        gmail = get_gmail_service(current_user["email"])
        emails = gmail.get_emails(max_results=min(count, 20), query=query)
        
        # Generate summaries for each email
        for email in emails:
            email.summary = await summarize_email(email)
        
        # Store in context for reference
        user_email_context[current_user["email"]] = emails
        
        return emails
        
    except Exception as e:
        logger.error(f"Failed to fetch emails: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/emails/{email_id}")
async def get_email(
    email_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific email by ID."""
    try:
        gmail = get_gmail_service(current_user["email"])
        email = gmail.get_email_by_id(email_id)
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        return email
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/emails/send")
async def send_email(
    request: SendEmailRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send an email or reply."""
    try:
        logger.info(f"Sending email from {current_user['email']} to {request.to}")
        gmail = get_gmail_service(current_user["email"])
        result = gmail.send_email(
            to=request.to,
            subject=request.subject,
            body=request.body,
            thread_id=request.thread_id,
            reply_to_message_id=request.message_id
        )
        return result
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.delete("/emails/{email_id}")
async def delete_email(
    email_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an email (move to trash)."""
    try:
        logger.info(f"Deleting email {email_id} for {current_user['email']}")
        gmail = get_gmail_service(current_user["email"])
        result = gmail.delete_email(email_id)
        
        # Update context
        if current_user["email"] in user_email_context:
            user_email_context[current_user["email"]] = [
                e for e in user_email_context[current_user["email"]]
                if e.id != email_id
            ]
        
        return result
    except Exception as e:
        logger.error(f"Failed to delete email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/emails/{email_id}/generate-reply")
async def generate_reply(
    email_id: str,
    custom_instruction: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Generate an AI reply for an email."""
    try:
        gmail = get_gmail_service(current_user["email"])
        email = gmail.get_email_by_id(email_id)
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        reply = await generate_email_reply(email, custom_instruction)
        return {"reply": reply, "email": email}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate reply: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============== Chat Routes ==============

@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """Process a chat message and execute email actions."""
    try:
        user_email = current_user["email"]
        user_name = current_user["name"]
        
        logger.info(f"Processing chat message from {user_email}")
        
        # Get email context if available
        emails_context = user_email_context.get(user_email, [])
        pending_action = user_pending_actions.get(user_email)
        
        # Process with AI
        response_message, action = await process_chat_message(
            user_message=request.message,
            user_name=user_name,
            conversation_history=request.conversation_history,
            emails_context=emails_context,
            pending_action=pending_action
        )
        
        result_data = None
        
        # Execute action if present
        if action:
            action_type = action.get("action")
            logger.info(f"Executing action: {action_type}")
            
            try:
                if action_type == "read_emails":
                    count = action.get("count", 5)
                    query = action.get("query")
                    gmail = get_gmail_service(user_email)
                    emails = gmail.get_emails(max_results=min(count, 20), query=query)
                    
                    for email in emails:
                        email.summary = await summarize_email(email)
                    
                    user_email_context[user_email] = emails
                    result_data = {"emails": [e.model_dump() for e in emails]}
                    
                elif action_type == "generate_reply":
                    email_index = action.get("email_index", 1) - 1
                    if emails_context and 0 <= email_index < len(emails_context):
                        target_email = emails_context[email_index]
                        custom_instruction = action.get("custom_instruction")
                        reply = await generate_email_reply(target_email, custom_instruction)
                        target_email.suggested_reply = reply
                        result_data = {
                            "email": target_email.model_dump(),
                            "suggested_reply": reply
                        }
                    else:
                        response_message += "\n\nI couldn't find that email. Please fetch emails first with 'show my emails'."
                
                elif action_type == "delete_email":
                    # Check if this needs confirmation
                    if not pending_action or pending_action.get("action") != "delete_email":
                        # Store as pending action
                        user_pending_actions[user_email] = action
                        response_message = "Are you sure you want to delete this email? Reply 'yes' to confirm or 'no' to cancel."
                    else:
                        # Already confirmed, execute
                        email_index = action.get("email_index")
                        if email_index and emails_context:
                            idx = email_index - 1
                            if 0 <= idx < len(emails_context):
                                target_email = emails_context[idx]
                                gmail = get_gmail_service(user_email)
                                gmail.delete_email(target_email.id)
                                user_email_context[user_email] = [
                                    e for e in emails_context if e.id != target_email.id
                                ]
                                result_data = {"deleted": True, "email_id": target_email.id}
                                response_message = f"✅ Email from {target_email.sender} has been moved to trash."
                        
                        # Clear pending action
                        user_pending_actions.pop(user_email, None)
                
                elif action_type == "send_reply":
                    email_index = action.get("email_index", 1) - 1
                    reply_text = action.get("reply_text")
                    if emails_context and 0 <= email_index < len(emails_context) and reply_text:
                        target_email = emails_context[email_index]
                        gmail = get_gmail_service(user_email)
                        result = gmail.send_email(
                            to=target_email.sender_email,
                            subject=f"Re: {target_email.subject}",
                            body=reply_text,
                            thread_id=target_email.thread_id,
                            reply_to_message_id=target_email.id
                        )
                        result_data = {"sent": True, "message_id": result.get("message_id")}
                        response_message = f"✅ Reply sent to {target_email.sender}!"
                    else:
                        response_message += "\n\nI couldn't send the reply. Please make sure the email exists and the reply is provided."
                
                elif action_type == "confirm":
                    confirmed = action.get("confirmed", False)
                    if confirmed and pending_action:
                        # Re-execute the pending action
                        pending_type = pending_action.get("action")
                        if pending_type == "delete_email":
                            email_index = pending_action.get("email_index")
                            if email_index and emails_context:
                                idx = email_index - 1
                                if 0 <= idx < len(emails_context):
                                    target_email = emails_context[idx]
                                    gmail = get_gmail_service(user_email)
                                    gmail.delete_email(target_email.id)
                                    user_email_context[user_email] = [
                                        e for e in emails_context if e.id != target_email.id
                                    ]
                                    result_data = {"deleted": True, "email_id": target_email.id}
                                    response_message = f"✅ Email from {target_email.sender} has been deleted."
                    
                    # Clear pending action regardless
                    user_pending_actions.pop(user_email, None)
                    
            except Exception as action_error:
                logger.error(f"Action execution failed: {action_error}")
                response_message += f"\n\n⚠️ Action failed: {str(action_error)}"
        
        return ChatResponse(
            message=response_message,
            action=action.get("action") if action else None,
            data=result_data
        )
        
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/chat/digest")
async def get_digest(current_user: dict = Depends(get_current_user)):
    """Generate a daily digest of emails."""
    try:
        user_email = current_user["email"]
        gmail = get_gmail_service(user_email)
        emails = gmail.get_emails(max_results=20)
        
        digest = await generate_daily_digest(emails)
        categories = await categorize_emails(emails)
        
        return {
            "digest": digest,
            "categories": categories,
            "email_count": len(emails)
        }
    except Exception as e:
        logger.error(f"Failed to generate digest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/chat/categorize")
async def categorize(current_user: dict = Depends(get_current_user)):
    """Categorize emails in inbox."""
    try:
        user_email = current_user["email"]
        gmail = get_gmail_service(user_email)
        emails = gmail.get_emails(max_results=20)
        
        for email in emails:
            email.summary = await summarize_email(email)
        
        categories = await categorize_emails(emails)
        user_email_context[user_email] = emails
        
        return {
            "emails": [e.model_dump() for e in emails],
            "categories": categories
        }
    except Exception as e:
        logger.error(f"Failed to categorize emails: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
