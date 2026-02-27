# AI Ops Email Agent

An intelligent, AI-powered email automation agent that processes unread emails, classifies them by intent, and generates contextual replies with human-in-the-loop approval. Built with FastAPI, LangGraph, and Groq LLM.

## 📋 Overview

The AI Ops Email Agent automates routine email handling by:
- Reading and analyzing unread emails from Gmail
- Classifying emails into intent categories (support, sales, ops, spam, urgent)
- Making intelligent decisions on whether to auto-reply, ignore, or request human review
- Generating professional, personalized replies using AI
- Allowing human approval/rejection/editing before sending
- Automatically sending approved replies and marking emails as read

## 🎯 Key Features

- **Email Classification**: Uses Groq's Llama 3.1 model to classify emails with confidence scores
- **Intelligent Routing**: Routes emails based on intent and confidence thresholds
- **Human-in-the-Loop**: Interrupts workflow for human approval on uncertain or high-priority emails
- **Draft Editing**: Humans can review and edit AI-generated drafts before sending
- **Gmail Integration**: Direct integration with Google Gmail API for reading and sending emails
- **HTML Email Support**: Automatically cleans and extracts text from HTML emails
- **REST API**: Simple HTTP endpoints to trigger processing and approvals

## 🏗️ Architecture

The agent uses a **LangGraph state machine** with the following workflow:

```
Start
  ↓
[Fetch Email] → Extract unread email from Gmail
  ↓
[Classify Intent] → Analyze subject/body, determine category (support/sales/ops/spam/urgent)
  ↓
[Decide Action] → Route based on intent and confidence:
  ├─ High-confidence spam → Ignore
  ├─ Urgent or low-confidence → Human review
  └─ Legitimate categories → Auto-reply
  ↓
[Draft Reply] → Generate professional reply using AI
  ↓
[Route Decision] 
  ├─ Human review needed → [Human Approval] (interrupt for user input)
  └─ Auto-reply approved → [Send Reply]
  ↓
[Send Reply] → Send email via Gmail API & mark original as read
  ↓
[Log Result] → Log processing outcome
  ↓
End
```

### Workflow Nodes

| Node | Purpose |
|------|---------|
| **fetch_email** | Retrieves next unread email from Gmail |
| **classify_intent** | Uses Groq LLM to classify email intent |
| **decide_action** | Routes based on intent and confidence |
| **draft_reply** | Generates AI-powered reply |
| **human_approval** | Interrupts and waits for human approval |
| **send_reply** | Sends approved reply via Gmail |
| **log_result** | Logs the processing outcome |

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Gmail account with API access enabled
- Google OAuth 2.0 credentials
- Groq API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd "AI Ops Agent"
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   
   Create a `.env` file in the project root:
   ```env
   GROQ_API_KEY=your_groq_api_key
   GMAIL_REFRESH_TOKEN=your_gmail_refresh_token
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   GOOGLE_TOKEN_URI=https://oauth2.googleapis.com/token
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
   AUTO_SEND_EMAILS=false  # Set to 'true' to enable automatic sending
   ```

5. **Set up Gmail API credentials**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable Gmail API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download credentials as `client_secret.json` and place in project root

### Running the Application

**Development Server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

**Production (Docker):**
```bash
docker build -t ai-ops-agent .
docker run -p 8000:8000 --env-file .env ai-ops-agent
```

## 🔌 API Endpoints

### GET `/`
Health check endpoint.

**Response:**
```json
{
  "status": "running"
}
```

### POST `/run`
Start the email processing workflow.

**Response (Needs Approval):**
```json
{
  "status": "needs_approval",
  "data": {
    "email_id": "abc123",
    "thread_id": "thread123",
    "from": "sender@example.com",
    "subject": "Meeting Request",
    "draft_reply": "Thank you for reaching out...",
    "message": "Approve, edit, or reject this reply"
  }
}
```

**Response (Auto-Completed):**
```json
{
  "status": "completed",
  "result": {
    "email_id": "abc123",
    "action": "reply",
    "intent": "ops",
    ...
  }
}
```

### POST `/approve`
Approve or reject a pending email action.

**Parameters:**
- `approved` (boolean): Whether to approve the action
- `edited_reply` (string, optional): Modified reply text

**Request:**
```json
{
  "approved": true,
  "edited_reply": "Modified reply text if needed"
}
```

**Response:**
```json
{
  "status": "resumed",
  "result": {
    "email_id": "abc123",
    "action": "reply",
    ...
  }
}
```

### GET `/auth/login`
Initiates OAuth 2.0 authorization flow.

**Response:**
```json
{
  "auth": "https://accounts.google.com/o/oauth2/auth?..."
}
```

### GET `/auth/callback`
OAuth 2.0 callback endpoint.

**Parameters:**
- `code` (string): Authorization code from Google

**Response:**
```json
{
  "access_token": "...",
  "refresh_token": "..."
}
```

## 📊 Email Classification

The agent classifies emails into these categories:

| Category | Description |
|----------|-------------|
| **support** | Customer support inquiries |
| **sales** | Sales/partnership opportunities |
| **ops** | Operational/internal matters |
| **spam** | Unsolicited/irrelevant messages |
| **urgent** | Time-sensitive or high-priority |

Each classification includes:
- `intent`: The category
- `confidence`: Score from 0-1 indicating classification certainty
- `reason`: Explanation for the classification

## 🤖 Decision Making

The agent decides on actions based on:

```python
- High-confidence spam (≥0.7) → Ignore email
- Urgent or low-confidence (<0.6) → Request human review
- Support/Sales/Ops with good confidence → Auto-reply
- All other cases → Request human review (safety default)
```

## 📝 Email Processing

### Email Body Cleaning
- Removes scripts and styles from HTML emails
- Extracts plain text content
- Removes URLs and excessive whitespace
- Strips common boilerplate phrases (e.g., "View job", job alert templates)
- Hard limit: 800 characters

### Reply Generation
- Uses Groq's Llama 3.1 model with low temperature (0.2) for consistency
- Signed as "Meet Dabgar"
- Tone: Professional, concise, personalized
- Does not mention the sender is an Operations Assistant

## 🔑 Environment Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | Your Groq API key for LLM access |
| `GMAIL_REFRESH_TOKEN` | ✅ | Gmail OAuth refresh token |
| `GOOGLE_CLIENT_ID` | ✅ | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | ✅ | Google OAuth client secret |
| `GOOGLE_TOKEN_URI` | ✅ | Google token endpoint (usually standard) |
| `GOOGLE_REDIRECT_URI` | ❌ | OAuth callback URL (default: http://localhost:8000/auth/callback) |
| `AUTO_SEND_EMAILS` | ❌ | Set to "true" to enable automatic email sending (default: false) |

## 🐳 Docker Deployment

A `Dockerfile` is included for containerized deployment:

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📦 Dependencies

- **fastapi** - Web framework
- **uvicorn** - ASGI server
- **langgraph** - Workflow orchestration
- **groq** - LLM provider
- **google-api-python-client** - Gmail API client
- **google-auth-oauthlib** - OAuth authentication
- **beautifulsoup4** - HTML parsing
- **python-dotenv** - Environment configuration
- **email-validator** - Email validation

## 🔐 Security Considerations

- Store `client_secret.json` in `.gitignore` (already configured)
- Use environment variables for sensitive data (API keys, tokens)
- Set `AUTO_SEND_EMAILS=false` by default for safety
- Human review is default routing when confidence is low
- All email operations use authenticated Gmail API

## 🛠️ Development

### Project Structure
```
AI Ops Agent/
├── app/
│   ├── main.py              # FastAPI app initialization
│   └── api/
│       ├── routes.py        # API endpoint handlers
│       ├── state.py         # LangGraph workflow definition
│       └── helpers.py       # Gmail, LLM, and utility functions
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container configuration
├── .env                    # Environment variables (git-ignored)
├── client_secret.json      # Google OAuth credentials (git-ignored)
└── README.md              # This file
```

### Running Tests

Currently, manual testing is recommended using the API endpoints.

### Code Style

- Python 3.10+ syntax
- Type hints with `TypedDict` for state management
- Error handling for Gmail API failures
- Safety checks on draft replies before sending

## 🚨 Error Handling

- **No unread emails**: Raises `RuntimeError`
- **Missing approval context**: Returns error message
- **Gmail API failures**: Propagates Google API exceptions
- **LLM failures**: Handled by Groq client

## 📝 Logging

The agent logs processed emails with:
- Email ID
- Subject
- Detected intent
- Action taken

Format:
```
=== EMAIL PROCESSED ===
ID: <email_id>
Subject: <subject>
Intent: <intent>
Action: <action>
======================
```

## 🎓 Example Usage Flow

1. **Start Processing**: `POST /run`
   - Agent fetches unread email
   - Classifies intent and decides action
   - If needs approval, returns with `status: needs_approval`

2. **Human Review**: Check the returned draft reply and decide

3. **Approve/Modify**: `POST /approve`
   ```json
   {
     "approved": true,
     "edited_reply": "Optional custom reply"
   }
   ```

4. **Completion**: Email is sent and marked as read

5. **Repeat**: Call `/run` again for the next email

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 📞 Support

For issues or questions:
- Check the email processing logs
- Verify environment variables are set correctly
- Ensure Gmail API credentials have proper scopes:
  - `gmail.modify`
  - `gmail.send`
  - `gmail.readonly`

## 🔮 Future Enhancements

- Database persistence for email history
- Advanced email threading and conversation tracking
- Multi-user support with role-based access
- Custom classification models and rules
- Webhook support for real-time email notifications
- Dashboard UI for monitoring and management
- Batch email processing
- Integration with other email providers

---

**Built with ❤️ by Meet Dabgar**
