from aws_lambda_powertools.tracing import Tracer
from shared.instrumentation.noop_tracer import NoOpTracer

try:
    tracer_instance = Tracer()
except Exception:
    tracer_instance = NoOpTracer()

tracer = tracer_instance
