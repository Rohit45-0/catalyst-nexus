"""
Video Processing Utilities
==========================

Frame extraction, video processing, and media manipulation helpers.
"""

from typing import List, Optional, Tuple, Generator
from pathlib import Path
import asyncio
import tempfile
import structlog

import cv2
import numpy as np
from PIL import Image

logger = structlog.get_logger(__name__)


async def extract_frames(
    video_path: str,
    output_dir: Optional[str] = None,
    fps: Optional[float] = None,
    max_frames: Optional[int] = None,
    start_time: float = 0.0,
    end_time: Optional[float] = None,
) -> List[str]:
    """
    Extract frames from a video file.
    
    Args:
        video_path: Path to the video file.
        output_dir: Directory to save frames. If None, uses temp directory.
        fps: Target FPS for extraction. If None, uses video's native FPS.
        max_frames: Maximum number of frames to extract.
        start_time: Start time in seconds.
        end_time: End time in seconds. If None, processes to end.
        
    Returns:
        List of paths to extracted frame images.
    """
    logger.info("Extracting frames", video_path=video_path)
    
    # Run in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _extract_frames_sync,
        video_path,
        output_dir,
        fps,
        max_frames,
        start_time,
        end_time,
    )


def _extract_frames_sync(
    video_path: str,
    output_dir: Optional[str],
    fps: Optional[float],
    max_frames: Optional[int],
    start_time: float,
    end_time: Optional[float],
) -> List[str]:
    """Synchronous frame extraction implementation."""
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
    
    # Get video properties
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / video_fps if video_fps > 0 else 0
    
    # Calculate extraction parameters
    target_fps = fps or video_fps
    frame_interval = max(1, int(video_fps / target_fps))
    
    start_frame = int(start_time * video_fps)
    end_frame = int((end_time or duration) * video_fps)
    end_frame = min(end_frame, total_frames)
    
    # Setup output directory
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="frames_")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Extract frames
    frame_paths = []
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    frame_count = 0
    current_frame = start_frame
    
    while current_frame < end_frame:
        if max_frames and frame_count >= max_frames:
            break
        
        ret, frame = cap.read()
        if not ret:
            break
        
        if (current_frame - start_frame) % frame_interval == 0:
            frame_path = str(Path(output_dir) / f"frame_{frame_count:06d}.png")
            cv2.imwrite(frame_path, frame)
            frame_paths.append(frame_path)
            frame_count += 1
        
        current_frame += 1
    
    cap.release()
    
    logger.info(f"Extracted {len(frame_paths)} frames")
    return frame_paths


async def frames_to_video(
    frame_paths: List[str],
    output_path: str,
    fps: int = 24,
    codec: str = "mp4v",
    quality: int = 95,
) -> str:
    """
    Compose frames into a video file.
    
    Args:
        frame_paths: List of paths to frame images.
        output_path: Output video file path.
        fps: Frames per second.
        codec: Video codec to use.
        quality: Output quality (1-100).
        
    Returns:
        Path to the created video file.
    """
    logger.info("Composing video", frame_count=len(frame_paths), fps=fps)
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _frames_to_video_sync,
        frame_paths,
        output_path,
        fps,
        codec,
        quality,
    )


def _frames_to_video_sync(
    frame_paths: List[str],
    output_path: str,
    fps: int,
    codec: str,
    quality: int,
) -> str:
    """Synchronous video composition implementation."""
    if not frame_paths:
        raise ValueError("No frames provided")
    
    # Read first frame to get dimensions
    first_frame = cv2.imread(frame_paths[0])
    if first_frame is None:
        raise ValueError(f"Could not read frame: {frame_paths[0]}")
    
    height, width = first_frame.shape[:2]
    
    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*codec)
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Write frames
    for frame_path in frame_paths:
        frame = cv2.imread(frame_path)
        if frame is not None:
            # Ensure consistent dimensions
            if frame.shape[:2] != (height, width):
                frame = cv2.resize(frame, (width, height))
            out.write(frame)
    
    out.release()
    
    logger.info("Video created", output_path=output_path)
    return output_path


async def get_video_info(video_path: str) -> dict:
    """
    Get information about a video file.
    
    Args:
        video_path: Path to the video file.
        
    Returns:
        Dictionary with video properties.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_video_info_sync, video_path)


def _get_video_info_sync(video_path: str) -> dict:
    """Synchronous video info extraction."""
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
    
    info = {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "codec": int(cap.get(cv2.CAP_PROP_FOURCC)),
    }
    
    info["duration"] = info["frame_count"] / info["fps"] if info["fps"] > 0 else 0
    
    cap.release()
    return info


async def resize_video(
    video_path: str,
    output_path: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    maintain_aspect: bool = True,
) -> str:
    """
    Resize a video file.
    
    Args:
        video_path: Input video path.
        output_path: Output video path.
        width: Target width.
        height: Target height.
        maintain_aspect: Whether to maintain aspect ratio.
        
    Returns:
        Path to resized video.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _resize_video_sync,
        video_path,
        output_path,
        width,
        height,
        maintain_aspect,
    )


def _resize_video_sync(
    video_path: str,
    output_path: str,
    width: Optional[int],
    height: Optional[int],
    maintain_aspect: bool,
) -> str:
    """Synchronous video resize implementation."""
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
    
    orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Calculate target dimensions
    if maintain_aspect:
        if width and height:
            # Fit within bounds
            scale = min(width / orig_width, height / orig_height)
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)
        elif width:
            scale = width / orig_width
            new_width = width
            new_height = int(orig_height * scale)
        elif height:
            scale = height / orig_height
            new_width = int(orig_width * scale)
            new_height = height
        else:
            new_width, new_height = orig_width, orig_height
    else:
        new_width = width or orig_width
        new_height = height or orig_height
    
    # Ensure dimensions are even (required for many codecs)
    new_width = new_width - (new_width % 2)
    new_height = new_height - (new_height % 2)
    
    # Initialize writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (new_width, new_height))
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        out.write(resized)
    
    cap.release()
    out.release()
    
    return output_path


def frame_iterator(
    video_path: str,
    start_frame: int = 0,
    end_frame: Optional[int] = None,
) -> Generator[Tuple[int, np.ndarray], None, None]:
    """
    Iterator that yields frames from a video.
    
    Args:
        video_path: Path to the video file.
        start_frame: Starting frame index.
        end_frame: Ending frame index (exclusive).
        
    Yields:
        Tuple of (frame_index, frame_array).
    """
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    end_frame = min(end_frame or total_frames, total_frames)
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    for frame_idx in range(start_frame, end_frame):
        ret, frame = cap.read()
        if not ret:
            break
        yield frame_idx, frame
    
    cap.release()


async def create_thumbnail(
    video_path: str,
    output_path: str,
    time_position: float = 0.0,
    size: Tuple[int, int] = (320, 180),
) -> str:
    """
    Create a thumbnail from a video.
    
    Args:
        video_path: Path to the video file.
        output_path: Output thumbnail path.
        time_position: Time position to extract thumbnail from (seconds).
        size: Thumbnail dimensions (width, height).
        
    Returns:
        Path to the created thumbnail.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _create_thumbnail_sync,
        video_path,
        output_path,
        time_position,
        size,
    )


def _create_thumbnail_sync(
    video_path: str,
    output_path: str,
    time_position: float,
    size: Tuple[int, int],
) -> str:
    """Synchronous thumbnail creation."""
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_number = int(time_position * fps)
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise ValueError("Could not read frame for thumbnail")
    
    # Resize and save
    thumbnail = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
    cv2.imwrite(output_path, thumbnail)
    
    return output_path
