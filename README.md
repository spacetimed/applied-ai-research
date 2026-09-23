# Applying Phoenix to identify which new GPT-6 model is right

As of today (September 22nd), OpenAI has expanded their GPT-6 family to include Luna and Sol, alongside Astra. These models provide many of the same advances as Astra, while providing cheaper compute, as shown on their benchmarks. While general benchmarks released provide some insight for what may meet one's demands, no benchmark can be personal enough. 

My project will be framed around using these new models in an agentic environment with provided tools to answer how well this model helps one's specific workflow. I chose a specific question to simulate being a consumer trying to assess model practicality for a business-need.

**Research question: How do cheaper GPT-6 models (Luna, Sol) compare to Astra in terms of cost, correctness, latency, and usage?**

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

At this point, I generated a dataset a fairly-rich dataset for the agents to work with. Full details can be found in [Dataset](#).


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