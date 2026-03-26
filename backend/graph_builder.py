import sqlite3
import networkx as nx
from database import get_connection

# Node colors by type (used in frontend)
NODE_COLORS = {
    "SalesOrder":           "#4A90D9",
    "SalesOrderItem":       "#74B3E8",
    "Delivery":             "#50C878",
    "DeliveryItem":         "#82D9A0",
    "BillingDocument":      "#FF6B6B",
    "JournalEntry":         "#FFD700",
    "Payment":              "#FF9F40",
    "Customer":             "#9B59B6",
    "Product":              "#E67E22",
    "Plant":                "#1ABC9C",
}

def safe_fetch(conn, query, limit=500):
    try:
        cursor = conn.execute(query + f" LIMIT {limit}")
        cols = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        print(f"  ⚠️  Query error: {e}\n  Query: {query}")
        return []

def build_graph():
    conn = get_connection()
    G = nx.DiGraph()

    # ── Sales Order Headers ───────────────────────────────────
    records = safe_fetch(conn, "SELECT * FROM sales_order_headers")
    for r in records:
        nid = f"SO_{r.get('salesOrder','')}"
        G.add_node(nid, type="SalesOrder", label=f"SO {r.get('salesOrder','')}",
                   color=NODE_COLORS["SalesOrder"], **{k: str(v or '') for k,v in r.items()})

    # ── Sales Order Items ─────────────────────────────────────
    records = safe_fetch(conn, "SELECT * FROM sales_order_items")
    for r in records:
        so_id = f"SO_{r.get('salesOrder','')}"
        nid = f"SOI_{r.get('salesOrder','')}_{r.get('salesOrderItem','')}"
        G.add_node(nid, type="SalesOrderItem", label=f"Item {r.get('salesOrderItem','')}",
                   color=NODE_COLORS["SalesOrderItem"], **{k: str(v or '') for k,v in r.items()})
        if so_id in G:
            G.add_edge(so_id, nid, relation="HAS_ITEM")

    # ── Outbound Delivery Headers ──────────────────────────────
    records = safe_fetch(conn, "SELECT * FROM outbound_delivery_headers")
    for r in records:
        nid = f"DEL_{r.get('deliveryDocument','')}"
        G.add_node(nid, type="Delivery", label=f"DEL {r.get('deliveryDocument','')}",
                   color=NODE_COLORS["Delivery"], **{k: str(v or '') for k,v in r.items()})

    # ── Outbound Delivery Items → link to Sales Order ──────────
    records = safe_fetch(conn, "SELECT * FROM outbound_delivery_items")
    for r in records:
        del_id = f"DEL_{r.get('deliveryDocument','')}"
        so_id = f"SO_{r.get('referenceSdDocument','')}"
        # Link delivery → sales order
        if del_id in G and so_id in G:
            G.add_edge(so_id, del_id, relation="HAS_DELIVERY")

    # ── Billing Document Headers ───────────────────────────────
    records = safe_fetch(conn, "SELECT * FROM billing_document_headers")
    for r in records:
        nid = f"BILL_{r.get('billingDocument','')}"
        G.add_node(nid, type="BillingDocument", label=f"BILL {r.get('billingDocument','')}",
                   color=NODE_COLORS["BillingDocument"], **{k: str(v or '') for k,v in r.items()})

    # ── Billing Document Items → link to Delivery ─────────────
    records = safe_fetch(conn, "SELECT * FROM billing_document_items")
    for r in records:
        bill_id = f"BILL_{r.get('billingDocument','')}"
        del_id = f"DEL_{r.get('referenceSdDocument','')}"
        if bill_id in G and del_id in G:
            G.add_edge(del_id, bill_id, relation="HAS_BILLING")

    # Also link billing → sales order via billing headers soldToParty
    records = safe_fetch(conn, "SELECT billingDocument, soldToParty FROM billing_document_headers")
    for r in records:
        bill_id = f"BILL_{r.get('billingDocument','')}"
        cust_id = f"CUST_{r.get('soldToParty','')}"
        if bill_id in G and cust_id in G:
            G.add_edge(cust_id, bill_id, relation="CUSTOMER_BILLED")

    # ── Journal Entries → link to Billing Document ─────────────
    records = safe_fetch(conn, "SELECT * FROM journal_entries")
    for r in records:
        nid = f"JE_{r.get('accountingDocument','')}_{r.get('accountingDocumentItem','')}"
        G.add_node(nid, type="JournalEntry", label=f"JE {r.get('accountingDocument','')}",
                   color=NODE_COLORS["JournalEntry"], **{k: str(v or '') for k,v in r.items()})
        bill_id = f"BILL_{r.get('referenceDocument','')}"
        if bill_id in G:
            G.add_edge(bill_id, nid, relation="HAS_JOURNAL_ENTRY")

    # ── Payments → link to Journal Entry ──────────────────────
    records = safe_fetch(conn, "SELECT * FROM payments")
    for r in records:
        nid = f"PAY_{r.get('accountingDocument','')}_{r.get('accountingDocumentItem','')}"
        G.add_node(nid, type="Payment", label=f"PAY {r.get('accountingDocument','')}",
                   color=NODE_COLORS["Payment"], **{k: str(v or '') for k,v in r.items()})
        # Link clearing document
        clearing_id = f"JE_{r.get('clearingAccountingDocument','')}_1"
        if clearing_id in G:
            G.add_edge(clearing_id, nid, relation="CLEARED_BY")

    # ── Business Partners (Customers) ─────────────────────────
    records = safe_fetch(conn, "SELECT * FROM business_partners", limit=300)
    for r in records:
        nid = f"CUST_{r.get('customer','') or r.get('businessPartner','')}"
        G.add_node(nid, type="Customer",
                   label=f"CUST {r.get('businessPartnerName','') or r.get('businessPartner','')}",
                   color=NODE_COLORS["Customer"], **{k: str(v or '') for k,v in r.items()})

    # Link Customer → Sales Order via soldToParty
    records = safe_fetch(conn, "SELECT salesOrder, soldToParty FROM sales_order_headers")
    for r in records:
        so_id = f"SO_{r.get('salesOrder','')}"
        cust_id = f"CUST_{r.get('soldToParty','')}"
        if so_id in G and cust_id in G:
            G.add_edge(cust_id, so_id, relation="PLACED_ORDER")

    # ── Products ───────────────────────────────────────────────
    records = safe_fetch(conn, "SELECT p.product, pd.productDescription, p.productType, p.grossWeight, p.weightUnit FROM products p LEFT JOIN product_descriptions pd ON p.product = pd.product WHERE pd.language = 'EN' OR pd.language IS NULL", limit=300)
    for r in records:
        nid = f"PROD_{r.get('product','')}"
        G.add_node(nid, type="Product",
                   label=f"{r.get('productDescription','') or r.get('product','')}",
                   color=NODE_COLORS["Product"], **{k: str(v or '') for k,v in r.items()})

    # Link Product → Sales Order Item
    records = safe_fetch(conn, "SELECT salesOrder, salesOrderItem, material FROM sales_order_items")
    for r in records:
        soi_id = f"SOI_{r.get('salesOrder','')}_{r.get('salesOrderItem','')}"
        prod_id = f"PROD_{r.get('material','')}"
        if soi_id in G and prod_id in G:
            G.add_edge(soi_id, prod_id, relation="CONTAINS_PRODUCT")

    # ── Plants ────────────────────────────────────────────────
    records = safe_fetch(conn, "SELECT * FROM plants", limit=100)
    for r in records:
        nid = f"PLANT_{r.get('plant','')}"
        G.add_node(nid, type="Plant", label=f"Plant {r.get('plantName','') or r.get('plant','')}",
                   color=NODE_COLORS["Plant"], **{k: str(v or '') for k,v in r.items()})

    # Link Delivery Item → Plant
    records = safe_fetch(conn, "SELECT deliveryDocument, plant FROM outbound_delivery_items")
    for r in records:
        del_id = f"DEL_{r.get('deliveryDocument','')}"
        plant_id = f"PLANT_{r.get('plant','')}"
        if del_id in G and plant_id in G:
            if not G.has_edge(plant_id, del_id):
                G.add_edge(plant_id, del_id, relation="SHIPS_FROM")

    conn.close()
    print(f"✅ Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def graph_to_json(G, limit_nodes=600):
    """Convert graph to JSON for frontend, limiting size for performance."""
    # Prioritize by type order for sampling
    type_priority = ["Customer", "SalesOrder", "Delivery", "BillingDocument",
                     "JournalEntry", "Payment", "Product", "SalesOrderItem",
                     "DeliveryItem", "Plant"]

    all_nodes = list(G.nodes(data=True))

    # Sort by type priority
    def priority(item):
        t = item[1].get("type", "")
        return type_priority.index(t) if t in type_priority else 99

    all_nodes.sort(key=priority)
    selected = all_nodes[:limit_nodes]
    selected_ids = {n[0] for n in selected}

    nodes = []
    for node_id, data in selected:
        nodes.append({
            "id": node_id,
            "type": data.get("type", "Unknown"),
            "label": data.get("label", node_id),
            "color": data.get("color", "#aaa"),
            "data": {k: v for k, v in data.items()
                     if k not in ("type", "label", "color") and v and v != "None"}
        })

    edges = []
    for src, tgt, data in G.edges(data=True):
        if src in selected_ids and tgt in selected_ids:
            edges.append({
                "source": src,
                "target": tgt,
                "relation": data.get("relation", "RELATED_TO")
            })

    return {"nodes": nodes, "edges": edges}
