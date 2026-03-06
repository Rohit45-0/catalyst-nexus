"""
Find Your Instagram Business Account ID
=======================================

This script will query the Facebook Graph API to find your Instagram Business Account ID.
"""

import requests

# Your access token
ACCESS_TOKEN = 'EAAZA6ygrlE3EBQhwbXFqOZCI0zWsbGQHJGXu3IDjqYztPg1oltdA8WkKlfgZBOHccHEiCOHn4u958ikopKsnA1gk8GNZADiBT7NSImZB99vF9gSZBT9gtvTRsyUiuHK6lSKmKgPXKaQpY1ZCXDgIdvKkMp4K3ODgfjo6cx22jXQvyrGd0atsWm5N8mCH4ruWgZDZD'
PAGE_ID = '1012567998597853'  # This is your Facebook Page ID

print("="*80)
print("FINDING YOUR INSTAGRAM BUSINESS ACCOUNT ID")
print("="*80)

print(f"\n🔍 Step 1: Checking if {PAGE_ID} is a Facebook Page...")

# Get page info
page_url = f"https://graph.facebook.com/v18.0/{PAGE_ID}"
page_params = {
    'access_token': ACCESS_TOKEN,
    'fields': 'id,name,instagram_business_account'
}

page_response = requests.get(page_url, params=page_params)

print(f"\nResponse Status: {page_response.status_code}")
print(f"Response: {page_response.text}")

if page_response.status_code == 200:
    page_data = page_response.json()
    
    print(f"\n✅ Found Facebook Page:")
    print(f"   Page ID: {page_data.get('id')}")
    print(f"   Page Name: {page_data.get('name', 'N/A')}")
    
    if 'instagram_business_account' in page_data:
        ig_account = page_data['instagram_business_account']
        ig_account_id = ig_account.get('id')
        
        print(f"\n✅ Found Instagram Business Account!")
        print(f"{'='*80}")
        print(f"Instagram Business Account ID: {ig_account_id}")
        print(f"{'='*80}")
        
        print(f"\n📝 Update your .env file with:")
        print(f"   INSTAGRAM_ACCOUNT_ID={ig_account_id}")
        
        # Get Instagram account details
        print(f"\n🔍 Getting Instagram account details...")
        ig_url = f"https://graph.facebook.com/v18.0/{ig_account_id}"
        ig_params = {
            'access_token': ACCESS_TOKEN,
            'fields': 'id,username,name,profile_picture_url'
        }
        
        ig_response = requests.get(ig_url, params=ig_params)
        if ig_response.status_code == 200:
            ig_data = ig_response.json()
            print(f"\n📊 Instagram Account Details:")
            print(f"   ID: {ig_data.get('id')}")
            print(f"   Username: @{ig_data.get('username', 'unknown')}")
            print(f"   Name: {ig_data.get('name', 'N/A')}")
        
    else:
        print(f"\n❌ No Instagram Business Account connected to this Facebook Page!")
        print(f"\n📝 You need to:")
        print(f"   1. Link an Instagram Business Account to your Facebook Page")
        print(f"   2. Go to: https://www.facebook.com/{PAGE_ID}/settings")
        print(f"   3. Navigate to 'Instagram' in the left sidebar")
        print(f"   4. Connect your Instagram Business Account")
else:
    print(f"\n❌ Failed to get page information!")
    try:
        error_data = page_response.json()
        print(f"   Error: {error_data}")
    except:
        print(f"   Response: {page_response.text}")

print(f"\n{'='*80}")
