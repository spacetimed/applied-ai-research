import json
import random
import sqlite3

from datetime import date, timedelta
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# (name, category, price)
PRODUCTS = [
    ("Americano", "Coffee", 3.50),
    ("Latte", "Coffee", 5.00),
    ("Matcha Latte", "Tea", 5.50),
    ("Chai Latte", "Tea", 5.00),
    ("Croissant", "Pastries", 4.00),
    ("Blueberry Muffin", "Pastries", 3.50),
]

# Data generation config
ORDER_COUNT = 100
REVIEW_COUNT = 25
SEED = 1337
START_DATE = date(2026, 9, 22)
DAY_COUNT = 60
MODEL = "gpt-5-nano"

# One repeatable bias per product: 0 leans negative, 1 leans positive.
# The U-shaped distribution favors stronger opinions over neutral ones.
rng = random.Random(SEED)
PRODUCT_BIASES = [rng.betavariate(0.5, 0.5) for _ in PRODUCTS]
PRODUCT_POPULARITY = [rng.lognormvariate(0, 0.4) for _ in PRODUCTS]

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "store.sqlite"

def generate_orders(products):
    orders = []

    days = [START_DATE + timedelta(days=i) for i in range(DAY_COUNT)]
    daily_demand = [rng.lognormvariate(0, 0.6) for _ in days]
    order_days = sorted(rng.choices(days, weights=daily_demand, k=ORDER_COUNT))

    for order_id, day in enumerate(order_days, start=1):
        
        product = rng.choices(products, weights=PRODUCT_POPULARITY, k=1)[0]
        product_id,name,category,price = product

        # Sample a quantity per order using fixed probabilities.
        quantity = rng.choices([1, 2, 3, 5, 10], weights=[65, 20, 8, 5, 2], k=1)[0]
        orders.append((order_id, product_id, day.isoformat(), quantity, price))

    return orders


def generate_reviews(products):
    if REVIEW_COUNT == 0:
        return []
    rng = random.Random(SEED)

    review_products = []
    while len(review_products) < REVIEW_COUNT:
        batch = list(products)
        rng.shuffle(batch)
        review_products.extend(batch)
    review_products = review_products[:REVIEW_COUNT]
    rng.shuffle(review_products)

    review_specs = []
    for review_id, product in enumerate(review_products, start=1):
        product_id, name, category, price = product
        bias = PRODUCT_BIASES[product_id - 1]
        target_rating = 1 + 4 * bias
        rating = round(rng.gauss(target_rating, 1.0))
        rating = max(1, min(5, rating))
        review_specs.append(
            {"review_id": review_id, "product_id": product_id, "rating": rating}
        )

    prompt = f"""
    Write one short synthetic customer review for each specification below.
    Each product is listed as (product_id, name, category, price):
    {products}

    Review specifications (use the assigned product and rating exactly):
    {json.dumps(review_specs)}

    Give each product recurring praise or complaint themes, with varied wording.
    1 star: strongly negative, frustrated, or disappointed.
    2 stars: clearly unhappy, but less intense.
    3 stars: neutral, chill, matter-of-fact; neither praise nor outrage.
    4 stars: pleased, with a minor reservation.
    5 stars: strongly positive and enthusiastic.

    Use natural customer language and specific product details, not just adjectives.
    A 1-star review must clearly express dissatisfaction, not mild praise.
    Never mention stars, numeric scores, or phrases such as "1/5" or "five out of five".
    Each review is from a different customer. Do not refer to other reviews or
    write "again" as if these were one person's continuing conversation.
    Keep the writing believable for a coffee shop, with varied sentence lengths.

    Return a JSON object with this structure:
    {{"reviews": [{{"review_id": 1, "review_text": "..."}}]}}
    """
    print(f"Generating {REVIEW_COUNT} review texts with {MODEL}...")
    client = OpenAI()
    response = client.responses.create(
        model=MODEL,
        input=prompt,
        reasoning={"effort": "low"},
        text={"format": {"type": "json_object"}},
        max_output_tokens=6000,
    )
    reviews = json.loads(response.output_text)["reviews"]
    if len(reviews) != REVIEW_COUNT:
        raise ValueError(f"Expected {REVIEW_COUNT} reviews, received {len(reviews)}")

    texts = {review["review_id"]: review["review_text"] for review in reviews}
    expected_ids = {spec["review_id"] for spec in review_specs}
    if set(texts) != expected_ids:
        raise ValueError("Generated reviews have missing or unexpected IDs")

    rows = []
    for spec in review_specs:
        review_text = texts[spec["review_id"]]
        if not isinstance(review_text, str) or not review_text.strip():
            raise ValueError("Generated review text must be nonempty")
        rows.append(
            (spec["review_id"], spec["product_id"], spec["rating"], review_text)
        )
    print(f"Received {len(rows)} reviews; IDs and nonempty text checked.")
    return rows


def save_database(products, orders, reviews):
    with sqlite3.connect(":memory:") as db:
        db.executescript("""
            PRAGMA foreign_keys = ON;

            CREATE TABLE products (
                product_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL
            );

            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                product_id INTEGER NOT NULL REFERENCES products(product_id),
                date TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL
            );

            CREATE TABLE reviews (
                review_id INTEGER PRIMARY KEY,
                product_id INTEGER NOT NULL REFERENCES products(product_id),
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                review_text TEXT NOT NULL
            );
        """)
        db.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", products)
        db.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", orders)
        db.executemany("INSERT INTO reviews VALUES (?, ?, ?, ?)", reviews)
        db.commit()

        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(DB_PATH) as output:
            db.backup(output)


def main():
    if not PRODUCTS or ORDER_COUNT < 0 or REVIEW_COUNT < 0 or DAY_COUNT < 1:
        raise ValueError("Provide products, nonnegative row counts, and at least one day.")
    load_dotenv(ROOT / ".env")
    print(f"Building dataset with seed={SEED}...")

    # Construct products table
    products = []
    for product_id, (name, category, price) in enumerate(PRODUCTS, start=1):
        products.append((product_id, name, category, price))
        bias = PRODUCT_BIASES[product_id-1]
        print(f"  {name}: review bias {bias:.2f}")

    # Construct orders table
    orders = generate_orders(products)
    print(f"Generated {len(orders)} orders across a {DAY_COUNT}-day window.")

    # Construct reviews table
    reviews = generate_reviews(products)

    # Small data summary
    print("Product coverage:")
    for product_id, name, category, price in products:
        order_count = sum(order[1] == product_id for order in orders)
        ratings = [review[2] for review in reviews if review[1] == product_id]
        average = f"{sum(ratings) / len(ratings):.2f}" if ratings else "n/a"
        print(f"  {name}: {order_count} orders, {len(ratings)} reviews, average rating {average}")

    print("Saving database (overwriting if needed)...")
    save_database(products, orders, reviews)

    print(f"{len(products)} products, {len(orders)} orders, {len(reviews)} reviews")
    print(f"Saved file to {DB_PATH}")


if __name__ == "__main__":
    main()
