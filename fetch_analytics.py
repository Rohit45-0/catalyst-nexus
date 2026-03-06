"""
Fetch Instagram Post Analytics
==============================

This script fetches analytics/insights for your published Instagram post.
"""

import requests
from datetime import datetime

# Your credentials
ACCESS_TOKEN = 'EAAZA6ygrlE3EBQhwbXFqOZCI0zWsbGQHJGXu3IDjqYztPg1oltdA8WkKlfgZBOHccHEiCOHn4u958ikopKsnA1gk8GNZADiBT7NSImZB99vF9gSZBT9gtvTRsyUiuHK6lSKmKgPXKaQpY1ZCXDgIdvKkMp4K3ODgfjo6cx22jXQvyrGd0atsWm5N8mCH4ruWgZDZD'
ACCOUNT_ID = '17841478698032119'  # Correct Instagram Business Account ID

print("="*80)
print("📊 INSTAGRAM POST ANALYTICS")
print("="*80)

# Step 1: Get recent media (posts)
print(f"\n📥 Fetching recent posts from @itsfunyyyyyyyy...")

media_url = f"https://graph.facebook.com/v18.0/{ACCOUNT_ID}/media"
media_params = {
    'access_token': ACCESS_TOKEN,
    'fields': 'id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count',
    'limit': 10
}

media_response = requests.get(media_url, params=media_params)

if media_response.status_code != 200:
    print(f"❌ Failed to fetch media: {media_response.json()}")
    exit(1)

media_data = media_response.json()
posts = media_data.get('data', [])

print(f"✅ Found {len(posts)} recent posts\n")

# Display recent posts
print("="*80)
print("RECENT POSTS")
print("="*80)

for i, post in enumerate(posts, 1):
    print(f"\n📸 Post {i}:")
    print(f"   ID: {post.get('id')}")
    print(f"   Type: {post.get('media_type')}")
    print(f"   Caption: {post.get('caption', 'No caption')[:100]}...")
    print(f"   Likes: {post.get('like_count', 0)}")
    print(f"   Comments: {post.get('comments_count', 0)}")
    print(f"   Posted: {post.get('timestamp', 'Unknown')}")
    print(f"   Link: {post.get('permalink', 'N/A')}")

# Step 2: Get insights for the most recent post (the laptop post)
if posts:
    latest_post = posts[0]
    post_id = latest_post['id']
    
    print(f"\n{'='*80}")
    print(f"📈 DETAILED ANALYTICS FOR LATEST POST (LAPTOP)")
    print(f"{'='*80}")
    
    # Fetch insights
    insights_url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
    insights_params = {
        'access_token': ACCESS_TOKEN,
        'metric': 'impressions,reach,engagement,saved,shares'
    }
    
    insights_response = requests.get(insights_url, params=insights_params)
    
    print(f"\n📊 Insights API Response Status: {insights_response.status_code}")
    
    if insights_response.status_code == 200:
        insights_data = insights_response.json()
        
        print(f"\n✅ Analytics Retrieved:")
        print(f"{'='*80}")
        
        if 'data' in insights_data:
            for metric in insights_data['data']:
                metric_name = metric.get('name')
                metric_values = metric.get('values', [])
                
                if metric_values:
                    value = metric_values[0].get('value', 0)
                    print(f"   {metric_name.upper()}: {value}")
        else:
            print("   Note: Insights may not be available yet (posts need 24-48 hours)")
    else:
        print(f"\n⚠️  Insights not available yet")
        print(f"   Response: {insights_response.text}")
        print(f"\n   Instagram insights are typically available:")
        print(f"   - After 24-48 hours for photo posts")
        print(f"   - Immediately for some basic metrics")
    
    # Basic metrics (available immediately)
    print(f"\n📊 BASIC METRICS (Available Now):")
    print(f"{'='*80}")
    print(f"   Likes: {latest_post.get('like_count', 0)}")
    print(f"   Comments: {latest_post.get('comments_count', 0)}")
    print(f"   Post Type: {latest_post.get('media_type')}")
    print(f"   Posted At: {latest_post.get('timestamp')}")
    
    # Step 3: Get account insights
    print(f"\n{'='*80}")
    print(f"📊 ACCOUNT INSIGHTS (Last 7 Days)")
    print(f"{'='*80}")
    
    account_insights_url = f"https://graph.facebook.com/v18.0/{ACCOUNT_ID}/insights"
    account_insights_params = {
        'access_token': ACCESS_TOKEN,
        'metric': 'impressions,reach,profile_views,follower_count',
        'period': 'day',
        'since': '2026-02-03',
        'until': '2026-02-10'
    }
    
    account_response = requests.get(account_insights_url, params=account_insights_params)
    
    if account_response.status_code == 200:
        account_data = account_response.json()
        
        print(f"\n✅ Account Analytics:")
        
        if 'data' in account_data:
            for metric in account_data['data']:
                metric_name = metric.get('name')
                metric_values = metric.get('values', [])
                
                if metric_values:
                    # Sum up all values
                    total = sum(v.get('value', 0) for v in metric_values)
                    print(f"   {metric_name.upper()}: {total}")
    else:
        print(f"   Response: {account_response.text[:200]}")

else:
    print("\n❌ No posts found")

print(f"\n{'='*80}")
print(f"Analytics completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*80}\n")

print(f"\n💡 TIP: For complete analytics dashboard, visit:")
print(f"   https://www.instagram.com/itsfunyyyyyyyy/")
print(f"   Then go to Insights in your Instagram app or business.facebook.com")
