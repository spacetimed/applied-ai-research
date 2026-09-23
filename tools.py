from database import execute_query

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "get_schema",
        "description": "Get the SQLite table definitions, including columns and their relationships.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "run_sql",
        "description": "Run a single read-only SQLite query. Returns columns and rows.",
        "parameters": {
            "type": "object",
            "properties": {"sql": {"type": "string"}},
            "required": ["sql"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def get_schema():
    return execute_query("""
        SELECT name, sql FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)


def run_sql(sql):
    return execute_query(sql)
