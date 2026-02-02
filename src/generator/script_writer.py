"""
Script Writer
=============
Generates high-retention, "Viewer as Hero" scripts using Claude API.
"""

from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import anthropic

from ..collectors.rss_collector import NewsItem
from .context_researcher import ContextResearcher
from ..utils.config import settings
from ..utils.logger import logger
from ..utils.rate_limiter import rate_limiter


# =============================================================================
# SYSTEM PROMPT - THE "SECRET SAUCE"
# =============================================================================

SYSTEM_PROMPT = """You are an expert short-form video scriptwriter specializing in HIGH-RETENTION content for Instagram Reels.

## YOUR CORE PHILOSOPHY: "VIEWER AS HERO"
The viewer is NOT a spectator. They are the PROTAGONIST of a micro-story.
Every script must make them feel like they just discovered a superpower.

## STRICT CONSTRAINTS (NEVER VIOLATE):

### 1. PERSPECTIVE
- ALWAYS use "You" (Second Person)
- NEVER say "I found this" or "People are saying" or "There's this new thing"
- Frame EVERY sentence from the viewer's POV: "You wake up. You realize. You now have..."

### 2. LENGTH
- Target: 30-40 seconds when spoken
- Maximum: 60 seconds
- Word count: 70-100 words MAXIMUM
- Each sentence: 8 words or fewer

### 3. READING LEVEL
- 6th grade reading level
- No jargon without immediate analogy
- Use concrete, sensory words over abstract terms

### 4. EDITING CUES (KEEP SIMPLE!)
- ONLY use these cues:
  - [Face Cam] - You talking to camera
  - [Cut] - Simple jump cut
  - [Screen: X] - Show X on screen (screenshot/recording)
  - [Text: X] - Text overlay with X
  - [Zoom] - Simple zoom in
- NEVER suggest: 3D animations, complex graphics, green screen, motion graphics

### 5. STRUCTURE (The Hero's Micro-Journey)
1. **Hook (0-3s)**: The Inciting Incident
   - Put them IN the scene
   - Example: "You wake up. Your job is gone."
   
2. **Gap (3-10s)**: The Struggle
   - Show what they're missing
   - Validate their pain
   - Example: "You try ChatGPT. It's slow. It hallucinates."
   
3. **Bridge (10-25s)**: The Weapon
   - Introduce the news/tool as their solution
   - Make it feel like a game-changing discovery
   - Example: "Enter [Tool]. It writes code while you sleep."
   
4. **Payoff (25-30s)**: The Victory
   - Show immediate value
   - Make them feel powerful
   - Example: "Now you build apps in hours, not weeks."
   
5. **CTA (30s+)**: Join the Guild
   - Low friction community call
   - Example: "Follow for more weapons like this."

### 6. EMOTIONAL TONE
- Empowering, not preachy
- Excited, but not fake hype
- Insider knowledge vibe
- Like a smart friend sharing a secret

## OUTPUT FORMAT:
Provide the script in this EXACT format:

---
**HOOK (0-3s)**
[Editing cue]
"Exact words to say"

**GAP (3-10s)**
[Editing cue]
"Exact words to say"

**BRIDGE (10-25s)**
[Editing cue]
"Exact words to say"

**PAYOFF (25-30s)**
[Editing cue]
"Exact words to say"

**CTA**
[Editing cue]
"Exact words to say"

---
📊 **Stats:**
- Word Count: X
- Estimated Duration: Xs
- Reading Level: 6th Grade ✓
---

REMEMBER: The viewer should feel like a HERO who just found a SECRET WEAPON, not a student being lectured."""


class ScriptWriter:
    """
    Generates scripts using Claude API with psychological prompting.
    
    Features:
    - "Viewer as Hero" framework
    - Context-enriched prompts
    - Rate limiting
    - Token cost tracking
    """
    
    def __init__(self):
        """Initialize script writer."""
        self.client: Optional[anthropic.Anthropic] = None
        self.researcher = ContextResearcher()
        self._init_client()
    
    def _init_client(self) -> None:
        """Initialize Anthropic client."""
        if not settings.anthropic_api_key:
            logger.warning("ANTHROPIC_API_KEY not set. Script generation disabled.")
            return
        
        try:
            self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            logger.info("Anthropic client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
    
    def _build_user_prompt(self, item: NewsItem, context: str) -> str:
        """
        Build the user prompt for script generation.
        
        Args:
            item: The news item to script
            context: Research context
            
        Returns:
            Formatted user prompt
        """
        return f"""Generate a HIGH-RETENTION Instagram Reel script for this topic:

## TOPIC
**Headline:** {item.title}
**Source:** {item.source}
**Summary:** {item.summary}

## RESEARCH CONTEXT
{context}

## YOUR TASK
Write a 30-40 second script that makes the viewer feel like a HERO who just discovered this as their new SECRET WEAPON.

Remember:
- Use "You" throughout
- Keep sentences under 8 words
- Only simple editing cues ([Face Cam], [Cut], [Screen: X], [Text: X], [Zoom])
- Make them feel POWERFUL, not lectured

Generate the script now."""
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _call_claude(self, user_prompt: str) -> str:
        """
        Call Claude API with retry logic.
        
        Args:
            user_prompt: The user prompt
            
        Returns:
            Generated script text
        """
        if not self.client:
            raise ValueError("Anthropic client not initialized")
        
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        # Extract text from response
        response_text = message.content[0].text
        
        # Log token usage
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        logger.info(f"Claude tokens used - Input: {input_tokens}, Output: {output_tokens}")
        
        return response_text
    
    def generate_script(self, item: NewsItem) -> Optional[str]:
        """
        Generate a script for a news item.
        
        Args:
            item: The NewsItem to script
            
        Returns:
            Generated script string, or None on failure
        """
        # Check rate limit
        if not rate_limiter.can_generate_script(settings.max_scripts_per_day):
            logger.warning("Daily script limit reached. Cannot generate.")
            return None
        
        if not self.client:
            logger.error("Cannot generate script: Anthropic client not initialized")
            return None
        
        try:
            # Research context
            logger.info(f"Researching context for: {item.title[:50]}...")
            context = self.researcher.research_topic(item.title)
            
            # Build prompt
            user_prompt = self._build_user_prompt(item, context)
            
            # Generate script
            logger.info("Calling Claude API...")
            script = self._call_claude(user_prompt)
            
            # Record usage
            rate_limiter.record_script_generation()
            
            logger.info(f"Script generated successfully ({len(script)} chars)")
            return script
            
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            return None
    
    def regenerate_script(self, item: NewsItem, feedback: str = "") -> Optional[str]:
        """
        Regenerate a script with optional feedback.
        
        Args:
            item: The NewsItem to script
            feedback: Optional feedback for improvement
            
        Returns:
            Regenerated script string, or None on failure
        """
        if feedback:
            # Append feedback to the item summary
            item.summary = f"{item.summary}\n\nUSER FEEDBACK: {feedback}"
        
        return self.generate_script(item)
