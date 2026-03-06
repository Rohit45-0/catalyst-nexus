"""
Spatiotemporal Agent
====================

Handles motion scaffolding, temporal consistency, and animation control
for video generation. This agent ensures smooth, coherent motion while
maintaining identity consistency across frames.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
import asyncio
import structlog

import numpy as np

logger = structlog.get_logger(__name__)


class MotionType(str, Enum):
    """Types of motion that can be applied."""
    STATIC = "static"
    SUBTLE = "subtle"
    MODERATE = "moderate"
    DYNAMIC = "dynamic"
    CUSTOM = "custom"


class CameraMotion(str, Enum):
    """Types of camera motion."""
    STATIC = "static"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    DOLLY = "dolly"
    ORBIT = "orbit"
    CUSTOM = "custom"


@dataclass
class MotionKeyframe:
    """Represents a keyframe in the motion sequence."""
    frame_index: int
    timestamp: float
    pose: Dict[str, Any]
    camera: Dict[str, float]
    expression: Optional[Dict[str, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MotionScaffold:
    """Complete motion scaffold for a video generation."""
    keyframes: List[MotionKeyframe]
    fps: int
    total_frames: int
    duration_seconds: float
    motion_type: MotionType
    camera_motion: CameraMotion
    interpolation: str = "smooth"
    metadata: Dict[str, Any] = field(default_factory=dict)


class SpatiotemporalAgent:
    """
    Spatiotemporal Agent for motion control and temporal consistency.
    
    This agent generates and manages motion scaffolds that guide video
    generation, ensuring smooth transitions and consistent character motion.
    
    Capabilities:
    - Motion path generation
    - Keyframe interpolation
    - Camera motion control
    - Temporal consistency enforcement
    - Expression/pose sequencing
    """
    
    def __init__(self):
        """Initialize the Spatiotemporal agent."""
        self.default_fps = 24
        self.interpolation_modes = ["linear", "smooth", "ease_in", "ease_out", "ease_in_out"]
        logger.info("Spatiotemporal Agent initialized")
    
    async def create_motion_scaffold(
        self,
        duration_seconds: float,
        motion_type: MotionType = MotionType.MODERATE,
        camera_motion: CameraMotion = CameraMotion.STATIC,
        fps: int = 24,
        keyframe_density: float = 0.5,
        options: Optional[Dict[str, Any]] = None
    ) -> MotionScaffold:
        """
        Create a motion scaffold for video generation.
        
        Args:
            duration_seconds: Length of the video in seconds.
            motion_type: Type of subject motion.
            camera_motion: Type of camera movement.
            fps: Frames per second.
            keyframe_density: Density of keyframes (0-1).
            options: Additional generation options.
            
        Returns:
            MotionScaffold: Complete motion scaffold.
        """
        logger.info(
            "Creating motion scaffold",
            duration=duration_seconds,
            motion_type=motion_type,
            camera_motion=camera_motion
        )
        
        options = options or {}
        total_frames = int(duration_seconds * fps)
        
        # Calculate keyframe positions
        keyframe_count = max(2, int(total_frames * keyframe_density))
        keyframe_indices = self._calculate_keyframe_positions(
            total_frames, keyframe_count
        )
        
        # Generate keyframes
        keyframes = []
        for i, frame_idx in enumerate(keyframe_indices):
            timestamp = frame_idx / fps
            
            keyframe = MotionKeyframe(
                frame_index=frame_idx,
                timestamp=timestamp,
                pose=self._generate_pose(
                    i / len(keyframe_indices),
                    motion_type,
                    options
                ),
                camera=self._generate_camera_state(
                    i / len(keyframe_indices),
                    camera_motion,
                    options
                ),
                expression=self._generate_expression(
                    i / len(keyframe_indices),
                    options
                ),
            )
            keyframes.append(keyframe)
        
        scaffold = MotionScaffold(
            keyframes=keyframes,
            fps=fps,
            total_frames=total_frames,
            duration_seconds=duration_seconds,
            motion_type=motion_type,
            camera_motion=camera_motion,
            interpolation=options.get("interpolation", "smooth"),
            metadata={
                "keyframe_count": len(keyframes),
                "keyframe_density": keyframe_density,
            }
        )
        
        logger.info(
            "Motion scaffold created",
            total_frames=total_frames,
            keyframe_count=len(keyframes)
        )
        
        return scaffold
    
    def _calculate_keyframe_positions(
        self,
        total_frames: int,
        keyframe_count: int
    ) -> List[int]:
        """Calculate evenly distributed keyframe positions."""
        if keyframe_count <= 1:
            return [0]
        
        step = total_frames / (keyframe_count - 1)
        positions = [int(i * step) for i in range(keyframe_count)]
        positions[-1] = total_frames - 1  # Ensure last frame is included
        
        return positions
    
    def _generate_pose(
        self,
        progress: float,
        motion_type: MotionType,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate pose data for a keyframe."""
        # Base pose structure
        pose = {
            "head": {"rotation": [0.0, 0.0, 0.0], "position": [0.0, 0.0, 0.0]},
            "body": {"rotation": [0.0, 0.0, 0.0], "position": [0.0, 0.0, 0.0]},
            "arms": {
                "left": {"angle": 0.0, "bend": 0.0},
                "right": {"angle": 0.0, "bend": 0.0},
            },
        }
        
        # Apply motion type variations
        if motion_type == MotionType.SUBTLE:
            pose["head"]["rotation"][1] = np.sin(progress * np.pi * 2) * 5
        elif motion_type == MotionType.MODERATE:
            pose["head"]["rotation"][1] = np.sin(progress * np.pi * 2) * 15
            pose["body"]["rotation"][1] = np.sin(progress * np.pi) * 5
        elif motion_type == MotionType.DYNAMIC:
            pose["head"]["rotation"][1] = np.sin(progress * np.pi * 4) * 30
            pose["body"]["rotation"][1] = np.sin(progress * np.pi * 2) * 15
            pose["arms"]["left"]["angle"] = np.cos(progress * np.pi * 2) * 30
        
        return pose
    
    def _generate_camera_state(
        self,
        progress: float,
        camera_motion: CameraMotion,
        options: Dict[str, Any]
    ) -> Dict[str, float]:
        """Generate camera state for a keyframe."""
        camera = {
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
            "rotation_x": 0.0,
            "rotation_y": 0.0,
            "rotation_z": 0.0,
            "fov": 50.0,
        }
        
        intensity = options.get("camera_intensity", 1.0)
        
        if camera_motion == CameraMotion.PAN_LEFT:
            camera["rotation_y"] = progress * -30 * intensity
        elif camera_motion == CameraMotion.PAN_RIGHT:
            camera["rotation_y"] = progress * 30 * intensity
        elif camera_motion == CameraMotion.TILT_UP:
            camera["rotation_x"] = progress * -15 * intensity
        elif camera_motion == CameraMotion.TILT_DOWN:
            camera["rotation_x"] = progress * 15 * intensity
        elif camera_motion == CameraMotion.ZOOM_IN:
            camera["z"] = progress * 20 * intensity
            camera["fov"] = 50 - progress * 10 * intensity
        elif camera_motion == CameraMotion.ZOOM_OUT:
            camera["z"] = progress * -20 * intensity
            camera["fov"] = 50 + progress * 10 * intensity
        elif camera_motion == CameraMotion.ORBIT:
            camera["rotation_y"] = progress * 360 * intensity
            camera["x"] = np.sin(progress * np.pi * 2) * 10 * intensity
            camera["z"] = np.cos(progress * np.pi * 2) * 10 * intensity
        
        return camera
    
    def _generate_expression(
        self,
        progress: float,
        options: Dict[str, Any]
    ) -> Dict[str, float]:
        """Generate facial expression weights for a keyframe."""
        base_expression = options.get("base_expression", "neutral")
        
        expressions = {
            "neutral": {"smile": 0.0, "blink": 0.0, "eyebrow_raise": 0.0},
            "happy": {"smile": 0.7, "blink": 0.1, "eyebrow_raise": 0.2},
            "serious": {"smile": -0.2, "blink": 0.0, "eyebrow_raise": -0.1},
            "surprised": {"smile": 0.3, "blink": 0.0, "eyebrow_raise": 0.8},
        }
        
        base = expressions.get(base_expression, expressions["neutral"])
        
        # Add natural variation
        return {
            "smile": base["smile"] + np.sin(progress * np.pi * 4) * 0.1,
            "blink": 1.0 if int(progress * 100) % 30 == 0 else 0.0,  # Periodic blinks
            "eyebrow_raise": base["eyebrow_raise"] + np.sin(progress * np.pi * 2) * 0.05,
        }
    
    async def interpolate_scaffold(
        self,
        scaffold: MotionScaffold,
        target_fps: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Interpolate a motion scaffold to generate per-frame data.
        
        Args:
            scaffold: The motion scaffold to interpolate.
            target_fps: Target FPS (defaults to scaffold FPS).
            
        Returns:
            List of frame data dictionaries.
        """
        target_fps = target_fps or scaffold.fps
        total_frames = int(scaffold.duration_seconds * target_fps)
        
        frames = []
        keyframe_times = [kf.timestamp for kf in scaffold.keyframes]
        
        for frame_idx in range(total_frames):
            timestamp = frame_idx / target_fps
            
            # Find surrounding keyframes
            prev_kf, next_kf, t = self._find_surrounding_keyframes(
                timestamp, scaffold.keyframes
            )
            
            # Interpolate values
            frame_data = self._interpolate_frame(
                prev_kf, next_kf, t, scaffold.interpolation
            )
            frame_data["frame_index"] = frame_idx
            frame_data["timestamp"] = timestamp
            
            frames.append(frame_data)
        
        return frames
    
    async def interpolate_with_optical_flow(
        self,
        scaffold: MotionScaffold,
        reference_image_path: Optional[str] = None,
        target_fps: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Interpolate scaffold with optical flow for better temporal consistency.
        
        Args:
            scaffold: Motion scaffold to interpolate.
            reference_image_path: Path to reference image for consistency.
            target_fps: Target FPS.
            
        Returns:
            List of frame data with optical flow enhanced interpolation.
        """
        # First get basic interpolation
        frames = await self.interpolate_scaffold(scaffold, target_fps)
        
        # Apply optical flow smoothing if reference available
        if reference_image_path:
            frames = self._apply_optical_flow_smoothing(frames, reference_image_path)
        
        return frames
    
    def _apply_optical_flow_smoothing(
        self,
        frames: List[Dict[str, Any]],
        reference_image_path: str
    ) -> List[Dict[str, Any]]:
        """
        Apply optical flow based smoothing to maintain product consistency.
        
        Args:
            frames: Interpolated frame data.
            reference_image_path: Reference image path.
            
        Returns:
            Smoothed frame data.
        """
        # Placeholder for optical flow implementation
        # In production, would use OpenCV or RAFT for optical flow
        # For now, add minor smoothing to pose/camera data
        
        smoothed_frames = []
        for i, frame in enumerate(frames):
            smoothed_frame = frame.copy()
            
            # Apply temporal smoothing to camera and pose
            if i > 0 and i < len(frames) - 1:
                prev_frame = frames[i-1]
                next_frame = frames[i+1]
                
                # Smooth camera position
                for key in ['x', 'y', 'z']:
                    if key in frame.get('camera', {}):
                        smoothed_frame['camera'][key] = (
                            prev_frame['camera'][key] * 0.25 +
                            frame['camera'][key] * 0.5 +
                            next_frame['camera'][key] * 0.25
                        )
                
                # Smooth pose rotations
                for part in ['head', 'body']:
                    if part in frame.get('pose', {}):
                        for axis in range(3):
                            prev_rot = prev_frame['pose'][part]['rotation'][axis]
                            curr_rot = frame['pose'][part]['rotation'][axis]
                            next_rot = next_frame['pose'][part]['rotation'][axis]
                            smoothed_frame['pose'][part]['rotation'][axis] = (
                                prev_rot * 0.25 + curr_rot * 0.5 + next_rot * 0.25
                            )
            
            smoothed_frames.append(smoothed_frame)
        
        return smoothed_frames
    
    def _find_surrounding_keyframes(
        self,
        timestamp: float,
        keyframes: List[MotionKeyframe]
    ) -> Tuple[MotionKeyframe, MotionKeyframe, float]:
        """Find the keyframes surrounding a given timestamp."""
        for i, kf in enumerate(keyframes[:-1]):
            if keyframes[i].timestamp <= timestamp <= keyframes[i + 1].timestamp:
                duration = keyframes[i + 1].timestamp - keyframes[i].timestamp
                t = (timestamp - keyframes[i].timestamp) / duration if duration > 0 else 0
                return keyframes[i], keyframes[i + 1], t
        
        # Default to last keyframe
        return keyframes[-1], keyframes[-1], 0.0
    
    def _interpolate_frame(
        self,
        prev_kf: MotionKeyframe,
        next_kf: MotionKeyframe,
        t: float,
        interpolation: str
    ) -> Dict[str, Any]:
        """Interpolate between two keyframes."""
        # Apply easing function
        t_eased = self._apply_easing(t, interpolation)
        
        # Interpolate pose
        pose = self._lerp_dict(prev_kf.pose, next_kf.pose, t_eased)
        
        # Interpolate camera
        camera = self._lerp_dict(prev_kf.camera, next_kf.camera, t_eased)
        
        # Interpolate expression
        expression = None
        if prev_kf.expression and next_kf.expression:
            expression = self._lerp_dict(prev_kf.expression, next_kf.expression, t_eased)
        
        return {
            "pose": pose,
            "camera": camera,
            "expression": expression,
        }
    
    def _apply_easing(self, t: float, interpolation: str) -> float:
        """Apply easing function to interpolation parameter."""
        if interpolation == "linear":
            return t
        elif interpolation == "smooth" or interpolation == "ease_in_out":
            return t * t * (3 - 2 * t)  # Smoothstep
        elif interpolation == "ease_in":
            return t * t
        elif interpolation == "ease_out":
            return 1 - (1 - t) ** 2
        return t
    
    def _lerp_dict(
        self,
        a: Dict[str, Any],
        b: Dict[str, Any],
        t: float
    ) -> Dict[str, Any]:
        """Linearly interpolate between two dictionaries."""
        result = {}
        for key in a:
            if isinstance(a[key], dict):
                result[key] = self._lerp_dict(a[key], b.get(key, a[key]), t)
            elif isinstance(a[key], (int, float)):
                result[key] = a[key] + (b.get(key, a[key]) - a[key]) * t
            elif isinstance(a[key], list):
                result[key] = [
                    a[key][i] + (b.get(key, a[key])[i] - a[key][i]) * t
                    for i in range(len(a[key]))
                ]
            else:
                result[key] = a[key]
        return result
    
    async def transfer_motion(
        self,
        source_video_path: str,
        target_scaffold: MotionScaffold
    ) -> MotionScaffold:
        """
        Extract motion from a source video and apply to a new scaffold.
        
        Args:
            source_video_path: Path to source video for motion extraction.
            target_scaffold: Scaffold to apply motion to.
            
        Returns:
            MotionScaffold with transferred motion.
        """
        logger.info("Starting motion transfer", source=source_video_path)
        
        # Extract motion from source video (placeholder)
        # Would use pose estimation models in production
        extracted_keyframes = await self._extract_motion_keyframes(source_video_path)
        
        # Map extracted motion to target scaffold
        new_keyframes = []
        for i, kf in enumerate(target_scaffold.keyframes):
            if i < len(extracted_keyframes):
                new_kf = MotionKeyframe(
                    frame_index=kf.frame_index,
                    timestamp=kf.timestamp,
                    pose=extracted_keyframes[i].pose,
                    camera=kf.camera,  # Keep original camera
                    expression=extracted_keyframes[i].expression,
                )
                new_keyframes.append(new_kf)
            else:
                new_keyframes.append(kf)
        
        return MotionScaffold(
            keyframes=new_keyframes,
            fps=target_scaffold.fps,
            total_frames=target_scaffold.total_frames,
            duration_seconds=target_scaffold.duration_seconds,
            motion_type=MotionType.CUSTOM,
            camera_motion=target_scaffold.camera_motion,
            interpolation=target_scaffold.interpolation,
            metadata={
                **target_scaffold.metadata,
                "motion_transferred_from": source_video_path,
            }
        )
    
    async def _extract_motion_keyframes(
        self,
        video_path: str
    ) -> List[MotionKeyframe]:
        """Extract motion keyframes from a video file."""
        # Placeholder for motion extraction
        # Would use MediaPipe, OpenPose, or similar
        return []
