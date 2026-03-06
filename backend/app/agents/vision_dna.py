"""
Vision DNA Agent - The Identity Extraction Engine
==================================================

The core "Geometric Lock" extraction agent that analyzes product images to create
persistent identity embeddings for zero-shot video generation consistency.

Pipeline:
1. GPT-4o-Vision → Extracts material properties, lighting, structural JSON
2. OpenAI Embeddings → Converts JSON to 1536-dim vector (the "Geometric Lock")
3. Store in pgvector → Enables similarity search across product versions

Author: Catalyst Nexus Team
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import base64
import json
import httpx
import asyncio
import logging
from pathlib import Path

import numpy as np

from backend.app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class MaterialProperties:
    """Extracted material/surface properties of a product."""
    primary_material: str = ""
    secondary_materials: List[str] = field(default_factory=list)
    surface_finish: str = ""  # matte, glossy, metallic, textured
    transparency: str = ""    # opaque, translucent, transparent
    reflectivity: float = 0.0  # 0.0 to 1.0
    texture_description: str = ""
    color_palette: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_material": self.primary_material,
            "secondary_materials": self.secondary_materials,
            "surface_finish": self.surface_finish,
            "transparency": self.transparency,
            "reflectivity": self.reflectivity,
            "texture_description": self.texture_description,
            "color_palette": self.color_palette,
        }


@dataclass
class LightingConditions:
    """Extracted lighting conditions from the product image."""
    primary_light_direction: str = ""  # top, bottom, left, right, front, back
    light_type: str = ""               # natural, studio, ambient, dramatic
    light_intensity: str = ""          # soft, medium, hard
    shadow_characteristics: str = ""
    highlights: List[str] = field(default_factory=list)
    color_temperature: str = ""        # warm, neutral, cool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_light_direction": self.primary_light_direction,
            "light_type": self.light_type,
            "light_intensity": self.light_intensity,
            "shadow_characteristics": self.shadow_characteristics,
            "highlights": self.highlights,
            "color_temperature": self.color_temperature,
        }


@dataclass
class StructuralAnalysis:
    """Extracted structural/geometric properties of the product."""
    overall_shape: str = ""
    dimensions_ratio: str = ""  # e.g., "tall and narrow", "compact square"
    key_components: List[str] = field(default_factory=list)
    symmetry: str = ""          # symmetric, asymmetric, radial
    distinctive_features: List[str] = field(default_factory=list)
    brand_elements: List[str] = field(default_factory=list)  # logos, text, icons
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_shape": self.overall_shape,
            "dimensions_ratio": self.dimensions_ratio,
            "key_components": self.key_components,
            "symmetry": self.symmetry,
            "distinctive_features": self.distinctive_features,
            "brand_elements": self.brand_elements,
        }


@dataclass
class VisualDNA:
    """The complete Visual DNA of a product - used for the Geometric Lock."""
    product_category: str = ""
    product_description: str = ""
    materials: MaterialProperties = field(default_factory=MaterialProperties)
    lighting: LightingConditions = field(default_factory=LightingConditions)
    structure: StructuralAnalysis = field(default_factory=StructuralAnalysis)
    motion_recommendations: List[str] = field(default_factory=list)
    camera_angle_suggestions: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_category": self.product_category,
            "product_description": self.product_description,
            "materials": self.materials.to_dict(),
            "lighting": self.lighting.to_dict(),
            "structure": self.structure.to_dict(),
            "motion_recommendations": self.motion_recommendations,
            "camera_angle_suggestions": self.camera_angle_suggestions,
            "confidence_score": self.confidence_score,
        }
    
    def to_embedding_text(self) -> str:
        """Convert Visual DNA to text for embedding generation."""
        parts = [
            f"Product: {self.product_category} - {self.product_description}",
            f"Materials: {self.materials.primary_material}, finish: {self.materials.surface_finish}",
            f"Colors: {', '.join(self.materials.color_palette)}",
            f"Lighting: {self.lighting.light_type}, {self.lighting.color_temperature}",
            f"Shape: {self.structure.overall_shape}, {self.structure.symmetry}",
            f"Features: {', '.join(self.structure.distinctive_features)}",
            f"Brand Elements: {', '.join(self.structure.brand_elements)}",
        ]
        return " | ".join(parts)


@dataclass
class ExtractionResult:
    """Complete result of identity extraction."""
    visual_dna: VisualDNA
    embedding: List[float]  # 1536-dim vector for pgvector
    raw_analysis: str       # Original GPT-4o response
    source_images: List[str]
    extraction_timestamp: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# VISION DNA AGENT
# ============================================================================

class VisionDNAAgent:
    """
    Vision DNA Agent - The "Geometric Lock" Extractor
    
    This agent processes product images through GPT-4o-Vision to extract
    a comprehensive Visual DNA profile, then generates a 1536-dimensional
    embedding vector for storage in pgvector.
    
    The embedding acts as a mathematical "fingerprint" ensuring zero-shot
    consistency when generating videos of the same product.
    
    Usage:
        agent = VisionDNAAgent()
        result = await agent.extract_product_identity(
            image_sources=["https://example.com/product.jpg"],
            product_name="Premium Headphones"
        )
        # Store result.embedding in ProductEmbedding.embedding_vector
        # Store result.visual_dna.to_dict() in ProductEmbedding.visual_dna_json
    """
    
    # GPT-4o Vision system prompt for product analysis
    VISION_ANALYSIS_PROMPT = """You are an expert product photographer and material scientist. 
Analyze the provided product image(s) and extract detailed information for AI video generation.

Your analysis MUST be returned as valid JSON with this exact structure:
{
    "product_category": "category name",
    "product_description": "detailed one-paragraph description",
    "materials": {
        "primary_material": "main material (e.g., aluminum, plastic, glass, leather)",
        "secondary_materials": ["list", "of", "other", "materials"],
        "surface_finish": "matte|glossy|metallic|brushed|textured|satin",
        "transparency": "opaque|translucent|transparent",
        "reflectivity": 0.0 to 1.0,
        "texture_description": "describe surface texture",
        "color_palette": ["#hex1", "#hex2", "or color names"]
    },
    "lighting": {
        "primary_light_direction": "top|bottom|left|right|front|back|top-left|etc",
        "light_type": "natural|studio|ambient|dramatic|product",
        "light_intensity": "soft|medium|hard",
        "shadow_characteristics": "describe shadows",
        "highlights": ["where highlights appear"],
        "color_temperature": "warm|neutral|cool"
    },
    "structure": {
        "overall_shape": "describe the shape",
        "dimensions_ratio": "tall/narrow, wide/flat, compact/cube, etc",
        "key_components": ["list main parts"],
        "symmetry": "symmetric|asymmetric|radial",
        "distinctive_features": ["unique visual elements"],
        "brand_elements": ["logos", "text", "icons visible"]
    },
    "motion_recommendations": [
        "suggested camera movements for video (e.g., slow 360 rotation, zoom to detail)"
    ],
    "camera_angle_suggestions": [
        "best angles to showcase this product"
    ],
    "confidence_score": 0.0 to 1.0
}

Be precise and technical. Focus on attributes that affect 3D rendering and motion graphics."""

    def __init__(self):
        """Initialize the Vision DNA Agent with Azure OpenAI credentials."""
        self.azure_endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        self.api_key = settings.AZURE_OPENAI_API_KEY
        self.deployment_name = settings.AZURE_DEPLOYMENT_NAME
        self.api_version = "2024-02-15-preview"
        
        # Embedding model (using text-embedding-3-large for 1536 dims)
        self.embedding_deployment = "text-embedding-3-large"
        
        logger.info(f"🧬 Vision DNA Agent initialized")
        logger.info(f"   Endpoint: {self.azure_endpoint}")
        logger.info(f"   Deployment: {self.deployment_name}")
    
    async def extract_product_identity(
        self,
        image_sources: List[str],
        product_name: str = "Unknown Product",
        additional_context: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract the complete Visual DNA and embedding from product images.
        
        Args:
            image_sources: List of image URLs or base64 strings
            product_name: Name of the product for context
            additional_context: Optional extra info about the product
            
        Returns:
            ExtractionResult with visual_dna and embedding vector
        """
        logger.info(f"🔬 Starting identity extraction for: {product_name}")
        logger.info(f"   Processing {len(image_sources)} image(s)")
        
        # Step 1: Analyze images with GPT-4o Vision
        visual_dna, raw_analysis = await self._analyze_with_gpt4o_vision(
            image_sources=image_sources,
            product_name=product_name,
            additional_context=additional_context
        )
        
        # Step 2: Generate embedding vector from Visual DNA
        embedding = await self._generate_embedding(visual_dna)
        
        # Step 3: Compile result
        result = ExtractionResult(
            visual_dna=visual_dna,
            embedding=embedding,
            raw_analysis=raw_analysis,
            source_images=image_sources,
            extraction_timestamp=datetime.utcnow().isoformat(),
            confidence=visual_dna.confidence_score,
            metadata={
                "product_name": product_name,
                "image_count": len(image_sources),
                "embedding_model": self.embedding_deployment,
                "embedding_dimensions": len(embedding),
            }
        )
        
        logger.info(f"✅ Identity extraction complete!")
        logger.info(f"   Confidence: {result.confidence:.2%}")
        logger.info(f"   Embedding dims: {len(result.embedding)}")
        
        return result
    
    async def _analyze_with_gpt4o_vision(
        self,
        image_sources: List[str],
        product_name: str,
        additional_context: Optional[str]
    ) -> tuple[VisualDNA, str]:
        """Call GPT-4o Vision API to analyze product images."""
        
        # Build the message content with images
        content = []
        
        # Add text prompt
        user_prompt = f"Analyze this product: {product_name}"
        if additional_context:
            user_prompt += f"\n\nAdditional context: {additional_context}"
        user_prompt += "\n\nProvide your analysis as the specified JSON structure."
        
        content.append({"type": "text", "text": user_prompt})
        
        # Add images
        for img_source in image_sources:
            if img_source.startswith(("http://", "https://")):
                content.append({
                    "type": "image_url",
                    "image_url": {"url": img_source, "detail": "high"}
                })
            elif img_source.startswith("data:image"):
                # Already base64 encoded
                content.append({
                    "type": "image_url",
                    "image_url": {"url": img_source, "detail": "high"}
                })
            else:
                # Assume it's a file path - encode to base64
                encoded = await self._encode_image_to_base64(img_source)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": encoded, "detail": "high"}
                })
        
        # Call Azure OpenAI
        url = f"{self.azure_endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"
        
        payload = {
            "messages": [
                {"role": "system", "content": self.VISION_ANALYSIS_PROMPT},
                {"role": "user", "content": content}
            ],
            "max_tokens": 4096,
            "temperature": 0.1,  # Low temperature for consistent analysis
        }
        
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
        
        # Extract the response
        raw_content = result["choices"][0]["message"]["content"]
        
        # Parse JSON from response (handle markdown code blocks)
        json_str = self._extract_json_from_response(raw_content)
        analysis_data = json.loads(json_str)
        
        # Convert to VisualDNA dataclass
        visual_dna = self._parse_analysis_to_visual_dna(analysis_data)
        
        return visual_dna, raw_content
    
    async def _generate_embedding(self, visual_dna: VisualDNA) -> List[float]:
        """Generate 1536-dim embedding from Visual DNA text representation."""
        
        # Convert Visual DNA to text for embedding
        text_for_embedding = visual_dna.to_embedding_text()
        
        logger.info(f"📊 Generating embedding for: {text_for_embedding[:100]}...")
        
        # Call Azure OpenAI Embeddings API
        if "azure" in self.azure_endpoint.lower():
            url = f"{self.azure_endpoint}/openai/deployments/{self.embedding_deployment}/embeddings?api-version={self.api_version}"
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key,
            }
            # Azure payload
            payload = {
                "input": text_for_embedding,
                "encoding_format": "float"
            }
        else:
            url = "https://api.openai.com/v1/embeddings"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            }
            # Switch payload to standard format
            payload = {
                "input": text_for_embedding,
                "model": "text-embedding-3-small", 
                "encoding_format": "float"
            }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            embedding = result["data"][0]["embedding"]
            logger.info(f"   ✓ Generated {len(embedding)}-dim embedding")
            return embedding
            
        except httpx.HTTPStatusError as e:
            logger.warning(f"Embedding API error: {e}. Using fallback method.")
            # Fallback: Generate deterministic pseudo-embedding from text hash
            return self._generate_fallback_embedding(text_for_embedding)
    
    def _generate_fallback_embedding(self, text: str) -> List[float]:
        """Generate a deterministic pseudo-embedding when API is unavailable."""
        import hashlib
        
        # Create a deterministic seed from the text
        hash_bytes = hashlib.sha512(text.encode()).digest()
        seed = int.from_bytes(hash_bytes[:4], 'big')
        
        # Generate reproducible random embedding
        rng = np.random.RandomState(seed)
        embedding = rng.randn(1536).astype(np.float32)
        
        # Normalize to unit length
        embedding = embedding / np.linalg.norm(embedding)
        
        return embedding.tolist()
    
    async def _encode_image_to_base64(self, file_path: str) -> str:
        """Encode a local image file to base64 data URL."""
        path = Path(file_path)
        
        # Determine MIME type
        suffix = path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_types.get(suffix, "image/jpeg")
        
        # Read and encode
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        
        return f"data:{mime_type};base64,{encoded}"
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from GPT response, handling markdown code blocks."""
        # Try to find JSON in code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            return response[start:end].strip()
        else:
            # Assume the whole response is JSON
            return response.strip()
    
    def _parse_analysis_to_visual_dna(self, data: Dict[str, Any]) -> VisualDNA:
        """Convert parsed JSON analysis to VisualDNA dataclass."""
        
        materials_data = data.get("materials", {})
        materials = MaterialProperties(
            primary_material=materials_data.get("primary_material", ""),
            secondary_materials=materials_data.get("secondary_materials", []),
            surface_finish=materials_data.get("surface_finish", ""),
            transparency=materials_data.get("transparency", "opaque"),
            reflectivity=float(materials_data.get("reflectivity", 0.0)),
            texture_description=materials_data.get("texture_description", ""),
            color_palette=materials_data.get("color_palette", []),
        )
        
        lighting_data = data.get("lighting", {})
        lighting = LightingConditions(
            primary_light_direction=lighting_data.get("primary_light_direction", ""),
            light_type=lighting_data.get("light_type", ""),
            light_intensity=lighting_data.get("light_intensity", ""),
            shadow_characteristics=lighting_data.get("shadow_characteristics", ""),
            highlights=lighting_data.get("highlights", []),
            color_temperature=lighting_data.get("color_temperature", ""),
        )
        
        structure_data = data.get("structure", {})
        structure = StructuralAnalysis(
            overall_shape=structure_data.get("overall_shape", ""),
            dimensions_ratio=structure_data.get("dimensions_ratio", ""),
            key_components=structure_data.get("key_components", []),
            symmetry=structure_data.get("symmetry", ""),
            distinctive_features=structure_data.get("distinctive_features", []),
            brand_elements=structure_data.get("brand_elements", []),
        )
        
        return VisualDNA(
            product_category=data.get("product_category", ""),
            product_description=data.get("product_description", ""),
            materials=materials,
            lighting=lighting,
            structure=structure,
            motion_recommendations=data.get("motion_recommendations", []),
            camera_angle_suggestions=data.get("camera_angle_suggestions", []),
            confidence_score=float(data.get("confidence_score", 0.8)),
        )
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    async def compare_identities(
        self,
        embedding_a: List[float],
        embedding_b: List[float]
    ) -> float:
        """
        Compare two identity embeddings using cosine similarity.
        
        Args:
            embedding_a: First identity embedding (1536-dim)
            embedding_b: Second identity embedding (1536-dim)
            
        Returns:
            Similarity score between 0 and 1
        """
        a = np.array(embedding_a)
        b = np.array(embedding_b)
        
        # Cosine similarity
        similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        return float(max(0, min(1, (similarity + 1) / 2)))  # Normalize to 0-1
    
    async def merge_identities(
        self,
        embeddings: List[List[float]],
        weights: Optional[List[float]] = None
    ) -> List[float]:
        """
        Merge multiple embeddings into a single identity vector.
        
        Useful for creating a unified identity from multiple product angles.
        
        Args:
            embeddings: List of embedding vectors
            weights: Optional weights for each embedding
            
        Returns:
            Merged and normalized embedding vector
        """
        if not embeddings:
            raise ValueError("No embeddings provided for merging")
        
        if weights is None:
            weights = [1.0 / len(embeddings)] * len(embeddings)
        
        # Weighted average
        embeddings_array = np.array(embeddings)
        weights_array = np.array(weights).reshape(-1, 1)
        merged = np.sum(embeddings_array * weights_array, axis=0)
        
        # Normalize to unit length
        merged = merged / np.linalg.norm(merged)
        
        return merged.tolist()
    
    async def find_similar_products(
        self,
        query_embedding: List[float],
        stored_embeddings: List[tuple[str, List[float]]],
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[tuple[str, float]]:
        """
        Find similar products by comparing embeddings.
        
        Args:
            query_embedding: The embedding to search for
            stored_embeddings: List of (id, embedding) tuples
            top_k: Number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of (id, similarity_score) tuples
        """
        results = []
        
        for product_id, embedding in stored_embeddings:
            similarity = await self.compare_identities(query_embedding, embedding)
            if similarity >= threshold:
                results.append((product_id, similarity))
        
        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def get_vision_dna_agent() -> VisionDNAAgent:
    """Factory function to create a VisionDNAAgent instance."""
    return VisionDNAAgent()
