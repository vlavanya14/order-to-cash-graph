import sqlite3
import os
import re
from database import get_connection, get_schema

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    GEMINI_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    Groq = None
    GROQ_AVAILABLE = False

# ── LLM Provider: Groq (primary), Gemini (fallback) ──────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Initialize Groq client if available
groq_client = None
if GROQ_API_KEY and GROQ_AVAILABLE:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"⚠️  Failed to initialize Groq client: {e}")

if GROQ_API_KEY and GEMINI_API_KEY and GEMINI_AVAILABLE:
    genai.configure(api_key=GEMINI_API_KEY)
    LLM_PROVIDER = "groq"  # Will fallback to Gemini on failure
    print("🤖 LLM Provider: Groq (with Gemini fallback)")
elif GROQ_API_KEY:
    LLM_PROVIDER = "groq"
    print("🤖 LLM Provider: Groq (llama3-8b-8192)")
elif GEMINI_API_KEY and GEMINI_AVAILABLE:
    genai.configure(api_key=GEMINI_API_KEY)
    LLM_PROVIDER = "gemini"
    print("🤖 LLM Provider: Gemini")
else:
    LLM_PROVIDER = "none"
    print("⚠️  No LLM API key found. Set GROQ_API_KEY or GEMINI_API_KEY in .env")

DOMAIN_KEYWORDS = [
    "order", "delivery", "billing", "invoice", "payment", "journal",
    "customer", "product", "material", "sales", "document", "entry",
    "cash", "flow", "shipped", "billed", "po", "so", "gl", "account",
    "partner", "plant", "quantity", "amount", "currency", "status",
    "schedule", "cancell", "clearing", "fiscal", "accounting", "net",
    "gross", "total", "organization", "division", "channel", "region",
    "address", "city", "country", "weight", "trace", "track", "find",
    "show", "list", "which", "what", "how many", "identify", "broken",
    "incomplete", "highest", "lowest", "top", "bottom", "count", "sum"
]

SCHEMA_DESCRIPTION = """
Tables and their key columns:

1. sales_order_headers: salesOrder(PK), soldToParty(->customer), salesOrderType, 
   salesOrganization, totalNetAmount, overallDeliveryStatus, overallOrdReltdBillgStatus,
   transactionCurrency, creationDate, requestedDeliveryDate

2. sales_order_items: salesOrder(->SO), salesOrderItem, material(->product), 
   requestedQuantity, netAmount, productionPlant, storageLocation

3. outbound_delivery_headers: deliveryDocument(PK), shippingPoint, 
   overallGoodsMovementStatus, overallPickingStatus, creationDate

4. outbound_delivery_items: deliveryDocument(->delivery), deliveryDocumentItem, 
   referenceSdDocument(->salesOrder), referenceSdDocumentItem, plant, 
   actualDeliveryQuantity, storageLocation

5. billing_document_headers: billingDocument(PK), soldToParty(->customer), 
   billingDocumentType, billingDocumentDate, totalNetAmount, transactionCurrency,
   companyCode, fiscalYear, accountingDocument(->journalEntry), 
   billingDocumentIsCancelled, cancelledBillingDocument

6. billing_document_items: billingDocument(->billing), billingDocumentItem, 
   material(->product), referenceSdDocument(->deliveryDocument), 
   billingQuantity, netAmount

7. journal_entries: accountingDocument(PK), accountingDocumentItem, 
   referenceDocument(->billingDocument), companyCode, fiscalYear, glAccount, 
   amountInTransactionCurrency, transactionCurrency, postingDate, customer,
   clearingDate, clearingAccountingDocument, accountingDocumentType

8. payments: accountingDocument, accountingDocumentItem, clearingAccountingDocument,
   clearingDate, amountInTransactionCurrency, transactionCurrency, customer,
   invoiceReference, salesDocument, postingDate

9. business_partners: businessPartner(PK), customer, businessPartnerName, 
   organizationBpName1, businessPartnerCategory, creationDate, industry

10. product_descriptions: product(->products), language, productDescription

11. plants: plant(PK), plantName, salesOrganization, distributionChannel

12. products: product(PK), productType, grossWeight, weightUnit, netWeight, productGroup

KEY RELATIONSHIPS:
- sales_order_headers.soldToParty = business_partners.customer
- sales_order_items.salesOrder = sales_order_headers.salesOrder
- sales_order_items.material = products.product
- outbound_delivery_items.referenceSdDocument = sales_order_headers.salesOrder
- outbound_delivery_items.deliveryDocument = outbound_delivery_headers.deliveryDocument
- billing_document_items.referenceSdDocument = outbound_delivery_headers.deliveryDocument
- billing_document_headers.accountingDocument = journal_entries.accountingDocument
- journal_entries.referenceDocument = billing_document_headers.billingDocument
- product_descriptions.product = products.product (filter language='EN')
"""


def is_relevant_query(user_query: str) -> bool:
    q = user_query.lower()
    return any(kw in q for kw in DOMAIN_KEYWORDS)


def call_groq(prompt: str) -> str:
    if not groq_client:
        raise RuntimeError("Groq client not initialized")
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.1
    )
    return response.choices[0].message.content.strip()


def call_gemini(prompt: str) -> str:
    if not GEMINI_AVAILABLE or genai is None:
        raise RuntimeError("Gemini not available")
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return response.text.strip()


def call_llm(prompt: str) -> str:
    if LLM_PROVIDER == "groq":
        try:
            print("🔄 Trying Groq...")
            return call_groq(prompt)
        except Exception as e:
            print(f"🔁 Groq failed ({type(e).__name__}), trying Gemini fallback: {e}")
            if GEMINI_API_KEY and GEMINI_AVAILABLE:
                try:
                    print("🔄 Trying Gemini fallback...")
                    return call_gemini(prompt)
                except Exception as e2:
                    print(f"❌ Gemini fallback also failed: {e2}")
                    # Provide helpful error message with solutions
                    groq_error = str(e)[:200] if len(str(e)) > 200 else str(e)
                    gemini_error = str(e2)[:200] if len(str(e2)) > 200 else str(e2)
                    return f"""SELECT 'Both LLM providers failed.

Groq Error: {groq_error}
Gemini Error: {gemini_error}

SOLUTIONS:
1. Get a new Groq API key from https://console.groq.com/
2. Upgrade your Gemini API quota at https://makersuite.google.com/app/apikey
3. Or use the system without LLM queries for now.

Please update your .env file with working API keys.' AS message;"""
            else:
                print("❌ No Gemini API key available for fallback")
                return f"""SELECT 'Groq API failed: {str(e)[:200] if len(str(e)) > 200 else str(e)}

SOLUTION: Get a new Groq API key from https://console.groq.com/ and update your .env file.' AS message;"""
    elif LLM_PROVIDER == "gemini":
        try:
            return call_gemini(prompt)
        except Exception as e:
            return f"""SELECT 'Gemini API failed: {str(e)[:200] if len(str(e)) > 200 else str(e)}

SOLUTION: Check your Gemini API quota at https://makersuite.google.com/app/apikey' AS message;"""
    else:
        return "SELECT 'LLM not configured. Please set GROQ_API_KEY or GEMINI_API_KEY in .env' AS message;"


def generate_sql(user_query: str) -> str:
    prompt = f"""You are an expert SQLite SQL generator for an Order-to-Cash SAP-like business database.

{SCHEMA_DESCRIPTION}

User question: "{user_query}"

Rules:
1. Return ONLY valid SQLite SQL - no explanations, no markdown, no backticks, no comments.
2. LIMIT results to 50 rows.
3. Use only tables and columns listed above.
4. For product names always JOIN product_descriptions WHERE language='EN'.
5. For "broken flow": find sales orders with delivery but no billing, or billing but no journal entry.
6. If query cannot be answered, return: SELECT 'Data not available for this query' AS message;
7. Always use correct joins based on relationships.
8. If query involves billing → JOIN billing_document_items and billing_document_headers.
9. If query involves delivery → JOIN outbound_delivery_items.
10. For customer totals → GROUP BY soldToParty.
11. For missing flows → use LEFT JOIN and check NULL.

SQL:"""

    sql = call_llm(prompt)
    sql = re.sub(r"```sql|```", "", sql).strip()
    if not sql.upper().strip().startswith("SELECT"):
        sql = "SELECT 'Invalid query generated' AS message;"
    return sql


def run_sql(sql: str) -> dict:
    conn = get_connection()
    try:
        cursor = conn.execute(sql)
        cols = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        return {"columns": cols, "rows": [list(r) for r in rows], "error": None}
    except Exception as e:
        conn.close()
        return {"columns": [], "rows": [], "error": str(e)}


def generate_natural_response(user_query: str, sql: str, data: dict) -> str:
    if data.get("error"):
        return f"I encountered a database error: {data['error']}\n\nSQL tried:\n{sql}"

    rows = data.get("rows", [])
    cols = data.get("columns", [])

    if not rows or "Data not available" in str(rows):
        return "No data available for this query."

    sample_lines = []
    for row in rows[:15]:
        line = ", ".join(f"{cols[i]}: {row[i]}" for i in range(min(len(cols), len(row))))
        sample_lines.append(line)
    sample = "\n".join(sample_lines)

    prompt = f"""You are a business analyst for an Order-to-Cash process. Answer the user's question based on query results.

User question: "{user_query}"
Total rows returned: {len(rows)}
Sample results:
{sample}

Instructions:
- Give a clear, concise business answer in plain English.
- Mention specific IDs, amounts, counts from the data.
- No SQL, no technical jargon.
- Keep it under 150 words.
"""
    return call_llm(prompt)


def process_query(user_query: str) -> dict:
    if not is_relevant_query(user_query):
        return {
            "answer": "This system is designed to answer questions related to the Order-to-Cash dataset only. Please ask about sales orders, deliveries, billing documents, payments, customers, or products.",
            "sql": None,
            "data": None,
            "blocked": True
        }

    try:
        if "billing but no journal" in user_query.lower():
            sql = """
            SELECT b.billingDocument, b.soldToParty, b.totalNetAmount
            FROM billing_document_headers b
            LEFT JOIN journal_entries j
            ON b.accountingDocument = j.accountingDocument
            WHERE j.accountingDocument IS NULL
            LIMIT 50;
            """
            data = run_sql(sql)
            answer = generate_natural_response(user_query, sql, data)
            return {"answer": answer, "sql": sql, "data": data, "blocked": False}
        
        if "deliver" in user_query.lower() and "bill" in user_query.lower():
            sql = """
            SELECT DISTINCT o.referenceSdDocument AS salesOrder
            FROM outbound_delivery_items o
            LEFT JOIN billing_document_items b
            ON o.deliveryDocument = b.referenceSdDocument
            WHERE b.referenceSdDocument IS NULL
            LIMIT 50;
            """
            data = run_sql(sql)
            answer = generate_natural_response(user_query, sql, data)
            return {"answer": answer, "sql": sql, "data": data, "blocked": False}
        
        if "total billed amount per customer" in user_query.lower():
            sql = """
            SELECT b.soldToParty AS customer, 
                   SUM(b.totalNetAmount) AS total_billed
            FROM billing_document_headers b
            GROUP BY b.soldToParty
            ORDER BY total_billed DESC
            LIMIT 50;
            """
            data = run_sql(sql)
            answer = generate_natural_response(user_query, sql, data)
            return {"answer": answer, "sql": sql, "data": data, "blocked": False}
        
        if "highest total order amounts" in user_query.lower():
            sql = """
            SELECT soldToParty AS customer,
                   SUM(totalNetAmount) AS total_order_amount
            FROM sales_order_headers
            GROUP BY soldToParty
            ORDER BY total_order_amount DESC
            LIMIT 50;
            """
            data = run_sql(sql)
            answer = generate_natural_response(user_query, sql, data)
            return {"answer": answer, "sql": sql, "data": data, "blocked": False}

        if "highest number of billing documents" in user_query.lower():
            sql = """
            SELECT p.product,
                   d.productDescription,
                   COUNT(*) AS billing_count
            FROM billing_document_items b
            JOIN product_descriptions d
                ON b.material = d.product AND d.language = 'EN'
            JOIN products p
                ON b.material = p.product
            GROUP BY p.product, d.productDescription
            ORDER BY billing_count DESC
            LIMIT 50;
            """
            data = run_sql(sql)
            answer = generate_natural_response(user_query, sql, data)
            return {"answer": answer, "sql": sql, "data": data, "blocked": False}

        if "customer" in user_query.lower() and ("total" in user_query.lower() or "amount" in user_query.lower()):
            sql = """
            SELECT soldToParty AS customer,
                   SUM(totalNetAmount) AS total_billed
            FROM billing_document_headers
            GROUP BY soldToParty
            ORDER BY total_billed DESC
            LIMIT 50;
            """
            data = run_sql(sql)
            answer = generate_natural_response(user_query, sql, data)
            return {"answer": answer, "sql": sql, "data": data, "blocked": False}

        if "highest sales" in user_query.lower():
            sql = """
            SELECT soldToParty AS customer,
                   SUM(totalNetAmount) AS total_sales
            FROM sales_order_headers
            GROUP BY soldToParty
            ORDER BY total_sales DESC
            LIMIT 50;
            """
            data = run_sql(sql)
            answer = generate_natural_response(user_query, sql, data)
            return {"answer": answer, "sql": sql, "data": data, "blocked": False}

        sql = generate_sql(user_query)
    except Exception as e:
        return {
            "answer": f"LLM generation failed: {e}",
            "sql": None,
            "data": None,
            "blocked": False
        }

    data = run_sql(sql)

    # Auto-retry on SQL error
    if data.get("error"):
        retry_prompt = f"""This SQLite query failed with error: {data['error']}
Question: "{user_query}"
Broken SQL: {sql}

Return ONLY corrected valid SQLite SQL, no markdown, no backticks.
{SCHEMA_DESCRIPTION}
Corrected SQL:"""
        sql = call_llm(retry_prompt)
        sql = re.sub(r"```sql|```", "", sql).strip()
        if sql.upper().strip().startswith("SELECT"):
            data = run_sql(sql)

    answer = generate_natural_response(user_query, sql, data)
    if "Data not available" in str(data.get("rows")):
        data = None

    return {"answer": answer, "sql": sql, "data": data, "blocked": False}