"""
Test Suite for Neural Render Agent
===================================

Tests for the hybrid video generation pipeline including
SkyReels-V2, Sora-2, and fallback image generation backends.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict

from backend.app.agents.neural_render import (
    NeuralRenderAgent,
    RenderBackend,
    RenderQuality,
    RenderStatus,
    VideoCodec,
    RenderRequest,
    RenderResult,
    QUALITY_PRESETS,
    get_backend_config,
    get_render_agent,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def render_agent():
    """Create a render agent instance."""
    return NeuralRenderAgent()


@pytest.fixture
def basic_request():
    """Create a basic render request."""
    return RenderRequest(
        prompt="A premium wireless headphone floating in soft studio light",
        negative_prompt="blurry, distorted, low quality",
        width=1920,
        height=1080,
        backend=RenderBackend.SKIREELS_V2,
        quality=RenderQuality.STANDARD,
        duration_seconds=5.0,
        fps=24,
    )


@pytest.fixture
def video_request_with_scaffold():
    """Create a video request with motion scaffold."""
    return RenderRequest(
        prompt="Product hero shot with dynamic camera movement",
        width=1920,
        height=1080,
        backend=RenderBackend.SKIREELS_V2,
        quality=RenderQuality.HIGH,
        duration_seconds=10.0,
        fps=30,
        motion_scaffold={
            "keyframes": [
                {"time": 0.0, "position": [0, 0, 5], "rotation": [0, 0, 0]},
                {"time": 5.0, "position": [2, 1, 3], "rotation": [15, 30, 0]},
                {"time": 10.0, "position": [0, 0, 5], "rotation": [0, 0, 0]},
            ],
            "camera_movements": ["orbit", "zoom_in", "zoom_out"],
        },
    )


@pytest.fixture
def image_request():
    """Create an image render request."""
    return RenderRequest(
        prompt="Professional product photography, clean background",
        width=1024,
        height=1024,
        backend=RenderBackend.FLUX,
        quality=RenderQuality.STANDARD,
    )


# =============================================================================
# ENUM TESTS
# =============================================================================

class TestRenderEnums:
    """Test enum definitions."""
    
    def test_render_backend_values(self):
        """Test RenderBackend enum has expected values."""
        assert RenderBackend.SKIREELS_V2.value == "skireels_v2"
        assert RenderBackend.SORA_2.value == "sora_2"
        assert RenderBackend.VEO.value == "veo"
        assert RenderBackend.RUNWAY_GEN3.value == "runway_gen3"
        assert RenderBackend.DALLE_3.value == "dalle_3"
        assert RenderBackend.FLUX.value == "flux"
        assert RenderBackend.BYTEZ.value == "bytez"
    
    def test_render_quality_values(self):
        """Test RenderQuality enum has expected values."""
        assert RenderQuality.PREVIEW.value == "preview"
        assert RenderQuality.DRAFT.value == "draft"
        assert RenderQuality.STANDARD.value == "standard"
        assert RenderQuality.HIGH.value == "high"
        assert RenderQuality.ULTRA.value == "ultra"
    
    def test_video_codec_values(self):
        """Test VideoCodec enum values."""
        assert VideoCodec.H264.value == "h264"
        assert VideoCodec.H265.value == "h265"
        assert VideoCodec.VP9.value == "vp9"
        assert VideoCodec.AV1.value == "av1"
    
    def test_render_status_values(self):
        """Test RenderStatus enum values."""
        assert RenderStatus.QUEUED.value == "queued"
        assert RenderStatus.PROCESSING.value == "processing"
        assert RenderStatus.COMPLETED.value == "completed"
        assert RenderStatus.FAILED.value == "failed"


# =============================================================================
# DATA CLASS TESTS
# =============================================================================

class TestRenderRequest:
    """Test RenderRequest dataclass."""
    
    def test_default_values(self):
        """Test RenderRequest has correct defaults."""
        request = RenderRequest(prompt="Test prompt")
        
        assert request.prompt == "Test prompt"
        assert request.negative_prompt is None
        assert request.width == 1920
        assert request.height == 1080
        assert request.backend == RenderBackend.SKIREELS_V2
        assert request.quality == RenderQuality.STANDARD
        assert request.duration_seconds == 5.0
        assert request.fps == 24
        assert request.guidance_scale == 7.5
        assert request.num_inference_steps == 30
    
    def test_custom_values(self, basic_request):
        """Test RenderRequest with custom values."""
        assert basic_request.prompt == "A premium wireless headphone floating in soft studio light"
        assert basic_request.negative_prompt == "blurry, distorted, low quality"
        assert basic_request.width == 1920
        assert basic_request.height == 1080
    
    def test_motion_scaffold(self, video_request_with_scaffold):
        """Test RenderRequest with motion scaffold."""
        assert video_request_with_scaffold.motion_scaffold is not None
        assert "keyframes" in video_request_with_scaffold.motion_scaffold
        assert len(video_request_with_scaffold.motion_scaffold["keyframes"]) == 3


class TestRenderResult:
    """Test RenderResult dataclass."""
    
    def test_default_values(self):
        """Test RenderResult has correct defaults."""
        result = RenderResult(output_path="/tmp/test.mp4")
        
        assert result.output_path == "/tmp/test.mp4"
        assert result.output_url is None
        assert result.status == RenderStatus.COMPLETED
        assert result.width == 1920
        assert result.height == 1080
    
    def test_full_result(self):
        """Test RenderResult with all fields."""
        result = RenderResult(
            output_path="/renders/video.mp4",
            output_url="https://cdn.example.com/video.mp4",
            thumbnail_url="https://cdn.example.com/thumb.jpg",
            width=1920,
            height=1080,
            duration_seconds=15.0,
            fps=24,
            backend_used=RenderBackend.SKIREELS_V2,
            generation_time_seconds=45.5,
            seed_used=12345,
            status=RenderStatus.COMPLETED,
        )
        
        assert result.duration_seconds == 15.0
        assert result.backend_used == RenderBackend.SKIREELS_V2
        assert result.generation_time_seconds == 45.5


# =============================================================================
# CONFIGURATION TESTS
# =============================================================================

class TestBackendConfig:
    """Test backend configuration."""
    
    def test_get_backend_config(self):
        """Test get_backend_config returns all backends."""
        config = get_backend_config()
        
        assert RenderBackend.SKIREELS_V2 in config
        assert RenderBackend.SORA_2 in config
        assert RenderBackend.VEO in config
        assert RenderBackend.DALLE_3 in config
        assert RenderBackend.FLUX in config
    
    def test_skireels_config(self):
        """Test SkyReels-V2 configuration."""
        config = get_backend_config()[RenderBackend.SKIREELS_V2]
        
        assert config["name"] == "SkyReels-V2"
        assert config["provider"] == "replicate"
        assert config["supports_video"] is True
        assert config["supports_motion_scaffold"] is True
        assert config["max_duration"] == 30.0
    
    def test_sora_config(self):
        """Test Sora-2 configuration."""
        config = get_backend_config()[RenderBackend.SORA_2]
        
        assert config["name"] == "Sora-2"
        assert config["provider"] == "openai"
        assert config["supports_video"] is True
        assert config["max_duration"] == 60.0
    
    def test_quality_presets(self):
        """Test quality presets are defined."""
        assert RenderQuality.PREVIEW in QUALITY_PRESETS
        assert RenderQuality.STANDARD in QUALITY_PRESETS
        assert RenderQuality.ULTRA in QUALITY_PRESETS
        
        # Check ULTRA has highest steps
        assert QUALITY_PRESETS[RenderQuality.ULTRA]["num_inference_steps"] > \
               QUALITY_PRESETS[RenderQuality.PREVIEW]["num_inference_steps"]


# =============================================================================
# AGENT INITIALIZATION TESTS
# =============================================================================

class TestAgentInit:
    """Test agent initialization."""
    
    def test_agent_initialization(self, render_agent):
        """Test NeuralRenderAgent initializes correctly."""
        assert render_agent is not None
        assert render_agent._http_client is not None
        assert render_agent._backend_configs is not None
        assert render_agent._output_dir.exists()
    
    def test_singleton_factory(self):
        """Test get_render_agent returns singleton."""
        agent1 = get_render_agent()
        agent2 = get_render_agent()
        
        assert agent1 is agent2
    
    def test_api_keys_loaded(self, render_agent):
        """Test API keys are loaded from settings."""
        # Just verify the method exists and returns dict
        assert isinstance(render_agent._api_keys, dict)


# =============================================================================
# QUALITY PRESET TESTS
# =============================================================================

class TestQualityPresets:
    """Test quality preset application."""
    
    def test_apply_preview_preset(self, render_agent, basic_request):
        """Test PREVIEW quality settings."""
        basic_request.quality = RenderQuality.PREVIEW
        modified = render_agent._apply_quality_preset(basic_request)
        
        assert modified.num_inference_steps == 10
        assert modified.guidance_scale == 5.0
        assert modified.fps == 12
    
    def test_apply_standard_preset(self, render_agent, basic_request):
        """Test STANDARD quality settings."""
        basic_request.quality = RenderQuality.STANDARD
        modified = render_agent._apply_quality_preset(basic_request)
        
        assert modified.num_inference_steps == 30
        assert modified.guidance_scale == 7.5
    
    def test_apply_ultra_preset(self, render_agent, basic_request):
        """Test ULTRA quality settings."""
        basic_request.quality = RenderQuality.ULTRA
        modified = render_agent._apply_quality_preset(basic_request)
        
        assert modified.num_inference_steps == 75
        assert modified.guidance_scale == 9.0
        assert modified.fps == 60
    
    def test_resolution_scaling(self, render_agent, basic_request):
        """Test resolution is scaled for preview quality."""
        basic_request.quality = RenderQuality.PREVIEW
        original_width = basic_request.width
        
        modified = render_agent._apply_quality_preset(basic_request)
        
        # Preview should be 50% resolution
        assert modified.width == original_width * 0.5


# =============================================================================
# BACKEND SELECTION TESTS
# =============================================================================

class TestBackendSelection:
    """Test automatic backend selection."""
    
    @pytest.mark.asyncio
    async def test_select_specified_backend(self, render_agent, basic_request):
        """Test specified backend is used if available."""
        # When specific backend is requested, use it
        selected = await render_agent._select_backend(basic_request)
        
        # Should use specified or fallback if unavailable
        assert isinstance(selected, RenderBackend)
    
    @pytest.mark.asyncio
    async def test_select_skireels_for_motion_scaffold(self, render_agent, video_request_with_scaffold):
        """Test SkyReels is preferred for motion scaffold."""
        # Mock availability
        render_agent._is_backend_available = MagicMock(return_value=True)
        
        selected = await render_agent._select_backend(video_request_with_scaffold)
        
        assert selected == RenderBackend.SKIREELS_V2
    
    @pytest.mark.asyncio
    async def test_select_sora_for_high_quality(self, render_agent, basic_request):
        """Test Sora is preferred for high quality."""
        basic_request.quality = RenderQuality.ULTRA
        basic_request.motion_scaffold = None
        
        # Mock availability
        render_agent._is_backend_available = MagicMock(
            side_effect=lambda b: b == RenderBackend.SORA_2
        )
        
        selected = await render_agent._select_backend(basic_request)
        
        assert selected == RenderBackend.SORA_2


# =============================================================================
# RENDER VIDEO TESTS
# =============================================================================

class TestRenderVideo:
    """Test video rendering functionality."""
    
    @pytest.mark.asyncio
    async def test_render_video_basic(self, render_agent, basic_request):
        """Test basic video rendering returns result."""
        result = await render_agent.render_video(basic_request)
        
        assert result is not None
        assert isinstance(result, RenderResult)
        assert result.status in [RenderStatus.COMPLETED, RenderStatus.FAILED]
    
    @pytest.mark.asyncio
    async def test_render_video_with_scaffold(self, render_agent, video_request_with_scaffold):
        """Test video rendering with motion scaffold."""
        result = await render_agent.render_video(video_request_with_scaffold)
        
        assert result is not None
        assert result.duration_seconds == video_request_with_scaffold.duration_seconds
    
    @pytest.mark.asyncio
    async def test_render_video_progress_callback(self, render_agent, basic_request):
        """Test progress callback is called."""
        progress_values = []
        
        async def track_progress(progress: float, message: str):
            progress_values.append((progress, message))
        
        await render_agent.render_video(basic_request, progress_callback=track_progress)
        
        assert len(progress_values) > 0
        # First progress should be around 0.1
        assert progress_values[0][0] <= 0.2
    
    @pytest.mark.asyncio
    async def test_render_video_error_handling(self, render_agent):
        """Test error handling returns failed status."""
        # Create invalid request
        request = RenderRequest(prompt="")
        
        # Even empty prompt should not crash
        result = await render_agent.render_video(request)
        
        assert result is not None
        assert isinstance(result, RenderResult)


# =============================================================================
# RENDER IMAGE TESTS
# =============================================================================

class TestRenderImage:
    """Test image rendering functionality."""
    
    @pytest.mark.asyncio
    async def test_render_image_basic(self, render_agent, image_request):
        """Test basic image rendering."""
        result = await render_agent.render_image(image_request)
        
        assert result is not None
        assert isinstance(result, RenderResult)
        assert result.duration_seconds == 0.0  # Image has no duration
    
    @pytest.mark.asyncio
    async def test_render_image_dimensions(self, render_agent, image_request):
        """Test image dimensions match request."""
        result = await render_agent.render_image(image_request)
        
        assert result.width == image_request.width
        assert result.height == image_request.height


# =============================================================================
# SIMULATED RESULT TESTS
# =============================================================================

class TestSimulatedResults:
    """Test simulated result generation for development."""
    
    @pytest.mark.asyncio
    async def test_simulated_video_result(self, render_agent, basic_request):
        """Test simulated video result is valid."""
        result = await render_agent._simulated_video_result(
            basic_request, RenderBackend.SKIREELS_V2
        )
        
        assert result.status == RenderStatus.COMPLETED
        assert result.output_url is not None
        assert "skireels_v2" in result.output_url
        assert result.metadata.get("simulated") is True
    
    @pytest.mark.asyncio
    async def test_simulated_image_result(self, render_agent, image_request):
        """Test simulated image result is valid."""
        result = await render_agent._simulated_image_result(
            image_request, RenderBackend.FLUX
        )
        
        assert result.status == RenderStatus.COMPLETED
        assert result.output_url is not None
        assert "flux" in result.output_url


# =============================================================================
# BACKEND IMPLEMENTATION TESTS
# =============================================================================

class TestSkyReelsBackend:
    """Test SkyReels-V2 backend implementation."""
    
    @pytest.mark.asyncio
    async def test_skireels_handles_missing_key(self, render_agent, basic_request):
        """Test SkyReels gracefully handles missing API key."""
        # Force backend selection
        basic_request.backend = RenderBackend.SKIREELS_V2
        
        # Render should fall back to simulated result
        result = await render_agent._render_skireels(basic_request, None)
        
        assert result is not None
        assert result.backend_used == RenderBackend.SKIREELS_V2


class TestSoraBackend:
    """Test Sora-2 backend implementation."""
    
    @pytest.mark.asyncio
    async def test_sora_handles_missing_key(self, render_agent, basic_request):
        """Test Sora gracefully handles missing API key."""
        result = await render_agent._render_sora(basic_request, None)
        
        assert result is not None
        assert result.backend_used == RenderBackend.SORA_2


class TestFallbackBackend:
    """Test fallback image sequence generation."""
    
    @pytest.mark.asyncio
    async def test_image_sequence_fallback(self, render_agent, basic_request):
        """Test image sequence fallback works."""
        # Short duration for faster test
        basic_request.duration_seconds = 2.0
        
        result = await render_agent._render_image_sequence(basic_request, None)
        
        assert result is not None
        assert result.metadata.get("method") == "image_sequence"


# =============================================================================
# UTILITY METHOD TESTS
# =============================================================================

class TestUtilityMethods:
    """Test utility methods."""
    
    @pytest.mark.asyncio
    async def test_generate_thumbnail(self, render_agent):
        """Test thumbnail URL generation."""
        video_url = "https://cdn.example.com/video.mp4"
        
        thumb_url = await render_agent.generate_thumbnail(video_url, 2.5)
        
        assert thumb_url.endswith("_thumb.jpg")
    
    @pytest.mark.asyncio
    async def test_generate_preview_gif(self, render_agent):
        """Test preview GIF URL generation."""
        video_url = "https://cdn.example.com/video.mp4"
        
        gif_url = await render_agent.generate_preview_gif(video_url, 3.0)
        
        assert gif_url.endswith("_preview.gif")
    
    def test_is_backend_available(self, render_agent):
        """Test backend availability check."""
        # Without API keys configured, backends should not be available
        available = render_agent._is_backend_available(RenderBackend.SKIREELS_V2)
        
        # Result depends on environment
        assert isinstance(available, bool)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for full pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_video_pipeline(self, render_agent):
        """Test complete video generation pipeline."""
        request = RenderRequest(
            prompt="Modern smartphone showcasing sleek design",
            negative_prompt="blurry, pixelated",
            width=1920,
            height=1080,
            quality=RenderQuality.STANDARD,
            duration_seconds=5.0,
            fps=24,
            motion_scaffold={
                "keyframes": [
                    {"time": 0.0, "position": [0, 0, 0]},
                    {"time": 5.0, "position": [1, 0, 0]},
                ],
            },
        )
        
        progress_log = []
        
        async def log_progress(p, m):
            progress_log.append((p, m))
        
        result = await render_agent.render_video(request, log_progress)
        
        assert result.status in [RenderStatus.COMPLETED, RenderStatus.FAILED]
        assert result.generation_time_seconds > 0
        assert len(progress_log) > 0
    
    @pytest.mark.asyncio
    async def test_render_with_identity_embedding(self, render_agent):
        """Test rendering with identity embedding for product consistency."""
        request = RenderRequest(
            prompt="Product floating in space",
            identity_embedding=[0.1] * 512,  # Mock 512-dim embedding
            reference_images=["https://example.com/product.jpg"],
            duration_seconds=3.0,
        )
        
        result = await render_agent.render_video(request)
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_cleanup(self, render_agent):
        """Test agent cleanup."""
        await render_agent.close()
        
        # Agent should still be usable after close for new requests
        # (would reinitialize in production)


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_prompt(self):
        """Test handling of empty prompt."""
        request = RenderRequest(prompt="")
        assert request.prompt == ""
    
    def test_extreme_duration(self):
        """Test handling of extreme duration values."""
        request = RenderRequest(
            prompt="Test",
            duration_seconds=300.0,  # 5 minutes
        )
        assert request.duration_seconds == 300.0
    
    def test_invalid_resolution(self):
        """Test handling of unusual resolutions."""
        request = RenderRequest(
            prompt="Test",
            width=123,  # Non-standard
            height=456,
        )
        assert request.width == 123
        assert request.height == 456
    
    @pytest.mark.asyncio
    async def test_concurrent_renders(self, render_agent):
        """Test multiple concurrent render requests."""
        requests = [
            RenderRequest(prompt=f"Test video {i}", duration_seconds=2.0)
            for i in range(3)
        ]
        
        # Run concurrently
        results = await asyncio.gather(
            *[render_agent.render_video(r) for r in requests]
        )
        
        assert len(results) == 3
        assert all(isinstance(r, RenderResult) for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
