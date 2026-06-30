from duckduckgo_search import DDGS


def search_web(query: str) -> str:
    """Searches the web for recipes, cooking ideas, grocery stores, or restaurants.

    Args:
        query: The search query (e.g., "healthy vegetarian dinner recipes" or "grocery stores near me").

    Returns:
        A string containing the top search results with titles, URLs, and snippets.
    """
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
