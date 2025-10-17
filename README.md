# Deployx - LLM Code Deployment Server

A production-ready FastAPI application that automates the complete workflow of generating, deploying, and publishing web applications using LLM code generation and GitHub Pages.

## Features

- **Autonomous Code Generation**: Uses Gemini 2.0 Flash to generate complete web applications from natural language briefs
- **GitHub Integration**: Automatically creates repositories, commits code, and enables GitHub Pages
- **Async Processing**: Background task processing for non-blocking request handling
- **Retry Logic**: Exponential backoff for evaluation submissions
- **Security**: API key validation and secret management
- **Production Ready**: Docker support, health checks, and proper error handling

## Architecture

```
Request → Validation → LLM Generation → GitHub Repo Creation → 
Pages Deployment → Evaluation Submission
```

### Workflow Steps

1. **Request Validation**: Verify secret key and required fields
2. **Immediate Response**: Return HTTP 200 to acknowledge receipt
3. **Background Processing**:
   - Generate code files using Gemini 2.0 Flash
   - Create project structure with LICENSE and README
   - Initialize Git repository
   - Create GitHub repository using gh CLI
   - Enable GitHub Pages
   - Wait for Pages to be live (200 OK)
   - Submit evaluation with retry logic

## Installation

### Local Setup

1. **Clone the repository**:
```bash
git clone https://github.com/23f1001691/Deployx.git
cd Deployx
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Install GitHub CLI**:
```bash
# macOS
brew install gh

# Ubuntu/Debian
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

5. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your credentials
```

6. **Authenticate GitHub CLI**:
```bash
gh auth login
```

## Configuration

Edit `.env` file with your credentials:

```bash
# API Keys
SECRET_KEY=your_secure_secret_key
GOOGLE_API_KEY=your_gemini_api_key

# GitHub
GITHUB_TOKEN=ghp_your_github_token
GITHUB_USERNAME=your_username
```

## Usage

### Start the Server

**Local**:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

#### POST `/api-endpoint`

Deploy a new web application.

**Request**:
```json
{
  "email": "student@example.com",
  "secret": "your_secret_key",
  "task": "captcha-solver",
  "round": 1,
  "nonce": "ab12cd34",
  "brief": "Create a captcha solver that handles ?url=https://.../image.png",
  "checks": [
    "Repo has MIT license",
    "README.md is professional",
    "Page displays captcha URL passed at ?url=...",
    "Page displays solved captcha text within 15 seconds"
  ],
  "evaluation_url": "https://example.com/notify",
  "attachments": [
    {
      "name": "sample.png",
      "url": "data:image/png;base64,iVBORw0KG..."
    }
  ]
}
```

**Response** (200 OK):
```json
{
  "status": "accepted",
  "message": "Deployment started"
}
```

#### GET `/health`

Health check endpoint.

**Response**:
```json
{
  "status": "healthy"
}
```

### Testing

Test the endpoint using curl:

```bash
curl -X POST http://localhost:8000/api-endpoint \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "secret": "your_secret_key",
    "task": "test-app",
    "round": 1,
    "nonce": "test123",
    "brief": "Create a simple hello world webpage",
    "checks": ["Has MIT license", "Professional README"],
    "evaluation_url": "https://webhook.site/your-unique-url",
    "attachments": []
  }'
```

## Code Structure

```
├── src/
│   ├── main.py              
│   └── github.py
|   └── evaluation.py
|   └── llm.py
|   └── prompts.py
|   └── utils.py   
├── requirements.txt       
├── Dockerfile            
├── .env.example          
├── .gitignore        
└── README.md           
└── LICENSE            
```

### Key Components

**`CodeGenerator`**: Orchestrates LLM code generation using pydantic-ai
- Connects to Gemini 2.0 Flash
- Generates index.html, style.css, script.js, README.md
- Parses and validates LLM responses

**`GitHubDeployer`**: Manages GitHub repository operations
- Creates repositories via GitHub CLI
- Configures Git and pushes code
- Enables GitHub Pages
- Waits for deployment completion

**`process_deployment`**: Main workflow orchestrator
- Generates project files
- Creates repository structure
- Deploys to GitHub Pages
- Submits evaluation with retries

## Error Handling

- **Validation Errors**: Returns 400/401 with error details
- **LLM Failures**: Catches parsing errors and retries
- **GitHub Errors**: Logs and propagates deployment failures
- **Evaluation Submission**: Exponential backoff retry (1s, 2s, 4s, 8s, 16s)

## Troubleshooting

**GitHub CLI authentication fails**:
```bash
gh auth login
gh auth status
```

**Pages not deploying**:
- Check repository settings on GitHub
- Verify Pages is enabled
- Wait up to 5 minutes for initial deployment
- Check GitHub Actions tab for build status

**LLM generation fails**:
- Verify Gemini API key is valid
- Check API quota limits
- Review error logs for details

**Evaluation submission fails**:
- Verify evaluation_url is accessible
- Check for rate limiting
- Review retry logs

## Performance

- **Request Processing**: <100ms (immediate 200 response)
- **Code Generation**: 30-60 seconds (Gemini API)
- **GitHub Deployment**: 20-40 seconds
- **Pages Activation**: 1-5 minutes
- **Total Workflow**: 2-7 minutes

## License

MIT License - See LICENSE file for details
