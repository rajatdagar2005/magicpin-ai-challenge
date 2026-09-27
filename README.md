# 🤖 MagicPin Vera AI Challenge — Conversational Engagement Bot

> **A deterministic, context-aware conversational engagement engine built for the MagicPin Vera AI Challenge.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API%20Framework-009688.svg)](https://fastapi.tiangolo.com/)
[![Render](https://img.shields.io/badge/Deployed-Render-46E3B7.svg)](https://render.com/)
[![Status](https://img.shields.io/badge/Status-Live-success.svg)](https://magicpin-ai-challenge-4nmt.onrender.com/)
[![License](https://img.shields.io/badge/License-Challenge%20Submission-lightgrey.svg)](#)

---

## 🚀 Live Deployment

**Public Bot Endpoint**

https://magicpin-ai-challenge-4nmt.onrender.com/

### Health Check

`GET /v1/healthz`

### Metadata

`GET /v1/metadata`

The bot is deployed as a public FastAPI service and exposes all API endpoints required by the Vera AI Challenge.

---

# 📌 Table of Contents

* [Overview](#-overview)
* [Challenge Objective](#-challenge-objective)
* [Core Idea](#-core-idea)
* [Key Features](#-key-features)
* [Architecture](#-architecture)
* [System Flow](#-system-flow)
* [Project Structure](#-project-structure)
* [Context Management](#-context-management)
* [Deterministic Composer](#-deterministic-composer)
* [Conversation State Machine](#-conversation-state-machine)
* [Suppression System](#-suppression-system)
* [API Reference](#-api-reference)

  * [`GET /v1/healthz`](#1-get-v1healthz)
  * [`GET /v1/metadata`](#2-get-v1metadata)
  * [`POST /v1/context`](#3-post-v1context)
  * [`POST /v1/tick`](#4-post-v1tick)
  * [`POST /v1/reply`](#5-post-v1reply)
* [Decision Pipeline](#-decision-pipeline)
* [Safety and Guardrails](#-safety-and-guardrails)
* [Reliability Design](#-reliability-design)
* [Testing](#-testing)
* [Judge Simulation](#-judge-simulation)
* [Deployment](#-deployment)
* [Local Development](#-local-development)
* [Environment Variables](#-environment-variables)
* [Example Flow](#-example-flow)
* [Design Decisions](#-design-decisions)
* [Why Deterministic?](#-why-deterministic)
* [Performance](#-performance)
* [Limitations](#-limitations)
* [Future Improvements](#-future-improvements)
* [Challenge Compliance](#-challenge-compliance)
* [Author](#-author)

---

# 🧠 Overview

This project implements a **context-aware conversational engagement bot** for the MagicPin Vera AI Challenge.

The system receives structured information about:

* merchants
* categories
* customers
* engagement triggers
* conversation replies

and uses that information to determine:

1. Whether an engagement should be generated.
2. What type of message should be sent.
3. How the merchant/category context should influence the message.
4. Which CTA should be presented.
5. Whether the conversation should continue, wait, or end.
6. Whether duplicate engagement should be suppressed.

The implementation intentionally uses a **deterministic decision engine** instead of relying entirely on generative model output.

This makes the core behavior:

* predictable
* reproducible
* testable
* low-latency
* resistant to prompt variability
* easier to validate against structured challenge scenarios

---

# 🎯 Challenge Objective

The Vera challenge requires a bot that exposes a public HTTP API capable of handling context, trigger evaluation, engagement generation, and conversation replies.

The required API surface is:

| Method | Endpoint       | Purpose                                          |
| ------ | -------------- | ------------------------------------------------ |
| `GET`  | `/v1/healthz`  | Service health                                   |
| `GET`  | `/v1/metadata` | Bot metadata                                     |
| `POST` | `/v1/context`  | Push/update challenge context                    |
| `POST` | `/v1/tick`     | Evaluate available triggers and generate actions |
| `POST` | `/v1/reply`    | Handle conversational replies                    |

The implementation is designed around these requirements.

---

# 💡 Core Idea

The bot follows a simple principle:

> **Structured context → deterministic decision → context-specific message → controlled conversation**

Instead of treating every trigger as an opportunity to send a generic promotional message, the engine first gathers the relevant context.

For a trigger, the system resolves:

```text
Trigger
   │
   ├── Merchant
   │
   ├── Category
   │
   └── Customer
          │
          ▼
   Deterministic Composer
          │
          ├── Message body
          ├── CTA
          ├── Send channel
          └── Rationale
```

This ensures that generated actions remain tied to the information provided by the challenge.

---

# ✨ Key Features

## 1. Context-Aware Engagement

Messages are composed using multiple context sources:

* Trigger context
* Merchant context
* Category context
* Customer context

This allows the bot to produce messages that are specific to the current engagement opportunity.

---

## 2. Deterministic Message Composition

The core composer does not depend on random generation.

Given the same:

```text
category + merchant + trigger + customer
```

the system can produce a consistent result.

This improves:

* reproducibility
* debugging
* testing
* reliability

---

## 3. Trigger-Based Decisioning

The `/v1/tick` endpoint evaluates available triggers and determines which ones are eligible for action.

The system checks:

* trigger existence
* merchant availability
* category availability
* customer context
* expiration
* suppression state

Only valid opportunities are converted into actions.

---

## 4. Expiration Handling

Triggers with an expiration timestamp are checked before generating an action.

Conceptually:

```text
current_time >= expires_at
        │
        ├── YES → skip trigger
        │
        └── NO  → continue evaluation
```

This prevents expired engagement opportunities from being surfaced.

---

## 5. Duplicate Suppression

The bot maintains a suppression store to prevent the same suppression key from repeatedly generating an engagement.

This is particularly important for scheduled/tick-based systems where the same trigger may be encountered multiple times.

---

## 6. Conversation State Management

The `/v1/reply` endpoint maintains conversation state and distinguishes between:

```text
ENGAGED
WAITING
ENDED
```

The reply handler determines the next action based on the merchant/customer interaction.

---

## 7. Merchant Reply Tracking

Merchant messages are tracked to identify conversational behavior and prevent uncontrolled automatic replies.

This allows the system to maintain a more disciplined conversational flow.

---

## 8. Context Versioning

Context updates are version-aware.

A stale context version is rejected instead of silently overwriting newer information.

Conceptually:

```text
Incoming version
       │
       ▼
Compare with current version
       │
   ┌───┴────┐
   │        │
 stale    newer
   │        │
 reject   accept
```

This protects the context store from out-of-order updates.

---

## 9. Action Limits

The tick endpoint respects the challenge's action limit and stops producing actions after the configured maximum.

This prevents excessive responses from a single tick.

---

## 10. Lightweight API

The service uses FastAPI and Uvicorn.

The architecture intentionally avoids unnecessary infrastructure so that the challenge bot remains:

* lightweight
* fast
* easy to deploy
* easy to inspect

---

# 🏗 Architecture

The application is organized into several logical layers.

```text
                         ┌───────────────────────┐
                         │      Vera Judge       │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │     FastAPI App       │
                         │      app/main.py      │
                         └───────────┬───────────┘
                                     │
                ┌────────────────────┼────────────────────┐
                │                    │                    │
                ▼                    ▼                    ▼
       ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
       │ Context Store  │   │ Conversation   │   │  Suppression   │
       │                │   │     Store      │   │     Store      │
       └───────┬────────┘   └───────┬────────┘   └───────┬────────┘
               │                    │                    │
               └────────────────────┼────────────────────┘
                                    │
                                    ▼
                         ┌───────────────────────┐
                         │   State Machine       │
                         │ core/state_machine.py │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ Deterministic        │
                         │ Composer             │
                         │ composer/             │
                         │ deterministic.py      │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │    Action / Reply     │
                         └───────────────────────┘
```

---

# 🔄 System Flow

## Context Flow

The judge first pushes structured context.

```text
Category
   ↓
Merchant
   ↓
Customer
   ↓
Trigger
```

Each context object is stored according to its scope and version.

---

## Tick Flow

When the judge calls:

```http
POST /v1/tick
```

the application:

1. Reads the available trigger IDs.
2. Loads each trigger.
3. Resolves its merchant.
4. Resolves the merchant's category.
5. Resolves customer information when available.
6. Checks trigger expiration.
7. Checks suppression state.
8. Passes relevant context to the deterministic composer.
9. Generates an action.
10. Stores suppression information.
11. Returns the generated actions.

---

## Reply Flow

When the judge calls:

```http
POST /v1/reply
```

the application:

1. Stores the incoming message.
2. Tracks merchant messages where applicable.
3. Loads the conversation.
4. Passes the message to the state machine.
5. Determines whether to:

   * respond
   * wait
   * end
6. Updates conversation state.
7. Returns the appropriate response.

---

# 📁 Project Structure

```text
magicpin-ai-challenge/
│
├── app/
│   ├── composer/
│   │   └── deterministic.py
│   │
│   ├── core/
│   │   ├── state_machine.py
│   │   └── suppression.py
│   │
│   ├── stores/
│   │   ├── context_store.py
│   │   └── conversation_store.py
│   │
│   ├── main.py
│   └── models.py
│
├── dataset/
│
├── examples/
│
├── challenge-brief.md
├── challenge-testing-brief.md
├── engagement-design.md
├── engagement-research.md
│
├── judge_simulator.py
├── requirements.txt
├── .gitignore
└── README.md
```

---

# 🗂 Context Management

The context store maintains challenge-provided information by scope.

Supported scopes include:

```text
category
merchant
customer
trigger
```

Each context is identified using a context ID and associated version.

For example:

```text
merchant
   │
   └── merchant_id

category
   │
   └── category_slug

customer
   │
   └── customer_id

trigger
   │
   └── trigger_id
```

The `/v1/context` endpoint acts as the ingestion layer.

---

# 🧩 Context Versioning

Context updates follow a version-aware model.

Suppose the current merchant context is:

```text
merchant_123 → version 5
```

and an incoming update contains:

```text
version 3
```

The update is rejected as stale.

If the incoming update contains:

```text
version 6
```

it replaces the previous version.

This prevents old data from overwriting newer context.

---

# ✍️ Deterministic Composer

The main message generation logic lives in:

```text
app/composer/deterministic.py
```

The composer receives structured context and produces a normalized composition result.

Conceptually:

```python
{
    "body": "...",
    "cta": "...",
    "send_as": "...",
    "rationale": "..."
}
```

The composition process considers information such as:

* merchant identity
* merchant attributes
* category
* trigger reason
* customer context
* available engagement opportunity

The resulting message is intended to feel:

* relevant
* concise
* contextual
* conversational
* actionable

---

# 🧠 Conversation State Machine

Conversation handling is implemented in:

```text
app/core/state_machine.py
```

The system models the conversation lifecycle using controlled states.

```text
             merchant/customer reply
                       │
                       ▼
                ┌──────────────┐
                │   ENGAGED    │
                └──────┬───────┘
                       │
            ┌──────────┼──────────┐
            │          │          │
            ▼          ▼          ▼
         reply       wait        end
            │          │          │
            ▼          ▼          ▼
        ENGAGED      WAITING     ENDED
```

This keeps conversations from becoming uncontrolled loops.

---

# 🛑 Suppression System

The suppression system is implemented in:

```text
app/core/suppression.py
```

Each trigger may provide a suppression key.

Once an engagement is successfully generated, the corresponding key can be suppressed.

This provides protection against:

```text
same trigger
     ↓
same tick
     ↓
same opportunity
     ↓
repeated message
```

Instead:

```text
first valid opportunity → send
subsequent duplicate    → suppress
```

---

# 🌐 API Reference

## 1. `GET /v1/healthz`

Returns service health information.

### Example

```http
GET /v1/healthz
```

### Response

```json
{
  "status": "ok",
  "uptime_seconds": 120,
  "contexts_loaded": {
    "category": 5,
    "merchant": 10,
    "customer": 25,
    "trigger": 25
  }
}
```

The endpoint is useful for:

* deployment verification
* uptime monitoring
* judge warm-up
* debugging

---

# 2. `GET /v1/metadata`

Returns bot metadata.

### Example

```http
GET /v1/metadata
```

### Response

```json
{
  "team_name": "Antigravity",
  "team_members": [
    "Agent"
  ],
  "model": "Deterministic (Fallback)",
  "approach": "Deterministic Composer with robust state machine",
  "contact_email": "agent@example.com",
  "version": "1.0.0"
}
```

---

# 3. `POST /v1/context`

Pushes structured challenge context into the bot.

### Request

The endpoint accepts:

* scope
* context ID
* version
* payload

Conceptually:

```json
{
  "scope": "merchant",
  "context_id": "merchant_123",
  "version": 2,
  "payload": {
    "name": "Example Merchant"
  }
}
```

### Successful Response

```json
{
  "accepted": true,
  "ack_id": "ack_merchant_123_v2",
  "stored_at": "..."
}
```

### Stale Version

```json
{
  "accepted": false,
  "reason": "stale_version",
  "current_version": 3
}
```

---

# 4. `POST /v1/tick`

Evaluates available engagement triggers.

### Conceptual Request

```json
{
  "now": "2026-09-27T10:00:00Z",
  "available_triggers": [
    "trigger_001",
    "trigger_002"
  ]
}
```

### Conceptual Response

```json
{
  "actions": [
    {
      "conversation_id": "conv_merchant_123_trigger_001",
      "merchant_id": "merchant_123",
      "customer_id": "customer_456",
      "send_as": "merchant",
      "trigger_id": "trigger_001",
      "template_name": "deterministic_v1",
      "template_params": [],
      "body": "Context-aware engagement message...",
      "cta": "Explore now",
      "suppression_key": "example_key",
      "rationale": "Relevant engagement opportunity based on trigger and merchant context."
    }
  ]
}
```

---

# 5. `POST /v1/reply`

Handles incoming conversation messages.

### Conceptual Request

```json
{
  "conversation_id": "conv_merchant_123_trigger_001",
  "merchant_id": "merchant_123",
  "from_role": "merchant",
  "message": "Yes, tell me more",
  "turn_number": 2
}
```

The state machine can return one of the supported conversational actions.

### Response Types

#### Continue

```json
{
  "action": "reply",
  "body": "...",
  "cta": "...",
  "rationale": "..."
}
```

#### Wait

```json
{
  "action": "wait",
  "wait_seconds": 1800,
  "rationale": "..."
}
```

#### End

```json
{
  "action": "end",
  "rationale": "..."
}
```

---

# 🔍 Decision Pipeline

The complete decision process can be represented as:

```text
                    Trigger
                       │
                       ▼
              Is trigger available?
                       │
                 ┌─────┴─────┐
                 │           │
                NO          YES
                 │           │
               SKIP         ▼
                       Merchant exists?
                              │
                         ┌────┴────┐
                         │         │
                        NO        YES
                         │         │
                       SKIP        ▼
                              Category exists?
                                    │
                               ┌────┴────┐
                               │         │
                              NO        YES
                               │         │
                             SKIP        ▼
                                  Customer context
                                  if available
                                      │
                                      ▼
                                Expiration check
                                      │
                                      ▼
                                Suppression check
                                      │
                                      ▼
                           Deterministic Composer
                                      │
                                      ▼
                               Generated Action
                                      │
                                      ▼
                             Suppression recorded
```

This pipeline keeps invalid or duplicate opportunities from reaching the user.

---

# 🛡 Safety and Guardrails

The bot applies several structural guardrails.

## Missing Context

If required context cannot be resolved, the trigger is skipped rather than generating an unsupported message.

---

## Expired Triggers

Expired triggers are ignored.

---

## Duplicate Suppression

Previously handled suppression keys are ignored.

---

## Action Limit

The tick endpoint limits the number of generated actions.

---

## State Control

Conversation states prevent unlimited automatic replies.

---

## Version Protection

Stale context updates do not overwrite newer versions.

---

# ⚙️ Reliability Design

The application intentionally keeps its critical decision path deterministic.

The main reliability principles are:

### Predictable

The same structured inputs produce consistent decisions.

### Observable

Health and metadata endpoints provide deployment visibility.

### Modular

Context management, composition, suppression, and conversation handling are separated.

### Testable

The deterministic components can be exercised independently.

### Lightweight

No heavyweight database or external orchestration layer is required for the challenge flow.

---

# 🧪 Testing

Testing was performed at multiple levels.

## Syntax Validation

Python modules were compiled/validated during development.

Example:

```bash
python -m py_compile app/main.py
```

---

## Local API Testing

The API was tested locally using the challenge judge simulator.

The following were exercised:

```text
/v1/healthz
/v1/metadata
/v1/context
/v1/tick
/v1/reply
```

---

# 🧑‍⚖️ Judge Simulation

The provided judge simulator was also used against the **public Render deployment** rather than only localhost.

The live evaluation exercised:

* health check
* metadata
* context ingestion
* category context
* merchant context
* trigger context
* tick processing
* generated actions
* scoring workflow

The public deployment successfully completed the full supplied evaluation flow.

### Evaluation Configuration

The supplied judge loaded:

```text
5 categories
10 merchants
25 triggers
25 evaluated messages
```

The test completed successfully against the deployed endpoint.

### Local Judge Result

The supplied judge produced an average score of:

```text
35 / 50
70%
```

with approximately:

```text
Specificity       7/10
Category Fit      7/10
Merchant Fit      7/10
Decision Quality  7/10
Engagement        7/10
```

This result is included as an engineering validation reference. The official Vera evaluation may use its own scenarios, scoring process, and evaluation data.

---

# 🚀 Deployment

The application is deployed using **Render**.

Deployment configuration:

```text
Runtime: Python
Build Command:
pip install -r requirements.txt

Start Command:
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

The service is configured to listen on the port provided by Render.

---

# ☁️ Production Endpoint

Current public deployment:

```text
https://magicpin-ai-challenge-4nmt.onrender.com/
```

API routes:

```text
GET  /v1/healthz
GET  /v1/metadata
POST /v1/context
POST /v1/tick
POST /v1/reply
```

---

# 💻 Local Development

## 1. Clone Repository

```bash
git clone https://github.com/rajatdagar2005/magicpin-ai-challenge.git
cd magicpin-ai-challenge
```

---

## 2. Create Virtual Environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Run Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

The API will be available at:

```text
http://localhost:8080
```

---

# 📦 Dependencies

The primary runtime dependencies are intentionally minimal.

```text
fastapi
uvicorn
pydantic
```

This keeps the deployment lightweight and reduces unnecessary dependency complexity.

---

# 🔐 Environment Variables

Secrets should **never be committed to Git**.

The local `.env` file is ignored using `.gitignore`.

For deployment environments, sensitive credentials should be configured through the platform's environment-variable system.

Example:

```text
GROQ_API_KEY=<configured securely in environment>
```

The actual secret value is intentionally not included in this repository.

---

# 🔁 Example End-to-End Flow

A typical challenge interaction looks like this:

## Step 1 — Context Push

The judge pushes a category:

```text
POST /v1/context
```

↓

The category is stored.

---

## Step 2 — Merchant Context

The judge pushes merchant information.

```text
POST /v1/context
```

↓

Merchant is stored and linked to its category.

---

## Step 3 — Trigger Context

A trigger is pushed.

```text
POST /v1/context
```

↓

The trigger becomes available for evaluation.

---

## Step 4 — Tick

The judge sends:

```text
POST /v1/tick
```

↓

The bot resolves:

```text
trigger
  ↓
merchant
  ↓
category
  ↓
customer
```

↓

The composer generates a contextual action.

---

## Step 5 — Conversation

The user/merchant responds.

```text
POST /v1/reply
```

↓

The state machine determines:

```text
reply
wait
end
```

↓

Conversation state is updated.

---

# 🧱 Design Decisions

## Why a Deterministic Composer?

The challenge requires reliable behavior over structured context.

A deterministic composer provides:

* reproducibility
* low latency
* predictable output
* easier debugging
* easier testing
* controlled decision boundaries

A generative model can be useful for richer language generation, but using it as the sole decision-maker can introduce variability.

Therefore, the architecture separates:

```text
Decision Logic
      +
Message Composition
```

from uncontrolled model behavior.

---

# 🎯 Separation of Concerns

The project intentionally separates major responsibilities.

### `main.py`

HTTP/API orchestration.

### `models.py`

Request and response schemas.

### `context_store.py`

Context ingestion and versioning.

### `conversation_store.py`

Conversation persistence and merchant-message tracking.

### `state_machine.py`

Conversation decision logic.

### `suppression.py`

Duplicate engagement prevention.

### `deterministic.py`

Context-aware message composition.

This makes individual components easier to modify and test.

---

# 📈 Performance Considerations

The core path is designed to be lightweight.

Most operations involve:

* in-memory lookups
* dictionary-based context resolution
* deterministic branching
* lightweight object construction

No expensive database round-trip is required for the challenge's core flow.

This is especially useful under evaluation constraints involving:

* request timeouts
* request rate limits
* repeated context operations
* multiple triggers per tick

---

# 🔄 Idempotency-Oriented Behavior

The combination of:

```text
context versioning
+
suppression keys
+
conversation state
```

helps prevent accidental repeated processing.

For example:

```text
same context version
→ no unnecessary replacement

same suppression key
→ no repeated engagement

ended conversation
→ no uncontrolled continuation
```

---

# 🧪 Edge Cases Considered

The implementation accounts for scenarios such as:

* missing merchant context
* missing category context
* optional customer context
* stale context versions
* expired triggers
* duplicate suppression keys
* multiple available triggers
* repeated merchant messages
* conversation termination
* waiting behavior
* maximum action count

The goal is to fail safely by skipping invalid opportunities instead of producing fabricated context.

---

# ⚠️ Limitations

This implementation is intentionally optimized for the challenge environment.

### In-Memory State

The stores are in-memory.

A production-scale deployment would normally require durable storage such as:

```text
PostgreSQL
Redis
or another persistent datastore
```

for distributed state management.

---

### Single-Service Architecture

The application currently runs as one FastAPI service.

At larger scale, the architecture could be split into:

```text
API Gateway
      │
      ├── Context Service
      ├── Engagement Engine
      ├── Conversation Service
      ├── Suppression Service
      └── Analytics
```

---

### Deterministic Language Generation

The deterministic approach prioritizes consistency over unlimited natural-language variation.

A production implementation could introduce a controlled LLM layer while keeping the deterministic policy engine responsible for:

* eligibility
* safety
* context selection
* suppression
* conversation state

---

# 🔮 Future Improvements

If this system were extended beyond the challenge, several improvements could be added.

## 1. Persistent Storage

Replace in-memory stores with:

```text
PostgreSQL + Redis
```

for durability and distributed deployments.

---

## 2. Controlled LLM Layer

Use an LLM only after deterministic eligibility checks.

```text
Context
   ↓
Policy Engine
   ↓
Eligible?
   ↓
LLM-assisted wording
   ↓
Validation
   ↓
Response
```

This would provide richer language while maintaining predictable business logic.

---

## 3. Observability

Add:

* structured logs
* request IDs
* latency metrics
* error rates
* engagement conversion metrics

---

## 4. Automated Tests

Add a dedicated test suite covering:

```text
context versioning
trigger expiration
suppression
conversation transitions
missing context
maximum actions
```

---

## 5. Persistent Conversation History

A production system could retain conversation history for:

* personalization
* analytics
* re-engagement
* customer support
* experimentation

---

## 6. Experimentation Framework

Different message strategies could be evaluated using controlled experiments:

```text
Strategy A
Strategy B
Strategy C
```

with metrics such as:

* engagement rate
* response rate
* conversion
* opt-out rate

---

# 📋 Challenge Compliance

| Requirement                 | Implementation      |
| --------------------------- | ------------------- |
| Public bot endpoint         | ✅ Render deployment |
| `POST /v1/context`          | ✅                   |
| `POST /v1/tick`             | ✅                   |
| `POST /v1/reply`            | ✅                   |
| `GET /v1/healthz`           | ✅                   |
| `GET /v1/metadata`          | ✅                   |
| Context version handling    | ✅                   |
| Trigger expiration handling | ✅                   |
| Suppression handling        | ✅                   |
| Conversation state          | ✅                   |
| Maximum action control      | ✅                   |
| Deterministic composition   | ✅                   |
| Public endpoint validation  | ✅                   |
| Judge simulator testing     | ✅                   |

---

# 🏁 Final Status

The MagicPin Vera AI Challenge bot is deployed and publicly accessible.

### Current Deployment

```text
https://magicpin-ai-challenge-4nmt.onrender.com/
```

### API

```text
GET  /v1/healthz
GET  /v1/metadata

POST /v1/context
POST /v1/tick
POST /v1/reply
```

### Validation

The supplied judge simulator successfully exercised the deployed public service through the complete challenge flow.

---

# 👨‍💻 Author

## Rajat Dagar

**B.Tech Computer Science & Engineering — JIIT Noida**

### Profiles

* GitHub: `rajatdagar2005`
* LinkedIn: `rajat-dagar-822a76291`
* Portfolio: `rajatdagar.vercel.app`

---

# ⭐ Repository

If you find the architecture or deterministic engagement approach useful, feel free to explore the repository and the implementation.

**Repository:**

https://github.com/rajatdagar2005/magicpin-ai-challenge

---

## 🧠 Engineering Philosophy

The project follows a simple principle:

> **Make the decision deterministic, make the context explicit, and make the conversation controlled.**

The result is a lightweight conversational engagement system designed to be:

```text
Context-aware
      +
Deterministic
      +
Stateful
      +
Testable
      +
Deployable
```

---

**Built for the MagicPin Vera AI Challenge. 🚀**
