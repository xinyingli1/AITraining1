import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, SpanProcessor, ReadableSpan
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from tools.pii import redact_pii

# Global tracer instance
_tracer = None


class PiiRedactingSpanProcessor(SpanProcessor):
    """Span processor that redacts PII from all span attributes before exporting."""

    def on_start(self, span, parent_context=None):
        pass

    def on_end(self, span: ReadableSpan) -> None:
        if span.attributes:
            try:
                for key, value in list(span.attributes.items()):
                    if isinstance(value, str):
                        span.attributes[key] = redact_pii(value)
                    elif isinstance(value, list):
                        span.attributes[key] = [
                            redact_pii(v) if isinstance(v, str) else v
                            for v in value
                        ]
            except Exception:
                try:
                    for key, value in list(span._attributes.items()):
                        if isinstance(value, str):
                            span._attributes[key] = redact_pii(value)
                        elif isinstance(value, list):
                            span._attributes[key] = [
                                redact_pii(v) if isinstance(v, str) else v
                                for v in value
                            ]
                except Exception:
                    pass


def init_telemetry(service_name="meal-planning-agent"):
    global _tracer

    # Create a resource to identify the service
    resource = Resource(
        attributes={"service.name": service_name, "service.version": "1.0.0"}
    )

    # Initialize the Tracer Provider
    provider = TracerProvider(resource=resource)

    # Register the PII Redacting Span Processor first
    provider.add_span_processor(PiiRedactingSpanProcessor())

    # Export to Console for local debugging/visibility
    console_exporter = ConsoleSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(console_exporter))

    
    # Export to OTLP collector (e.g. Jaeger)
    # OpenTelemetry automatically looks at OTEL_EXPORTER_OTLP_ENDPOINT env var.
    # We attempt to load the OTLPSpanExporter.
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    except Exception as e:
        # Fallback to HTTP exporter if gRPC is not available or fails
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPHttpSpanExporter
            otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
            otlp_exporter = OTLPHttpSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        except Exception as ex:
            print(f"Warning: OTLP Exporters could not be initialized (gRPC: {e}, HTTP: {ex}). Traces will only be logged to console.")
        
    # Export to Google Cloud Trace (Stackdriver)
    try:
        from opentelemetry.exporter.gcp.trace import CloudTraceSpanExporter
        # Automatically detects project ID using Application Default Credentials (ADC)
        gcp_exporter = CloudTraceSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(gcp_exporter))
    except Exception:
        # Expected to fail locally if GCP project or ADC is not configured
        pass

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)
    return _tracer

def get_tracer():
    global _tracer
    if _tracer is None:
        # Fallback if init_telemetry wasn't called yet
        _tracer = trace.get_tracer("meal-planning-agent")
    return _tracer
