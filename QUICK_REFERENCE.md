# 🚀 Catalyst Nexus - Publishing & Analytics Quick Reference

## 📥 What Was Fixed
```
Problem: Videos generated but never published ❌
Solution: Auto-publishing to Instagram/LinkedIn ✅

Problem: No analytics tracking ❌
Solution: Real-time tracking + hourly insights ✅

Problem: No monitoring dashboard ❌  
Solution: Comprehensive analytics API ✅
```

## 📂 New Files Created (9 files)
```
backend/app/services/
  ├─ publishing_service.py    (Publish to social media)
  ├─ analytics_service.py     (Analytics collection)
  └─ scheduler.py             (Auto insights fetching)

backend/app/agents/
  └─ publish_node.py          (Publishing workflow node)

backend/app/api/v1/
  └─ analytics.py             (Analytics REST API)

Root directory:
  ├─ test_publishing_analytics.py
  ├─ setup_publishing_analytics.py
  ├─ PUBLISHING_ANALYTICS_FIX.md
  └─ PUBLISHING_ANALYTICS_FIX_SUMMARY.md
```

## 🔄 New Workflow
```
OLD: Research → Content → Motion → Render → Finalize
NEW: Research → Content → Motion → Render → Publish → Finalize
```

## 🌐 New API Endpoints (8 endpoints)
```http
GET    /api/v1/analytics/campaigns/{id}/analytics
POST   /api/v1/analytics/campaigns/{id}/fetch-insights
POST   /api/v1/analytics/insights/fetch-all
GET    /api/v1/analytics/dashboard?days=7
GET    /api/v1/analytics/campaigns/{id}/timeline
GET    /api/v1/analytics/campaigns/{id}/spread
GET    /api/v1/analytics/campaigns/{id}/spikes
GET    /api/v1/analytics/health
```

## ⚡ Quick Start

### 1. Validate Setup
```bash
python setup_publishing_analytics.py
```

### 2. Run Tests
```bash
python test_publishing_analytics.py
```

### 3. Manual Integration (Required)
See `PUBLISHING_ANALYTICS_FIX.md` for:
- Orchestrator updates
- Main app updates
- Dependency installation

### 4. Start with Publishing
```python
from backend.app.agents.orchestrator import get_orchestrator

orchestrator = get_orchestrator()

result = await orchestrator.run(
    workflow_type="full_pipeline",
    product_name="My Product",
    product_images=["https://..."],
    auto_publish=True,  # ⭐ Enable publishing
    publish_to_platforms=["instagram"],
    publish_caption="Check this out! #product"
)

print(f"Video: {result['video_url']}")
print(f"Campaign: {result['campaign_id']}")
print(f"Track: {result['tracking_link']}")
```

### 5. View Analytics
```bash
curl http://localhost:8000/api/v1/analytics/dashboard?days=7
```

## 📊 Analytics Features

### Dashboard Metrics
- Total campaigns published
- Aggregate clicks, reach, engagement
- Top performing content
- Campaign summaries

### Campaign Analytics  
- Click events with geo-location
- Engagement metrics (reach, impressions, saves, shares)
- Geographic distribution
- Spike detection (trending cities)
- Spread graph (viral propagation)

### Automation
- Hourly Instagram insights fetching
- Automatic campaign tracking
- Real-time monitoring

## 🔧 Configuration

### Required Environment Variables
```env
INSTAGRAM_ACCESS_TOKEN=your_token
INSTAGRAM_ACCOUNT_ID=your_account_id
```

### Optional Settings
```python
# In orchestrator.run()
auto_publish=True                    # Enable auto-publishing
publish_to_platforms=["instagram"]   # Platforms to publish to
publish_caption="Your caption"       # Social media caption
```

## 📝 Example Usage

### Publish a Video
```python
from backend.app.db.base import SessionLocal
from backend.app.services.publishing_service import PublishingService

db = SessionLocal()
service = PublishingService(db)

result = await service.publish_to_instagram(
    media_url="https://example.com/video.mp4",
    caption="Amazing product! #tech",
    user_id=1
)
# Returns: {campaign_id, post_id, tracking_link}
```

### Fetch Analytics
```python
from backend.app.services.analytics_service import AnalyticsService

service = AnalyticsService(db)
dashboard = service.get_analytics_dashboard(days=7)
# Returns: {total_campaigns, aggregate_metrics, top_campaigns}
```

### Get Campaign Details
```python
analytics = service.get_campaign_analytics("campaign_id")
# Returns: {metrics, geo_distribution, spikes, spread_analysis}
```

## 🎯 Complete Integration Checklist

- [ ] Run `setup_publishing_analytics.py` to validate
- [ ] Run `test_publishing_analytics.py` to test
- [ ] Update `orchestrator.py` (see PUBLISHING_ANALYTICS_FIX.md)
- [ ] Update `main.py` (see PUBLISHING_ANALYTICS_FIX.md)
- [ ] Install: `pip install APScheduler==3.10.4`
- [ ] Configure Instagram credentials in `.env`
- [ ] Restart FastAPI server
- [ ] Test API endpoints
- [ ] Test full workflow with `auto_publish=True`
- [ ] Monitor analytics dashboard

## 💡 Pro Tips

1. **Test with auto_publish=False first** to verify video generation
2. **Use manual insights fetch** before enabling hourly automation
3. **Monitor spike detection** to identify trending markets
4. **Check spread analysis** to understand viral propagation
5. **Review dashboard daily** to track overall performance

## 🐛 Troubleshooting

**Publishing fails:**
- Check Instagram credentials in `.env`
- Verify media URL is publicly accessible
- Check Instagram API rate limits

**No analytics data:**
- Run manual insights fetch
- Verify campaign has post_id
- Check Instagram API permissions

**Scheduler not running:**
- Check scheduler.get_scheduler_status()
- Verify APScheduler is installed
- Check logs for errors

## 📚 Documentation

- **Full Guide:** `PUBLISHING_ANALYTICS_FIX.md`
- **Summary:** `PUBLISHING_ANALYTICS_FIX_SUMMARY.md`
- **This Card:** `QUICK_REFERENCE.md`

---

**Questions?** Check the detailed documentation files!
