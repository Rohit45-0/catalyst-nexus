"""
Tests for Vision DNA Agent
==========================

Unit tests for the identity extraction logic.
All external API calls are mocked to avoid consuming credits.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
import json

from backend.app.agents.vision_dna import (
    VisionDNAAgent,
    VisualDNA,
    MaterialProperties,
    LightingConditions,
    StructuralAnalysis,
    ExtractionResult,
    get_vision_dna_agent
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def vision_agent():
    """Create a VisionDNAAgent instance for testing."""
    return VisionDNAAgent()


@pytest.fixture
def mock_gpt4o_response():
    """Mock GPT-4o Vision API response."""
    return {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "product_category": "Electronics - Headphones",
                    "product_description": "Premium over-ear wireless headphones with noise cancellation.",
                    "materials": {
                        "primary_material": "aluminum",
                        "secondary_materials": ["leather", "memory foam", "plastic"],
                        "surface_finish": "brushed",
                        "transparency": "opaque",
                        "reflectivity": 0.7,
                        "texture_description": "Smooth brushed aluminum with soft leather accents",
                        "color_palette": ["#2C2C2C", "#C0C0C0", "#8B4513"]
                    },
                    "lighting": {
                        "primary_light_direction": "top-left",
                        "light_type": "studio",
                        "light_intensity": "soft",
                        "shadow_characteristics": "Soft diffused shadows",
                        "highlights": ["ear cup edges", "headband curve"],
                        "color_temperature": "neutral"
                    },
                    "structure": {
                        "overall_shape": "Curved arc with circular ear cups",
                        "dimensions_ratio": "wide and tall",
                        "key_components": ["headband", "ear cups", "cushions", "adjustment sliders"],
                        "symmetry": "symmetric",
                        "distinctive_features": ["touch controls on ear cup", "folding hinge"],
                        "brand_elements": ["logo on ear cup"]
                    },
                    "motion_recommendations": [
                        "Slow 360 rotation showcasing build quality",
                        "Zoom to touch control area",
                        "Folding motion demonstration"
                    ],
                    "camera_angle_suggestions": [
                        "Hero shot at 45 degrees",
                        "Side profile showing curves",
                        "Top-down flat lay"
                    ],
                    "confidence_score": 0.92
                })
            }
        }]
    }


@pytest.fixture
def mock_embedding_response():
    """Mock OpenAI Embeddings API response."""
    return {
        "data": [{
            "embedding": [0.1] * 1536  # 1536-dimensional embedding
        }]
    }


@pytest.fixture
def sample_visual_dna():
    """Create sample VisualDNA for testing."""
    return VisualDNA(
        product_category="Electronics",
        product_description="Test product",
        materials=MaterialProperties(
            primary_material="plastic",
            color_palette=["#FFFFFF", "#000000"]
        ),
        lighting=LightingConditions(
            light_type="studio",
            color_temperature="neutral"
        ),
        structure=StructuralAnalysis(
            overall_shape="rectangular",
            symmetry="symmetric"
        ),
        confidence_score=0.9
    )


# =============================================================================
# UNIT TESTS - Data Classes
# =============================================================================

class TestMaterialProperties:
    """Tests for MaterialProperties dataclass."""
    
    def test_default_values(self):
        """Test default values are set correctly."""
        materials = MaterialProperties()
        assert materials.primary_material == ""
        assert materials.secondary_materials == []
        assert materials.reflectivity == 0.0
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        materials = MaterialProperties(
            primary_material="aluminum",
            surface_finish="matte",
            reflectivity=0.5
        )
        result = materials.to_dict()
        
        assert result["primary_material"] == "aluminum"
        assert result["surface_finish"] == "matte"
        assert result["reflectivity"] == 0.5


class TestLightingConditions:
    """Tests for LightingConditions dataclass."""
    
    def test_default_values(self):
        """Test default values are set correctly."""
        lighting = LightingConditions()
        assert lighting.light_type == ""
        assert lighting.highlights == []
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        lighting = LightingConditions(
            light_type="studio",
            color_temperature="warm"
        )
        result = lighting.to_dict()
        
        assert result["light_type"] == "studio"
        assert result["color_temperature"] == "warm"


class TestStructuralAnalysis:
    """Tests for StructuralAnalysis dataclass."""
    
    def test_default_values(self):
        """Test default values are set correctly."""
        structure = StructuralAnalysis()
        assert structure.key_components == []
        assert structure.brand_elements == []
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        structure = StructuralAnalysis(
            overall_shape="cylindrical",
            symmetry="radial",
            distinctive_features=["handle", "spout"]
        )
        result = structure.to_dict()
        
        assert result["overall_shape"] == "cylindrical"
        assert result["symmetry"] == "radial"
        assert "handle" in result["distinctive_features"]


class TestVisualDNA:
    """Tests for VisualDNA dataclass."""
    
    def test_to_dict(self, sample_visual_dna):
        """Test full VisualDNA conversion to dictionary."""
        result = sample_visual_dna.to_dict()
        
        assert result["product_category"] == "Electronics"
        assert "materials" in result
        assert "lighting" in result
        assert "structure" in result
        assert result["confidence_score"] == 0.9
    
    def test_to_embedding_text(self, sample_visual_dna):
        """Test conversion to embedding text."""
        text = sample_visual_dna.to_embedding_text()
        
        assert "Electronics" in text
        assert "plastic" in text
        assert "studio" in text
        assert "rectangular" in text


# =============================================================================
# UNIT TESTS - VisionDNAAgent
# =============================================================================

class TestVisionDNAAgent:
    """Tests for VisionDNAAgent class."""
    
    def test_initialization(self, vision_agent):
        """Test agent initializes correctly."""
        assert vision_agent.azure_endpoint is not None
        assert vision_agent.api_key is not None
        assert vision_agent.deployment_name is not None
    
    def test_extract_json_from_response_with_code_block(self, vision_agent):
        """Test JSON extraction from markdown code blocks."""
        response = '```json\n{"key": "value"}\n```'
        result = vision_agent._extract_json_from_response(response)
        
        parsed = json.loads(result)
        assert parsed["key"] == "value"
    
    def test_extract_json_from_response_plain(self, vision_agent):
        """Test JSON extraction from plain text."""
        response = '{"key": "value"}'
        result = vision_agent._extract_json_from_response(response)
        
        parsed = json.loads(result)
        assert parsed["key"] == "value"
    
    def test_parse_analysis_to_visual_dna(self, vision_agent):
        """Test parsing analysis JSON to VisualDNA."""
        analysis = {
            "product_category": "Footwear",
            "product_description": "Running shoes",
            "materials": {
                "primary_material": "mesh",
                "color_palette": ["#FF0000"]
            },
            "lighting": {
                "light_type": "natural"
            },
            "structure": {
                "overall_shape": "curved"
            },
            "confidence_score": 0.85
        }
        
        result = vision_agent._parse_analysis_to_visual_dna(analysis)
        
        assert isinstance(result, VisualDNA)
        assert result.product_category == "Footwear"
        assert result.materials.primary_material == "mesh"
        assert result.confidence_score == 0.85
    
    def test_generate_fallback_embedding(self, vision_agent):
        """Test fallback embedding generation."""
        text = "Test product description"
        embedding = vision_agent._generate_fallback_embedding(text)
        
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)
        
        # Test determinism - same input should give same output
        embedding2 = vision_agent._generate_fallback_embedding(text)
        assert embedding == embedding2
    
    @pytest.mark.asyncio
    async def test_compare_identities(self, vision_agent):
        """Test embedding comparison."""
        # Identical embeddings should have similarity ~1.0
        embedding = [0.1] * 1536
        similarity = await vision_agent.compare_identities(embedding, embedding)
        
        assert 0.99 <= similarity <= 1.0
    
    @pytest.mark.asyncio
    async def test_compare_orthogonal_identities(self, vision_agent):
        """Test comparison of orthogonal embeddings."""
        import numpy as np
        
        # Create orthogonal embeddings
        embedding_a = [1.0] + [0.0] * 1535
        embedding_b = [0.0] + [1.0] + [0.0] * 1534
        
        similarity = await vision_agent.compare_identities(embedding_a, embedding_b)
        
        # Orthogonal vectors have cosine similarity of 0, normalized to 0.5
        assert 0.4 <= similarity <= 0.6
    
    @pytest.mark.asyncio
    async def test_merge_identities(self, vision_agent):
        """Test embedding merging."""
        embeddings = [
            [1.0] * 1536,
            [0.5] * 1536,
        ]
        
        merged = await vision_agent.merge_identities(embeddings)
        
        assert len(merged) == 1536
        # Merged should be normalized (unit length)
        import numpy as np
        norm = np.linalg.norm(merged)
        assert 0.99 <= norm <= 1.01
    
    @pytest.mark.asyncio
    async def test_merge_identities_with_weights(self, vision_agent):
        """Test weighted embedding merging."""
        embeddings = [
            [1.0] * 1536,
            [0.0] * 1536,
        ]
        weights = [0.8, 0.2]
        
        merged = await vision_agent.merge_identities(embeddings, weights)
        
        assert len(merged) == 1536
    
    @pytest.mark.asyncio
    async def test_merge_empty_raises_error(self, vision_agent):
        """Test that merging empty list raises ValueError."""
        with pytest.raises(ValueError, match="No embeddings provided"):
            await vision_agent.merge_identities([])
    
    @pytest.mark.asyncio
    async def test_find_similar_products(self, vision_agent):
        """Test similarity search."""
        query = [0.5] * 1536
        stored = [
            ("id1", [0.5] * 1536),  # Should match
            ("id2", [0.1] * 1536),  # Should match but lower
            ("id3", [-0.5] * 1536), # Should not match
        ]
        
        results = await vision_agent.find_similar_products(
            query_embedding=query,
            stored_embeddings=stored,
            top_k=5,
            threshold=0.5
        )
        
        # Should return at least id1 and id2
        assert len(results) >= 1
        assert results[0][0] == "id1"  # Highest similarity first


# =============================================================================
# INTEGRATION TESTS (with mocked APIs)
# =============================================================================

class TestVisionDNAAgentIntegration:
    """Integration tests with mocked external APIs."""
    
    @pytest.mark.asyncio
    async def test_extract_product_identity_full_flow(
        self,
        vision_agent,
        mock_gpt4o_response,
        mock_embedding_response
    ):
        """Test full identity extraction flow with mocked APIs."""
        
        with patch('httpx.AsyncClient.post') as mock_post:
            # Setup mock responses
            mock_response = AsyncMock()
            mock_response.json.side_effect = [
                mock_gpt4o_response,  # First call: GPT-4o Vision
                mock_embedding_response  # Second call: Embeddings
            ]
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            # Create a simpler mock that returns directly
            async def mock_post_fn(*args, **kwargs):
                mock_resp = MagicMock()
                mock_resp.raise_for_status = MagicMock()
                
                # Determine which API is being called based on URL
                url = args[0] if args else kwargs.get('url', '')
                if 'chat/completions' in url:
                    mock_resp.json.return_value = mock_gpt4o_response
                else:
                    mock_resp.json.return_value = mock_embedding_response
                
                return mock_resp
            
            with patch.object(vision_agent, '_analyze_with_gpt4o_vision') as mock_analyze:
                with patch.object(vision_agent, '_generate_embedding') as mock_embed:
                    # Setup return values
                    mock_analyze.return_value = (
                        VisualDNA(
                            product_category="Electronics - Headphones",
                            product_description="Premium headphones",
                            confidence_score=0.92
                        ),
                        "raw analysis text"
                    )
                    mock_embed.return_value = [0.1] * 1536
                    
                    # Execute
                    result = await vision_agent.extract_product_identity(
                        image_sources=["https://example.com/headphones.jpg"],
                        product_name="Premium Headphones"
                    )
                    
                    # Verify
                    assert isinstance(result, ExtractionResult)
                    assert result.visual_dna.product_category == "Electronics - Headphones"
                    assert len(result.embedding) == 1536
                    assert result.confidence == 0.92
    
    @pytest.mark.asyncio
    async def test_encode_image_to_base64(self, vision_agent, tmp_path):
        """Test image encoding to base64."""
        # Create a test image file
        test_image = tmp_path / "test.jpg"
        test_image.write_bytes(b'\xff\xd8\xff\xe0')  # JPEG magic bytes
        
        result = await vision_agent._encode_image_to_base64(str(test_image))
        
        assert result.startswith("data:image/jpeg;base64,")


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================

class TestFactoryFunction:
    """Tests for the factory function."""
    
    def test_get_vision_dna_agent(self):
        """Test factory function returns valid agent."""
        agent = get_vision_dna_agent()
        
        assert isinstance(agent, VisionDNAAgent)
        assert agent.azure_endpoint is not None


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
