# Order-to-Cash Graph Explorer

A context graph system with LLM-powered natural language query interface for analyzing the Order-to-Cash business process.

## Architecture

```
Frontend (React + react-force-graph-2d)
    ↕ REST API (axios)
Backend (FastAPI + Python)
    ├── SQLite Database (all JSONL data loaded on startup)
    ├── NetworkX Graph (built from SQLite relationships)
    └── Google Gemini LLM (natural language → SQL → answer)
```

### Why SQLite?
- Zero setup, file-based, fast for read-heavy workloads
- The LLM generates SQL queries dynamically against it
- All 19 JSONL folders are loaded into tables on first startup

### Why NetworkX?
- Excellent for in-memory graph construction and traversal
- Graph is serialized to JSON and served to the frontend
- Handles directed edges (Sales Order → Delivery → Billing → Journal Entry)

### Graph Schema (Nodes & Edges)

```
Customer ──PLACED_ORDER──► SalesOrder ──HAS_ITEM──► SalesOrderItem
                                │                        │
                          HAS_DELIVERY              CONTAINS_PRODUCT
                                │                        │
                           Delivery ◄──SHIPS_FROM── Plant    Product
                                │
                          HAS_BILLING
                                │
                         BillingDocument
                                │
                        HAS_JOURNAL_ENTRY
                                │
                          JournalEntry
                                │
                           CLEARED_BY
                                │
                            Payment
```

## LLM Prompting Strategy

1. **Schema injection**: Full table schemas with relationships are embedded in every SQL generation prompt
2. **SQL-only output**: LLM is instructed to return raw SQLite SQL with no markdown
3. **Auto-retry**: On SQL error, the error message is fed back to the LLM for self-correction
4. **Natural language response**: Results are sent to a second LLM call for business-friendly summarization
5. **Table preview**: Raw query results shown alongside the natural language answer

## Guardrails

- **Keyword allowlist**: Only queries containing business-domain keywords are processed
- **SELECT-only enforcement**: Any non-SELECT SQL is rejected before execution
- **Off-topic rejection**: General knowledge, coding, creative writing questions are blocked with a clear message
- **Result grounding**: All answers reference actual data from the query results

## Setup

### 1. Clone and organize data

```bash
git clone <your-repo>
cd order-to-cash-graph
python setup_data.py /path/to/downloaded/data
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY from https://ai.google.dev
uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

## Data Structure

| Table | Source Folder | Key Fields |
|-------|--------------|------------|
| sales_order_headers | sales_order_headers/ | salesOrder, soldToParty, totalNetAmount |
| sales_order_items | sales_order_items/ | salesOrder, salesOrderItem, material |
| outbound_delivery_headers | outbound_delivery_headers/ | deliveryDocument |
| outbound_delivery_items | outbound_delivery_items/ | deliveryDocument, referenceSdDocument |
| billing_document_headers | billing_document_headers/ | billingDocument, accountingDocument |
| billing_document_items | billing_document_items/ | billingDocument, referenceSdDocument |
| journal_entries | journal_entry_items_accounts_receivable/ | accountingDocument, referenceDocument |
| payments | payments_accounts_receivable/ | accountingDocument, clearingAccountingDocument |
| business_partners | business_partners/ | businessPartner, customer |
| products | products/ | product, productType |

## Example Queries

- "Which products are associated with the highest number of billing documents?"
- "Trace the full flow of billing document 90504298"
- "Identify sales orders that have been delivered but not billed"
- "Which customers have the highest total order amounts?"
- "Show me sales orders with billing but no journal entry"
- "What is the total billed amount per customer?"

## LLM Provider

Using **Google Gemini 1.5 Flash** (free tier). 
Get your API key at: https://ai.google.dev

Alternative free providers:
- Groq (llama-3.1-8b-instant)
- OpenRouter
- HuggingFace Inference API
