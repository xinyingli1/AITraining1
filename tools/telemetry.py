import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

# Global tracer instance
_tracer = None

def init_telemetry(service_name="meal-planning-agent"):
    global _tracer
    
    # Create a resource to identify the service
    resource = Resource(attributes={
        "service.name": service_name,
        "service.version": "1.0.0"
    })
    
    # Initialize the Tracer Provider
    provider = TracerProvider(resource=resource)
    
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
    except Exception as e:
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
