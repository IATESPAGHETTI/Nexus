"""The simulated shop's product catalog: a fixed in-memory list, deliberately NOT stored in the
orders database. Browsing products therefore keeps working while the database is slow, and
only DB-backed actions (checkout, order history) degrade -- like many real shops.
Prices are authoritative here: checkout computes totals from this list, never from the client."""

PRODUCTS = [
    {"id": 1, "name": "Trail Backpack", "price": 59.00, "emoji": "🎒", "blurb": "28 L, water-resistant"},
    {"id": 2, "name": "Insulated Bottle", "price": 24.50, "emoji": "🧴", "blurb": "Keeps drinks cold 24 h"},
    {"id": 3, "name": "Wireless Headphones", "price": 89.99, "emoji": "🎧", "blurb": "40 h battery"},
    {"id": 4, "name": "Desk Lamp", "price": 34.00, "emoji": "💡", "blurb": "Warm and cool light"},
    {"id": 5, "name": "Notebook Set", "price": 12.75, "emoji": "📓", "blurb": "3 pack, dotted"},
    {"id": 6, "name": "Running Shoes", "price": 74.00, "emoji": "👟", "blurb": "Lightweight daily trainer"},
    {"id": 7, "name": "Coffee Grinder", "price": 41.25, "emoji": "☕", "blurb": "Burr, manual"},
    {"id": 8, "name": "Phone Stand", "price": 15.00, "emoji": "📱", "blurb": "Foldable aluminium"},
]

BY_ID = {p["id"]: p for p in PRODUCTS}
