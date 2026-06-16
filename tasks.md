# Gmail Auto-Draft Agent Tasks

This document contains an atomic, dependency-phased breakdown of the tasks required to implement the Gmail Customer Query Auto-Draft Agent based on the PRD.

## Phase 1: Project Setup & Infrastructure
- [x] Initialize GitHub repository and basic Python project structure.
- [x] Create `requirements.txt` with required dependencies (`google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib`, `groq`, `PyPDF2` / `pdfplumber`, `python-docx`).
- [x] Setup initial GitHub Actions workflow file (`.github/workflows/agent.yml`) with a cron trigger (`0 * * * *`) and Python 3.11+ environment.
- [x] Document required GitHub Secrets (`GOOGLE_REFRESH_TOKEN`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GROQ_API_KEY`).

## Phase 2: Authentication (Gmail & Google Drive)
- [x] Create OAuth 2.0 helper utility to authenticate using the `GOOGLE_REFRESH_TOKEN` via `google.oauth2.credentials.Credentials`.
- [x] Implement token refresh mechanism to get short-lived access tokens dynamically.
- [x] Initialize the Gmail API client with the `https://www.googleapis.com/auth/gmail.modify` scope.
- [x] Initialize the Google Drive API client with the `https://www.googleapis.com/auth/drive.readonly` scope.
- [x] Write a connection test script to verify both API clients can successfully fetch basic user info/metadata.

## Phase 3: State Management (Gmail Labels)
- [x] Implement utility to list all existing labels for the authenticated Gmail account.
- [x] Implement utility to fetch the Label IDs for `Agent-Processed` and `Needs-Human`.
- [x] Implement utility to automatically create the `Agent-Processed` and `Needs-Human` labels if they do not already exist.
- [x] Implement utility to add a specific label to a thread (`users.threads.modify`).
- [x] Implement utility to remove a specific label from a thread.

## Phase 4: Gmail Ingestion & Filtering
- [x] Implement function to query Gmail for messages received within the last 2 hours.
- [x] Add pagination support for the `users.messages.list` endpoint.
- [x] Implement logic to handle the initial run cap (limit ingestion to the latest 15 messages) vs. normal runs.
- [x] Implement `check_attachments` utility to identify if an email contains attachments, bypassing further logic and applying the `Needs-Human` label immediately.
- [x] Implement idempotency filtering logic to skip threads that:
  - [x] Have the `Agent-Processed` label.
  - [x] Already contain a draft reply.
  - [x] Have the `Needs-Human` label AND contain a non-draft human reply.

## Phase 5: LLM Triage (Filtering Noise)
- [x] Initialize Groq API client using the `GROQ_API_KEY`.
- [x] Construct the Triage Prompt using the rules defined in the PRD (focus on subject/body, identify genuine customer queries).
- [x] Implement function to call the Groq API (using a fast/cheap model like `llama-3.1-8b-instant`) with the triage prompt.
- [x] Implement logic to parse the expected JSON output (`{"is_customer_query": true/false}`).
- [x] Integrate triage logic into the pipeline: if `false`, apply the `Agent-Processed` label and skip the drafting phase.

## Phase 6: Knowledge Retrieval & Document Processing
- [x] Implement function to list files (PDF, DOCX) in the specified Google Drive knowledge folder.
- [x] Implement function to download the content of the files from Google Drive.
- [x] Implement text extraction function for PDF files, ensuring images/tables are skipped.
- [x] Implement text extraction function for DOCX files.
- [x] Implement `build_knowledge_context` function to concatenate all extracted text into a single context string, enforcing token limit truncation if necessary.

## Phase 7: LLM Drafting
- [x] Construct the Drafting Prompt, injecting the concatenated knowledge context, email subject, and body.
- [x] Implement function to call the Groq API (using a capable model like `llama-3.3-70b-versatile`) with the drafting prompt.
- [x] Implement output handling logic: if the model returns `KNOWLEDGE_GAP` (or empty/uncertain response), apply the `Needs-Human` label and abort draft creation.

## Phase 8: Gmail Draft Creation
- [x] Implement function to format the LLM drafting output into an email payload.
- [x] Implement function to create a draft reply within the original email thread via the Gmail API (`drafts.create`).
- [x] Implement logic to apply the `Agent-Processed` label once the draft is successfully created.

## Phase 9: Human Handoff & Auto-Cleanup
- [x] Implement `scan_needs_human_threads` function to fetch all threads currently labeled `Needs-Human`.
- [x] Implement logic to analyze messages in `Needs-Human` threads to detect new, non-draft human replies.
- [x] Implement logic to remove the `Needs-Human` label and apply the `Agent-Processed` label when a human reply is detected.

## Phase 10: Error Handling, Alerting & Observability
- [x] Implement exponential backoff for Groq API and Gmail/Drive API rate limits.
- [x] Implement graceful handling and logging for edge cases (e.g., Drive folder empty, expired refresh token, no new emails).
- [x] Add structured JSON logging throughout the application (e.g., `{"event": "draft_created", "thread_id": "...", "model": "..."}`).
- [x] Update the GitHub Actions workflow to trigger a failure notification (Slack webhook or equivalent) if any step in the pipeline fails.
