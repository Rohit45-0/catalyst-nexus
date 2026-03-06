#!/usr/bin/env python3
"""
🚀 CATALYST NEXUS - FULL AI VIDEO PIPELINE
==========================================

Complete end-to-end video ad generation:
1. VisionDNA Agent → Analyzes product image with GPT-4o Vision
2. Creative Director → Plans marketing strategy & storyboard
3. Prompt Engineer → Crafts optimized Sora-2 prompt
4. Neural Render → Generates video with FastRouter Sora-2
5. Post-Processing → Adds branding metadata

Author: Catalyst Nexus Team
"""

import asyncio
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.core.config import settings

# =============================================================================
# CONFIGURATION
# =============================================================================

# HP Laptop image (base64 encode from file or use attached)
HP_LAPTOP_IMAGE_PATH = r"D:\Catalyst Nexus\hp_laptop.jpg"  # Save your image here


# Load API key from environment
from dotenv import load_dotenv
load_dotenv(override=True)
_raw_key = os.getenv("FASTROUTER_API_KEY") or settings.FASTROUTER_API_KEY
FASTROUTER_API_KEY = _raw_key.strip() if _raw_key else None
if FASTROUTER_API_KEY and (FASTROUTER_API_KEY.startswith('"') or FASTROUTER_API_KEY.startswith("'")):
    FASTROUTER_API_KEY = FASTROUTER_API_KEY[1:-1]

FASTROUTER_API_URL = "https://go.fastrouter.ai/api/v1/videos"

FASTROUTER_STATUS_URL = "https://go.fastrouter.ai/api/v1/getVideoResponse"


OUTPUT_DIR = Path(__file__).parent / "output" / "full_pipeline"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# STEP 1: VISION DNA AGENT - Product Analysis with GPT-4o
# =============================================================================

async def analyze_product_with_vision(image_base64: str) -> dict:
    """
    Use Azure OpenAI GPT-4o Vision to deeply analyze the product image.
    Returns structured data about the product.
    """
    print("\n" + "="*60)
    print("🧬 STEP 1: VISION DNA EXTRACTION")
    print("="*60)
    print("   Analyzing product image with GPT-4o Vision...")
    
    VISION_PROMPT = """You are an expert product analyst and marketing specialist.
Analyze this product image and extract detailed information for creating a video advertisement.

Return your analysis as JSON with this structure:
{
    "product": {
        "category": "product type (laptop, phone, etc)",
        "brand": "brand name if visible",
        "model": "model name/number if visible",
        "tagline": "suggested marketing tagline"
    },
    "physical": {
        "primary_color": "main color",
        "secondary_colors": ["other colors"],
        "material": "main material (aluminum, plastic, etc)",
        "finish": "surface finish (matte, glossy, brushed, etc)",
        "form_factor": "shape description"
    },
    "display": {
        "has_screen": true/false,
        "screen_content": "what's shown on screen",
        "screen_colors": ["dominant colors on display"],
        "screen_mood": "mood/feeling of display content"
    },
    "distinctive_features": ["list of unique visual elements"],
    "brand_elements": ["logos, text, symbols visible"],
    "suggested_scenes": [
        {"scene": "description", "duration": seconds, "camera": "movement type"}
    ],
    "target_audience": "who would buy this",
    "emotional_appeal": "what feeling it evokes",
    "key_selling_points": ["main benefits to highlight"]
}

Be specific and detailed. Focus on elements that will make a compelling video ad."""


    # Ensure endpoint doesn't end with slash to avoid double slash
    base_endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip('/')
    url = f"{base_endpoint}/openai/deployments/{settings.AZURE_DEPLOYMENT_NAME}/chat/completions?api-version=2024-02-15-preview"
    
    payload = {
        "messages": [
            {"role": "system", "content": VISION_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": "Analyze this product for a video advertisement. If the image is unclear, provide a generic analysis for a high-end laptop."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}", "detail": "low"}}
            ]}
        ],
        "max_tokens": 1000,
        "temperature": 0.3
    }
    
    headers = {
        "Content-Type": "application/json",
        "api-key": settings.AZURE_OPENAI_API_KEY
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
        content = result["choices"][0]["message"]["content"]
        
        # Extract JSON from response
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0]
        else:
            json_str = content
        
        analysis = json.loads(json_str.strip())
        print("   ✅ Vision analysis complete!")
        
    except Exception as e:
        print(f"   ⚠️ Vision analysis failed: {e}")
        if hasattr(e, 'response') and e.response:
           print(f"   ⚠️ Response: {e.response.text}")
        print("   ⚠️ Using fallback analysis...")
        
        analysis = {
            "product": {"category": "laptop", "brand": "HP", "model": "Spectre / Envy", "tagline": "Power meets elegance"},
            "physical": {"primary_color": "silver", "secondary_colors": ["black"], "material": "aluminum", "finish": "brushed", "form_factor": "slim laptop"},
            "display": {"has_screen": True, "screen_content": "abstract blue wallpaper", "screen_colors": ["blue", "cyan", "black"], "screen_mood": "modern, tech-forward"},
            "distinctive_features": ["ultra-thin chassis", "infinity edge display", "premium metal finish"],
            "brand_elements": ["HP logo on lid"],
            "suggested_scenes": [{"scene": "opening lid reveal", "duration": 3, "camera": "tilt up"}],
            "target_audience": "creative professionals",
            "emotional_appeal": "innovation and reliability",
            "key_selling_points": ["portability", "high-resolution display", "premium build quality"]
        }

    print(f"\n   📦 Product: {analysis.get('product', {}).get('brand', 'Unknown')} {analysis.get('product', {}).get('category', 'Product')}")
    print(f"   🎨 Colors: {analysis.get('physical', {}).get('primary_color', 'N/A')}")
    print(f"   🖥️  Display: {analysis.get('display', {}).get('screen_content', 'N/A')}")
    print(f"   🎯 Audience: {analysis.get('target_audience', 'N/A')}")
    
    return analysis


# =============================================================================
# STEP 2: CREATIVE DIRECTOR - Marketing Strategy
# =============================================================================

async def plan_creative_strategy(product_analysis: dict) -> dict:
    """
    Use GPT-4o to plan the creative strategy and storyboard for the ad.
    """
    print("\n" + "="*60)
    print("🎬 STEP 2: CREATIVE DIRECTION")
    print("="*60)
    print("   Planning marketing strategy and storyboard...")
    
    CREATIVE_PROMPT = f"""You are a world-class creative director for tech product commercials.

Based on this product analysis:
{json.dumps(product_analysis, indent=2)}

Create a compelling 10-second video ad storyboard. Return JSON:
{{
    "concept": "one-line creative concept",
    "mood": "overall mood/feeling",
    "color_palette": ["hex colors for the ad"],
    "music_style": "type of background music",
    "scenes": [
        {{
            "scene_number": 1,
            "duration_seconds": 3,
            "description": "detailed visual description",
            "camera_movement": "specific camera movement",
            "lighting": "lighting style",
            "focus_element": "what to highlight"
        }}
    ],
    "text_overlays": [
        {{"time": 0, "text": "text to show", "position": "center/bottom/top"}}
    ],
    "call_to_action": "final CTA text",
    "sora_prompt": "optimized prompt for Sora-2 video generation (detailed, cinematic)"
}}

Make it premium, cinematic, and compelling. The Sora prompt should be extremely detailed."""


    # Ensure endpoint doesn't end with slash to avoid double slash
    base_endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip('/')
    url = f"{base_endpoint}/openai/deployments/{settings.AZURE_DEPLOYMENT_NAME}/chat/completions?api-version=2024-02-15-preview"
    
    payload = {
        "messages": [
            {"role": "system", "content": "You are an expert creative director specializing in premium tech commercials."},
            {"role": "user", "content": CREATIVE_PROMPT}
        ],
        "max_tokens": 2000,
        "temperature": 0.7
    }
    
    headers = {
        "Content-Type": "application/json",
        "api-key": settings.AZURE_OPENAI_API_KEY
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
        
        content = result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"   ⚠️ Creative planning failed: {e}")
        if hasattr(e, 'response') and e.response:
           print(f"   ⚠️ Response: {e.response.text}")
        print("   ⚠️ Using fallback creative plan...")
        return create_fallback_creative_plan(product_analysis)

    
    try:
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0]
        else:
            json_str = content
        
        creative_plan = json.loads(json_str.strip())
    except:
        # Fallback creative plan
        creative_plan = create_fallback_creative_plan(product_analysis)
    
    print("   ✅ Creative strategy complete!")
    print(f"\n   💡 Concept: {creative_plan.get('concept', 'N/A')}")
    print(f"   🎭 Mood: {creative_plan.get('mood', 'N/A')}")
    print(f"   🎵 Music: {creative_plan.get('music_style', 'N/A')}")
    print(f"   📝 Scenes: {len(creative_plan.get('scenes', []))}")
    
    return creative_plan


def create_fallback_creative_plan(product_analysis: dict) -> dict:
    """Create a fallback creative plan if GPT fails."""
    brand = product_analysis.get('product', {}).get('brand', 'HP')
    category = product_analysis.get('product', {}).get('category', 'laptop')
    color = product_analysis.get('physical', {}).get('primary_color', 'silver')
    screen = product_analysis.get('display', {}).get('screen_content', 'vibrant display')
    
    return {
        "concept": f"Elegance Unleashed - {brand} {category.title()}",
        "mood": "premium, sophisticated, inspiring",
        "color_palette": ["#1a1a2e", "#4a69bd", "#00d4ff", "#ffffff"],
        "music_style": "ambient electronic with subtle bass",
        "scenes": [
            {"scene_number": 1, "duration_seconds": 3, "description": f"Dark void, particle effects swirl. A {color} {category} emerges from darkness, rotating slowly.", "camera_movement": "slow push in", "lighting": "dramatic rim light", "focus_element": "product silhouette"},
            {"scene_number": 2, "duration_seconds": 4, "description": f"The {category} opens gracefully, screen illuminates with {screen}. Blue light reflects on the {color} surface.", "camera_movement": "orbital pan", "lighting": "screen glow + ambient", "focus_element": "display reveal"},
            {"scene_number": 3, "duration_seconds": 3, "description": f"Final beauty shot. {category} at hero angle, brand logo glows. Particles settle.", "camera_movement": "slow zoom out", "lighting": "soft studio", "focus_element": "complete product"}
        ],
        "text_overlays": [
            {"time": 7, "text": brand, "position": "center"},
            {"time": 9, "text": "Elegance Unleashed", "position": "bottom"}
        ],
        "call_to_action": f"Discover the new {brand}",
        "sora_prompt": f"Cinematic commercial: A premium {color} {brand} {category} with sleek aluminum body rotates elegantly in dramatic dark studio. Blue ambient particles float around. The laptop opens smoothly revealing a vibrant screen with {screen}. Soft blue light emanates from the display, reflecting on the brushed metal surface. Camera orbits slowly capturing every angle. Ultra-premium product photography, 4K, cinematic lighting, dark moody atmosphere with blue accent lights, floating particle effects, professional advertisement quality."
    }


# =============================================================================
# STEP 3: PROMPT ENGINEERING - Optimize for Sora-2
# =============================================================================

def optimize_prompt_for_sora(product_analysis: dict, creative_plan: dict) -> str:
    """
    Craft the optimal prompt for Sora-2 based on analysis and creative direction.
    """
    print("\n" + "="*60)
    print("✨ STEP 3: PROMPT ENGINEERING")
    print("="*60)
    
    
    # Use the creative director's prompt as base, enhance it
    base_prompt = creative_plan.get("sora_prompt", "")
    scenes = creative_plan.get("scenes", [])
    concept = creative_plan.get("concept", "Premium product showcase")
    mood = creative_plan.get("mood", "premium")

    # Add specific details from product analysis
    product = product_analysis.get('product', {})
    brand = product.get('brand', 'premium')
    category = product.get('category', 'laptop')
    physical = product_analysis.get('physical', {})
    color = physical.get('primary_color', 'silver')
    material = physical.get('material', 'aluminum')
    finish = physical.get('finish', 'brushed')
    display = product_analysis.get('display', {})
    screen_content = display.get('screen_content', 'vibrant wallpaper')
    screen_colors = display.get('screen_colors', ['blue'])
    features = product_analysis.get('distinctive_features', [])
    
    # Build enhanced prompt
    scene_description = ""
    if scenes and isinstance(scenes, list):
        # Combine scenes into a flow
        scene_description = "Sequence: " + " -> ".join([f"{s.get('scene', s)}" for s in scenes[:3]])
    
    # Construct a highly detailed prompt for Seedance/Sora
    enhanced_prompt = (
        f"High-quality commercial for {brand} {category}. "
        f"Concept: {concept}. Mood: {mood}. "
        f"Product Visuals: Sleek {color} {material} body with {finish} finish. "
        f"Display shows {screen_content} with glowing {', '.join(screen_colors[:2])} light. "
        f"\n\n{scene_description}\n\n"
        f"Camera: Cinematic camera movements, orbital shots, slow pans over {', '.join(features[:2]) if features else 'details'}. "
        f"Lighting: Studio lighting, dramatic rim lights, volumetric atmosphere. "
        f"Style: Photorealistic, 8k resolution, highly detailed, professional color grading, depth of field."
    )

    if base_prompt and len(base_prompt) > 50:
         # If the creative plan gave a detailed prompt, prefer it but augment with specs
         enhanced_prompt = f"{base_prompt} \n\nTechnical Specs: {color} {material}, {finish} finish. {screen_content}."

    print("   ✅ Prompt optimized for Seedance Pro!")
    print(f"\n   📝 Prompt length: {len(enhanced_prompt)} characters")
    print(f"   🎯 Key elements: {brand} {category}, {color}, {mood}")
    
    return enhanced_prompt


# =============================================================================
# STEP 4: NEURAL RENDER - Generate Video with FastRouter Sora-2
# =============================================================================

async def generate_video_with_sora(prompt: str, duration: int = 10) -> str:
    """
    Generate video using FastRouter Sora-2 API.
    Returns path to the generated video.
    """
    print("\n" + "="*60)
    print("🎥 STEP 4: NEURAL RENDERING (Sora-2)")
    print("="*60)
    print(f"   Duration: {duration} seconds")
    print(f"   Model: Bytedance Seedance Pro")
    print("\n   ⏳ Initiating video generation...")
    
    # Ensure key is clean
    if not FASTROUTER_API_KEY:
        print("   ❌ FASTROUTER_API_KEY not found!")
        return ""
        
    clean_key = FASTROUTER_API_KEY.strip()
    if clean_key.startswith('"') and clean_key.endswith('"'): clean_key = clean_key[1:-1]
        
    
    # Validation constraints for Seedance Pro
    # 1. Prompt max 1000 chars
    # 2. Length must be 5 or 10
    # 3. Resolution required
    
    clean_prompt = prompt[:950] + "..." if len(prompt) > 950 else prompt
    clean_duration = 5 if duration < 8 else 10 # Map to allowed values
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {clean_key}"
    }
    
    payload = {
        "model": "bytedance/seedance-pro",
        "prompt": clean_prompt,
        "length": clean_duration,
        "resolution": "1080p"
    }

    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Step 1: Initiate generation
            response = await client.post(FASTROUTER_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            init_result = response.json()
            
            # Try multiple fields for ID
            task_id = init_result.get("id") or init_result.get("taskId") or init_result.get("task_id")
            if not task_id and "data" in init_result and isinstance(init_result["data"], dict):
                # Fix: Check both "id" and "taskId" inside data object
                task_id = init_result["data"].get("id") or init_result["data"].get("taskId")

                
            print(f"   ✅ Task created: {task_id}")
            print(f"   📊 Credits used: {init_result.get('usage', {}).get('credits_used', 'N/A')}")
            
            if not task_id:
                print(f"   ❌ ERROR: No Task ID found in response! Response keys: {list(init_result.keys())}")
                # Print full response for debugging
                print(f"   Response dump: {json.dumps(init_result)[:500]}")
                return ""
            
            # Step 2: Poll for completion
            print("\n   ⏳ Generating video (this takes 30-90 seconds)...")
            
            poll_payload = {
                "taskId": task_id,
                "model": "bytedance/seedance-pro"
            }
            
            max_attempts = 120  # 4 minutes max
            for attempt in range(max_attempts):
                await asyncio.sleep(2)
                
                # Progress bar
                progress = min(95, 10 + (attempt * 0.7))
                bar_filled = int(progress / 2.5)
                bar = "█" * bar_filled + "░" * (40 - bar_filled)
                print(f"\r   [{bar}] {progress:.0f}% - Generating...", end="", flush=True)
                
                poll_response = await client.post(FASTROUTER_STATUS_URL, json=poll_payload, headers=headers)
                
                if poll_response.status_code != 200:
                    print(f"\r   [{bar}] ⚠️ Status: {poll_response.status_code} - {poll_response.text[:50]}...", end="", flush=True)
                    continue
                
                # Check if it's binary video data (completed)
                content_type = poll_response.headers.get("content-type", "")
                
                if "video" in content_type or "octet-stream" in content_type or len(poll_response.content) > 10000:
                    # It's binary video data!
                    print(f"\r   [{'█' * 40}] 100% - Video ready!              ")
                    
                    # Check if it's actually video data (MP4 starts with certain bytes)
                    content = poll_response.content
                    if len(content) > 1000:  # Minimum size for a valid video
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_path = OUTPUT_DIR / f"hp_laptop_full_pipeline_{timestamp}.mp4"
                        
                        with open(output_path, "wb") as f:
                            f.write(content)
                        
                        print(f"\n   ✅ Video saved: {output_path}")
                        print(f"   📦 Size: {len(content) / (1024*1024):.2f} MB")
                        
                        return str(output_path)
                
                # Try to parse as JSON to check status
                try:
                    result = poll_response.json()
                    status = result.get("status", "").lower()
                    
                    if status in ["completed", "success", "done"]:
                        video_url = result.get("url") or result.get("video_url")
                        if video_url:
                            # Download from URL
                            video_response = await client.get(video_url)
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            output_path = OUTPUT_DIR / f"hp_laptop_full_pipeline_{timestamp}.mp4"
                            
                            with open(output_path, "wb") as f:
                                f.write(video_response.content)
                            
                            print(f"\r   [{'█' * 40}] 100% - Video ready!              ")
                            print(f"\n   ✅ Video saved: {output_path}")
                            return str(output_path)
                            
                    elif status in ["failed", "error"]:
                        raise RuntimeError(f"Video generation failed: {result}")
                        
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Likely binary data, save it
                    content = poll_response.content
                    if len(content) > 50000:  # Reasonable video size
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_path = OUTPUT_DIR / f"hp_laptop_full_pipeline_{timestamp}.mp4"
                        
                        with open(output_path, "wb") as f:
                            f.write(content)
                        
                        print(f"\r   [{'█' * 40}] 100% - Video ready!              ")
                        print(f"\n   ✅ Video saved: {output_path}")
                        print(f"   📦 Size: {len(content) / (1024*1024):.2f} MB")
                        
                        return str(output_path)
            
            raise TimeoutError("Video generation timed out after 4 minutes")
            
    except Exception as e:
        print(f"\n   ❌ Video generation failed: {e}")
        if hasattr(e, 'response') and e.response:
           print(f"   ❌ Response: {e.response.text}")
        return ""


# =============================================================================
# STEP 4.5: POSTER GENERATION - Google Gemini Flash
# =============================================================================

async def generate_product_poster(product_analysis: dict, creative_plan: dict) -> str:
    """
    Generate a high-quality product poster using Google Gemini via FastRouter.
    """
    print("\n" + "="*60)
    print("🖼️ STEP 4.5: POSTER GENERATION (Gemini Flash)")
    print("="*60)
    
    brand = product_analysis.get('product', {}).get('brand', 'Premium')
    category = product_analysis.get('product', {}).get('category', 'Product')
    mood = creative_plan.get('mood', 'cinematic')
    
    prompt = f"""Professional product advertisement poster for {brand} {category}. 
    Style: {mood}. 
    High resolution, 8k, photorealistic, advertising photography. 
    Key features: {', '.join(product_analysis.get('distinctive_features', [])[:3])}.
    Text overlay: '{creative_plan.get('concept', 'New Release')}'."""

    print(f"   🎨 Generating poster for: {brand} {category}")
    
    # Using OpenAI client format as requested for FastRouter/Gemini
    from openai import OpenAI
    
    # Initialize client with FastRouter config
    # Ensure FASTROUTER_API_KEY is available
    if not FASTROUTER_API_KEY:
        print("   ❌ Missing FASTROUTER_API_KEY")
        return ""
        
    client = OpenAI(
        api_key=FASTROUTER_API_KEY,
        base_url="https://go.fastrouter.ai/api/v1"
    )
    
    try:
        # Run in thread executor since OpenAI client is synchronous
        def _generate():
            # Check if Gemini Flash model is preferred
            return client.images.generate(
                model="google/gemini-2.5-flash-image",
                prompt=prompt,
                n=1,
                size="1024x1024"
            )
        
        print("   ⏳ Generating poster via Gemini Flash...")
        img_response = await asyncio.to_thread(_generate)
        
        # Depending on response format (b64_json or url)
        if hasattr(img_response.data[0], 'b64_json') and img_response.data[0].b64_json:
            image_base64 = img_response.data[0].b64_json
            image_bytes = base64.b64decode(image_base64)
        elif hasattr(img_response.data[0], 'url') and img_response.data[0].url:
             # Download URL
             async with httpx.AsyncClient() as dl:
                 r = await dl.get(img_response.data[0].url)
                 image_bytes = r.content
        else:
             print("   ❌ No image data returned")
             return ""
        
        # Save image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"poster_{timestamp}.png"
        
        with open(output_path, "wb") as f:
            f.write(image_bytes)
            
        print(f"   ✅ Poster saved: {output_path}")
        return str(output_path)
        
    except Exception as e:
        print(f"   ❌ Poster generation failed: {e}")
        return ""

# =============================================================================
# STEP 4.8: TEXT ASSET GENERATION - Blogs, Tweets, Scripts
# =============================================================================

async def generate_text_assets(product_analysis: dict, creative_plan: dict) -> dict:
    """
    Generate high-volume text content: 1 Blog, 5 Tweets, 1 Short Script.
    """
    print("\n" + "="*60)
    print("📝 STEP 4.8: TEXT CONTENT GENERATION")
    print("="*60)
    
    brand = product_analysis.get('product', {}).get('brand', 'Brand')
    
    PROMPT = f"""Create marketing assets for {brand}.
    
    1. WRITE A BLOG POST (Title + 300 words) about why this product is a game changer.
    2. WRITE 5 VIRAL TWEETS/THREADS about the product features.
    3. WRITE A 30-SECOND REEL SCRIPT (Hook, Value, CTA).
    
    Return as JSON:
    {{
        "blog_post": {{ "title": "...", "content": "..." }},
        "tweets": ["tweet 1", "tweet 2", ...],
        "reel_script": "search text..."
    }}"""
    
    # Reuse Azure Client from earlier steps
    base_endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip('/')
    url = f"{base_endpoint}/openai/deployments/{settings.AZURE_DEPLOYMENT_NAME}/chat/completions?api-version=2024-02-15-preview"
    
    payload = {
        "messages": [
            {"role": "system", "content": "You are a senior content marketing manager."},
            {"role": "user", "content": PROMPT}
        ],
        "max_tokens": 1500,
        "temperature": 0.7
    }
    
    headers = { "Content-Type": "application/json", "api-key": settings.AZURE_OPENAI_API_KEY }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                try:
                    # Basic cleanup
                    if "```json" in content: content = content.split("```json")[1].split("```")[0]
                    elif "```" in content: content = content.split("```")[1].split("```")[0]
                    assets = json.loads(content.strip())
                    print("   ✅ Text assets generated successfully!")
                    return assets
                except:
                    print("   ⚠️ JSON parsing failed for text assets, saving raw text.")
                    return {"raw_text": content}
            else:
                print(f"   ⚠️ Text generation failed: {response.status_code} - {response.text}")
    except Exception as e:
         print(f"   ⚠️ Text generation error: {e}")
         
    return {}
    return {}

# =============================================================================
# STEP 5: POST-PROCESSING - Add Metadata
# =============================================================================

def create_video_metadata(
    video_path: str,
    product_analysis: dict,
    creative_plan: dict,
    prompt: str
) -> dict:
    """
    Create comprehensive metadata for the generated video.
    """
    print("\n" + "="*60)
    print("📋 STEP 5: POST-PROCESSING")
    print("="*60)
    
    metadata = {
        "video_path": video_path,
        "generated_at": datetime.now().isoformat(),
        "pipeline": "Catalyst Nexus Full Pipeline v1.0",
        "stages_completed": [
            "VisionDNA Analysis",
            "Creative Direction",
            "Prompt Engineering",
            "Sora-2 Rendering",
            "Post-Processing"
        ],
        "product": product_analysis.get("product", {}),
        "creative_concept": creative_plan.get("concept", ""),
        "mood": creative_plan.get("mood", ""),
        "prompt_used": prompt,
        "model": "openai/sora-2",
        "api": "FastRouter"
    }
    
    # Save metadata JSON alongside video
    metadata_path = video_path.replace(".mp4", "_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"   ✅ Metadata saved: {metadata_path}")
    
    return metadata


# =============================================================================
# MAIN PIPELINE - MIXED MEDIA
# =============================================================================

async def run_mixed_media_campaign(image_base64: str):
    """
    Run a budget-conscious campaign: 1 Video, 1 Poster, Many Text Assets.
    """
    print("\n")
    print("╔" + "═"*60 + "╗")
    print("║" + " 🚀 CATALYST NEXUS - MIXED MEDIA CAMPAIGN ".center(60) + "║")
    print("╠" + "═"*60 + "╣")
    print("║" + " Budget Mode: 1 Video, 1 Poster, High-Vol Text ".center(60) + "║")
    print("╚" + "═"*60 + "╝")
    
    start_time = datetime.now()
    
    try:
        # 1. VisionDNA
        product_analysis = await analyze_product_with_vision(image_base64)
        
        # 2. Strategy
        creative_plan = await plan_creative_strategy(product_analysis)
        
        # 3. Prompting
        optimized_prompt = optimize_prompt_for_sora(product_analysis, creative_plan)
        
        # 4. Neural Render (Limit: 1 Video)
        print(f"   🎥 Generating video with Bytedance Seedance Pro (10s)...")
        video_path = await generate_video_with_sora(optimized_prompt, duration=10) 
        
        # 5. Poster Generation (Limit: 1 Poster)
        poster_path = await generate_product_poster(product_analysis, creative_plan)
        
        # 6. Text Assets (Unlimited)
        text_assets = await generate_text_assets(product_analysis, creative_plan)
        
        # 7. Final Report & Saving
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Save Text Assets
        text_path = OUTPUT_DIR / f"campaign_copy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(text_path, "w") as f:
            json.dump(text_assets, f, indent=2)
            
        print("\n")
        print("╔" + "═"*60 + "╗")
        print("║" + " 🎉 CAMPAIGN GENERATION COMPLETE! ".center(60) + "║")
        print("╠" + "═"*60 + "╣")
        print(f"║  🎥 Video: {Path(video_path).name}".ljust(61) + "║")
        print(f"║  🖼️  Poster: {Path(poster_path).name}".ljust(61) + "║")
        print(f"║  � Text Assets: {text_path.name}".ljust(61) + "║")
        print("╚" + "═"*60 + "╝")
        
    except Exception as e:
        print(f"\n❌ Campaign failed: {e}")
        import traceback
        traceback.print_exc()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Use placeholder/test image if file doesn't exist to allow immediate testing
    image_path = HP_LAPTOP_IMAGE_PATH
    
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode()
        print(f"✅ Loaded image from: {image_path}")
    else:
        print(f"⚠️  Image not found at {image_path}")
        print("   Using a placeholder black image for testing pipeline flow...")
        # Create a valid 1x1 black pixel base64 jpeg for testing flow
        image_base64 = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAAAP/EABQBAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8A0g//2Q=="
    
    asyncio.run(run_mixed_media_campaign(image_base64))
