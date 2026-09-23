# Comparing the new family of GPT-6 models using Phoenix

As of September 22nd, OpenAI has expanded their GPT-6 family, [launching Luna and Sol](https://openai.com/index/introducing-gpt-6-sol-and-luna/), expanding beyond their flagship Astra model. These two new models provide many of the same advances as Astra at a cheaper price, with the launch page showing impressive results from many benchmarks. 

With such an expansion comes freedom of choice, and therefore, many will wonder which model is right for them. While all three models share similarities, they can also differ significantly. For example, `gpt-6-luna` appears to be around 10x cheaper than `gpt-6-astra` in API costs. Benchmarks can also be unreliable or misleading, especially when under a company's launch page. Lastly, on the day of a model's launch, limited public information is available about the model itself.

Such concerns greatly illuminate the value in being able to devise one's own laboratory for comparing models, within their specialized use-case. This write-up describes how a coffee shop owner may use **Phoenix** to choose which model is right for their purpose of sales analyzing.

## Project: Analyzing a coffee shop's sales

<img src="images/art.png" width="300">

A **coffee shop owner** tends to use AI agents through OpenAI's API to analyze their sales data. Their question:
- **How do the newly-released GPT-6 models (Luna, Sol) compare to Astra in terms of cost, correctness, latency, tool utilization, and token usage, under my specific needs?**

I've chronologically documented my process of addressing this question, demonstrating how Phoenix greatly aids the process, while pointing out some challenges I've faced throughout. The [Results](#results) section compresses the experiment's results, and highlights what I've learned.

## Designing the experiment

My first **challenge** was decomposing the proposed research question and designing an experiment to assess it. I began by asking:

***What are we comparing?***

The only independent variable in this experiment is the model itself (`gpt-6-luna`, `gpt-6-sol`, `gpt-6-astra`). For the sake of comparison, all other variables (reasoning effort, prompt, available tools) remain the same.

***What are we measuring?*** Cost, correctness, latency, tools, tokens

| Category | Metric name as revealed by Phoenix | 
| --- | --- |
| Cost | `costSummary.total.cost` |
| Correctness | `correctness` (see below) |
| Latency | `latency_ms` |
| Tools Used | `span_kind = "TOOL"` |
| Token Usage | `llm.token_count.prompt`, `llm.token_count.completion`, `llm.token_count.total` |

***What defines correctness?***

For evaluating correctness, 6 questions within 3 categories (beginner, intermediate, advanced) will be asked to the agent about the coffee shop's sales data, and responses will be compared to expected output. 

⭐️ *Full details about the questions asked are in the [Evaluation Questions](#evaluation-questions) section.*

***Where can I find accurate sales data for a coffee shop?***

Most of the datasets I could find online were pretty dramatic in scope—either too specialized, too reduced, or just confusing. I wanted data rich enough for the agent to work with, but simple enough to not detract from the demo's focus.

I decided the cleanest approach here would be to devise my own mock dataset, containing 3 tables: `products`, `orders`, and `reviews`. In terms of generating reviews, this also provides me a nicely contained environment to begin using OpenAI's API. 
Inside `helpers/build_dataset.py`, I bulit a small helper script which allowed me to dynamically define a few product entries, and populate the table according to some variables I choose (order count, review count). 

I realized quickly that the data needed some "shape" to it, and so rather than naively populating each table with random selections, I added some "flavor" to the data:
- Fixed random seeds
- Make certain products favor certain sentiments (a review bias)
- Make certain products more popular (log-normal weights for populating orders)
- Vary demand-per-day to simulate busier/quieter days
- Balance review coverage independently of sales

For the purpose of this demo, I generated a fairly-rich dataset for the agents to work with and extract meaningful insights from. 

⭐️ *Specific details of the dataset used are in the [Dataset](#dataset) section.*

***What tools should the agents use?***

For the available tools, I chose to be deliberately modest, because I was really interested in comparing how different models work with a limited set of tools. The agents only have two tools available to them:
- `get_schema()`: returns a schema of the SQLite table, including columns/relationships
- `run_sql(query)`: execute a read-only SQL query on the table, returns columns and rows.

## File structure

Another **challenge** I faced was in architecting the actual project structure. Abstraction becomes fairly difficult when there is a lot of unknown, so I spent significant time understanding the dataflow, and what my code needs to provide. I ended with the following structure, which felt very clean to work with:

```sh
├── data
│   ├── questions.json   #   6 questions in json format, for eval.py
│   └── store.sqlite     #   sqlite dataset (see Dataset section)
│
├── helpers              
│   └── build_dataset.py # generates the store data into store.sqlite
│
├── agent.py             # provides run_agent(question, model) for experiment.py
├── tools.py             # provides get_schema(), run_sql(sql) tools for agent.py
├── database.py          # provides SQLite query execution for tools.py
├── eval.py              # provides evaluate(output, expected) -> score for experiment.py
│
├── experiment.py        # main wrapper, interfaces with everything else
├── tracing.py           # initializes tracer, provides wrapper
│
└── pyproject.toml

```

## Running experiments

```sh
python experiment.py --models gpt-6-luna gpt-6-sol gpt-6-astra

# or alternatively, run models independently
python experiment.py --models gpt-6-luna
python experiment.py --models gpt-6-sol
python experiment.py --models gpt-6-astra
```

## Evaluation questions

To simulate the demands of a business analyst's agentic workflow, I've defined **6 questions tiered into 3 groups, with 2 questions per group**:
1. 🟢 **elementary:** more simple, such as basic SQL counts/sums
2. 🟡 **intermediate:** more complex, perhaps involving joins/groups/filtering
3. 🔴 **advanced:** combine sales and review aggregates with multiple conditions; may require more complex SQL, but not necessarily more tool calls

**Question bank:**


| Tier | Question | Expected |
| --- | --- | --- |
| 🟢 | 1. How many orders are recorded? | 100 |
| 🟢 | 2. What is the total revenue? | $716.50 |
| 🟡 | 3. For each category, report its order count, units sold, and revenue. Sort alphabetically by category. | Coffee: 38 orders, 57 units, $250.50; Pastries: 29 orders, 53 units, $204.50; Tea: 33 orders, 50 units, $261.50 |
| 🟡 | 4. Which three products generated the most revenue? Return their names and revenue, ranked highest first. Break ties by lower product ID. | Latte: $170.00; Croissant: $152.00; Chai Latte: $135.00 |
| 🔴 | 5. Which products sold at least 20 units and have an average rating strictly below 2? Report their names, units sold, and average ratings, ordered alphabetically by product name. | Chai Latte: 27 units, 1.00; Latte: 34 units, 1.80; Matcha Latte: 23 units, 1.50 |
| 🔴 | 6. For each category, report total revenue and the percentage of all reviews in that category rated 1 or 2. Count each order and each review once, and sort alphabetically by category. | Coffee: $250.50, 55.56%; Pastries: $204.50, 0.00%; Tea: $261.50, 100.00% |

Note: Use all recorded data. An order is one row in `orders`; units sold is the sum of `quantity`; revenue is the sum of `quantity × unit_price` in USD. Average ratings weight each review equally, and rating thresholds apply before rounding. *Expected* values are displayed to two decimal places where relevant; the evaluator compares structured values rather than exact response wording.


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

# Resources
- https://github.com/arize-ai/phoenix
- https://arize-phoenix.readthedocs.io/projects/otel/
