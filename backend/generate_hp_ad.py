#!/usr/bin/env python3
"""
HP Laptop Professional Video Ad Generator
=========================================
Generates a stunning 10-second video advertisement for the HP Laptop
using FastRouter Sora-2 API.
"""

import asyncio
import httpx
import os
import sys
from datetime import datetime
from pathlib import Path

# Configuration
API_KEY = os.getenv("FASTROUTER_API_KEY", "")
API_URL = "https://go.fastrouter.ai/api/v1/videos"
STATUS_URL = "https://go.fastrouter.ai/api/v1/getVideoResponse"
OUTPUT_DIR = Path("D:/Catalyst Nexus/catalyst-nexus-core/backend/output/hp_laptop_ads")

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Professional Ad Prompt - Carefully crafted for stunning visuals
AD_PROMPT = """
Cinematic commercial advertisement for a premium silver HP laptop.

Opening shot: The sleek silver HP laptop emerges from darkness, bathed in soft blue and white ambient lighting. The laptop slowly rotates, showcasing its thin profile and elegant silver aluminum body.

Middle: The laptop opens gracefully, revealing a vibrant display showing a stunning blue butterfly among cherry blossoms. Subtle lens flares and light rays emphasize the premium build quality. The black keyboard with white letters contrasts beautifully against the silver body.

Closing: Camera pulls back to show the full laptop in a modern minimalist setting. Soft particles of light float around. The HP logo gleams with a subtle reflection. 

Style: Ultra high-end tech commercial, Apple-like production quality, premium lighting, shallow depth of field, cinematic color grading, 4K quality, product showcase masterpiece.
""".strip()

# Shorter prompt version (API may have limits)
AD_PROMPT_SHORT = """
Cinematic commercial: A premium silver HP laptop with black keyboard rotates elegantly in dramatic blue ambient lighting. The laptop opens to reveal a vibrant display with blue butterfly wallpaper. Ultra high-end Apple-style tech commercial quality. Premium lighting with subtle lens flares. Minimalist setting, shallow depth of field. The HP logo gleams with reflection. 4K cinematic product showcase.
""".strip()


def print_banner():
    """Print a fancy banner."""
    print("\n" + "=" * 60)
    print("🎬  HP LAPTOP VIDEO AD GENERATOR")
    print("    Powered by Catalyst Nexus + FastRouter Sora-2")
    print("=" * 60 + "\n")


def print_progress(percent: float, message: str):
    """Print a progress bar."""
    bar_length = 40
    filled = int(bar_length * percent)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\r[{bar}] {percent*100:.0f}% - {message}", end="", flush=True)


async def generate_video(duration: int = 10) -> str:
    """Generate the HP laptop ad video."""
    
    print(f"📝 Prompt Preview (first 200 chars):")
    print(f"   {AD_PROMPT_SHORT[:200]}...")
    print(f"\n⏱️  Requested Duration: {duration} seconds")
    print(f"🎨 Model: OpenAI Sora-2 via FastRouter\n")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    
    payload = {
        "model": "openai/sora-2",
        "prompt": AD_PROMPT_SHORT,
        "length": duration,
    }
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Step 1: Initiate video generation
        print_progress(0.05, "Initiating Sora-2...")
        print()
        
        response = await client.post(API_URL, json=payload, headers=headers)
        
        if response.status_code not in [200, 201, 202]:
            print(f"\n❌ API Error: {response.status_code}")
            print(f"   {response.text}")
            return None
        
        init_data = response.json()
        task_id = init_data.get("id") or init_data.get("taskId")
        
        print(f"\n✅ Video generation started!")
        print(f"   Task ID: {task_id}")
        print(f"   Model: {init_data.get('model', 'sora-2')}")
        print(f"   Resolution: {init_data.get('size', '720x1280')}")
        print(f"   Credits Used: {init_data.get('usage', {}).get('credits_used', 'N/A')}")
        print(f"\n⏳ Generating video (this takes 60-120 seconds)...\n")
        
        # Step 2: Poll for completion
        poll_payload = {
            "taskId": task_id,
            "model": "openai/sora-2"
        }
        
        start_time = datetime.now()
        max_polls = 300  # 10 minutes max
        poll_interval = 2
        
        for attempt in range(max_polls):
            elapsed = (datetime.now() - start_time).total_seconds()
            progress = min(0.1 + (0.85 * elapsed / 120), 0.95)  # Assume ~120s generation
            
            print_progress(progress, f"Generating... ({elapsed:.0f}s elapsed)")
            
            try:
                poll_response = await client.post(
                    STATUS_URL, 
                    json=poll_payload, 
                    headers=headers,
                    timeout=30.0
                )
                
                if poll_response.status_code != 200:
                    await asyncio.sleep(poll_interval)
                    continue
                
                # Check if it's binary video data (completed)
                content = poll_response.content
                
                # Check for MP4 magic bytes
                is_mp4 = len(content) > 8 and content[4:8] == b'ftyp'
                is_large = len(content) > 50000  # > 50KB
                
                if is_mp4 or is_large:
                    # Video is ready! Save it
                    print_progress(1.0, "Video ready!")
                    print()
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = OUTPUT_DIR / f"hp_laptop_ad_{timestamp}.mp4"
                    
                    with open(filename, 'wb') as f:
                        f.write(content)
                    
                    elapsed = (datetime.now() - start_time).total_seconds()
                    file_size_mb = len(content) / (1024 * 1024)
                    
                    print(f"\n" + "=" * 60)
                    print(f"🎉 VIDEO GENERATED SUCCESSFULLY!")
                    print(f"=" * 60)
                    print(f"📁 File: {filename}")
                    print(f"📦 Size: {file_size_mb:.2f} MB")
                    print(f"⏱️  Generation Time: {elapsed:.1f} seconds")
                    print(f"=" * 60 + "\n")
                    
                    return str(filename)
                
                # Try to parse as JSON (status check)
                try:
                    status_data = poll_response.json()
                    status = status_data.get("status", "").lower()
                    
                    if status in ["failed", "error"]:
                        print(f"\n❌ Generation failed: {status_data.get('error', 'Unknown')}")
                        return None
                        
                except:
                    pass  # Not JSON, might be processing
                    
            except httpx.RequestError as e:
                print(f"\n⚠️  Network error: {e}, retrying...")
            
            await asyncio.sleep(poll_interval)
        
        print(f"\n❌ Timeout after {max_polls * poll_interval} seconds")
        return None


async def main():
    """Main entry point."""
    print_banner()
    
    print("🖥️  Product: HP Laptop (Silver, Butterfly Wallpaper)")
    print("🎯 Goal: Generate stunning 10-second video advertisement")
    print()
    print("-" * 60)
    
    result = await generate_video(duration=10)
    
    if result:
        print(f"🚀 Your video ad is ready!")
        print(f"   Open: {result}")
        print()
        
        # Try to open the file
        if sys.platform == "win32":
            os.startfile(result)
    else:
        print("❌ Video generation failed. Please check the logs.")


if __name__ == "__main__":
    asyncio.run(main())
