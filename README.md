# Comparing GPT-6 Luna, Sol, and Astra with Phoenix

As of September 22nd, **OpenAI** has expanded their GPT-6 family, [launching Luna and Sol](https://openai.com/index/introducing-gpt-6-sol-and-luna/), expanding beyond their flagship Astra model. These two new models provide many of the same advances as Astra at a cheaper price. 

With such an expansion comes freedom of choice, and therefore, many will wonder which model is right for them. Limited public information, necessarily-generalized launch benchmarks, and drastically varying usage costs are factors which make that decision difficult for an ordinary AI developer.

Such concerns greatly illuminate Phoenix's value of being able to devise one's own laboratory, comparing models under their own specialized use-case. I designed an experiment which models this problem practically, and then answers it with Phoenix.

# Analyzing a coffee shop's sales to choose the right GPT-6 model

<center><img src="images/art.png" width="300"></Center>

Consider a **coffee shop owner** who tends to use AI agents through OpenAI's API to analyze their sales data and wants to know:

- **How do the newly-released GPT-6 models (Luna, Sol) compare to Astra in terms of cost, correctness, latency, tool utilization, and token usage, under the specialized purpose of business analytics?**

## 1. Designing the experiment

One of my first **challenges** was in decomposing this proposed research question, and designing an experiment to depict and measure it. I began by asking:

***What are we comparing?***

The only independent variable in this experiment is the model itself (`gpt-6-luna`, `gpt-6-sol`, `gpt-6-astra`). For the sake of comparison, all other variables (reasoning effort, prompt, available tools) remain the same.

***What are we measuring?***: Cost, correctness, latency, tools, tokens.

| Category | Metric (as revealed by Phoenix) | 
| --- | --- |
| Cost | `costSummary.total.cost` |
| Correctness | `correctness` (see below) |
| Latency | `latency_ms` |
| Tools Used | `span_kind = "TOOL"` |
| Token Usage | `llm.token_count.prompt`, `llm.token_count.completion`, `llm.token_count.total` |

***Where can we find accurate sales data for a coffee shop?***

Another problem was that most datasets I found online were quite dramatic in scope—either too specialized or too reduced. After speaking with someone involved in the coffee shop industry and understanding their general problem space, I desired data rich enough for the agent to work with meaningfully and relevantly, yet simple enough to not detract away from this demo's focus of Phoenix.

The cleanest approach I decided on was to generate my own mock dataset, containing 3 tables: `products`, `orders`, and `reviews`. This provided me a nice warmup in integrating OpenAI's API into the project, as I used `gpt-5-nano` to generate reviews with natural language. 

I also added some character to my data through fixed seeds, making certain products favor certain sentiments (review bias), making certain products more popular (log-normal weights for populating orders), and varying daily demand to simulate busier/quieter days.

The full generation logic can be found in `helpers/build_dataset.py`.

⭐️ *Details of the specific dataset generated for the agent will be described in the [3. Providing the agent with data](#2-providing-the-agent-with-data) section.*

***What should the agent be evaluated on, and what defines correctness?***

For evaluating correctness, **6 questions about sales data will be asked to the agent**. There will be 3 modes of difficulty (**easy, medium, hard**), with 2 questions asked per difficulty-level, and the more difficult a question, the more reasoning I anticipate each will take. Responses will be compared to expected output to evaluate correctness.

⭐️ *Details about the evaluation questions asked will be explained in the [3. Evaluation questions](#3-evaluation-questions) section.*

***What tools should the agents use?***

For the available tools, I chose to be deliberately modest, because I was really interested in comparing how different models work with a limited set of tools. The agents have two tools available to them:
- `get_schema()`: return a schema of the SQLite table, including columns/relationships
- `run_sql(query)`: execute a read-only SQL query on the table, return columns/rows.

## 2. Providing the agent with data

The dataset my agents will work with is stored in `store.sqlite`, with the following schema:

| Table | Columns |
| --- | --- |
| `products` | `product_id`, `name`, `category`, `price` |
| `orders` | `order_id`, `product_id`, `date`, `quantity`, `unit_price` |
| `reviews` | `review_id`, `product_id`, `rating`, `review_text` |

The specific dataset I generated contains 6 products (listed below), 100 orders, and 25 reviews. 

Each `(product, category, price)` entry below summarizes the generated order counts, review counts, sentiment bias (0 = negative, 1 = positive), and the observed average rating out of 5. The bias influences individual ratings but does not guarantee a particular average.

```py
("Americano", "Coffee", 3.50),          # orders=13, reviews=4, bias=0.74, avg=3.50
("Latte", "Coffee", 5.00),              # orders=25, reviews=5, bias=0.16, avg=1.80
("Matcha Latte", "Tea", 5.50),          # orders=12, reviews=4, bias=0.30, avg=1.50
("Chai Latte", "Tea", 5.00),            # orders=21, reviews=4, bias=0.07, avg=1.00
("Croissant", "Pastries", 4.00),        # orders=18, reviews=4, bias=0.44, avg=3.25
("Blueberry Muffin", "Pastries", 3.50), # orders=11, reviews=4, bias=0.84, avg=4.00
```

Note that orders may contain multiple units, but only of the same product type: for example, a single order may contain a quantity of 5 croissants.

**Some meaningful properties about our data can be inferred:**
- Lattes generate the most revenue and receive the most orders, despite a low average.
- Croissants lead in units sold.
- Blueberry muffins have the highest average rating, but the lowest revenue.
- Chai lattes receive the second-most orders, despite having a low rating.

**A small preview of our coffee shop's data:** (`LIMIT 3`)

![](./images/data.png)

## 3. Evaluation questions

To simulate the demands of a business analyst's agentic workflow relative to our mock data, I've defined **6 questions tiered into 3 groups, with 2 questions per group**:


| Tier | Question | Expected |
| --- | --- | --- |
| 🟢 | 1. How many orders are recorded? | 100 |
| 🟢 | 2. What is the total revenue? | $716.50 |
| 🟡 | 3. For each category, report its order count, units sold, and revenue. Sort alphabetically by category. | Coffee: 38 orders, 57 units, $250.50; Pastries: 29 orders, 53 units, $204.50; Tea: 33 orders, 50 units, $261.50 |
| 🟡 | 4. Which three products generated the most revenue? Return their names and revenue, ranked highest first. Break ties by lower product ID. | Latte: $170.00; Croissant: $152.00; Chai Latte: $135.00 |
| 🔴 | 5. Which products sold at least 20 units and have an average rating strictly below 2? Report their names, units sold, and average ratings, ordered alphabetically by product name. | Chai Latte: 27 units, 1.00; Latte: 34 units, 1.80; Matcha Latte: 23 units, 1.50 |
| 🔴 | 6. For each category, report total revenue and the percentage of all reviews in that category rated 1 or 2. Count each order and each review once, and sort alphabetically by category. | Coffee: $250.50, 55.56%; Pastries: $204.50, 0.00%; Tea: $261.50, 100.00% |

*Tiers:*
- 🟢 **easy:** more simple, such as basic SQL counts/sums
- 🟡 **medium:** more complex, perhaps involving joins/groups/filtering
- 🔴 **hard:** combine sales and review aggregates with multiple conditions; may require more complex SQL, but not necessarily more tool calls

## 4. File structure

Another **challenge** I faced was in architecting the actual project structure. Abstraction becomes hard when there is a lot of unknown, so I spent significant time understanding the dataflow and what my code needed to provide. I ended with the following structure, which felt clean to work with, thus making data flow easy to reason about:

```sh
├── data
│   ├── questions.json   # 6 questions/answers in json format; for experiments.py
│   └── store.sqlite     # sqlite dataset
│
├── helpers              
│   └── build_dataset.py # generates the sqlite dataset
│
├── agent.py             # run_agent(question, model); for experiment.py
├── tools.py             #  get_schema(), run_sql(sql) tools; for agent.py
├── database.py          #   execute_query(sql); for tools.py
├── eval.py              # evaluate(output, expected); for experiment.py
│
├── experiment.py        # main driver, interfaces with everything else
├── tracing.py           # providers @tracer; for agents.py, tools.py
│
└── pyproject.toml
```

## 5. Phoenix enters the experiment

Upon adding Phoenix, I realized quickly that the hard work had already been done. Designing the experiment, dataset, and evaluation questions required some measured brainstorming, but at this point, everything was neatly modularized: `agent.py` was able to answer questions with different OpenAI models and tools, and `eval.py` was able to evaluate that model's answer for correctness. 

The exciting part: there was now a perfect application for both domains of Phoenix's offerings: observability and evaluation.

**Observability**

To add support for observability, I created `tracing.py` while referencing [Arize's Phoenix OTEL Reference](https://arize-phoenix.readthedocs.io/projects/otel/). Afterwards, I wrapped my agent with `@tracer.agent`, and my tools with `@tracer.tool`. Continuing the [Phoenix repository's installation process](https://github.com/arize-ai/phoenix#run-locally), I ran `phoenix serve` to fire up the frontend.

I ran a small prompt, and Phoenix's frontend provided a vast amount of detail for the inference, such as the entire tool chain, latency, and cost. At this point, I was impressed, because these traces provided everything I needed for the experiment, and implementing this layer was remarkably accessible. The amount of information available (such as seeing **Total tokens** for different stages) was very cool, and I spent a fair amount of time just exploring the UI. 

<center><img src="images/trace.png" height="600"></center>

**Evaluation**

Phoenix's evaluation layer also provided a great deal of simplicity, as even the mere process of writing a wrapper around `eval.py` to iterate through models, collect traces, and group experiments would have been significant work.

I composed an `experiment.py` file, and in under 50-lines I was able to import the `questions.json` as a dataset, name the experiment group, and use my already-created files to conduct the experiment. The output was elegant and succinct:

![](./images/output.png)

I designed my `experiment.py` so experiments could be ran cleanly, and working with Phoenix around this modularization was very natural:

```sh
python experiment.py --models gpt-6-luna gpt-6-sol gpt-6-astra

# or alternatively, run each model independently
python experiment.py --models gpt-6-luna
python experiment.py --models gpt-6-sol
python experiment.py --models gpt-6-astra
python experiment.py --models gpt-5.6-sol # and perhaps other models! 🙂
```

## 6. Results

Now was the exciting part. After running the three experiments, I was able to quickly sift through all of my findings, and the amount of detail and visualization was captivating.


The following measurements were exported from `coffee-shop-final-experiment`:

![](./images/comparison.png)

| Model | Cost | Correctness | Avg. Latency | Tool Calls | Prompt Tokens | Completion Tokens | Total Tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gpt-6-luna` | $0.0014818 | 1.00 (6/6) ✅ | 4,239.20 ms | 12 | 10,658 | 832 | 11,490 |
| `gpt-6-sol` | $0.0279600 | 1.00 (6/6) ✅ | 3,844.81 ms | 11 | 9,900 | 816 | 10,716 |
| `gpt-6-astra` | $0.1389600 | 1.00 (6/6) ✅ | 6,078.55 ms | 11 | 9,886 | 802 | 10,688 |

**Phoenix metrics used:**
- Cost: `costSummary.total.cost`
- Correctness: `correctness`
- Latency: `latency_ms`
- Tool calls: spans where `span_kind = "TOOL"`
- Token usage: `llm.token_count.prompt`, `llm.token_count.completion`, `llm.token_count.total`


What stood out to me was how little the extra spending benefited this particular use-case. Even for questions which seemed quite involved, each of the three models were able to score `6.0 / 6.0` on the evaluation score. **Luna's** total cost was roughly 94 times lower than **Astra's**, despite using slightly more tokens. **Sol** had the lowest average latency, though only about 0.4 seconds faster than **Luna**. 

For this coffee shop's six questions, the release of Luna particularly provides immense value in performing the responsibilities demanded for a much cheaper price. More reflection on this experiment and its results are mentioned in the upcoming [7. Reflection](#7-reflection) section.


## 7. Reflection

***What did the results from this experience teach me?***

I learned from the results of this experiment that it can often be deceptive how much advanced reasoning (or lack thereof) is required for a task. From what I've observed in my own social circles, we tend to overestimate how much reasoning our tasks demand, and consequently feel pressured to choose the latest and best model. But, as the results from this experiment teach, sometimes even smaller models can effortlessly complete the tasks that we personally rate as complex, while saving substantial costs. The problem-space of "choosing the right model" is very real right now, as options swarm consumers overwhelmingly, and Phoenix serves great utility in individually framing and answering such questions.

***What did I learn about Phoenix?***

I learned that Phoenix *greatly* simplifies tasks which would otherwise be significantly demanding and that it's very accessible. While the option to wire OpenTelemetry manually exists, Phoenix abstracts a lot of that setup (and more) into a much more user-friendly setup, and its tutorial documentation was simple and accessible. Implementing Phoenix into my project, along with its MCP server companion, was very streamlined—consequently, it's very easy to talk honestly about just *how much* its services assist an ordinary developer. The capabilities of Phoenix are powerful, and collecting traces, analyzing spans, and scoring evaluations was pleasant even for someone like me who had never used it before. 

Something special about this experiment is that the models I was using had just come out the day *of*. The only novel thing I had to do to account for this was import the model's API cost into Phoenix; nothing additional was needed beyond this triviality. Adaptability like that is remarkable in this field where change is imminent, and serves an astoundingly enticing point that I want to teach general AI developers about.

***What challenges did I personally encounter, and how did I approach them?***

**One challenge** I faced was in *transforming* a relevant topic (the release of GPT-6's new models) to a general and pressing question easily answerable by Phoenix. While reading about GPT-6's new models releasing, I knew this prompted significant questions for developers around the world. I wanted to choose the most general question all developers likely hold, transform that question into a practical "experimental space" to fully depict its essence, and answer that effortlessly with Phoenix, focusing especially on ease. 

**Another challenge** I faced (as mentioned in [1. Designing the experiment](#1-designing-the-experiment)) follows by extension to the previous challenge: seeding that general question with specificity, and modeling the experimental space accordingly. I briefly chatted with someone who has worked in the coffee industry and asked questions which allowed me to form "axes" around a general manager's problem-space. I was able to extract certain characteristics of the problem-space, such as the importance of product popularity and the unpredictableness of customer flow, which I used to model my mock shop's data and questions more accurately. Decomposing my now-specific research question into its core experimental domains (shop data, importance of model choice, metrics to consider) required significant measured thought, but this preplanning is exactly what aided my project's workflow and allowed me to stage a reasonable PoC within the same day.

**A third challenge** I faced was more general: meeting ambiguity with information; i.e. reducing the volume of perceived uncertainty. At the start of the day, Phoenix (as a tool), what a coffee shop sales analyst likely cares about, and the new OpenAI models were completely novel to me; by the end of the day, I understood Phoenix and its workflow reasonably well, and felt proficient at vouching for Phoenix's effectiveness towards ordinary developers when choosing between different models within the GPT-6 family, especially under a sales context. I systemize a lot of thought, which allows me to map knowledge (perhaps for general tasks like these) into its axiomatic domains, approaching each step iteratively and with intent. Realizing complexity is often times an illusion and that most pursuits can be broken down into a more axiomatic representation has been a superpower for me personally when it comes to learning new stuff—it makes the process exhilerating rather than draining, as I recognize the cognitive burn is what nurtures growth. 

***What can another developer learn from this?***

***What are the limitations of my experiment, and how would I change it?***

## References and resources
- [0]https://arize-phoenix.readthedocs.io/projects/otel/
- https://github.com/arize-ai/phoenix
