from typing import Annotated
from pydantic import validate_call, Field
from duckduckgo_search import DDGS
from opentelemetry import trace
from tools.telemetry import get_tracer

tracer = get_tracer()


@tracer.start_as_current_span("search_web")
@validate_call
def search_web(
    query: Annotated[
        str,
        Field(
            min_length=1,
            description="The search query (e.g., 'vegetarian lasagna recipe').",
        ),
    ]
) -> str:
    """Searches the web for recipes, cooking ideas, grocery stores, or restaurants.

    Args:
        query: The search query (e.g., "vegetarian lasagna recipe").

    Returns:
        A string containing the top search results with titles, URLs, and snippets.
    """
    span = trace.get_current_span()
    span.set_attribute("search.query", query)

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if not results:
                return "No search results found."

            formatted_results = []
            for idx, r in enumerate(results, 1):
                title = r.get("title", "No Title")
                href = r.get("href", "No URL")
                body = r.get("body", "No description available.")
                formatted_results.append(
                    f"{idx}. {title}\n   URL: {href}\n   Snippet: {body}\n"
                )

            return "\n".join(formatted_results)
    except Exception as e:
        return f"Web search failed: {str(e)}"
