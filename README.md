# MailMind AI

An AI-powered email assistant that lets you manage your Gmail inbox through natural conversation. Built with FastAPI and Next.js.

**Live Demo:** [https://shankar-ganesh.vercel.app](https://shankar-ganesh.vercel.app) *(update after deployment)*

---

## What it does

- **Chat with your inbox** - Ask questions like "show my recent emails" or "reply to the email from John"
- **AI summaries** - Get quick summaries of emails without reading the full content
- **Smart replies** - Generate context-aware replies and send them with one click
- **Delete emails** - Remove emails by sender, subject, or just say "delete email 2"
- **Daily digest** - Get a summary of what needs your attention

---

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Google Cloud project with OAuth credentials
- Groq API key (free tier works)

### 1. Clone and setup backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Setup frontend

```bash
cd frontend
npm install
```

### 3. Configure environment variables

**Backend** (`backend/.env`):
```
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
GROQ_API_KEY=your_groq_api_key
JWT_SECRET_KEY=generate_a_random_secret_key
FRONTEND_URL=http://localhost:3000
```

**Frontend** (`frontend/.env`):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use existing)
3. Enable **Gmail API**
4. Go to **Credentials** → Create **OAuth 2.0 Client ID**
5. Add authorized redirect URI: `http://localhost:8000/auth/callback`
6. For testing, go to **OAuth consent screen** → Add test users

> **For reviewers:** Add `testingcheckuser1234@gmail.com` as a test user in your OAuth consent screen.

### 5. Run

```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
python run.py

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, TailwindCSS |
| Backend | FastAPI, Python 3.11 |
| AI | Groq (Llama 3.3 70B) |
| Auth | Google OAuth 2.0, JWT |
| Email | Gmail API |

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## Deployment

### Frontend (Vercel)
1. Push to GitHub
2. Import in Vercel
3. Add environment variable: `NEXT_PUBLIC_API_URL=https://your-backend-url.com`

### Backend
Deploy to any Python hosting. Update:
- `GOOGLE_REDIRECT_URI` to your production callback URL
- `FRONTEND_URL` to your Vercel URL
- Add production URLs to Google OAuth authorized origins

---

## Known Limitations

- Session storage is in-memory (resets on backend restart)
- OAuth tokens aren't persisted to database
- Rate limits apply from Groq API (free tier)

---

## Built for

Constructure AI Technical Assessment
