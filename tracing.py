from phoenix.otel import register
from openinference.instrumentation.openai import OpenAIInstrumentor

provider = register(
    project_name="coffee-shop",
    endpoint="http://localhost:6006/v1/traces",
    protocol="http/protobuf",
    batch=True,
)

OpenAIInstrumentor().instrument(tracer_provider=provider)
tracer = provider.get_tracer("coffee-shop")
