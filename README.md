# 🤖 AI Code Review Automation

An AI-powered GitHub App that automatically reviews pull requests using Google Gemini.

## Features

- **4 Specialized Review Agents:**
  - 🎨 **Style Agent** - Naming conventions, formatting, code organization
  - 🔒 **Security Agent** - Vulnerabilities, hardcoded secrets, injection risks
  - ⚡ **Performance Agent** - Complexity, memory issues, N+1 queries
  - 🧠 **Logic Agent** - Bugs, edge cases, error handling

- **BYO API Key** - Users provide their own Google Gemini API key
- **GitHub Marketplace Ready** - Install with one click
- **Configurable** - Enable/disable individual agents

## Quick Start - Local Testing

### 1. Install Dependencies

```bash
cd "AI Code Review Automation"
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Get a Gemini API Key

Get your free API key from [Google AI Studio](https://aistudio.google.com/apikey)

### 3. Run Local Test

```bash
# Set your API key
export GEMINI_API_KEY="your-api-key-here"

# Test on sample file with intentional issues
python test_local.py test_samples/sample_code.py

# Test on your own file
python test_local.py path/to/your/file.py

# Run only specific agent
python test_local.py --agent security path/to/file.py
```

## Project Structure

```
AI Code Review Automation/
├── api/                      # Vercel serverless functions
│   ├── webhook.py           # GitHub webhook handler
│   ├── install.py           # Installation callback
│   └── config.py            # User config API
├── agents/                   # AI Review Agents
│   ├── base.py              # Base agent class
│   ├── style_agent.py       # Style analysis
│   ├── security_agent.py    # Security analysis
│   ├── performance_agent.py # Performance analysis
│   └── logic_agent.py       # Logic/bug analysis
├── github/                   # GitHub integration
│   ├── client.py            # GitHub App client
│   └── webhook_handler.py   # Webhook parser
├── db/                       # Database
│   ├── schema.sql           # Supabase schema
│   └── client.py            # Database client
├── public/                   # Frontend
│   └── config.html          # Configuration UI
├── test_samples/             # Test files
│   └── sample_code.py       # Sample with issues
├── test_local.py            # Local test runner
├── requirements.txt
├── vercel.json
└── README.md
```

## Deployment

### Prerequisites

1. **Supabase Account** - [supabase.com](https://supabase.com) (free tier)
2. **Vercel Account** - [vercel.com](https://vercel.com) (free tier)
3. **GitHub App** - Create in GitHub Developer Settings

### Step 1: Set Up Supabase

1. Create a new Supabase project
2. Go to SQL Editor and run `db/schema.sql`
3. Copy your project URL and service key

### Step 2: Create GitHub App

1. Go to GitHub Settings → Developer Settings → GitHub Apps
2. Create New GitHub App with:
   - **Webhook URL**: `https://your-vercel-app.vercel.app/api/webhook`
   - **Permissions**:
     - Pull requests: Read & Write
     - Contents: Read
   - **Events**: Pull request
3. Generate and download private key
4. Note your App ID and generate a webhook secret

### Step 3: Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Login and deploy
vercel login
vercel

# Set environment variables
vercel env add GITHUB_APP_ID
vercel env add GITHUB_PRIVATE_KEY
vercel env add GITHUB_WEBHOOK_SECRET
vercel env add SUPABASE_URL
vercel env add SUPABASE_SERVICE_KEY
vercel env add ENCRYPTION_KEY
```

### Step 4: Test Installation

1. Install your GitHub App on a test repository
2. Open a pull request
3. Wait for the AI review comment!

## Configuration

After installing the app, users are redirected to configure:

- **API Key**: Their Google Gemini API key (stored encrypted)
- **Agents**: Which review types to enable

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_APP_ID` | Your GitHub App ID |
| `GITHUB_PRIVATE_KEY` | GitHub App private key (PEM) |
| `GITHUB_WEBHOOK_SECRET` | Webhook secret for signature verification |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `ENCRYPTION_KEY` | 32-byte key for encrypting user API keys |

Generate encryption key:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

## License

MIT
