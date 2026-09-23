# Applying Phoenix to identify which new GPT-6 model is right

As of today (September 22nd), OpenAI has expanded their GPT-6 family to include Luna and Sol, alongside Astra. These models provide many of the same advances as Astra, while providing cheaper compute, as shown on their benchmarks. While general benchmarks released provide some insight for what may meet one's demands, no benchmark can be personal enough. 

My project will be framed around using these new models in an agentic environment with provided tools to answer how well this model helps one's specific workflow. I chose a specific question to simulate being a consumer trying to assess model practicality for a business-need.

## Outline

Research question: **How do the newly-released GPT-6 models (Luna, Sol) compare to Astra in terms of cost, correctness, latency, tool utilization, and token usage?**

- Define evaluation questions
- Define tools
- Build smallest working agent prototype (use cheaper model for testing)
- Connect phoenix early
- Inspectg differences

## Measurements

I'll run one Phoenix experiment per model against the same six questions. Each question produces an agent run with a trace and a correctness evaluation. The prompt, tools, database, reasoning effort, and evaluation criteria will remain fixed across models.

**Observability**

| Measurement | Source / calculation |
| --- | --- |
| Model | `llm.model_name` on the model-call spans |
| Input tokens | `llm.token_count.prompt` |
| Output tokens | `llm.token_count.completion` |
| Total tokens | `llm.token_count.total` |
| Reasoning tokens, when reported | `llm.token_count.completion_details.reasoning` |
| Agent latency | End-to-end duration of the agent span, excluding evaluation |
| Tool calls | Number of executed tool spans with `openinference.span.kind = "TOOL"` |
| LLM calls | Number of model-call spans with `openinference.span.kind = "LLM"` |
| Execution errors | Spans marked `ERROR`; distinguish recovered tool errors from failed agent runs |
| Estimated cost | Token usage multiplied by the applicable model pricing, accounting for cache usage where reported |

Token counts are recorded per LLM call and summed across the agent run, without also counting parent-span totals. Reasoning tokens are a breakdown of output usage, not an additional amount to add to total tokens. Missing usage fields will be treated as unavailable rather than zero. Evaluation uses Python code and requires no additional model calls.

Phoenix supports automatic cost calculation when it has the matching model pricing. I'll verify the rates for these new models and configure custom prices if needed. See [Phoenix cost tracking](https://arize.com/docs/phoenix/tracing/how-to-tracing/cost-tracking).

**Evaluation — whether the answer was correct**

Phoenix will run a deterministic Python evaluator that compares the agent's structured answer with the reference answer. It checks the requested fields, values, completeness, and sorting. Numeric formatting differences such as `170` versus `170.00` are equivalent; money, ratings, and percentages are compared at two decimal places. The agent's output format will be specified consistently across models, so scoring does not depend on matching prose. No LLM judge is used.

| Output | Meaning |
| --- | --- |
| Label | `correct` or `incorrect` |
| Score | `1` for a correct answer; `0` for an incorrect, missing, or incomplete answer |
| Explanation | Why the answer passed or failed |

I'll compare accuracy overall and by difficulty tier, alongside latency, tokens, cost, and tool calls per question. Evaluator failures will be reported separately from incorrect agent answers. Tool-call counts measure usage, not correctness: fewer calls are only useful if the answer is still right.

## File structure

```
tools.py - used by agents.py
    get_schema()
    run_query(sql) -> result

agents.py - called by experiment.py
    run_agent(question, model) -> answer

eval.py - called by experiment.py
    deterministic comparison of structured answers
    evaluate(expected_answer, answer) -> label, score, explanation

experiment.py - coordinates agent and evaluator
    loads dataset
    configure tracing
    for each model
        start experiment(model)
        for each question
            run_agent(question, model) -> answer
            evaluate(expected_answer, answer) -> label, score, explanation
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

# Resources
- https://github.com/arize-ai/phoenix
- https://arize-phoenix.readthedocs.io/projects/otel/