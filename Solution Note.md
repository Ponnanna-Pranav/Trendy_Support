# Solution Note – Trendly Agentic Support Assistant

## Overview

The Trendly Agentic Support Assistant is an AI-powered customer support system designed to automate repetitive support requests while safely escalating complex cases to human agents.

The assistant is built using an agent-based architecture rather than simple prompt-response logic. It combines LLM reasoning with tool calling, conversation memory, business rule validation, and policy grounding to complete customer requests end-to-end.

The primary objectives are:

- Reduce repetitive support workload
- Prevent hallucinated policy answers
- Safely perform return/exchange decisions
- Maintain conversation context
- Escalate only when appropriate

---

# Architecture

```
                User
                  │
                  ▼
          FastAPI Backend
                  │
                  ▼
          Agent Orchestrator
                  │
      ┌───────────┼─────────────┐
      │           │             │
      ▼           ▼             ▼
 Order Tool   Policy Tool   Eligibility Tool
      │           │             │
      ▼           ▼             ▼
 orders.json  trendly_policy.md Business Rules
      │
      ▼
 Escalation Generator
      │
      ▼
 Structured Response
```

## Components

### 1. Agent Orchestrator

The orchestrator is responsible for deciding which tool(s) should be executed.

Instead of matching keywords, the LLM reasons about the user's intent and selects the appropriate function:

- Order lookup
- Policy lookup
- Return eligibility
- Exchange eligibility
- Escalation
- Refusal

The orchestration layer also manages conversation state across multiple turns.

---

### 2. Order Lookup Tool

Reads the provided `orders.json`.

Capabilities:

- Fetch order by ID
- Explain shipment progress
- Detect delayed shipments
- Detect delivered orders
- Detect cancelled orders
- Detect missing orders

Instead of returning raw JSON, the assistant converts the data into customer-friendly language.

---

### 3. Policy Retrieval Tool

All policy questions are answered only using `trendly_policy.md`.

The assistant never answers from model memory.

If the requested information is not present in the policy document, it explicitly responds:

> "I couldn't find that information in Trendly's policy."

This eliminates policy hallucination.

---

### 4. Eligibility Engine

This tool combines:

- order information
- policy rules

to determine whether a return or exchange is allowed.

Example checks include:

- delivery date
- return window
- product condition
- final-sale items
- cancellation status

The decision is deterministic, while the LLM explains the reasoning in natural language.

---

### 5. Escalation Tool

If the assistant cannot safely resolve the issue, it generates a structured handoff.

Example:

Customer:
Sarah Johnson

Issue:
Package marked delivered but customer never received it.

Actions already taken:
- Verified order
- Checked delivery status
- Reviewed policy

Recommended next step:
Human investigation with shipping partner.

This minimizes repeated questioning after transfer.

---

### 6. Safety Layer

The assistant refuses requests such as:

- unauthorized refunds
- policy fabrication
- leaking customer information
- modifying unrelated orders
- giving discounts without authorization

Unknown requests are escalated rather than guessed.

---

# Key Design Trade-offs

## 1. Rule-Based Decisions vs LLM Decisions

Return eligibility is implemented using deterministic business rules instead of allowing the LLM to decide.

Pros

- Consistent
- Explainable
- Easy to test

Cons

- Requires explicit rule implementation.

---

## 2. Grounded Policy Responses

Policy answers are generated only from the provided markdown file.

Pros

- No hallucinations
- Predictable behavior

Cons

- Cannot answer questions outside the document.

---

## 3. Simple Conversation Memory

The assistant stores only relevant context from previous turns (order ID, intent, customer state).

Pros

- Lightweight
- Easy to maintain

Cons

- Limited long-term memory.

---

## 4. Local JSON Instead of Database

The assignment provides only 10 orders, so JSON was chosen instead of a database.

Pros

- Zero setup
- Fast lookup

Cons

- Not scalable for production.

---

# Known Limitations

- Uses a static JSON dataset.
- No customer authentication.
- Single-language support.
- No real shipping carrier integration.
- No payment gateway integration.
- Limited conversation memory.
- Does not execute real refunds or exchanges.
- Policy updates require replacing the markdown file.
- Escalation is simulated instead of creating actual support tickets.

---

# Future Improvements

Given additional development time, I would add:

- Vector search over policy documents
- Authentication using customer accounts
- Real OMS integration
- Shipping carrier APIs
- CRM integration (Zendesk/Freshdesk)
- Persistent conversation memory
- Human feedback learning
- Analytics dashboard
- Multi-language support
- Voice support

---

# Discovery Questions for Trendly's Operations Team

Before building this system for production, I would ask:

### 1. What are the top reasons chats are escalated today?

Understanding the current escalation patterns helps prioritize automation and identify common failure cases.

---

### 2. Which actions is the AI actually allowed to perform?

For example:

- initiate returns?
- cancel orders?
- issue refunds?
- apply discounts?

Understanding operational permissions is critical for designing safe automation.

---

### 3. Where does the order information come from?

Is there:

- Shopify
- Magento
- OMS
- ERP
- Custom API

This determines the production tool integrations.

---

### 4. What information must always be collected before handing off to an agent?

Knowing the required escalation context helps minimize repeated customer questions and reduce handling time.

---

### 5. How is success measured?

Examples:

- First Contact Resolution
- Average Handle Time
- Containment Rate
- CSAT
- Escalation Rate

These metrics directly influence orchestration strategy and prompt design.

---

# Conclusion

The assistant focuses on safe automation rather than answering everything. It combines deterministic business logic with LLM reasoning, grounds all policy answers in official documentation, maintains conversational context, and escalates complex situations with actionable summaries.

The architecture is intentionally modular, making it straightforward to replace local JSON tools with production APIs while preserving the orchestration layer.