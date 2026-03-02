# Feature Specification: Silver Tier — Functional Assistant

**Feature Branch**: `003-silver-functional-assistant`
**Created**: 2026-02-27
**Status**: Draft
**Input**: Silver Tier — Gmail + WhatsApp watchers, local action layer (email, calendar, WhatsApp reply, LinkedIn posting), HITL approval workflow, and Agent Skills for all AI functionality.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Inbound Email Processing & Reply (Priority: P1)

Taha receives a client email in Gmail. The AI Employee automatically detects it, reads the content, drafts a contextually appropriate reply, and places the draft in the Pending Approval folder as a markdown file. Taha reviews the draft in Obsidian, moves the file to the Approved folder, and the AI sends the email on his behalf without any further input.

**Why this priority**: Email is the highest-value business communication channel. Automating inbound email triage and reply drafting directly reduces time spent on repetitive correspondence and demonstrates the core value of the AI Employee.

**Independent Test**: Send a test email to the monitored Gmail account. Within 3 minutes, verify a task file appears in `Inbox/`. Trigger the orchestrator; confirm a draft reply appears in `Pending_Approval/`. Move it to `Approved/`; verify the email is sent and logged.

**Acceptance Scenarios**:

1. **Given** a new unread email arrives in Gmail, **When** the Gmail watcher polls the inbox, **Then** a structured task file (`EMAIL_<id>.md`) appears in `Vault/Inbox/` within 3 minutes containing sender, subject, and message body.
2. **Given** a task file exists in `Needs_Action/`, **When** the orchestrator processes it, **Then** a draft reply file appears in `Pending_Approval/` with action type, recipient, subject, and proposed reply body.
3. **Given** a draft reply file is moved to `Approved/`, **When** the orchestrator detects the approval, **Then** the email is sent via the Gmail service and the event is logged in `Vault/Logs/`.
4. **Given** a draft reply file is moved to `Rejected/`, **When** the orchestrator detects the rejection, **Then** no email is sent, the rejection is logged, and no further action is taken.
5. **Given** the Gmail watcher service crashes, **When** the system detects the failure, **Then** the service automatically restarts within 15 seconds.

---

### User Story 2 — WhatsApp Message Detection & Reply (Priority: P2)

A client or contact sends Taha a WhatsApp message containing an urgent request or business keyword. The AI Employee detects the message, creates a task file, drafts a reply, and places it in Pending Approval. Taha approves in Obsidian and the reply is sent automatically via WhatsApp.

**Why this priority**: WhatsApp is the primary informal business communication channel in many markets. Capturing and responding to urgent client messages autonomously is a high-value, high-visibility capability.

**Independent Test**: Send a WhatsApp message containing a trigger keyword (e.g., "invoice", "urgent") to Taha's phone. Within 60 seconds, verify a `WHATSAPP_<id>.md` task file appears in `Vault/Inbox/`. Approve the draft reply; verify the reply is sent in the WhatsApp conversation.

**Acceptance Scenarios**:

1. **Given** a WhatsApp message containing a business keyword is received, **When** the WhatsApp monitor detects it, **Then** a structured task file (`WHATSAPP_<id>.md`) appears in `Vault/Inbox/` within 60 seconds containing sender, message content, and timestamp.
2. **Given** a WhatsApp task file is processed by the orchestrator, **Then** a draft reply appears in `Pending_Approval/` with proposed message content.
3. **Given** the draft is approved, **Then** the WhatsApp reply is sent to the original sender and logged.
4. **Given** a WhatsApp message does NOT contain a business keyword, **Then** no task file is created and the message is silently ignored.
5. **Given** the WhatsApp monitor is restarted after a crash, **Then** it resumes the existing session without requiring a QR code re-scan.

---

### User Story 3 — Google Calendar Event Creation (Priority: P3)

An email or task mentions a meeting, deadline, or scheduled commitment. The AI Employee identifies the scheduling intent, drafts a calendar event with the correct details, and places the creation request in Pending Approval. Taha approves and the event is automatically added to his Google Calendar.

**Why this priority**: Calendar management is a direct extension of email processing that adds concrete scheduling value. It requires the same approval infrastructure as email, making it a natural second action type once the HITL workflow exists.

**Independent Test**: Drop a task file referencing a meeting ("Can we meet Tuesday at 3pm?") into `Inbox/`. Confirm a calendar event request appears in `Pending_Approval/`. Approve it; verify the event appears in Google Calendar.

**Acceptance Scenarios**:

1. **Given** a task contains scheduling intent (date, time, participants), **When** the orchestrator processes it, **Then** a calendar event request file appears in `Pending_Approval/` with event title, date, time, duration, and attendees.
2. **Given** the event request is approved, **Then** the event is created in Google Calendar within 30 seconds and logged.
3. **Given** a task contains no clear scheduling intent, **Then** no calendar event request is created.

---

### User Story 4 — LinkedIn Business Post Publishing (Priority: P4)

Taha or a scheduled trigger initiates a LinkedIn post. The AI Employee drafts a professional, sales-oriented post based on business context from the vault, places it in Pending Approval, and publishes it to LinkedIn after Taha approves.

**Why this priority**: LinkedIn posting is a proactive outbound capability that generates business value (sales leads, visibility). It extends the AI Employee from reactive (respond to inputs) to proactive (generate business outputs). Required by the hackathon Silver tier.

**Independent Test**: Drop a prompt file ("Write a LinkedIn post about our Q1 results") into `Inbox/`. Confirm a LinkedIn post draft appears in `Pending_Approval/`. Approve it; verify the post appears on Taha's LinkedIn profile within 30 seconds.

**Acceptance Scenarios**:

1. **Given** a task requests a LinkedIn post, **When** the orchestrator processes it, **Then** a post draft appears in `Pending_Approval/` containing the proposed post text (max 3,000 characters) and hashtags.
2. **Given** the post draft is approved, **Then** the post is published to LinkedIn and visible on Taha's profile within 30 seconds, and the event is logged.
3. **Given** the post draft is rejected, **Then** no post is published and the rejection is logged.

---

### User Story 5 — Agent Skills for All AI Capabilities (Priority: P5)

Every AI capability introduced in Silver tier is packaged as a reusable Agent Skill. Each skill encapsulates the reasoning, context requirements, and output format for one capability (e.g., draft email reply, draft WhatsApp reply, create calendar event, draft LinkedIn post, handle HITL approval). Skills are independently invokable and composable.

**Why this priority**: The hackathon explicitly requires all AI functionality to be implemented as Agent Skills. Skills make capabilities reusable, testable, and extensible into Gold tier without reimplementation.

**Independent Test**: Invoke each skill individually via the Claude Code interface and verify it produces the correct output artifact for a sample input.

**Acceptance Scenarios**:

1. **Given** a skill is installed, **When** the orchestrator encounters a relevant task type, **Then** it loads and applies the correct skill automatically.
2. **Given** a skill is invoked with a sample task, **Then** it produces a correctly formatted output file (Pending Approval request or plan) without requiring manual prompt engineering.
3. **Given** all 6 skills are installed, **Then** each can be invoked independently in isolation.

---

### Edge Cases

- What happens when Gmail API credentials expire mid-operation? Watcher logs the error and retries with the refresh token; if refresh also fails, it alerts via a file in `Vault/Logs/` and pauses until credentials are renewed.
- What happens when a WhatsApp session is invalidated by the phone (user unlinks device)? The watcher logs the session loss and creates a `SYSTEM_whatsapp-session-expired.md` file in `Needs_Action/` prompting the user to re-link.
- What happens when an approval file is left in `Pending_Approval/` past its expiry time (default 24 hours)? The orchestrator moves it to `Rejected/` with an `expired` status and logs the auto-rejection.
- What happens when two approval files are approved simultaneously? Each is processed sequentially; no race conditions since the orchestrator is single-threaded per action type.
- What happens if the Gmail watcher detects an email already processed (service restart)? Watcher tracks processed message IDs in a local state file; already-seen IDs are skipped.
- What happens if a LinkedIn post exceeds platform character limits? The skill truncates or re-drafts the content and flags it in the approval request for human review.
- What happens when the LinkedIn access token expires (every 60 days)? The action layer detects the expiry, logs a `SYSTEM_linkedin-token-expired.md` alert to `Needs_Action/`, and halts LinkedIn posting until the token is renewed.

---

## Requirements *(mandatory)*

### Functional Requirements

**Inbound Monitoring**

- **FR-001**: The Gmail watcher MUST poll the Gmail inbox at regular intervals (default: every 2 minutes) and create a structured task file in `Vault/Inbox/` for each new unread email that meets importance criteria (starred, marked important, or from a known contact).
- **FR-002**: The WhatsApp monitor MUST detect new incoming WhatsApp messages containing configurable business keywords and create a structured task file in `Vault/Inbox/` within 60 seconds of receipt.
- **FR-003**: Both watchers MUST track previously processed messages to prevent duplicate task files across restarts.
- **FR-004**: Both watchers MUST run as persistent background services with automatic restart on failure, following the same systemd pattern established in Bronze tier.

**HITL Approval Workflow**

- **FR-005**: The orchestrator MUST write all proposed outbound actions (email reply, WhatsApp reply, calendar event, LinkedIn post) as approval request files to `Vault/Pending_Approval/` before executing any action.
- **FR-006**: Each approval request file MUST contain: action type, target recipient or platform, proposed content, creation timestamp, expiry timestamp (default 24 hours), and status field.
- **FR-007**: The orchestrator MUST continuously monitor `Vault/Approved/` and execute the corresponding action within 30 seconds of a file appearing there.
- **FR-008**: The orchestrator MUST continuously monitor `Vault/Rejected/` and log the rejection without taking any action.
- **FR-009**: Approval request files older than 24 hours MUST be automatically moved to `Vault/Rejected/` with status `expired`.
- **FR-010**: The system MUST NEVER execute an outbound action without a corresponding file in `Vault/Approved/`.

**Outbound Actions**

- **FR-011**: When an email approval is granted, the system MUST send the reply via the Gmail service using the original thread context and log the result.
- **FR-012**: When a WhatsApp approval is granted, the system MUST send the reply to the original sender via the WhatsApp session and log the result.
- **FR-013**: When a calendar event approval is granted, the system MUST create the event in Google Calendar with title, date/time, duration, and attendees as specified in the approval file.
- **FR-014**: When a LinkedIn post approval is granted, the system MUST publish the post to the user's LinkedIn profile within 30 seconds and log the result.

**Agent Skills**

- **FR-015**: All AI reasoning capabilities MUST be implemented as Agent Skills (`SKILL.md` files) installable into the Claude Code skills directory.
- **FR-016**: The following skills MUST be created: `gmail-watcher`, `whatsapp-watcher`, `gmail-reply`, `calendar-event`, `whatsapp-reply`, `linkedin-post`, `hitl-approval`.
- **FR-017**: Each skill MUST define: its purpose, the input task format it expects, the output file format it produces, and the action it triggers.

**Data & Security**

- **FR-018**: All credentials (Gmail OAuth2 tokens, LinkedIn access token, WhatsApp session) MUST be stored locally on the user's machine; no credentials or personal data MAY be transmitted to third-party cloud relay services.
- **FR-019**: All actions and their outcomes MUST be logged to `Vault/Logs/` in the existing JSON log format.
- **FR-020**: The Gmail and Calendar services MUST authenticate via the same Google Cloud project using locally stored OAuth2 credentials.

### Key Entities

- **InboundMessage**: A structured `.md` file in `Vault/Inbox/` representing a detected email or WhatsApp message. Contains: source (gmail/whatsapp), sender, subject/preview, body, received timestamp, message ID.
- **ApprovalRequest**: A `.md` file in `Vault/Pending_Approval/` representing a proposed outbound action awaiting human review. Contains: action type, target, proposed content, created timestamp, expiry timestamp, status.
- **ApprovedAction**: An ApprovalRequest file moved to `Vault/Approved/` by the user, authorising execution.
- **RejectedAction**: An ApprovalRequest file moved to `Vault/Rejected/` (manually or by expiry), blocking execution.
- **AgentSkill**: A `SKILL.md` file defining a reusable AI capability — its trigger conditions, expected inputs, reasoning instructions, and output format.
- **WatcherState**: A local state file (per watcher) tracking processed message IDs to prevent duplicate task creation across service restarts.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: New emails appear as task files in `Vault/Inbox/` within 3 minutes of arrival in Gmail, verified end-to-end.
- **SC-002**: New WhatsApp messages with keywords appear as task files in `Vault/Inbox/` within 60 seconds of receipt.
- **SC-003**: A complete Gmail workflow (email received → task file → plan → approval request → email sent) completes within 5 minutes of user approval action.
- **SC-004**: A complete WhatsApp workflow (message received → task file → plan → approval request → reply sent) completes within 3 minutes of user approval action.
- **SC-005**: Calendar events and LinkedIn posts appear in their respective platforms within 30 seconds of the approval file being moved.
- **SC-006**: Both watcher services and the orchestrator recover from a simulated crash and resume processing within 15 seconds, without human intervention.
- **SC-007**: No personal data (email content, WhatsApp messages, OAuth tokens) is transmitted to any service other than the directly targeted platform (Gmail, WhatsApp, Google Calendar, LinkedIn). Verifiable by network inspection.
- **SC-008**: All 7 Agent Skills are individually invokable and produce correctly formatted output files for a sample input without additional prompt engineering.
- **SC-009**: Zero outbound actions (email sends, WhatsApp replies, LinkedIn posts, calendar events) occur without a corresponding file in `Vault/Approved/`.

---

## Assumptions

1. Bronze tier is fully deployed: vault is initialised at `/mnt/d/AI_Employee_Vault`, and `fte-watcher` and `fte-orchestrator` systemd services are running.
2. The vault folder structure is extended to include: `Pending_Approval/`, `Approved/`, `Rejected/`, and `Done/` directories.
3. The user will complete a one-time Google Cloud Console setup (create project, enable Gmail API and Google Calendar API, configure OAuth2 consent for personal use) before deploying Silver tier.
4. The user will complete a one-time LinkedIn Developer App setup (create app, request "Share on LinkedIn" product, complete OAuth2 consent) before deploying LinkedIn posting.
5. The WhatsApp monitor uses the existing WhatsApp account linked to the user's personal phone — no WhatsApp Business account is required or assumed.
6. WhatsApp keyword filtering defaults to: `urgent`, `asap`, `invoice`, `payment`, `help`, `contract`. These are configurable.
7. Gmail filtering defaults to: unread emails labelled "Important" by Gmail, or from contacts in the user's address book. Spam and promotional emails are excluded.
8. The HITL approval expiry defaults to 24 hours; this is configurable per action type.
9. LinkedIn posts are for Taha's personal professional profile, not a company page.
10. All Silver tier services run on the same WSL2 machine as Bronze tier.
11. The WhatsApp session must be linked once via a QR code scan before the daemon starts; subsequent restarts reuse the stored session.
