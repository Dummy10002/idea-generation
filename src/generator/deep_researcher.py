"""
Deep Research Engine
====================
Provides thorough, multi-source research for news topics.

Uses multiple free search engines to gather comprehensive context:
- DuckDuckGo (primary)
- Wikipedia summaries
- Reddit discussions

This replaces the simple context_researcher.py with deeper research.
"""

from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.logger import logger


@dataclass
class ResearchResult:
    """A single research finding."""
    source: str
    title: str
    snippet: str
    url: str
    relevance: str  # 'high', 'medium', 'low'


class DeepResearcher:
    """
    Multi-source research engine for thorough topic analysis.
    
    Philosophy:
    - Not just headlines, but actual understanding
    - Cross-reference multiple sources
    - Find real use cases and examples
    - Identify what makes this news unique
    """
    
    def __init__(self):
        self.results: List[ResearchResult] = []
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
    )
    def _search_ddg(self, query: str, num_results: int = 5) -> List[Dict]:
        """Search DuckDuckGo for results."""
        results = []
        
        try:
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=num_results):
                    results.append({
                        'title': r.get('title', ''),
                        'snippet': r.get('body', ''),
                        'url': r.get('href', '')
                    })
            
            logger.debug(f"DDG found {len(results)} results for: {query[:40]}...")
            
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
        
        return results
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
    )
    def _search_reddit_discussions(self, topic: str) -> List[Dict]:
        """Find Reddit discussions about the topic."""
        import requests
        results = []
        
        try:
            # Search Reddit for discussions
            headers = {'User-Agent': 'AINewsResearcher/1.0'}
            response = requests.get(
                "https://www.reddit.com/search.json",
                params={
                    "q": topic,
                    "sort": "relevance",
                    "t": "week",  # Last week
                    "limit": 5
                },
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            for post in data.get("data", {}).get("children", []):
                post_data = post.get("data", {})
                results.append({
                    'title': post_data.get("title", ""),
                    'snippet': post_data.get("selftext", "")[:300],
                    'url': f"https://reddit.com{post_data.get('permalink', '')}",
                    'score': post_data.get("score", 0),
                    'subreddit': post_data.get("subreddit", "")
                })
            
            logger.debug(f"Reddit found {len(results)} discussions")
            
        except Exception as e:
            logger.warning(f"Reddit search failed: {e}")
        
        return results
    
    def _extract_key_facts(self, search_results: List[Dict]) -> List[str]:
        """Extract key facts from search results."""
        facts = []
        
        for result in search_results:
            snippet = result.get('snippet', '')
            # Extract sentences that contain numbers or specific claims
            sentences = snippet.split('.')
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 20:
                    continue
                # Prioritize sentences with numbers, percentages, dates
                if any(char.isdigit() for char in sentence):
                    facts.append(sentence + '.')
                elif any(word in sentence.lower() for word in ['launched', 'announced', 'released', 'new', 'first', 'fastest', 'best']):
                    facts.append(sentence + '.')
        
        # Deduplicate and return top facts
        seen = set()
        unique_facts = []
        for fact in facts:
            normalized = fact.lower()[:50]
            if normalized not in seen:
                seen.add(normalized)
                unique_facts.append(fact)
        
        return unique_facts[:5]  # Top 5 unique facts
    
    def _find_use_cases(self, topic: str) -> List[str]:
        """Find real-world use cases for the topic."""
        use_cases = []
        
        # Search for use cases specifically
        results = self._search_ddg(f"{topic} use cases examples how to use", num_results=3)
        
        for result in results:
            snippet = result.get('snippet', '')
            # Look for "you can" or "allows you to" patterns
            if any(phrase in snippet.lower() for phrase in ['you can', 'allows', 'enables', 'helps', 'makes it easy']):
                use_cases.append(snippet[:200])
        
        return use_cases[:3]
    
    def _find_comparisons(self, topic: str) -> List[str]:
        """Find comparisons with alternatives."""
        comparisons = []
        
        # Search for comparisons
        results = self._search_ddg(f"{topic} vs alternative comparison better than", num_results=3)
        
        for result in results:
            snippet = result.get('snippet', '')
            if any(phrase in snippet.lower() for phrase in ['better than', 'compared to', 'vs', 'unlike', 'faster', 'cheaper']):
                comparisons.append(snippet[:200])
        
        return comparisons[:2]
    
    def research_topic(self, topic: str) -> Dict:
        """
        Perform deep research on a topic.
        
        Returns comprehensive research report with:
        - Key facts
        - Use cases
        - Reddit community sentiment
        - Comparisons with alternatives
        - Why it matters (hook potential)
        """
        logger.info(f"Deep researching: {topic}")
        
        report = {
            "topic": topic,
            "researched_at": datetime.now().isoformat(),
            "summary": "",
            "key_facts": [],
            "use_cases": [],
            "reddit_sentiment": [],
            "comparisons": [],
            "hook_angles": [],
            "sources": []
        }
        
        # 1. General search for facts
        logger.info("  → Searching for key facts...")
        general_results = self._search_ddg(f"{topic} explained news", num_results=5)
        report["key_facts"] = self._extract_key_facts(general_results)
        report["sources"].extend([r.get('url', '') for r in general_results])
        
        # 2. Find use cases
        logger.info("  → Finding use cases...")
        report["use_cases"] = self._find_use_cases(topic)
        
        # 3. Reddit sentiment
        logger.info("  → Checking Reddit discussions...")
        reddit_results = self._search_reddit_discussions(topic)
        for r in reddit_results:
            sentiment = {
                "subreddit": r.get('subreddit', 'unknown'),
                "title": r.get('title', ''),
                "engagement": r.get('score', 0),
                "url": r.get('url', '')
            }
            report["reddit_sentiment"].append(sentiment)
        
        # 4. Comparisons
        logger.info("  → Finding comparisons...")
        report["comparisons"] = self._find_comparisons(topic)
        
        # 5. Generate hook angles
        report["hook_angles"] = self._generate_hook_angles(topic, report)
        
        # 6. Create summary
        report["summary"] = self._create_summary(report)
        
        logger.info(f"Research complete: {len(report['key_facts'])} facts, {len(report['use_cases'])} use cases")
        
        return report
    
    def _generate_hook_angles(self, topic: str, report: Dict) -> List[str]:
        """Generate potential hook angles for content."""
        hooks = []
        
        # Based on facts with numbers
        for fact in report["key_facts"]:
            if any(char.isdigit() for char in fact):
                hooks.append(f"💡 Number hook: {fact[:100]}...")
        
        # Based on Reddit engagement
        for r in report["reddit_sentiment"]:
            if r.get("engagement", 0) > 100:
                hooks.append(f"🔥 Trending on r/{r['subreddit']}: {r['title'][:60]}...")
        
        # Based on comparisons
        for comp in report["comparisons"]:
            hooks.append(f"⚔️ Comparison angle: {comp[:80]}...")
        
        return hooks[:5]
    
    def _create_summary(self, report: Dict) -> str:
        """Create a brief summary of the research."""
        parts = []
        
        if report["key_facts"]:
            parts.append(f"📊 {len(report['key_facts'])} key facts found")
        
        if report["use_cases"]:
            parts.append(f"🛠️ {len(report['use_cases'])} use cases identified")
        
        if report["reddit_sentiment"]:
            total_engagement = sum(r.get("engagement", 0) for r in report["reddit_sentiment"])
            parts.append(f"💬 Reddit buzz: {total_engagement:,} total upvotes")
        
        if report["hook_angles"]:
            parts.append(f"🎯 {len(report['hook_angles'])} potential hook angles")
        
        return " | ".join(parts) if parts else "Basic research complete"
    
    def format_for_delivery(self, report: Dict) -> str:
        """Format research report for human reading."""
        lines = [
            f"# 🔬 Deep Research: {report['topic']}",
            f"*Researched: {report['researched_at'][:16]}*",
            "",
            f"**Summary:** {report['summary']}",
            "",
            "---",
            "",
            "## 📊 Key Facts",
        ]
        
        for i, fact in enumerate(report["key_facts"], 1):
            lines.append(f"{i}. {fact}")
        
        if report["use_cases"]:
            lines.append("")
            lines.append("## 🛠️ Real-World Use Cases")
            for i, uc in enumerate(report["use_cases"], 1):
                lines.append(f"{i}. {uc}")
        
        if report["reddit_sentiment"]:
            lines.append("")
            lines.append("## 💬 Reddit Community Buzz")
            for r in report["reddit_sentiment"][:3]:
                lines.append(f"- **r/{r['subreddit']}** ({r['engagement']:,} pts): {r['title'][:60]}...")
        
        if report["hook_angles"]:
            lines.append("")
            lines.append("## 🎯 Potential Hook Angles")
            for hook in report["hook_angles"]:
                lines.append(f"- {hook}")
        
        if report["comparisons"]:
            lines.append("")
            lines.append("## ⚔️ Comparisons")
            for comp in report["comparisons"]:
                lines.append(f"- {comp}")
        
        return "\n".join(lines)
