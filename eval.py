import json
import math


def matches(actual, expected):
    # Takes (already-parsed) values and checks if they match our expected question answer.

    # Dictionaries: check for identical keys and values.
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and actual.keys() == expected.keys()
            and all(matches(actual[key], value) for key, value in expected.items())
        )

    # Lists: check for same length and identical values per-index
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(matches(a, e) for a, e in zip(actual, expected))
        )

    # Numbers: for integers, check that both values match exactly,
    #          for floats, check that both values match to two decimal places
    if type(expected) in (int, float):
        if type(actual) not in (int, float):
            return False
        if isinstance(actual, float) and not math.isfinite(actual):
            return False
        if isinstance(expected, int):
            return actual == expected
        return round(actual, 2) == round(expected, 2)

    # Other types (e.g. strings): check that types match and value matches exactly
    return type(actual) is type(expected) and actual == expected


def evaluate(output, expected):
    reference = expected["answer"]
    try:
        answer = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return {
            "score": 0,
            "label": "incorrect",
            "explanation": "Response is not valid JSON.",
        }

    correct = matches(answer, reference)
    return {
        "score": int(correct),
        "label": "correct" if correct else "incorrect",
        "explanation": (
            "All values and ordering match."
            if correct
            else f"Expected {reference!r}; received {answer!r}."
        ),
    }
