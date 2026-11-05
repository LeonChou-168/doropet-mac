"""搜索工具 — 百度、Bing、网页访问。"""

import json

import requests
from bs4 import BeautifulSoup

from src.agent.tools_cache import cached


@cached(ttl_seconds=300)
async def search_baidu(query: str) -> str:
    """Search for real-time information on the internet using Baidu.

    Args:
        query: The search keywords.
    """
    if not query:
        return json.dumps({"status": "error", "message": "Query is required."})

    try:
        url = "https://www.baidu.com/s"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        params = {"wd": query}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for item in soup.select('.result.c-container, .result-op.c-container'):
            title_elem = item.select_one("h3")
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            link = title_elem.select_one("a")["href"] if title_elem.select_one("a") else ""
            abstract_elem = item.select_one(".c-abstract") or item.select_one(".c-span18")
            abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""
            if title and link:
                results.append({"title": title, "link": link, "snippet": abstract})
            if len(results) >= 5:
                break

        return json.dumps({
            "status": "success",
            "message": f"Found {len(results)} results.",
            "results": results
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@cached(ttl_seconds=300)
async def search_bing(query: str) -> str:
    """Search for real-time information using Bing. Optimized for Chinese users and general queries.

    Args:
        query: The search keywords.
    """
    if not query:
        return json.dumps({"status": "error", "message": "Query is required."})

    try:
        url = "https://cn.bing.com/search"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        params = {"q": query}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for item in soup.select('.b_algo'):
            title_elem = item.select_one("h2 a")
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            link = title_elem["href"]
            snippet_elem = item.select_one(".b_caption p")
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            if title and link:
                results.append({"title": title, "link": link, "snippet": snippet})
            if len(results) >= 5:
                break

        return json.dumps({
            "status": "success",
            "message": f"Found {len(results)} results from Bing.",
            "results": results
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@cached(ttl_seconds=600)
async def visit_webpage(url: str) -> str:
    """Visit a specific URL and extract its text content.

    Args:
        url: The URL to visit.
    """
    if not url:
        return json.dumps({"status": "error", "message": "URL is required."})

    if not url.startswith("http"):
        url = "https://" + url

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, "html.parser")
        for script in soup(["script", "style", "nav", "footer", "header", "meta", "noscript"]):
            script.extract()

        text = soup.get_text(separator="\n", strip=True)
        content = text[:4000] + "..." if len(text) > 4000 else text

        return json.dumps({
            "status": "success",
            "message": f"Successfully visited {url}",
            "content": content or "No readable text found."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to visit webpage: {str(e)}"})
