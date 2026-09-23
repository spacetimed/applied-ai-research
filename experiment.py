import argparse
import json

from phoenix.client import Client
from phoenix.client.experiments import run_experiment

from agent import run_agent
from eval import evaluate

DATASET_NAME = "coffee-shop-final-experiment"


def main():
    parser = argparse.ArgumentParser(description="Evaluate models on the coffee-shop questions.")
    parser.add_argument("--models", nargs="+", default=["gpt-6-luna"])
    args = parser.parse_args()

    client = Client(base_url="http://localhost:6006")
    try:
        dataset = client.datasets.get_dataset(dataset=DATASET_NAME)
    except ValueError as error:
        if str(error) != f"Dataset not found: {DATASET_NAME}":
            raise
        with open("data/questions.json") as file:
            questions = json.load(file)
        dataset = client.datasets.create_dataset(name=DATASET_NAME, examples=questions)

    for model in args.models:
        print(f"Running experiment for {model}...")

        def task(input):
            return run_agent(input["question"], model=model)

        run_experiment(
            client=client,
            dataset=dataset,
            task=task,
            evaluators={"correctness": evaluate},
            experiment_name=model,
            experiment_metadata={"model": model},
            retries=0,
        )


if __name__ == "__main__":
    main()
