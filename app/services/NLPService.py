# app/services/nlp_service.py
from typing import Dict, List, Any, Optional
import json
import os
from enum import Enum
import logging

# Import all providers
import openai
try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from groq import AsyncGroq
except ImportError:
    AsyncGroq = None

from app.constants.constants import AxiUserRole, BuilderType, ExperienceLevel

# Setup logging
logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    """Available LLM providers"""
    GROQ = "groq"           # Free tier, ultra-fast
    ANTHROPIC = "anthropic" # Cost-effective, high quality
    OPENAI = "openai"       # Fallback, most expensive

class QueryAnalysis:
    def __init__(self, intent: str, entities: Dict, filters: Dict, confidence: float):
        self.intent = intent
        self.entities = entities
        self.filters = filters
        self.confidence = confidence

class NLPService:
    """Natural Language Processing Service with multi-provider support"""
    
    INTENTS = {
        "find_builders": "User wants to find developers/builders",
        "find_cofounders": "User wants to find co-founders",
        "find_investors": "User wants to find investors",
        "find_mentors": "User wants to find mentors/advisors",
        "find_startups": "User wants to find startups to join",
        "get_resources": "User wants resources/information",
        "ask_question": "User has a general question",
        "request_statistics": "User asking for statistics/counts/numbers about platform",
        "request_sensitive_info": "User asking for sensitive information (check sizes, revenue, etc.)"
    }
    
    def __init__(self, preferred_provider: LLMProvider = LLMProvider.GROQ):
        """
        Initialize NLP Service with provider priority
        
        Args:
            preferred_provider: First provider to try (defaults to GROQ for cost savings)
        """
        self.preferred_provider = preferred_provider
        self.providers = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available providers based on environment variables"""
        
        # Initialize Groq (Free tier - try first)
        if AsyncGroq is not None and os.getenv("GROQ_API_KEY"):
            try:
                self.providers[LLMProvider.GROQ] = {
                    "client": AsyncGroq(api_key=os.getenv("GROQ_API_KEY")),
                    "model": "llama-3.3-70b-versatile",  # Updated to latest model
                    "max_tokens": 1024,
                    "supports_json": True
                }
                logger.info("✅ Groq provider initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Groq: {e}")
        
        # Initialize Anthropic (Cost-effective - second choice)
        if anthropic is not None and os.getenv("ANTHROPIC_API_KEY"):
            try:
                self.providers[LLMProvider.ANTHROPIC] = {
                    "client": anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY")),
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1024,
                    "supports_json": True
                }
                logger.info("✅ Anthropic provider initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Anthropic: {e}")
        
        # Initialize OpenAI (Most expensive - last resort)
        if os.getenv("OPENAI_API_KEY"):
            try:
                self.providers[LLMProvider.OPENAI] = {
                    "client": openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")),
                    "model": "gpt-4o-mini",  # Using mini for cost savings
                    "max_tokens": 1024,
                    "supports_json": True
                }
                logger.info("✅ OpenAI provider initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize OpenAI: {e}")
        
        if not self.providers:
            logger.warning("⚠️ No LLM providers available! Will use fallback keyword matching only.")
    
    def _get_provider_priority(self) -> List[LLMProvider]:
        """Get list of providers in priority order"""
        priority = [self.preferred_provider]
        
        # Add remaining providers as fallbacks
        for provider in LLMProvider:
            if provider not in priority and provider in self.providers:
                priority.append(provider)
        
        return priority
    
    async def _call_groq(self, system_prompt: str, user_prompt: str) -> str:
        """Call Groq API"""
        provider_config = self.providers[LLMProvider.GROQ]
        
        response = await provider_config["client"].chat.completions.create(
            model=provider_config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=provider_config["max_tokens"],
            response_format={"type": "json_object"} if provider_config["supports_json"] else None
        )
        
        return response.choices[0].message.content
    
    async def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        """Call Anthropic API"""
        provider_config = self.providers[LLMProvider.ANTHROPIC]
        
        response = await provider_config["client"].messages.create(
            model=provider_config["model"],
            max_tokens=provider_config["max_tokens"],
            temperature=0.3,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        return response.content[0].text
    
    async def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI API"""
        provider_config = self.providers[LLMProvider.OPENAI]
        
        response = await provider_config["client"].chat.completions.create(
            model=provider_config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=provider_config["max_tokens"],
            response_format={"type": "json_object"} if provider_config["supports_json"] else None
        )
        
        return response.choices[0].message.content
    
    async def _call_llm(self, provider: LLMProvider, system_prompt: str, user_prompt: str) -> str:
        """Generic LLM call with provider routing"""
        if provider == LLMProvider.GROQ:
            return await self._call_groq(system_prompt, user_prompt)
        elif provider == LLMProvider.ANTHROPIC:
            return await self._call_anthropic(system_prompt, user_prompt)
        elif provider == LLMProvider.OPENAI:
            return await self._call_openai(system_prompt, user_prompt)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def analyze_query(
        self, 
        query: str, 
        user_id: int,
        context: Dict = None
    ) -> QueryAnalysis:
        """
        Analyze user query using best available LLM provider with automatic fallback
        """
        
        system_prompt = f"""You are AXI, an AI assistant for Africa's startup ecosystem.
Your job is to understand what users want and extract relevant information.

Available user roles in the system:
- FOUNDER: Creating/running a startup
- CO_FOUNDER: Looking to join as co-founder
- BUILDER: Developers, designers, etc. (types: DEVELOPER, DESIGNER, PRODUCT_MANAGER, MARKETER, SALES, OTHER)
- INVESTOR: Angel, VC, etc.
- ADVISOR: Providing advice
- MENTOR: Mentoring teams
- PARTNER: Organizations partnering

Experience levels: BEGINNER, INTERMEDIATE, EXPERT, SENIOR

Common intents:
{json.dumps(self.INTENTS, indent=2)}

IMPORTANT INTENT CLASSIFICATION RULES:
1. If user asks "how many X are there" or "what's the count of X" or "number of X in the system" → intent: "request_statistics"
2. If user asks about check sizes, investment amounts, revenues, salaries, rates → intent: "request_sensitive_info"
3. If user says "find", "show me", "looking for", "connect me with" → intent: appropriate find_* intent
4. Statistical questions include: "how many founders", "count of builders", "total investors", "list all X"

EXAMPLES:
- "How many founders are on the platform?" → request_statistics
- "Find founders" → find_cofounders (they want to connect, not count)
- "What are typical check sizes?" → request_sensitive_info
- "Show me investors who write $50k checks" → find_investors (specific search, OK)
- "List all builders" → request_statistics (wants full list, not search)
- "Find Python developers" → find_builders (specific search)

Analyze the user's query and respond ONLY with valid JSON in this exact format:
{{
  "intent": "find_builders|find_cofounders|find_investors|find_mentors|find_startups|get_resources|ask_question|request_statistics|request_sensitive_info",
  "confidence": 0.0-1.0,
  "entities": {{
    "role_seeking": "BUILDER|CO_FOUNDER|etc or null",
    "builder_type": "DEVELOPER|DESIGNER|etc or null",
    "experience_level": "BEGINNER|INTERMEDIATE|EXPERT|SENIOR or null",
    "skills": ["skill1", "skill2"] or [],
    "industry": "string or null",
    "location": "string or null",
    "startup_stage": "IDEA|MVP|EARLY|GROWTH|SCALE or null",
    "quantity": number or null
  }},
  "filters": {{
    "any additional filters extracted"
  }},
  "reasoning": "brief explanation of your analysis"
}}"""

        user_prompt = f"""User query: "{query}"

Current user context:
- User ID: {user_id}
{f"- Previous context: {json.dumps(context)}" if context else ""}

Analyze this query and extract all relevant information."""

        # Try providers in priority order
        provider_priority = self._get_provider_priority()
        
        for provider in provider_priority:
            try:
                logger.info(f"🤖 Trying {provider.value} for query analysis...")
                
                response_text = await self._call_llm(provider, system_prompt, user_prompt)
                analysis_data = json.loads(response_text)
                
                logger.info(f"✅ Successfully analyzed query using {provider.value}")
                
                return QueryAnalysis(
                    intent=analysis_data["intent"],
                    entities=analysis_data["entities"],
                    filters=analysis_data.get("filters", {}),
                    confidence=analysis_data["confidence"]
                )
                
            except Exception as e:
                logger.warning(f"❌ {provider.value} failed: {str(e)}")
                continue
        
        # All providers failed - use fallback
        logger.warning("⚠️ All LLM providers failed, using keyword fallback")
        return self._fallback_analysis(query)
    
    def _fallback_analysis(self, query: str) -> QueryAnalysis:
        """Simple keyword-based fallback if all LLMs fail"""
        query_lower = query.lower()
        
        # Check for statistics requests
        statistics_keywords = ["how many", "count", "number of", "total", "list all", "show all"]
        if any(keyword in query_lower for keyword in statistics_keywords):
            return QueryAnalysis(
                intent="request_statistics",
                entities={},
                filters={},
                confidence=0.7
            )
        
        # Check for sensitive info requests
        sensitive_keywords = ["check size", "investment amount", "revenue", "salary", "hourly rate", "how much"]
        if any(keyword in query_lower for keyword in sensitive_keywords):
            # If they're searching WITH criteria, it's a search; if asking ABOUT amounts, it's sensitive
            if any(word in query_lower for word in ["find", "show me", "looking for"]):
                pass  # Continue to normal search intent detection
            else:
                return QueryAnalysis(
                    intent="request_sensitive_info",
                    entities={},
                    filters={},
                    confidence=0.7
                )
        
        # Simple keyword matching for search intents
        intent = "ask_question"
        entities = {}
        
        if any(word in query_lower for word in ["find", "looking for", "need", "want", "show me"]):
            if any(word in query_lower for word in ["developer", "designer", "builder", "engineer"]):
                intent = "find_builders"
                entities["role_seeking"] = "BUILDER"
                
                if "developer" in query_lower or "engineer" in query_lower:
                    entities["builder_type"] = "DEVELOPER"
                elif "designer" in query_lower:
                    entities["builder_type"] = "DESIGNER"
                
                if "beginner" in query_lower:
                    entities["experience_level"] = "BEGINNER"
                elif "expert" in query_lower or "senior" in query_lower:
                    entities["experience_level"] = "EXPERT"
                elif "intermediate" in query_lower:
                    entities["experience_level"] = "INTERMEDIATE"
            
            elif any(word in query_lower for word in ["co-founder", "cofounder", "partner"]):
                intent = "find_cofounders"
                entities["role_seeking"] = "CO_FOUNDER"
            
            elif any(word in query_lower for word in ["investor", "investment", "funding", "vc"]):
                intent = "find_investors"
                entities["role_seeking"] = "INVESTOR"
            
            elif any(word in query_lower for word in ["mentor", "advisor", "guidance"]):
                intent = "find_mentors"
                entities["role_seeking"] = "MENTOR"
            
            elif any(word in query_lower for word in ["startup", "company", "team"]):
                intent = "find_startups"
        
        return QueryAnalysis(
            intent=intent,
            entities=entities,
            filters={},
            confidence=0.6
        )
    
    async def generate_response(
        self,
        query: str,
        results: List[Dict],
        analysis: QueryAnalysis
    ) -> str:
        """Generate conversational response based on search results"""
        
        # Handle special intents that shouldn't return search results
        if analysis.intent in ["request_statistics", "request_sensitive_info"]:
            return self._generate_restricted_response(query, analysis)
        
        # Determine search type for better context
        search_type_map = {
            "find_builders": "builders",
            "find_cofounders": "co-founders",
            "find_investors": "investors",
            "find_mentors": "mentors",
            "find_startups": "startups",
            "find_advisors": "advisors"
        }
        search_type = search_type_map.get(analysis.intent, "matches")
        
        if len(results) == 0:
            system_prompt = """You are AXI, a direct and helpful AI assistant for Africa's startup ecosystem.
When there are NO results, be concise and actionable. Never apologize or be overly wordy.

RULES FOR NO RESULTS:
- Keep it to 1-2 short sentences MAX
- Be direct: "No matches found" or "I couldn't find any..."
- Give ONE specific, actionable suggestion
- Don't use passive voice or corporate speak
- Don't say "yet" or be overly apologetic
- Sound like a modern AI assistant (ChatGPT-style)

GOOD EXAMPLES:
- "No builders found. Try different skills or expand your location!"
- "I couldn't find any co-founders matching that. Try broader search terms or specific skills instead."
- "No matches yet. Adjust your filters or try different criteria!"

BAD EXAMPLES (too wordy):
- "We didn't find any matches yet, but don't worry..."
- "Unfortunately, we couldn't locate any results at this time..."
- "Let's try refining your search to find the perfect..."
"""
        else:
            system_prompt = """You are AXI, an enthusiastic AI assistant for Africa's startup ecosystem.
When there ARE results, be brief, energetic, and encouraging.

RULES FOR RESULTS:
- Keep it to 1-2 sentences MAX
- Mention the number of results found
- Use action words: "Found", "Here are", "Check out"
- Be enthusiastic but professional
- Sound like a modern AI assistant

GOOD EXAMPLES:
- "Found 5 talented developers! Check out their profiles below."
- "Great! I found 3 experienced co-founders who match your criteria."
- "Here are 8 active investors interested in your industry!"

BAD EXAMPLES (too formal):
- "I have successfully located several results that may be of interest..."
- "Please find below the results of your search query..."
"""

        if len(results) == 0:
            # Map intents to specific suggestions
            suggestions_map = {
                "find_builders": "Try different skills or expand your location",
                "find_cofounders": "Try broader search terms or specific skills instead",
                "find_investors": "Try different investment stages or industries",
                "find_mentors": "Try broader expertise areas or remove location filters",
                "find_startups": "Try different industries or startup stages",
                "find_advisors": "Try different expertise areas or industries"
            }
            
            suggestion = suggestions_map.get(analysis.intent, "Try adjusting your search terms or filters")
            
            user_prompt = f"""User searched for: "{query}"
Search type: {search_type}
Results found: 0

Generate a direct, concise response (1-2 sentences) that:
1. States no matches found (be direct)
2. Gives this specific suggestion: "{suggestion}"

Return ONLY the response text, no JSON, no extra formatting."""

        else:
            user_prompt = f"""User searched for: "{query}"
Search type: {search_type}
Results found: {len(results)}

Generate an enthusiastic, brief response (1-2 sentences) that:
1. Mentions the number of results
2. Encourages them to explore

Return ONLY the response text, no JSON, no extra formatting."""

        # Try providers in priority order
        provider_priority = self._get_provider_priority()
        
        for provider in provider_priority:
            try:
                logger.info(f"🤖 Generating response using {provider.value}...")
                
                # For response generation, we don't need strict JSON mode
                # Just parse the response text
                if provider == LLMProvider.GROQ:
                    response = await self._call_groq_response(system_prompt, user_prompt)
                elif provider == LLMProvider.ANTHROPIC:
                    response = await self._call_anthropic_response(system_prompt, user_prompt)
                elif provider == LLMProvider.OPENAI:
                    response = await self._call_openai_response(system_prompt, user_prompt)
                else:
                    continue
                
                logger.info(f"✅ Response generated using {provider.value}")
                
                # Clean up the response - remove any JSON formatting if present
                response_text = response.strip()
                
                # If it's wrapped in JSON, extract it
                if response_text.startswith('{') and response_text.endswith('}'):
                    try:
                        data = json.loads(response_text)
                        response_text = data.get('response', response_text)
                    except:
                        pass
                
                # Remove any quotes wrapping the response
                response_text = response_text.strip('"\'')
                
                return response_text
                
            except Exception as e:
                logger.warning(f"❌ {provider.value} failed for response generation: {str(e)}")
                continue
        
        # Fallback response
        logger.warning("⚠️ All providers failed for response generation, using fallback")
        if len(results) == 0:
            return "I couldn't find any matches for your search right now. Try adjusting your search terms or ask me something else!"
        return f"I found {len(results)} {'match' if len(results) == 1 else 'matches'} for your search. Let me show you what I found!"
    
    async def _call_groq_response(self, system_prompt: str, user_prompt: str) -> str:
        """Call Groq API for response generation (without strict JSON mode)"""
        provider_config = self.providers[LLMProvider.GROQ]
        
        response = await provider_config["client"].chat.completions.create(
            model=provider_config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=100  # Reduced to force brevity
        )
        
        return response.choices[0].message.content.strip()
    
    async def _call_anthropic_response(self, system_prompt: str, user_prompt: str) -> str:
        """Call Anthropic API for response generation"""
        provider_config = self.providers[LLMProvider.ANTHROPIC]
        
        response = await provider_config["client"].messages.create(
            model=provider_config["model"],
            max_tokens=100,  # Reduced to force brevity
            temperature=0.7,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        return response.content[0].text.strip()
    
    async def _call_openai_response(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI API for response generation"""
        provider_config = self.providers[LLMProvider.OPENAI]
        
        response = await provider_config["client"].chat.completions.create(
            model=provider_config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=100  # Reduced to force brevity
        )
        
        return response.choices[0].message.content.strip()
    
    def get_active_provider(self) -> Optional[str]:
        """Get the name of the currently active provider"""
        provider_priority = self._get_provider_priority()
        return provider_priority[0].value if provider_priority else None
    
    def get_available_providers(self) -> List[str]:
        """Get list of all available providers"""
        return [provider.value for provider in self.providers.keys()]
    
    def _generate_restricted_response(self, query: str, analysis: QueryAnalysis) -> str:
        """Generate response for restricted queries (statistics, sensitive info)"""
        
        if analysis.intent == "request_statistics":
            # User asking for counts/numbers/statistics
            responses = [
                "I can't share overall platform statistics, but I'd be happy to help you find specific people! Try searching for 'find founders' or 'show me developers' instead.",
                "I don't have access to total counts, but I can help you discover and connect with people. What type of person are you looking for?",
                "Platform statistics aren't available through search, but I can help you find specific founders, builders, or investors. What are you looking for?",
            ]
            
            # Determine what they were asking about
            query_lower = query.lower()
            if "founder" in query_lower or "startup" in query_lower:
                return "I can't share total founder counts, but I can help you find specific founders to connect with! Try 'find founders in fintech' or similar searches."
            elif "builder" in query_lower or "developer" in query_lower:
                return "I can't provide builder statistics, but I'd love to help you find developers or designers! Try 'find Python developers' or 'show me UI designers'."
            elif "investor" in query_lower:
                return "I can't share investor counts, but I can help you find investors interested in your industry! Try 'find seed investors' or 'show me angel investors'."
            else:
                return responses[0]
        
        elif analysis.intent == "request_sensitive_info":
            # User asking for sensitive financial info
            query_lower = query.lower()
            
            if "check size" in query_lower or "investment amount" in query_lower:
                return "I can't share specific check sizes, but you can search for investors by stage (seed, Series A, etc.) and connect with them directly to discuss investment details!"
            elif "revenue" in query_lower or "salary" in query_lower or "rate" in query_lower:
                return "I can't provide financial details, but you can connect with people directly through search to discuss specifics. What type of person are you looking for?"
            else:
                return "I don't have access to that sensitive information, but I can help you find and connect with the right people. What are you looking for?"
        
        # Fallback
        return "I can help you find and connect with people in the ecosystem. Try searching for 'find founders', 'show me developers', or similar queries!"

    def generate_loading_message(self, query: str, intent: str = "") -> str:
        """
        Generate a contextual, engaging loading message based on the search query
        
        Args:
            query: The user's search query
            intent: Optional intent classification
        
        Returns:
            A personalized loading message
        """
        query_lower = query.lower()
        
        # Intent-based messages
        intent_messages = {
            "find_builders": [
                "🔍 Scanning our network of talented builders...",
                "🎯 Finding developers who match your criteria...",
                "💻 Searching through our builder community...",
                "⚡ Connecting you with skilled developers...",
            ],
            "find_cofounders": [
                "🤝 Looking for your perfect co-founder match...",
                "🚀 Finding potential co-founders in the ecosystem...",
                "💡 Searching for entrepreneurial partners...",
                "🎯 Matching you with like-minded founders...",
            ],
            "find_investors": [
                "💰 Searching for investors interested in your sector...",
                "🎯 Finding investors who match your stage...",
                "📊 Scanning our investor network...",
                "🤝 Connecting you with potential backers...",
            ],
            "find_mentors": [
                "🎓 Finding experienced mentors for you...",
                "🌟 Searching for the perfect advisor...",
                "🎯 Matching you with industry experts...",
                "💡 Looking for mentors in your domain...",
            ],
            "find_startups": [
                "🚀 Exploring exciting startup opportunities...",
                "🔍 Scanning startups looking for talent...",
                "💼 Finding teams that need your skills...",
                "⚡ Searching for your next adventure...",
            ],
        }
        
        # Keyword-based contextual messages
        if any(word in query_lower for word in ["python", "django", "developer", "engineer"]):
            return "💻 Searching for Python developers in the ecosystem..."
        
        elif any(word in query_lower for word in ["designer", "ui", "ux", "design"]):
            return "🎨 Finding creative designers for you..."
        
        elif any(word in query_lower for word in ["react", "frontend", "vue", "angular"]):
            return "⚛️ Looking for frontend developers..."
        
        elif any(word in query_lower for word in ["backend", "api", "database"]):
            return "🔧 Searching for backend engineers..."
        
        elif any(word in query_lower for word in ["mobile", "ios", "android", "flutter"]):
            return "📱 Finding mobile app developers..."
        
        elif any(word in query_lower for word in ["ai", "ml", "machine learning", "data science"]):
            return "🤖 Searching for AI/ML experts..."
        
        elif any(word in query_lower for word in ["blockchain", "web3", "crypto"]):
            return "⛓️ Finding blockchain developers..."
        
        elif any(word in query_lower for word in ["fintech", "finance"]):
            return "💳 Exploring fintech talent and opportunities..."
        
        elif any(word in query_lower for word in ["healthtech", "health"]):
            return "🏥 Searching healthcare tech innovators..."
        
        elif any(word in query_lower for word in ["edtech", "education"]):
            return "📚 Finding education technology experts..."
        
        elif any(word in query_lower for word in ["technical co-founder", "cto"]):
            return "👨‍💻 Looking for your technical co-founder..."
        
        elif any(word in query_lower for word in ["seed", "series a", "funding"]):
            return "💰 Connecting you with early-stage investors..."
        
        elif any(word in query_lower for word in ["mentor", "advice", "guidance"]):
            return "🎓 Finding experienced mentors for you..."
        
        elif any(word in query_lower for word in ["beginner", "junior", "entry"]):
            return "🌱 Searching for emerging talent..."
        
        elif any(word in query_lower for word in ["senior", "expert", "lead"]):
            return "⭐ Finding experienced professionals..."
        
        elif any(word in query_lower for word in ["ghana", "accra", "kumasi"]):
            return "🇬🇭 Searching Ghana's startup ecosystem..."
        
        elif any(word in query_lower for word in ["nigeria", "lagos", "abuja"]):
            return "🇳🇬 Exploring Nigeria's tech talent..."
        
        elif any(word in query_lower for word in ["kenya", "nairobi"]):
            return "🇰🇪 Scanning Kenya's innovation hub..."
        
        elif any(word in query_lower for word in ["remote", "anywhere"]):
            return "🌍 Searching globally for remote talent..."
        
        # Use intent-based messages if available
        if intent in intent_messages:
            import random
            return random.choice(intent_messages[intent])
        
        # Generic fallback messages (still better than static)
        generic_messages = [
            "🔍 Searching the AXI ecosystem...",
            "⚡ Finding the perfect matches for you...",
            "🎯 Scanning our network...",
            "🚀 Looking for great opportunities...",
            "💡 Discovering amazing talent...",
            "🤝 Connecting you with the ecosystem...",
        ]
        
        import random
        return random.choice(generic_messages)