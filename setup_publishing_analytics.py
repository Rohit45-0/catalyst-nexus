"""
Quick Setup Script for Publishing & Analytics Integration
==========================================================

This script helps integrate the new publishing and analytics features
into the Catalyst Nexus  orchestrator.

Run this script after reviewing the PUBLISHING_ANALYTICS_FIX.md document.
"""

import sys
import os

# Ensure backend is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("=" * 80)
print("Catalyst Nexus - Publishing & Analytics Integration Setup")
print("=" * 80)
print()

# Step 1: Check if required files exist
print("📋 Step 1: Checking created files...")
required_files = [
    "backend/app/services/publishing_service.py",
    "backend/app/services/analytics_service.py",
    "backend/app/agents/publish_node.py",
    "backend/app/api/v1/analytics.py",
    "backend/app/services/scheduler.py",
    "PUBLISHING_ANALYTICS_FIX.md"
]

all_exist = True
for file_path in required_files:
    exists = os.path.exists(file_path)
    status = "✅" if exists else "❌"
    print(f"  {status} {file_path}")
    if not exists:
        all_exist = False

print()

if not all_exist:
    print("❌ Some required files are missing. Please check the setup.")
    sys.exit(1)

# Step 2: Test imports
print("📦 Step 2: Testing imports...")
try:
    from backend.app.services.publishing_service import PublishingService
    print("  ✅ PublishingService")
except ImportError as e:
    print(f"  ❌ PublishingService: {e}")

try:
    from backend.app.services.analytics_service import AnalyticsService
    print("  ✅ AnalyticsService")
except ImportError as e:
    print(f"  ❌ AnalyticsService: {e}")

try:
    from backend.app.agents.publish_node import PublishNode
    print("  ✅ PublishNode")
except ImportError as e:
    print(f"  ❌ PublishNode: {e}")

try:
    from backend.app.api.v1 import analytics
    print("  ✅ Analytics API")
except ImportError as e:
    print(f"  ❌ Analytics API: {e}")

try:
    from backend.app.services.scheduler import start_scheduler, stop_scheduler
    print("  ✅ Scheduler")
except ImportError as e:
    print(f"  ❌ Scheduler: {e}")

print()

# Step 3: Instructions for manual integration
print("📝 Step 3: Manual Integration Required")
print()
print("The following manual steps are required to complete the integration:")
print()
print("1️⃣  Update backend/app/agents/orchestrator.py:")
print("   - Add import: from backend.app.agents.publish_node import PublishNode, route_after_publish")
print("   - Add publishing fields to NexusState TypedDict")
print("   - Add PublishNode to _build_graph() method")
print("   - Update route_after_render() to route to publish node")
print()
print("2️⃣  Update backend/app/main.py:")
print("   - Import analytics router: from backend.app.api.v1 import analytics")
print("   - Add router: app.include_router(analytics.router, prefix='/api/v1/analytics', tags=['analytics'])")
print("   - Import and start scheduler: from backend.app.services.scheduler import start_scheduler, stop_scheduler")
print("   - Add startup event: @app.on_event('startup') async def startup(): start_scheduler()")
print("   - Add shutdown event: @app.on_event('shutdown') async def shutdown(): stop_scheduler()")
print()
print("3️⃣  Update requirements.txt:")
print("   - Add: APScheduler==3.10.4")
print()
print("📖 For detailed instructions, see: PUBLISHING_ANALYTICS_FIX.md")
print()

# Step 4: Display new endpoints
print("🌐 Step 4: New API Endpoints (after integration)")
print()
print("Analytics Endpoints:")
print("  GET    /api/v1/analytics/campaigns/{campaign_id}/analytics")
print("  POST   /api/v1/analytics/campaigns/{campaign_id}/fetch-insights")
print("  POST   /api/v1/analytics/insights/fetch-all")
print("  GET    /api/v1/analytics/dashboard?days=7")
print("  GET    /api/v1/analytics/campaigns/{campaign_id}/timeline")
print("  GET    /api/v1/analytics/campaigns/{campaign_id}/spread")
print("  GET    /api/v1/analytics/campaigns/{campaign_id}/spikes")
print("  GET    /api/v1/analytics/health")
print()

# Step 5: Display workflow changes
print("🔄 Step 5: Updated Workflow")
print()
print("Old Workflow:")
print("  Research → Content → Motion → Render → Finalize")
print()
print("New Workflow:")
print("  Research → Content → Motion → Render → Publish → Finalize")
print()

# Step 6: Test availability
print("🧪 Step 6: Testing Database Connection")
try:
    from backend.app.db.base import SessionLocal
    db = SessionLocal()
    print("  ✅ Database connection successful")
    db.close()
except Exception as e:
    print(f"  ❌ Database connection failed: {e}")
print()

# Final summary
print("=" * 80)
print("✅ Setup script completed!")
print()
print("Next steps:")
print("1. Review the manual integration steps above")
print("2. Update orchestrator.py as described in PUBLISHING_ANALYTICS_FIX.md")
print("3. Update main.py to register analytics router and scheduler")
print("4. Install APScheduler: pip install APScheduler==3.10.4")
print("5. Restart the FastAPI server")
print("6. Test the new endpoints")
print()
print("For testing examples, see PUBLISHING_ANALYTICS_FIX.md")
print("=" * 80)
