# PRD: Gmail Customer Query Auto-Draft Agent

## 1. Overview

A lightweight, scheduled AI agent that monitors a business Gmail inbox, identifies genuine customer queries, and drafts replies using a knowledge base stored in Google Drive. The agent never sends emails autonomously. All drafts appear as standard Gmail drafts within the original thread for human review and sending. State is managed entirely through Gmail labels; no external database is used.

## 2. Goals & Non-Goals

### Goals
- Automatically triage incoming emails to identify customer queries vs. noise (newsletters, receipts, internal).
- Draft replies grounded strictly in Google Drive knowledge documents.
- Ensure zero autonomous sends; all outputs are Gmail drafts pending human approval.
- Operate within a near-zero cost footprint using free-tier LLM and serverless scheduling.

### Non-Goals
- Building a custom web app, dashboard, or UI.
- Processing historical email backlogs beyond the initial window.
- Handling non-text content (images, tables) within knowledge documents.
- Supporting languages other than English.
- Providing real-time or sub-hour latency.

## 3. User Stories

- **As a support team member**, I want to open Gmail and see draft replies already written for real customer queries, so I can review and send them quickly.
- **As a business owner**, I want the agent to refuse to answer if the knowledge base doesn't contain the answer, so I don't risk hallucinated or incorrect information being sent to customers.
- **As an ops person**, I want to know immediately if the agent breaks, so I can fix the auth or config without discovering it hours later.

## 4. Functional Requirements

### 4.1 Email Ingestion & Scope
- **Scope Window:** On every run, query Gmail for messages received within the last **2 hours**.
- **Initial Run Cap:** On the very first execution, limit ingestion to the **latest 15 messages** within that 2-hour window. Normal runs thereafter have no message count cap beyond the time window.
- **Pagination:** Use Gmail API pagination to handle the result set safely.

### 4.2 State Management (Gmail Labels)
- **Labels:**
  - `Agent-Processed` — Applied to a thread once the agent has created a draft or flagged it. Prevents re-processing.
  - `Needs-Human` — Applied when the agent cannot answer from the knowledge base, or when the email contains attachments.
- **Idempotency Rules:** Skip a thread if ANY of the following are true:
  1. The thread has the `Agent-Processed` label.
  2. The thread already contains a draft reply.
  3. The thread has the `Needs-Human` label AND contains a non-draft human reply (see 4.5).
- **Label Auto-Cleanup:** If a thread has `Needs-Human` and a new human reply is detected, remove `Needs-Human` and apply `Agent-Processed` instead (see 4.5).

### 4.3 Triage (Cheap LLM Gate)
- **Purpose:** Filter out non-queries before spending tokens on expensive drafting.
- **Input:** Email subject + body text (headers and sender metadata are ignored for this decision).
- **Output:** Binary decision — `is_customer_query: true/false`.
- **Model:** Groq free-tier fast/cheap model (e.g., `llama-3.1-8b-instant` or equivalent).
- **Behavior:** If `false`, apply `Agent-Processed` label and stop. No draft is created.

### 4.4 Knowledge Retrieval & Drafting
- **Document Source:** A single Google Drive folder containing ≤10 files (PDF, DOCX).
- **Ingestion:** On each run, list files in the folder, fetch their text content (text extraction only; images/tables are stripped/ignored), and build an in-memory context string.
- **Drafting Model:** Groq free-tier capable model (e.g., `llama-3.3-70b-versatile` or equivalent).
- **Prompting Strategy:**
  - Inject the full knowledge context into the system prompt.
  - Instruct the model: "Answer ONLY using the provided documents. If the answer is not contained in the documents, respond with the exact string `KNOWLEDGE_GAP`."
  - The model must not hallucinate or use outside knowledge.
- **Output Handling:**
  - If the model returns `KNOWLEDGE_GAP` or an empty/uncertain answer → Apply `Needs-Human` label. Do NOT create a draft.
  - If the model returns a valid answer → Create a Gmail draft reply in the thread. Apply `Agent-Processed` label.

### 4.5 Human Handoff & Flag Lifecycle
- **Attachment Rule:** If an incoming email contains attachments, bypass triage and drafting. Immediately apply `Needs-Human`.
- **Auto-Cleanup:** On every run, scan threads labeled `Needs-Human`. If a thread contains a new human reply (i.e., a message that is NOT a draft and NOT from the agent's own identity), remove `Needs-Human` and apply `Agent-Processed`. This prevents the flag from lingering forever.

### 4.6 Error Alerting
- **Channel:** If the GitHub Actions workflow fails at any step (auth, API, LLM, runtime exception), send a failure notification.
- **Destination:** Configurable webhook or email to an admin address. Minimum: print clear error logs in Actions; recommended: Slack webhook or email.
- **Content:** Include the run ID, failed step, and error message summary.

## 5. Technical Architecture

### 5.1 Runtime
- **Platform:** GitHub Actions.
- **Schedule:** Cron trigger every 1 hour (`0 * * * *`).
- **Timeout:** 10 minutes per run.
- **Language:** Python 3.11+.

### 5.2 Authentication
- **Gmail & Drive:** OAuth 2.0 for consumer Gmail (`@gmail.com`).
- **Token Generation:** Manual generation via Google OAuth 2.0 Playground to obtain a refresh token.
- **Storage:** Refresh token stored as a GitHub Actions secret (`GOOGLE_REFRESH_TOKEN`). Client ID and Client Secret stored as secrets (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`).
- **Token Refresh:** The script exchanges the refresh token for an access token at runtime.

### 5.3 API Integrations
| Service | API | Purpose |
|---------|-----|---------|
| Gmail | `gmail.users.messages.list`, `get`, `threads.get`, `drafts.create`, `users.labels.create/list`, `users.threads.modify` | Read emails, create drafts, manage labels. |
| Google Drive | `drive.files.list`, `drive.files.get` (with `alt=media` or export) | List and download knowledge documents. |
| Groq | Chat Completions API | Triage and drafting LLM calls. |

### 5.4 Document Processing
- **PDF:** `PyPDF2` or `pdfplumber` for text extraction.
- **DOCX:** `python-docx` for text extraction.
- **Limitation:** Images, charts, and complex tables are ignored. Only plain text content is fed to the LLM.

### 5.5 Data Flow
```
GitHub Actions Trigger (hourly)
    │
    ▼
[1] Authenticate Gmail & Drive
    │
    ▼
[2] Fetch messages from last 2 hours
    │
    ▼
[3] Filter: Skip threads with Agent-Processed, existing drafts, or resolved Needs-Human
    │
    ▼
[4] For each remaining thread:
    │
    ├── Check attachments → Yes → Needs-Human → Next
    │
    ├── Triage LLM (cheap) → Not a query → Agent-Processed → Next
    │
    ├── Fetch & parse Drive docs → Build context
    │
    ├── Drafting LLM → KNOWLEDGE_GAP → Needs-Human → Next
    │
    └── Drafting LLM → Valid answer → Create Gmail Draft → Agent-Processed
    │
    ▼
[5] Scan Needs-Human threads for human replies → Auto-remove flag
    │
    ▼
[6] Alert on failure
```

## 6. LLM Prompt Specifications

### 6.1 Triage Prompt
```
You are an email classifier. Read the email below and decide if it is a genuine customer query that requires a response from a business.

Rules:
- Ignore newsletters, promotional emails, receipts, invoices, automated notifications, and internal emails.
- Focus on the body content, not the sender or headers.
- A customer query asks a question, requests help, or seeks information about products/services.

Respond with ONLY a JSON object: {"is_customer_query": true/false}

Email Subject: {subject}
Email Body: {body}
```

### 6.2 Drafting Prompt
```
You are a helpful customer support assistant. Use ONLY the information in the provided documents to answer the customer's question.

Rules:
- If the answer is not found in the documents, respond with exactly: KNOWLEDGE_GAP
- Do not make up information. Do not use outside knowledge.
- Be concise, professional, and friendly.
- If the documents partially answer the question but leave a part unanswered, respond with KNOWLEDGE_GAP. Do not provide partial answers.

Documents:
{concatenated_document_text}

Customer Email:
Subject: {subject}
Body: {body}

Your draft reply:
```

## 7. Edge Cases & Handling

| Scenario | Handling |
|----------|----------|
| **No new emails** | Exit cleanly. No labels applied. |
| **Drive folder empty or inaccessible** | Log error, alert admin, skip drafting step. Do not apply labels to emails. |
| **Groq rate limit / timeout** | Retry once with exponential backoff (max 2 attempts). If still failing, alert admin and exit without labeling emails. |
| **Gmail API rate limit** | Back off and retry. If persistent, alert admin. |
| **Expired refresh token** | Catch 401, alert admin immediately. Do not proceed. |
| **Document > token limit** | Truncate from the end and log a warning. Do not split across multiple LLM calls. |
| **Thread has multiple new messages** | Evaluate the latest message only. Draft reply addresses the latest message context. |
| **Customer reply in already-processed thread** | The thread has `Agent-Processed`, so it is skipped. Human must handle follow-ups manually. |

## 8. Security & Privacy

- **Secrets:** All credentials (refresh token, client secrets, Groq API key) stored as GitHub Encrypted Secrets. Never commit to repository.
- **Scope Minimization:** Gmail OAuth scopes limited to `https://www.googleapis.com/auth/gmail.modify` (read, draft, label). Drive scope limited to `https://www.googleapis.com/auth/drive.readonly`.
- **Data Residency:** No email content or documents are persisted outside the GitHub Actions runner ephemeral storage. No logging of PII to stdout beyond error traces.
- **Agent Identity:** Drafts are created via API but appear as normal drafts in the user's Gmail. There is no separate "bot" identity.

## 9. Cost Analysis

| Component | Cost Basis | Expected Monthly Cost |
|-----------|------------|----------------------|
| GitHub Actions | Free tier: 2,000 minutes/month. ~30 min/day = ~900 min/month. | $0 |
| Groq API | Free tier: sufficient for ~20 emails/day × 2 calls (triage + draft). | $0 |
| Google APIs | Standard free quota (1B quota units/day for Gmail, generous Drive limits). | $0 |
| **Total** | | **$0** |

*Note: If volume grows beyond free tiers, Groq pay-as-you-go is ~$0.10–$0.30 per 1M tokens, keeping costs negligible.*

## 10. Monitoring & Observability

- **GitHub Actions Logs:** Primary debugging surface. All steps log start/end and key counts (emails found, triaged, drafted, flagged).
- **Structured Logging:** JSON log lines for emails processed: `{"event": "draft_created", "thread_id": "...", "model": "..."}`.
- **Failure Alerts:** See 4.6. Recommended: Slack incoming webhook or simple email via SendGrid/SES on failure.

## 11. Future Considerations (Out of Scope)

- Multi-language support.
- Processing email attachments (OCR, image understanding).
- Vector DB / RAG for large knowledge bases.
- Real-time Pub/Sub trigger instead of hourly cron.
- Confidence scoring for triage instead of binary.
- Dashboard for analytics (volume, response times, knowledge gaps).

## 12. Success Metrics

- **Coverage:** ≥90% of genuine customer queries receive a draft within 1 hour of arrival.
- **Accuracy:** <5% of drafts require heavy human rewriting (measured by team feedback).
- **Safety:** 0% autonomous sends. 100% of `KNOWLEDGE_GAP` cases correctly flagged as `Needs-Human`.
- **Uptime:** GitHub Actions workflow success rate ≥95%.

---
*Version: 1.0*
*Date: 2026-06-16*
*Status: Ready for Implementation*
