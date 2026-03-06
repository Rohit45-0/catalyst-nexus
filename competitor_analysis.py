"""
COMPETITOR DNA ANALYZER & CONTENT GENERATOR
===========================================

This engine deconstructs competitor content to find their "Winning Formula" 
and generates superior content for your brand.

Stack:
1. Tavily API (Search & Discovery)
2. Jina Reader (Blog/Article Extraction)
3. YouTube Transcript API (Video Extraction)
4. OpenAI GPT-4 (Analysis & Generation)
"""

import os
import sys
import json
import requests
from typing import List, Dict, Optional
from datetime import datetime
import re

# Add project root to path to access backend modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from backend.app.services.identity_vault import IdentityVault

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o")
API_VERSION = os.getenv("AZURE_API_VERSION", "2024-02-15-preview")

class TavilySearch:
    """Wrapper for Tavily AI Search API"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.tavily.com/search"
    
    def search(self, query: str, max_results=3, search_depth="advanced") -> List[Dict]:
        """Find top performing content on a topic."""
        print(f"Tavily Scouting: '{query}'...")
        
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "include_answer": True,
            "max_results": max_results,
            # We want both text and likelihood of finding videos
            "include_domains": ["linkedin.com", "medium.com", "youtube.com", "instagram.com"]
        }
        
        try:
            response = requests.post(self.base_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('results', [])
            print(f"   Found {len(results)} potential competitors.")
            return results
        except Exception as e:
            print(f"   Tavily Error: {e}")
            return []

class ContentExtractor:
    """Extracts raw 'DNA' (text/transcript) from URLs"""
    
    @staticmethod
    def extract(url: str) -> str:
        """Decide usage of Jina or YouTube based on URL."""
        
        # 1. YouTube Extraction
        if "youtube.com" in url or "youtu.be" in url:
            return ContentExtractor._extract_youtube(url)
            
        # 2. General Web/Blog Extraction (Jina Reader)
        return ContentExtractor._extract_web(url)
    
    @staticmethod
    def _extract_youtube(url: str) -> str:
        """Get transcript from YouTube video."""
        print(f"   Listening to YouTube Video...")
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            
            # Extract video ID
            video_id = None
            if "v=" in url:
                video_id = url.split("v=")[1].split("&")[0]
            elif "youtu.be/" in url:
                video_id = url.split("youtu.be/")[1].split("?")[0]
            
            if not video_id:
                return "Error: Could not parse Video ID"
                
            # Create instance and fetch transcript
            api = YouTubeTranscriptApi()
            transcript_obj = api.fetch(video_id)
            
            # Format nicely - FetchedTranscriptSnippet uses attributes, not dict keys
            full_text = ""
            for entry in transcript_obj:
                time_min = int(entry.start // 60)
                time_sec = int(entry.start % 60)
                full_text += f"[{time_min:02}:{time_sec:02}] {entry.text}\n"
                
            return full_text[:15000]
            
        except ImportError:
            return "Error: 'youtube_transcript_api' not installed. Run: pip install youtube-transcript-api"
        except Exception as e:
            return f"YouTube Error: {e}"

    @staticmethod
    def _extract_web(url: str) -> str:
        """Use Jina Reader to turn any blog/article into LLM-ready markdown."""
        print(f"   Scraping Article via Jina...")
        jina_url = f"https://r.jina.ai/{url}"
        
        try:
            response = requests.get(jina_url, timeout=15)
            if response.status_code == 200:
                text = response.text
                # Cleanup excessive newlines
                return re.sub(r'\n{3,}', '\n\n', text)[:15000]
            return f"Error: Jina returned {response.status_code}"
        except Exception as e:
            return f"Error scraping: {e}"

class CompetitorAnalyst:
    """The Brain: Deconstructs content and generates new strategy."""
    
    def __init__(self):
        # Determine if using Azure or Standard OpenAI
        self.is_azure = "azure" in str(OPENAI_ENDPOINT).lower() if OPENAI_ENDPOINT else False
        
    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Helper to call LLM (Azure or Standard)."""
        
        headers = {
            "Content-Type": "application/json",
            "api-key": OPENAI_API_KEY
        }
        
        url = f"{OPENAI_ENDPOINT}openai/deployments/{OPENAI_DEPLOYMENT}/chat/completions?api-version={API_VERSION}"
        
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 2000,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"LLM Error: {e}"

    def analyze_dna(self, content_text: str, content_type="blog") -> Dict:
        """Deconstructs the competitor's content."""
        print("   Analyzing Competitor DNA...")
        
        system_prompt = """You are an expert Content Strategist.
        Deconstruct this content into its 'Genetic Code'. 
        
        Return JSON with:
        - hook_strategy: How did they grab attention in first 5 sec/lines?
        - structure_outline: The skeleton of their argument.
        - psychological_triggers: (FOMO, Authority, Greed, etc).
        - keyword_clusters: Main topics covered.
        - missing_gaps: What did they FAIL to answer? (Crucial for outranking).
        - tone_voice: Describe the writing style.
        """
        
        response = self._call_llm(system_prompt, f"Content Type: {content_type}\n\nContent:\n{content_text[:4000]}...")
        
        # Clean markdown code blocks if present
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
            
        try:
            return json.loads(response)
        except:
            return {"raw_analysis": response}

    def generate_superior_content(self, competitor_dna: Dict, product_dna: Dict, topic: str) -> str:
        """Generates content that beats the competitor using User's DNA."""
        print("   Generating Superior Content...")
        
        system_prompt = """You are a World-Class Copywriter.
        Your goal is to write a piece of content that OUTRANKS the competitor.
        
        STRATEGY:
        1. Steal their Structure (it works).
        2. Improve their Hook.
        3. Fill their 'Missing Gaps' (Adversarial Value).
        4. Use the USER's Brand Voice/Visual Identity (Product DNA).
        """
        
        user_prompt = f"""
        TOPIC: {topic}
        
        COMPETITOR DNA (The Baseline):
        {json.dumps(competitor_dna, indent=2)}
        
        USER PRODUCT IDENTITY (Our Advantage):
        {json.dumps(product_dna, indent=2)}
        
        TASK:
        Write a LinkedIn Post / Short Article.
        - Use a contrarian or data-backed hook.
        - Specifically address the 'missing_gaps' found in competitor content.
        - Mention specific visual features from Product DNA.
        """
        
        return self._call_llm(system_prompt, user_prompt)

# ═══════════════════════════════════════════════════════════════════════════
# MAIN WORKFLOW
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("="*60)
    print("COMPETITOR DNA ANALYZER")
    print("="*60)
    
    # 1. Inputs
    if len(sys.argv) > 1:
        topic = sys.argv[1]
    else:
        topic = "Best Noise Cancelling Headphones for Travel"
        
    print(f"Goal: Dominate niche for '{topic}'")
    
    # 2. Get User Product DNA (from Vault)
    print("\naccessing Identity Vault...")
    try:
        vault = IdentityVault()
        # Just getting the most recent item for demo
        identities = vault.list_all(limit=1)
        if identities:
            product_id = identities[0]['id']
            full_identity = vault.get_by_id(product_id)
            product_dna = full_identity.get('visual_dna', {})
            print(f"   Using Identity: {full_identity['product_name']}")
        else:
            print("   No identities in vault. Using generic placeholder.")
            product_dna = {"brand": "Catalyst", "vibe": "Premium, Tech-forward"}
    except Exception as e:
        print(f"   Vault Error: {e}. Using placeholder.")
        product_dna = {"brand": "Catalyst", "vibe": "Premium, Tech-forward"}

    # 3. Scout Competitors
    if not TAVILY_API_KEY:
        print("❌ Missing TAVILY_API_KEY environment variable")
        return

    tavily = TavilySearch(TAVILY_API_KEY)
    results = tavily.search(f"{topic} success stories viral", max_results=2)
    
    if not results:
        print("No competitors found.")
        return

    # 4. Process Top Competitor
    top_result = results[0]
    print(f"\nAnalyzing Winner: {top_result['title']}")
    print(f"   URL: {top_result['url']}")
    
    extractor = ContentExtractor()
    raw_content = extractor.extract(top_result['url'])
    
    if len(raw_content) < 100:
        print("Content extraction failed (too short).")
        return

    # 5. Analyze & Generate
    analyst = CompetitorAnalyst()
    
    # Step A: Deconstruct
    dna_analysis = analyst.analyze_dna(raw_content)
    print(f"\nCompetitor DNA Extracted:")
    print(f"   Hook Strategy: {dna_analysis.get('hook_strategy', 'N/A')}")
    print(f"   Missing Gap: {dna_analysis.get('missing_gaps', 'N/A')}")
    
    # Step B: Generate
    new_content = analyst.generate_superior_content(dna_analysis, product_dna, topic)
    
    print(f"\n{'='*60}")
    print(f"GENERATED SUPERIOR CONTENT")
    print(f"{'='*60}\n")
    print(new_content)
    print(f"\n{'='*60}")
    
    # Save output
    filename = f"content_strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# Strategy for: {topic}\n\n")
        f.write(f"## Competitor Analysis\n{json.dumps(dna_analysis, indent=2)}\n\n")
        f.write(f"## Generated Content\n{new_content}")
    
    print(f"Saved to {filename}")

if __name__ == "__main__":
    main()
