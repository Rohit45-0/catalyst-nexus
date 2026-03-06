"""
Instagram Engagement-Based Geographic Spread Tracker
====================================================

Tracks viral spread WITHOUT user clicks by analyzing:
1. Who engages with your post (likes, comments)
2. Their profile locations
3. Engagement timestamps
4. Infer geographic spread pattern

This is the ONLY way to track spread without user interaction.
"""

from typing import List, Dict
import requests
from datetime import datetime
import time

ACCESS_TOKEN = 'EAAZA6ygrlE3EBQhwbXFqOZCI0zWsbGQHJGXu3IDjqYztPg1oltdA8WkKlfgZBOHccHEiCOHn4u958ikopKsnA1gk8GNZADiBT7NSImZB99vF9gSZBT9gtvTRsyUiuHK6lSKmKgPXKaQpY1ZCXDgIdvKkMp4K3ODgfjo6cx22jXQvyrGd0atsWm5N8mCH4ruWgZDZD'
ACCOUNT_ID = '17841478698032119'


class EngagementSpreadTracker:
    """
    Tracks geographic spread based on who engages with post.
    
    NO user interaction required!
    """
    
    def __init__(self):
        self.access_token = ACCESS_TOKEN
        self.account_id = ACCOUNT_ID
    
    def get_post_likers(self, post_id: str) -> List[Dict]:
        """
        Get list of users who liked the post.
        
        Instagram Graph API endpoint.
        """
        
        url = f"https://graph.facebook.com/v18.0/{post_id}/likes"
        
        params = {
            'access_token': self.access_token,
            'fields': 'id,username',
            'limit': 100
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('data', [])
        
        return []
    
    def get_post_commenters(self, post_id: str) -> List[Dict]:
        """
        Get list of users who commented.
        
        Includes comment text which may contain location hints.
        """
        
        url = f"https://graph.facebook.com/v18.0/{post_id}/comments"
        
        params = {
            'access_token': self.access_token,
            'fields': 'id,username,text,timestamp,from',
            'limit': 100
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('data', [])
        
        return []
    
    def get_user_location(self, user_id: str) -> Dict:
        """
        Get user's location from their profile.
        
        Note: Only available if profile is public!
        """
        
        url = f"https://graph.facebook.com/v18.0/{user_id}"
        
        params = {
            'access_token': self.access_token,
            'fields': 'id,username'
            # 'location' field not available via API for privacy
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
        
        return {}
    
    def infer_location_from_comment(self, comment_text: str) -> str:
        """
        Infer location from comment text.
        
        Example: "Love this! - Mumbai" → Mumbai
        """
        
        # Common Indian cities (expand this list)
        cities = [
            'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Pune',
            'Chennai', 'Kolkata', 'Ahmedabad', 'Jaipur', 'Lucknow',
            'Dubai', 'Singapore', 'London', 'New York'
        ]
        
        for city in cities:
            if city.lower() in comment_text.lower():
                return city
        
        return None
    
    def track_engagement_spread(self, post_id: str) -> Dict:
        """
        Track geographic spread based on engagement.
        
        Returns:
        {
          'engagement_by_time': [...],
          'inferred_cities': [...],
          'spread_pattern': [...]
        }
        """
        
        print(f"\n🔍 Tracking engagement spread for post: {post_id}")
        
        # Get commenters (best source with timestamps)
        commenters = self.get_post_commenters(post_id)
        
        print(f"   Found {len(commenters)} comments")
        
        # Analyze comments for location
        city_timeline = []
        
        for comment in commenters:
            text = comment.get('text', '')
            timestamp = comment.get('timestamp', '')
            
            # Try to infer location from comment
            city = self.infer_location_from_comment(text)
            
            if city:
                city_timeline.append({
                    'city': city,
                    'timestamp': timestamp,
                    'username': comment.get('from', {}).get('username', 'unknown')
                })
        
        # Sort by time
        city_timeline.sort(key=lambda x: x['timestamp'])
        
        # Detect spread pattern
        spread_pattern = []
        unique_cities = list(set(c['city'] for c in city_timeline))
        
        for i in range(len(unique_cities) - 1):
            spread_pattern.append({
                'from': unique_cities[i],
                'to': unique_cities[i + 1]
            })
        
        return {
            'total_comments': len(commenters),
            'comments_with_location': len(city_timeline),
            'city_timeline': city_timeline,
            'unique_cities': unique_cities,
            'spread_pattern': spread_pattern
        }


# Example usage
if __name__ == "__main__":
    tracker = EngagementSpreadTracker()
    
    # Your latest post ID
    post_id = "YOUR_POST_ID"  # Get from Instagram
    
    spread_data = tracker.track_engagement_spread(post_id)
    
    print(f"\n📊 SPREAD ANALYSIS:")
    print(f"   Comments with location: {spread_data['comments_with_location']}")
    print(f"   Cities detected: {', '.join(spread_data['unique_cities'])}")
    
    if spread_data['spread_pattern']:
        print(f"\n   Spread pattern:")
        for edge in spread_data['spread_pattern']:
            print(f"      {edge['from']} → {edge['to']}")
