# Applying Phoenix to identify which new GPT-6 model is right

As of today (September 22nd), OpenAI has expanded their GPT-6 family to include Luna and Sol, alongside Astra. These models provide many of the same advances as Astra, while providing cheaper compute, as shown on their benchmarks. While general benchmarks released provide some insight for what may meet one's demands, no benchmark can be personal enough. 

My project will be framed around using these new models in an agentic environment with provided tools to answer how well this model helps one's specific workflow. I chose a specific question to simulate being a consumer trying to assess model practicality for a business-need.

## Outline

Research question: **How do the newly-released GPT-6 models (Luna, Sol) compare to Astra in terms of cost, correctness, latency, and token usage?**

- Define evaluation questions
- Define tools
- Build smallest working agent prototype (use cheaper model for testing)
- Connect phoenix early
- Inspectg differences

## Evaluation questions

To simulate the demands of a business analyst's agentic workflow, I've defined **9 questions tiered into 3 groups**:
1. 🟢 **elementary:** more simple, such as basic SQL counts/sums
2. 🟡 **intermediate:** more complex, perhaps involving joins/groups/filtering
3. 🔴 **advanced:** complex, involving perhaps multiple SQL calls or additional resources

**Question bank:**


| Tier | Question | Expected |
| --- | --- | --- |
| 🟢 | 1. How many orders are recorded? | 100 |
| 🟢 | 2. How many total units were sold? | 160 |
| 🟢 | 3. What is the total revenue? | $716.50 |
| 🟡 | 4. For each category, report its order count, units sold, and revenue. Sort alphabetically by category. | Coffee: 38 orders, 57 units, $250.50; Pastries: 29 orders, 53 units, $204.50; Tea: 33 orders, 50 units, $261.50 |
| 🟡 | 5. Which three products generated the most revenue? Return their names and revenue, ranked highest first. Break ties by lower product ID. | Latte: $170.00; Croissant: $152.00; Chai Latte: $135.00 |
| 🟡 | 6. Which products in the catalog had no orders during September 2026? Return their names alphabetically. | Matcha Latte |
| 🔴 | 7. Which products sold at least 20 units and have an average rating strictly below 2? Report their names, units sold, and average ratings, ordered alphabetically by product name. | Chai Latte: 27 units, 1.00; Latte: 34 units, 1.80; Matcha Latte: 23 units, 1.50 |
| 🔴 | 8. For each category, report total revenue and the percentage of all reviews in that category rated 1 or 2. Count each order and each review once, and sort alphabetically by category. | Coffee: $250.50, 55.56%; Pastries: $204.50, 0.00%; Tea: $261.50, 100.00% |
| 🔴 | 9. For every category, find the product with the highest November 2026 revenue among products with at least one November order and an overall average rating strictly below 2. Report the category, product name, November revenue, and overall average rating. Include categories with no qualifying product using null for the product, revenue, and rating. Sort alphabetically by category and break revenue ties by lower product ID. | Coffee: Latte, $75.00, 1.80; Pastries: null, null, null; Tea: Matcha Latte, $88.00, 1.50 |

Note: *Expected* values are rounded to two decimal places, and exact response wording may vary slightly.


## Beginning the process

To begin, my first **challenge** was actually choosing a dataset for the agents to operate on. I wanted to simulate the environment of a business-analyst accurately enough, but most of the datasets I found were pretty dramatic in scope—either too specialized, too reduced, or just confusing.

I decided the cleanest approach here would be to devise my own sales dataset, containing `products`, `orders`, and `reviews`. In terms of generating reviews, this also provides me a nicely contained environment to begin using OpenAI's API.

To proceed, I built a small script (contained in `helpers/build_dataset.py`) which allows me to dynamically define a few `(product, category, price)` product entries, and then the script will populate the `products`, `orders`, and `reviews` tables accordingly.

While this is still the scaffolding phase, another **challenge** was shaping the data. Naively populating each table with uniformly random selections doesn't provide much value in the data, and therefore doesn't provide rich evaluation for our agent. 

Adding some flavor to our data, I solved this challenge with a few additions:
- Fixed random seeds
- Make certain products favor certain sentiments (a review bias)
- Make certain products more popular (log-normal weights for populating orders)
- Vary demand-per-day to simulate busier/quieter days
- Balance review coverage independently of sales

At this point, I generated a dataset a fairly-rich dataset for the agents to work with. Full details can be found in [Dataset](#dataset).


## Dataset

The dataset my agents will work with is stored in `store.sqlite`, with the following schema:

```
products    product_id, name, category, price
orders      order_id, product_id, date, quantity, unit_price
reviews     review_id, product_id, rating, review_text
```

The specific dataset I generated contains 6 products (listed below), 100 orders, and 25 reviews. 

Each `(product, category, price)` entry below summarizes order counts, review counts, the assigned sentiment bias (0 = negative, 1 = positive), and the observed average rating out of 5. The bias influences individual ratings but does not guarantee a particular average.

```py
("Americano", "Coffee", 3.50),          # orders=13, reviews=4, bias=0.74, avg=3.50
("Latte", "Coffee", 5.00),              # orders=25, reviews=5, bias=0.16, avg=1.80
("Matcha Latte", "Tea", 5.50),          # orders=12, reviews=4, bias=0.30, avg=1.50
("Chai Latte", "Tea", 5.00),            # orders=21, reviews=4, bias=0.07, avg=1.00
("Croissant", "Pastries", 4.00),        # orders=18, reviews=4, bias=0.44, avg=3.25
("Blueberry Muffin", "Pastries", 3.50), # orders=11, reviews=4, bias=0.84, avg=4.00
```

Some meaningful properties about our data can be inferred:
- Lattes generate the most revenue and receive the most orders, despite a low average
- Croissants lead in units sold
- Blueberry muffins have the highest average rating, but the lowest revenue
- Chai lattes receive the second-most orders, despite having a low-rating
