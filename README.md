# Gmail Customer Query Auto-Draft Agent

This is a lightweight, scheduled AI agent that monitors a business Gmail inbox, identifies genuine customer queries, and drafts replies using a knowledge base stored in Google Drive. 

## Project Setup

### Required Secrets for GitHub Actions

To run this agent via GitHub Actions, you must configure the following **Repository Secrets** (in your GitHub repo, go to `Settings` -> `Secrets and variables` -> `Actions`):

| Secret Name | Description |
|-------------|-------------|
| `GOOGLE_CLIENT_ID` | Your Google Cloud project OAuth 2.0 Client ID. |
| `GOOGLE_CLIENT_SECRET` | Your Google Cloud project OAuth 2.0 Client Secret. |
| `GOOGLE_REFRESH_TOKEN` | The OAuth 2.0 Refresh Token generated via Google OAuth 2.0 Playground. Must have Gmail modify and Drive readonly scopes. |
| `GROQ_API_KEY` | Your Groq API key for LLM triage and drafting capabilities. |

### Local Development / Testing

1. Create a Python virtual environment: `python -m venv venv`
2. Activate the environment: `venv\Scripts\activate` (Windows)
3. Install dependencies: `pip install -r requirements.txt`
4. Create a `.env` file at the root of the project mirroring the secrets above (ensure `.env` is added to `.gitignore`).
