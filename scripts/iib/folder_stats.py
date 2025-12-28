import os
import re
from typing import Dict, List, Set, Optional
from collections import Counter
from scripts.iib.db.datamodel import DataBase, FolderStats, Image, ImageTag, Tag, GlobalSetting
from scripts.iib.tool import is_media_file, is_valid_media_path, get_video_type
from scripts.iib.logger import logger
import json

# Default English stopwords
DEFAULT_STOPWORDS = [
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "will", "with",
    "i", "you", "we", "they", "this", "but", "or", "not", "if", "can", "my", "your",
    "all", "one", "two", "more", "been", "have", "had", "do", "does", "done", "so",
    "up", "out", "about", "into", "through", "during", "before", "after", "above",
    "below", "between", "under", "again", "further", "then", "once", "there", "when",
    "where", "why", "how", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "nor", "only", "own", "same", "than", "too", "very", "just"
]

STOPWORDS_SETTING_KEY = "folder_stats_stopwords"


def get_stopwords(conn) -> Set[str]:
    """Get stopwords from settings or return default"""
    setting = GlobalSetting.get_setting(conn, STOPWORDS_SETTING_KEY)
    if setting and isinstance(setting, list):
        return set(word.lower() for word in setting)
    return set(DEFAULT_STOPWORDS)


def save_stopwords(conn, stopwords: List[str]):
    """Save stopwords to settings"""
    GlobalSetting.save_setting(conn, STOPWORDS_SETTING_KEY, json.dumps(stopwords))


def extract_words_from_text(text: str, stopwords: Set[str], min_length: int = 2) -> List[str]:
    """
    Extract meaningful words from text, filtering out stopwords.
    
    Args:
        text: Input text to analyze
        stopwords: Set of words to exclude
        min_length: Minimum word length to include
    
    Returns:
        List of filtered words
    """
    if not text:
        return []
    
    # Convert to lowercase and extract words (alphanumeric + hyphens)
    words = re.findall(r'\b[a-z0-9][\w-]*\b', text.lower())
    
    # Filter by length and stopwords
    filtered_words = [
        word for word in words 
        if len(word) >= min_length and word not in stopwords
    ]
    
    return filtered_words


def get_file_and_folder_counts(folder_path: str, recursive: bool = True) -> Dict[str, int]:
    """
    Count files and subfolders in a directory.
    
    Args:
        folder_path: Path to the folder
        recursive: Whether to count recursively
    
    Returns:
        Dictionary with counts
    """
    file_count = 0
    subfolder_count = 0
    total_size = 0
    media_file_count = 0
    
    try:
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return {
                "file_count": 0,
                "subfolder_count": 0,
                "total_size_bytes": 0,
                "media_file_count": 0
            }
        
        if recursive:
            for root, dirs, files in os.walk(folder_path):
                subfolder_count += len(dirs)
                for file in files:
                    file_count += 1
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                        if is_media_file(file):
                            media_file_count += 1
                    except (OSError, FileNotFoundError):
                        pass
        else:
            with os.scandir(folder_path) as entries:
                for entry in entries:
                    try:
                        if entry.is_file():
                            file_count += 1
                            total_size += entry.stat().st_size
                            if is_media_file(entry.name):
                                media_file_count += 1
                        elif entry.is_dir():
                            subfolder_count += 1
                    except (OSError, FileNotFoundError):
                        pass
    
    except Exception as e:
        logger.error(f"Error counting files in {folder_path}: {e}")
    
    return {
        "file_count": file_count,
        "subfolder_count": subfolder_count,
        "total_size_bytes": total_size,
        "media_file_count": media_file_count
    }


def get_media_stats(conn, folder_path: str, recursive: bool = True, limit: Optional[int] = None) -> Dict:
    """
    Get statistics about media files in a folder from database.
    
    Args:
        conn: Database connection
        folder_path: Path to the folder
        recursive: Whether to analyze recursively
        limit: Maximum number of images to analyze (None for unlimited)
    
    Returns:
        Dictionary with media statistics
    """
    folder_path = os.path.normpath(folder_path)
    
    # Build path pattern for SQL LIKE query
    path_pattern = folder_path + os.sep + "%"
    
    try:
        from contextlib import closing
        
        # Get all images in folder
        with closing(conn.cursor()) as cur:
            if limit:
                # With limit
                cur.execute("""
                    SELECT id, path FROM image 
                    WHERE path LIKE ? 
                    ORDER BY date DESC
                    LIMIT ?
                """, (path_pattern, limit))
            else:
                # Without limit
                cur.execute("""
                    SELECT id, path FROM image 
                    WHERE path LIKE ?
                """, (path_pattern,))
            
            image_rows = cur.fetchall()
        
        # Filter for non-recursive mode (only direct children)
        if not recursive:
            filtered_rows = []
            for row in image_rows:
                img_path = row[1]
                # Check if file is direct child (no additional path separators after folder_path)
                rel_path = os.path.relpath(img_path, folder_path)
                if os.sep not in rel_path and rel_path != '.':
                    filtered_rows.append(row)
            image_rows = filtered_rows
        
        image_ids = [row[0] for row in image_rows]
        total_images = len(image_ids)
        
        if total_images == 0:
            return {
                "total_images": 0,
                "total_videos": 0,
                "indexed_media": 0,
                "tagged_images": 0,
                "untagged_images": 0,
                "analyzed_count": 0,
                "limit_applied": limit is not None
            }
        
        # Count videos vs images
        total_videos = sum(1 for row in image_rows if get_video_type(row[1]))
        total_images_only = total_images - total_videos
        
        # Get tagged image count (only custom tags)
        with closing(conn.cursor()) as cur:
            placeholders = ','.join('?' * len(image_ids))
            cur.execute(f"""
                SELECT COUNT(DISTINCT it.image_id) 
                FROM image_tag it
                JOIN tag t ON it.tag_id = t.id
                WHERE it.image_id IN ({placeholders})
                AND t.type = 'custom'
            """, image_ids)
            tagged_count = cur.fetchone()[0]
        
        return {
            "total_images": total_images_only,
            "total_videos": total_videos,
            "indexed_media": total_images,
            "tagged_images": tagged_count,
            "untagged_images": total_images - tagged_count,
            "analyzed_count": total_images,
            "limit_applied": limit is not None
        }
    
    except Exception as e:
        logger.error(f"Error getting media stats for {folder_path}: {e}")
        return {
            "total_images": 0,
            "total_videos": 0,
            "indexed_media": 0,
            "tagged_images": 0,
            "untagged_images": 0,
            "analyzed_count": 0,
            "limit_applied": limit is not None,
            "error": str(e)
        }


def get_top_tags(conn, folder_path: str, recursive: bool = True, limit: int = 10, max_images: Optional[int] = None) -> List[Dict]:
    """
    Get most frequently used tags in a folder.
    
    Args:
        conn: Database connection
        folder_path: Path to the folder
        recursive: Whether to analyze recursively
        limit: Number of top tags to return
        max_images: Maximum number of images to analyze
    
    Returns:
        List of tag dictionaries with counts
    """
    folder_path = os.path.normpath(folder_path)
    path_pattern = folder_path + os.sep + "%"
    
    try:
        from contextlib import closing
        
        # Get images in folder with optional limit
        with closing(conn.cursor()) as cur:
            if max_images:
                cur.execute("""
                    SELECT id, path FROM image 
                    WHERE path LIKE ? 
                    ORDER BY date DESC
                    LIMIT ?
                """, (path_pattern, max_images))
            else:
                cur.execute("""
                    SELECT id, path FROM image 
                    WHERE path LIKE ?
                """, (path_pattern,))
            
            image_rows = cur.fetchall()
        
        # Filter for non-recursive
        if not recursive:
            filtered_rows = []
            for row in image_rows:
                img_path = row[1]
                rel_path = os.path.relpath(img_path, folder_path)
                if os.sep not in rel_path and rel_path != '.':
                    filtered_rows.append(row)
            image_rows = filtered_rows
        
        image_ids = [row[0] for row in image_rows]
        
        if not image_ids:
            logger.info(f"No images found for tags in folder {folder_path}")
            return []
        
        logger.info(f"Found {len(image_ids)} images for tag analysis in {folder_path}")
        
        # Get tag counts (only custom tags)
        with closing(conn.cursor()) as cur:
            placeholders = ','.join('?' * len(image_ids))
            cur.execute(f"""
                SELECT 
                    tag.id, 
                    tag.name, 
                    tag.type,
                    COUNT(*) as count
                FROM image_tag
                INNER JOIN tag ON image_tag.tag_id = tag.id
                WHERE image_tag.image_id IN ({placeholders})
                AND tag.type = 'custom'
                GROUP BY tag.id
                ORDER BY count DESC
                LIMIT ?
            """, image_ids + [limit])
            
            rows = cur.fetchall()
        
        logger.info(f"Found {len(rows)} tags for folder {folder_path}")
        
        total_tags = sum(row[3] for row in rows)
        
        return [
            {
                "tag_id": row[0],
                "tag_name": row[1],
                "tag_type": row[2],
                "count": row[3],
                "percentage": round((row[3] / total_tags * 100), 2) if total_tags > 0 else 0
            }
            for row in rows
        ]
    
    except Exception as e:
        logger.error(f"Error getting top tags for {folder_path}: {e}")
        return []


def analyze_prompt_words(conn, folder_path: str, recursive: bool = True, limit: int = 20, max_images: Optional[int] = None) -> Dict:
    """
    Analyze word frequency in image prompts.
    
    Args:
        conn: Database connection
        folder_path: Path to the folder
        recursive: Whether to analyze recursively
        limit: Number of top words to return
        max_images: Maximum number of images to analyze
    
    Returns:
        Dictionary with word frequency analysis
    """
    folder_path = os.path.normpath(folder_path)
    path_pattern = folder_path + os.sep + "%"
    stopwords = get_stopwords(conn)
    
    try:
        from contextlib import closing
        
        # Get images with exif data
        with closing(conn.cursor()) as cur:
            if max_images:
                cur.execute("""
                    SELECT path, exif FROM image 
                    WHERE path LIKE ? AND exif IS NOT NULL AND exif != ''
                    ORDER BY date DESC
                    LIMIT ?
                """, (path_pattern, max_images))
            else:
                cur.execute("""
                    SELECT path, exif FROM image 
                    WHERE path LIKE ? AND exif IS NOT NULL AND exif != ''
                """, (path_pattern,))
            
            rows = cur.fetchall()
        
        # Filter for non-recursive
        if not recursive:
            filtered_rows = []
            for row in rows:
                img_path = row[0]
                rel_path = os.path.relpath(img_path, folder_path)
                if os.sep not in rel_path and rel_path != '.':
                    filtered_rows.append(row)
            rows = filtered_rows
        
        if not rows:
            return {
                "total_prompts_analyzed": 0,
                "top_words": []
            }
        
        # Collect all words from prompts
        all_words = []
        for row in rows:
            exif_data = row[1]
            if exif_data:
                # Extract only the positive prompt (before "Negative prompt:" or newline with "Steps:")
                # Format: "positive prompt\nNegative prompt: ...\nSteps: ..."
                prompt_text = exif_data
                
                # Stop at "Negative prompt:" line
                if '\nNegative prompt:' in prompt_text:
                    prompt_text = prompt_text.split('\nNegative prompt:')[0]
                # Or stop at "Steps:" line
                elif '\nSteps:' in prompt_text:
                    prompt_text = prompt_text.split('\nSteps:')[0]
                
                # Extract words only from the positive prompt
                words = extract_words_from_text(prompt_text, stopwords)
                all_words.extend(words)
        
        # Count word frequency
        word_counts = Counter(all_words)
        top_words = word_counts.most_common(limit)
        
        total_words = sum(word_counts.values())
        
        return {
            "total_prompts_analyzed": len(rows),
            "total_words_found": len(word_counts),
            "top_words": [
                {
                    "word": word,
                    "count": count,
                    "percentage": round((count / total_words * 100), 2) if total_words > 0 else 0
                }
                for word, count in top_words
            ]
        }
    
    except Exception as e:
        logger.error(f"Error analyzing prompts for {folder_path}: {e}")
        return {
            "total_prompts_analyzed": 0,
            "top_words": [],
            "error": str(e)
        }


def get_metadata_summary(conn, folder_path: str, recursive: bool = True, max_images: Optional[int] = None) -> Dict:
    """
    Get summary of metadata (models, image sizes) from images in folder.
    
    Args:
        conn: Database connection
        folder_path: Path to the folder
        recursive: Whether to analyze recursively
        max_images: Maximum number of images to analyze
    
    Returns:
        Dictionary with metadata summaries
    """
    folder_path = os.path.normpath(folder_path)
    path_pattern = folder_path + os.sep + "%"
    
    try:
        from contextlib import closing
        
        # Get images in folder
        with closing(conn.cursor()) as cur:
            if max_images:
                cur.execute("""
                    SELECT path, exif FROM image 
                    WHERE path LIKE ? AND exif IS NOT NULL AND exif != ''
                    ORDER BY date DESC
                    LIMIT ?
                """, (path_pattern, max_images))
            else:
                cur.execute("""
                    SELECT path, exif FROM image 
                    WHERE path LIKE ? AND exif IS NOT NULL AND exif != ''
                """, (path_pattern,))
            
            rows = cur.fetchall()
        
        # Filter for non-recursive
        if not recursive:
            filtered_rows = []
            for row in rows:
                img_path = row[0]
                rel_path = os.path.relpath(img_path, folder_path)
                if os.sep not in rel_path and rel_path != '.':
                    filtered_rows.append(row)
            rows = filtered_rows
        
        models = Counter()
        sizes = Counter()
        
        for row in rows:
            exif_data = row[1]
            if not exif_data:
                continue
            
            # Try to extract model name (common patterns)
            model_patterns = [
                r'Model:\s*([^\n,]+)',
                r'model:\s*([^\n,]+)',
                r'"model":\s*"([^"]+)"',
            ]
            
            for pattern in model_patterns:
                match = re.search(pattern, exif_data, re.IGNORECASE)
                if match:
                    model_name = match.group(1).strip()
                    if model_name:
                        models[model_name] += 1
                        break
            
            # Try to extract image size
            size_patterns = [
                r'Size:\s*(\d+x\d+)',
                r'size:\s*(\d+x\d+)',
                r'"size":\s*"(\d+x\d+)"',
                r'(\d{3,5}x\d{3,5})',  # Generic WxH pattern
            ]
            
            for pattern in size_patterns:
                match = re.search(pattern, exif_data, re.IGNORECASE)
                if match:
                    size = match.group(1)
                    sizes[size] += 1
                    break
        
        return {
            "models": dict(models.most_common(10)),
            "sizes": dict(sizes.most_common(10))
        }
    
    except Exception as e:
        logger.error(f"Error getting metadata summary for {folder_path}: {e}")
        return {
            "models": {},
            "sizes": {},
            "error": str(e)
        }


def compute_folder_stats(
    folder_path: str, 
    recursive: bool = True, 
    include_metadata: bool = True,
    analysis_limit: Optional[int] = None
) -> Dict:
    """
    Compute comprehensive statistics for a folder.
    
    Args:
        folder_path: Path to the folder
        recursive: Whether to analyze recursively
        include_metadata: Whether to include detailed metadata analysis
        analysis_limit: Maximum number of images to analyze for statistics (None = unlimited)
    
    Returns:
        Dictionary with all statistics
    """
    folder_path = os.path.normpath(folder_path)
    
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        raise ValueError(f"Invalid folder path: {folder_path}")
    
    conn = DataBase.get_conn()
    
    # Always compute file/folder counts (no limit)
    counts = get_file_and_folder_counts(folder_path, recursive)
    
    # Media stats with limit
    media_stats = get_media_stats(conn, folder_path, recursive, analysis_limit)
    
    # Tag analysis with limit
    top_tags = get_top_tags(conn, folder_path, recursive, limit=10, max_images=analysis_limit)
    
    # Prompt analysis with limit
    prompt_analysis = analyze_prompt_words(conn, folder_path, recursive, limit=20, max_images=analysis_limit)
    
    # Metadata summary with limit (only if requested)
    metadata_summary = {}
    if include_metadata:
        metadata_summary = get_metadata_summary(conn, folder_path, recursive, max_images=analysis_limit)
    
    return {
        "folder_path": folder_path,
        "recursive": recursive,
        "file_count": counts["file_count"],
        "subfolder_count": counts["subfolder_count"],
        "total_size_bytes": counts["total_size_bytes"],
        "media_file_count": counts["media_file_count"],
        "media_stats": media_stats,
        "top_tags": top_tags,
        "prompt_analysis": prompt_analysis,
        "metadata_summary": metadata_summary,
        "analysis_limit": analysis_limit
    }


def get_cached_or_compute_stats(
    folder_path: str,
    recursive: bool = True,
    force_refresh: bool = False,
    include_metadata: bool = True,
    analysis_limit: Optional[int] = None
) -> Dict:
    """
    Get folder statistics from cache or compute if needed.
    
    Args:
        folder_path: Path to the folder
        recursive: Whether to analyze recursively
        force_refresh: Force recomputation even if cache is valid
        include_metadata: Whether to include detailed metadata
        analysis_limit: Maximum number of images to analyze
    
    Returns:
        Dictionary with statistics and cache info
    """
    folder_path = os.path.normpath(folder_path)
    conn = DataBase.get_conn()
    
    # Check cache validity
    cache_expired = FolderStats.is_cache_expired(conn, folder_path)
    
    if not force_refresh and not cache_expired:
        # Return cached data
        cached = FolderStats.get_cached_stats(conn, folder_path)
        if cached:
            result = cached["stats"]
            result["cache_info"] = {
                "is_cached": True,
                "computed_at": cached["computed_at"],
                "cache_valid": True
            }
            return result
    
    # Compute fresh statistics
    stats = compute_folder_stats(folder_path, recursive, include_metadata, analysis_limit)
    
    # Cache the results
    try:
        FolderStats.cache_stats(conn, folder_path, stats)
        computed_at = stats.get("computed_at")
    except Exception as e:
        logger.error(f"Error caching stats for {folder_path}: {e}")
        computed_at = None
    
    # Add cache info
    stats["cache_info"] = {
        "is_cached": False,
        "computed_at": computed_at,
        "cache_valid": True
    }
    
    return stats
