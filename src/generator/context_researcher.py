"""
Context Researcher
==================
Fetches additional context about a topic before script generation.
Uses DuckDuckGo search (free, no API key needed).
"""

from typing import List, Optional
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.logger import logger


@dataclass
class SearchResult:
    """Represents a single search result."""
    title: str
    snippet: str
    url: str


class ContextResearcher:
    """
    Gathers additional context for script generation.
    
    Purpose: Scripts need real facts & use cases to be credible.
    We search for 2-3 relevant facts before writing.
    """
    
    def __init__(self, max_results: int = 3):
        """
        Initialize researcher.
        
        Args:
            max_results: Maximum search results to return
        """
        self.max_results = max_results
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
    )
    def _search_ddg(self, query: str) -> List[SearchResult]:
        """
        Search using DuckDuckGo.
        
        Args:
            query: Search query
            
        Returns:
            List of SearchResult objects
        """
        results = []
        
        try:
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=self.max_results):
                    results.append(SearchResult(
                        title=r.get('title', ''),
                        snippet=r.get('body', ''),
                        url=r.get('href', '')
                    ))
            
            logger.debug(f"Found {len(results)} results for: {query[:50]}...")
            
        except ImportError:
            logger.warning("duckduckgo-search not installed")
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
        
        return results
    
    def research_topic(self, topic: str) -> str:
        """
        Research a topic and return formatted context.
        
        Args:
            topic: The news topic/headline to research
            
        Returns:
            Formatted context string for the LLM prompt
        """
        # Build search queries
        queries = [
            f"{topic} explained simply",
            f"{topic} use cases examples",
        ]
        
        all_results: List[SearchResult] = []
        
        for query in queries:
            results = self._search_ddg(query)
            all_results.extend(results)
        
        if not all_results:
            logger.warning(f"No research results found for: {topic}")
            return "No additional context found. Generate script based on headline only."
        
        # Format for prompt
        context_lines = [
            "## Research Context",
            f"Topic: {topic}",
            "",
            "### Key Information Found:",
        ]
        
        for idx, result in enumerate(all_results[:5], 1):  # Limit to 5
            context_lines.append(f"{idx}. **{result.title}**")
            context_lines.append(f"   {result.snippet[:200]}...")
            context_lines.append("")
        
        return "\n".join(context_lines)
    
    def get_quick_facts(self, topic: str) -> List[str]:
        """
        Get a list of quick facts about a topic.
        
        Args:
            topic: The topic to research
            
        Returns:
            List of fact strings
        """
        results = self._search_ddg(f"{topic} facts key points")
        
        facts = []
        for r in results:
            # Extract first sentence of snippet as a "fact"
            snippet = r.snippet
            if '.' in snippet:
                fact = snippet.split('.')[0] + '.'
                if len(fact) > 20:  # Filter out too-short snippets
                    facts.append(fact)
        
        return facts[:3]  # Return top 3 facts
