from ..db.archive_repo import search_archive

def recall(user_id: str, query: str) -> str:
    """
    Searches the user's archive for a given query.
    Returns a formatted string of the top results.
    """
    if not query or not query.strip():
        return "Please provide a search query."
    results = search_archive(user_id, query)

    if not results:
        return "No results found in your archive for that query."

    formatted_results = ["From your archive:"]
    for res in results:
        title = res.get("title", "No title")
        updated_at = res.get("updatedAt", "No date")
        tags = ", ".join(res.get("tags", []))
        excerpt = res.get("summary", "No summary")

        formatted_results.append(
            f"- Title: {title}\n"
            f"  Updated: {updated_at}\n"
            f"  Tags: {tags}\n"
            f"  Excerpt: {excerpt}"
        )

    return "\n".join(formatted_results)
