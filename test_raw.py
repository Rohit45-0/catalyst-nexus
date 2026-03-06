
import asyncio
import instaloader
import os

async def test_raw():
    with open("raw_test.log", "w", encoding="utf-8") as f:
        f.write("Starting Raw Test...\n")
        try:
            L = instaloader.Instaloader()
            f.write("✅ Instaloader initialized\n")
            
            hashtag = "techreview"
            f.write(f"Scraping #{hashtag}...\n")
            hashtag_obj = instaloader.Hashtag.from_name(L.context, hashtag)
            
            count = 0
            for post in hashtag_obj.get_top_posts():
                if count >= 2: break
                f.write(f"Found post: {post.shortcode} by {post.owner_username}\n")
                f.write(f"Likes: {post.likes}\n")
                count += 1
            f.write("✅ Raw test complete\n")
        except Exception as e:
            f.write(f"❌ Raw test failed: {e}\n")

if __name__ == "__main__":
    asyncio.run(test_raw())
