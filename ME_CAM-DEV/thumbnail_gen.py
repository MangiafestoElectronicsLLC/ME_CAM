import cv2
import os
from loguru import logger

def extract_thumbnail(video_path: str, thumb_dir: str, thumb_name: str = None) -> str:
    """Extract first frame from video and save as thumbnail.
    
    Args:
        video_path: Path to video file
        thumb_dir: Directory to save thumbnail
        thumb_name: Optional custom name; defaults to video basename + .jpg
    
    Returns:
        Path to the thumbnail file.
    """
    try:
        os.makedirs(thumb_dir, exist_ok=True)
        
        if thumb_name is None:
            thumb_name = os.path.basename(video_path) + ".jpg"
        thumb_path = os.path.join(thumb_dir, thumb_name)
        
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()
        
        if ret and frame is not None:
            # Resize to thumbnail size (e.g., 200x112 for 16:9)
            frame = cv2.resize(frame, (200, 112))
            cv2.imwrite(thumb_path, frame)
            logger.info(f"[THUMBNAIL] Extracted: {thumb_path}")
            return thumb_path
        else:
            logger.warning(f"[THUMBNAIL] Could not extract frame from {video_path}")
            return None
    except Exception as e:
        logger.error(f"[THUMBNAIL] Failed to extract from {video_path}: {e}")
        return None
