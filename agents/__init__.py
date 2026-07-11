import os
import logging
from typing import Any
from google.antigravity import types

try:
    import google.cloud.logging
    gcp_logging_client = google.cloud.logging.Client()
    gcp_logging_client.setup_logging()
except Exception as e:
    pass

logger = logging.getLogger("ai_training_agents")

DEFAULT_PROJECT = None
try:
    import google.auth
    _, DEFAULT_PROJECT = google.auth.default()
except Exception:
    pass


# This function is not helpful in AgentPlatform
# cause LocalAgentConfig ignore vertex mode. I end up with providing GEMINI_API_Key
def get_default_gemini_config(model: str = "gemini-2.5-flash") -> Any | None:
    """Returns a GeminiConfig configured for Vertex AI using google.auth.default()."""
    project = DEFAULT_PROJECT
    logger.info("Using GCP project: %s", project)
    if not project:
        try:
            import google.auth
            _, project = google.auth.default()
        except Exception:
            pass

    if project:
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        import google.antigravity as ag
        gemini_config_cls = getattr(types, "GeminiConfig", getattr(ag, "GeminiConfig", None))
        if gemini_config_cls is not None:
            endpoint_obj = None
            if hasattr(types, "Endpoint"): 
                # this branch not triggered
                try:
                    endpoint_obj = types.Endpoint(use_vertex=True, project=project, location=location)
                except Exception:
                    pass
            logger.info("------------- Endpoint: %s", endpoint_obj)
            print("------------- Endpoint Print: %s", endpoint_obj)
            if endpoint_obj is not None:
                model_entry = types.ModelEntry(name=model, endpoint=endpoint_obj)
            else:
                model_entry = types.ModelEntry(name=model)
            models = types.ModelConfig(default=model_entry)
            # setting vertex=True has no use, cause LocalAgentConfig ignore vertex mode
            return gemini_config_cls(vertex=True, project=project, location=location, models=models)
    return None
