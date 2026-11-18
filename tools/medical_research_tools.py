
import json
from typing import Any

from Bio import Entrez
from langchain_core.tools import tool

from config.settings import settings


def _extract_text(value: Any) -> str:
    """Convert a PubMed XML value into plain text."""

    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(
            _extract_text(item)
            for item in value
        ).strip()

    return str(value).strip()


def _extract_publication_date(article: dict) -> str:
    """Extract the publication date from a PubMed article."""

    try:
        journal = article["MedlineCitation"]["Article"]["Journal"]
        publication_date = journal["JournalIssue"]["PubDate"]

        year = publication_date.get("Year", "")
        month = publication_date.get("Month", "")
        day = publication_date.get("Day", "")

        if year:
            return " ".join(
                str(part)
                for part in [year, month, day]
                if part
            )

        return _extract_text(
            publication_date.get("MedlineDate", "")
        )

    except (KeyError, TypeError):
        return ""


def _extract_authors(article: dict) -> list[str]:
    """Extract author names from a PubMed article."""

    authors = []

    try:
        author_list = (
            article["MedlineCitation"]["Article"]["AuthorList"]
        )

        for author in author_list:
            collective_name = author.get("CollectiveName")

            if collective_name:
                authors.append(str(collective_name))
                continue

            last_name = author.get("LastName", "")
            initials = author.get("Initials", "")

            full_name = " ".join(
                str(part)
                for part in [initials, last_name]
                if part
            )

            if full_name:
                authors.append(full_name)

    except (KeyError, TypeError):
        pass

    return authors


@tool
def search_medical_references(
    query: str,
    max_results: int = 5,
) -> str:
    """
    Search PubMed for biomedical research articles.

    Provide a medical or scientific search query.
    Returns article titles, authors, publication dates,
    abstracts, and PubMed IDs.

    This tool retrieves research references only.
    It does not diagnose patients or establish treatment plans.
    Do not include patient names, contact details, or other
    personally identifiable patient information in the query.
    """

    query = query.strip()

    if not query:
        return json.dumps({
            "success": False,
            "error": "Search query cannot be empty.",
        })

    if len(query) > 300:
        return json.dumps({
            "success": False,
            "error": "Search query must be 300 characters or fewer.",
        })

    if not 1 <= max_results <= 10:
        return json.dumps({
            "success": False,
            "error": "max_results must be between 1 and 10.",
        })

    try:
        # NCBI recommends identifying the application with an email.
        # An API key is not required for basic PubMed searches.
        if settings.pubmed_email:
            Entrez.email = settings.pubmed_email

        # Step 1: Search PubMed and retrieve matching article IDs.
        with Entrez.esearch(
            db="pubmed",
            term=query,
            retmax=max_results,
            sort="relevance",
        ) as search_handle:
            search_results = Entrez.read(search_handle)

        article_ids = search_results.get("IdList", [])

        if not article_ids:
            return json.dumps({
                "success": True,
                "query": query,
                "total_found": int(search_results.get("Count", 0)),
                "returned": 0,
                "articles": [],
                "message": "No matching PubMed articles were found.",
            }, indent=2)

        # Step 2: Fetch article details using the returned IDs.
        with Entrez.efetch(
            db="pubmed",
            id=",".join(article_ids),
            retmode="xml",
        ) as fetch_handle:
            records = Entrez.read(fetch_handle)

        articles = []

        # Step 3: Extract useful information from each article.
        for record in records.get("PubmedArticle", []):

            citation = record.get("MedlineCitation", {})
            article_data = citation.get("Article", {})

            abstract_data = article_data.get("Abstract", {})
            abstract_parts = abstract_data.get("AbstractText", [])

            abstract = _extract_text(abstract_parts)

            journal_data = article_data.get("Journal", {})

            articles.append({
                "pubmed_id": str(citation.get("PMID", "")),
                "title": _extract_text(
                    article_data.get("ArticleTitle", "")
                ),
                "authors": _extract_authors(record),
                "journal": _extract_text(
                    journal_data.get("Title", "")
                ),
                "publication_date": _extract_publication_date(
                    record
                ),
                "abstract": abstract,
                "pubmed_url": (
                    "https://pubmed.ncbi.nlm.nih.gov/"
                    f"{citation.get('PMID', '')}/"
                ),
            })

        return json.dumps({
            "success": True,
            "query": query,
            "total_found": int(search_results.get("Count", 0)),
            "returned": len(articles),
            "articles": articles,
        }, indent=2, ensure_ascii=False)

    except Exception:
        # Avoid exposing internal errors or configuration details.
        return json.dumps({
            "success": False,
            "error": (
                "PubMed search failed. Check your internet connection "
                "and try again."
            ),
        })
