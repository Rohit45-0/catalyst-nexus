"""
Tests for Nexus Orchestrator - LangGraph State Machine
======================================================

Unit and integration tests for the agentic orchestration pipeline.
All external AI calls are mocked.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime
import json

from backend.app.agents.orchestrator import (
    NexusOrchestrator,
    NexusState,
    JobStatus,
    WorkflowType,
    create_initial_state,
    get_orchestrator,
    ResearchNode,
    ContentNode,
    MotionNode,
    RenderNode,
    FinalizeNode,
    route_after_research,
    route_after_content,
    route_after_motion,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def orchestrator():
    """Create orchestrator instance for testing."""
    return NexusOrchestrator()


@pytest.fixture
def sample_state():
    """Create a sample initial state."""
    return create_initial_state(
        job_id=str(uuid4()),
        workflow_type=WorkflowType.PRODUCT_VIDEO.value,
        project_id=str(uuid4()),
        product_name="Test Product",
        product_images=["https://example.com/product.jpg"],
        duration_seconds=15.0,
        aspect_ratio="16:9"
    )


@pytest.fixture
def mock_visual_dna():
    """Mock VisualDNA extraction result."""
    return {
        "product_category": "Electronics",
        "product_description": "Test product",
        "materials": {"primary_material": "plastic"},
        "lighting": {"light_type": "studio"},
        "structure": {"overall_shape": "rectangular"},
        "motion_recommendations": ["360 rotation"],
        "camera_angle_suggestions": ["front view"],
        "confidence_score": 0.9
    }


# =============================================================================
# STATE TESTS
# =============================================================================

class TestNexusState:
    """Tests for state creation and management."""
    
    def test_create_initial_state(self, sample_state):
        """Test initial state is created correctly."""
        assert sample_state["status"] == JobStatus.PENDING.value
        assert sample_state["progress_percent"] == 0.0
        assert sample_state["current_stage"] == "initialization"
        assert sample_state["should_continue"] is True
        assert sample_state["errors"] == []
    
    def test_initial_state_has_required_fields(self, sample_state):
        """Test all required fields are present."""
        required_fields = [
            "job_id", "workflow_type", "status", "project_id",
            "product_name", "product_images", "duration_seconds",
            "current_stage", "progress_percent", "should_continue"
        ]
        for field in required_fields:
            assert field in sample_state
    
    def test_initial_state_outputs_are_none(self, sample_state):
        """Test output fields start as None."""
        assert sample_state["market_research"] is None
        assert sample_state["product_identity"] is None
        assert sample_state["motion_scaffold"] is None
        assert sample_state["video_url"] is None


class TestWorkflowTypes:
    """Tests for workflow type enum."""
    
    def test_all_workflow_types(self):
        """Test all workflow types are defined."""
        expected = [
            "product_video", "identity_extraction", "content_only",
            "motion_only", "render_only", "full_pipeline"
        ]
        actual = [w.value for w in WorkflowType]
        assert set(expected) == set(actual)


class TestJobStatus:
    """Tests for job status enum."""
    
    def test_all_job_statuses(self):
        """Test all job statuses are defined."""
        expected = [
            "pending", "researching", "generating_content",
            "creating_motion", "rendering", "reviewing",
            "completed", "failed", "cancelled"
        ]
        actual = [s.value for s in JobStatus]
        assert set(expected) == set(actual)


# =============================================================================
# ROUTING TESTS
# =============================================================================

class TestRouting:
    """Tests for routing functions."""
    
    def test_route_after_research_continues(self, sample_state):
        """Test research routes to content when continuing."""
        result = route_after_research(sample_state)
        assert result == "content"
    
    def test_route_after_research_stops_on_error(self, sample_state):
        """Test research routes to finalize when not continuing."""
        sample_state["should_continue"] = False
        result = route_after_research(sample_state)
        assert result == "finalize"
    
    def test_route_after_content_to_motion(self, sample_state):
        """Test content routes to motion for product video."""
        result = route_after_content(sample_state)
        assert result == "motion"
    
    def test_route_after_content_to_finalize_for_content_only(self, sample_state):
        """Test content routes to finalize for content-only workflow."""
        sample_state["workflow_type"] = WorkflowType.CONTENT_ONLY.value
        result = route_after_content(sample_state)
        assert result == "finalize"
    
    def test_route_after_motion_to_render(self, sample_state):
        """Test motion routes to render."""
        result = route_after_motion(sample_state)
        assert result == "render"
    
    def test_route_after_motion_to_finalize_for_motion_only(self, sample_state):
        """Test motion routes to finalize for motion-only workflow."""
        sample_state["workflow_type"] = WorkflowType.MOTION_ONLY.value
        result = route_after_motion(sample_state)
        assert result == "finalize"


# =============================================================================
# NODE TESTS
# =============================================================================

class TestResearchNode:
    """Tests for research node."""
    
    @pytest.mark.asyncio
    async def test_research_node_updates_state(self, sample_state):
        """Test research node updates state correctly."""
        node = ResearchNode()
        
        # Execute node
        result = await node(sample_state)
        
        assert result["status"] == JobStatus.RESEARCHING.value
        assert result["current_stage"] == "research"
        assert result["progress_percent"] > 0
        assert result["trending_hooks"] is not None
    
    @pytest.mark.asyncio
    async def test_research_node_provides_default_hooks(self, sample_state):
        """Test research provides default hooks when API unavailable."""
        node = ResearchNode()
        node.brave_api_key = None  # Disable API
        
        result = await node(sample_state)
        
        assert len(result["trending_hooks"]) > 0
        assert "Problem → Solution reveal" in result["trending_hooks"]


class TestContentNode:
    """Tests for content node."""
    
    @pytest.mark.asyncio
    async def test_content_node_updates_status(self, sample_state):
        """Test content node updates status."""
        node = ContentNode()
        
        with patch.object(node.vision_agent, 'extract_product_identity') as mock_extract:
            # Mock extraction
            mock_result = MagicMock()
            mock_result.visual_dna.to_dict.return_value = {
                "product_category": "Test",
                "motion_recommendations": [],
                "camera_angle_suggestions": []
            }
            mock_result.embedding = [0.1] * 1536
            mock_result.confidence = 0.9
            mock_extract.return_value = mock_result
            
            with patch.object(node, '_generate_script') as mock_script:
                mock_script.return_value = {
                    "script": "Test script",
                    "storyboard": [],
                    "voiceover": "Test voiceover"
                }
                
                result = await node(sample_state)
                
                assert result["status"] == JobStatus.GENERATING_CONTENT.value
                assert result["current_stage"] == "content"


class TestMotionNode:
    """Tests for motion node."""
    
    @pytest.mark.asyncio
    async def test_motion_node_creates_scaffold(self, sample_state):
        """Test motion node creates scaffold."""
        node = MotionNode()
        
        # Add required state data
        sample_state["product_identity"] = {
            "motion_recommendations": ["360 rotation"],
            "camera_suggestions": ["front view"]
        }
        sample_state["storyboard"] = [
            {"shot_number": 1, "description": "Test shot"}
        ]
        
        result = await node(sample_state)
        
        assert result["status"] == JobStatus.CREATING_MOTION.value
        assert result["current_stage"] == "motion"
        assert result["motion_scaffold"] is not None
    
    def test_create_basic_scaffold(self):
        """Test basic scaffold fallback."""
        node = MotionNode()
        scaffold = node._create_basic_scaffold(15.0)
        
        assert scaffold["fps"] == 24
        assert scaffold["duration_seconds"] == 15.0
        assert scaffold["total_frames"] == 360  # 15 * 24
        assert len(scaffold["keyframes"]) > 0


class TestRenderNode:
    """Tests for render node."""
    
    @pytest.mark.asyncio
    async def test_render_node_updates_status(self, sample_state):
        """Test render node updates status."""
        node = RenderNode()
        
        # Add required state data
        sample_state["motion_scaffold"] = {
            "fps": 24,
            "total_frames": 360
        }
        sample_state["product_identity"] = {}
        sample_state["script"] = "Test script"
        
        result = await node(sample_state)
        
        assert result["status"] == JobStatus.RENDERING.value
        assert result["render_settings"] is not None
    
    def test_build_render_settings_16_9(self, sample_state):
        """Test render settings for 16:9 aspect ratio."""
        node = RenderNode()
        sample_state["aspect_ratio"] = "16:9"
        sample_state["motion_scaffold"] = {"fps": 24}
        
        settings = node._build_render_settings(sample_state)
        
        assert settings["width"] == 1920
        assert settings["height"] == 1080
    
    def test_build_render_settings_9_16(self, sample_state):
        """Test render settings for 9:16 aspect ratio."""
        node = RenderNode()
        sample_state["aspect_ratio"] = "9:16"
        sample_state["motion_scaffold"] = {"fps": 24}
        
        settings = node._build_render_settings(sample_state)
        
        # Should be portrait oriented
        assert settings["height"] == 1080
        assert settings["width"] == 607  # 1080 * 9/16


class TestFinalizeNode:
    """Tests for finalize node."""
    
    @pytest.mark.asyncio
    async def test_finalize_success(self, sample_state):
        """Test finalize marks success correctly."""
        node = FinalizeNode()
        sample_state["errors"] = []
        
        result = await node(sample_state)
        
        assert result["status"] == JobStatus.COMPLETED.value
        assert result["progress_percent"] == 100.0
        assert result["should_continue"] is False
    
    @pytest.mark.asyncio
    async def test_finalize_with_errors(self, sample_state):
        """Test finalize marks failure correctly."""
        node = FinalizeNode()
        sample_state["errors"] = ["Test error"]
        
        result = await node(sample_state)
        
        assert result["status"] == JobStatus.FAILED.value
        assert result["progress_percent"] == 100.0


# =============================================================================
# ORCHESTRATOR TESTS
# =============================================================================

class TestNexusOrchestrator:
    """Tests for the main orchestrator class."""
    
    def test_initialization(self, orchestrator):
        """Test orchestrator initializes correctly."""
        assert orchestrator.graph is not None
        assert orchestrator.memory is not None
        assert orchestrator._active_jobs == {}
    
    def test_list_jobs_empty(self, orchestrator):
        """Test listing jobs when empty."""
        jobs = orchestrator.list_jobs()
        assert jobs == []
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job(self, orchestrator):
        """Test cancelling a job that doesn't exist."""
        result = await orchestrator.cancel_job("nonexistent")
        assert result is False
    
    def test_get_status_nonexistent(self, orchestrator):
        """Test getting status of nonexistent job."""
        status = orchestrator.get_status("nonexistent")
        assert status is None


class TestGetOrchestrator:
    """Tests for factory function."""
    
    def test_get_orchestrator_singleton(self):
        """Test factory returns singleton."""
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        
        # Should be the same instance
        assert orch1 is orch2
    
    def test_get_orchestrator_type(self):
        """Test factory returns correct type."""
        orch = get_orchestrator()
        assert isinstance(orch, NexusOrchestrator)


# =============================================================================
# INTEGRATION TESTS (with mocked nodes)
# =============================================================================

class TestOrchestratorIntegration:
    """Integration tests with mocked external calls."""
    
    @pytest.mark.asyncio
    async def test_identity_extraction_workflow(self, orchestrator):
        """Test identity extraction workflow."""
        # This would be a full integration test
        # Mocking all external calls
        pass
    
    @pytest.mark.asyncio
    async def test_content_only_workflow(self, orchestrator):
        """Test content-only workflow routes correctly."""
        # Would verify the workflow routes correctly
        pass


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
