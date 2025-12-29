"""
Background job for computing folder statistics.
Similar to img_cache_gen.py, this runs in a thread pool to compute stats for visible folders.
"""

import os
import time
from typing import List, Set
from concurrent.futures import ThreadPoolExecutor, Future
from threading import Lock
from scripts.iib.folder_stats import compute_folder_stats, get_cached_or_compute_stats
from scripts.iib.db.datamodel import DataBase
from scripts.iib.logger import logger

# Global state for background job
_executor: ThreadPoolExecutor = None
_pending_jobs: Set[str] = set()  # Set of folder paths being processed
_jobs_lock = Lock()
_initialized = False


def init_background_worker(max_workers: int = 4):
    """Initialize the background worker thread pool"""
    global _executor, _initialized
    if not _initialized:
        _executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="folder-stats-")
        _initialized = True
        logger.info(f"[FOLDER_STATS_BG] Background worker initialized with {max_workers} workers")
    else:
        logger.debug(f"[FOLDER_STATS_BG] Background worker already initialized")


def shutdown_background_worker():
    """Shutdown the background worker thread pool"""
    global _executor, _initialized
    if _executor:
        _executor.shutdown(wait=False)
        _executor = None
        _initialized = False
        logger.info("Folder stats background worker shut down")


def is_job_pending(folder_path: str) -> bool:
    """Check if a job is already pending for this folder"""
    folder_path = os.path.normpath(folder_path)
    with _jobs_lock:
        return folder_path in _pending_jobs


def _compute_stats_task(folder_path: str, recursive: bool = True, analysis_limit: int = 500):
    """Background task to compute folder statistics"""
    folder_path = os.path.normpath(folder_path)
    
    try:
        logger.info(f"[FOLDER_STATS_BG] Starting computation for: {folder_path} (recursive={recursive}, limit={analysis_limit})")
        start_time = time.time()
        
        # Compute and cache the stats
        stats = compute_folder_stats(
            folder_path=folder_path,
            recursive=recursive,
            include_metadata=False,
            analysis_limit=analysis_limit
        )
        
        # Cache the result
        conn = DataBase.get_conn()
        from scripts.iib.db.datamodel import FolderStats
        FolderStats.cache_stats(conn, folder_path, stats)
        conn.commit()
        
        elapsed = time.time() - start_time
        logger.info(f"[FOLDER_STATS_BG] ✓ Completed in {elapsed:.2f}s: {folder_path} "
                   f"({stats.get('media_file_count', 0)} media files, "
                   f"{len(stats.get('top_tags', []))} tags, "
                   f"{len(stats.get('prompt_analysis', {}).get('top_words', []))} words)")
        
    except Exception as e:
        logger.error(f"[FOLDER_STATS_BG] ✗ Error computing stats for {folder_path}: {e}", exc_info=True)
    finally:
        # Remove from pending jobs
        with _jobs_lock:
            _pending_jobs.discard(folder_path)
            logger.debug(f"[FOLDER_STATS_BG] Job removed from pending queue: {folder_path} (remaining: {len(_pending_jobs)})")


def submit_folder_for_processing(folder_path: str, recursive: bool = True, 
                                  analysis_limit: int = 500, force: bool = False) -> bool:
    """
    Submit a folder for background processing.
    
    Args:
        folder_path: Path to the folder
        recursive: Whether to analyze recursively
        analysis_limit: Maximum number of images to analyze
        force: Force recomputation even if cached
        
    Returns:
        True if job was submitted, False if already pending or cached
    """
    if not _initialized:
        init_background_worker()
    
    folder_path = os.path.normpath(folder_path)
    
    # Check if already pending
    if is_job_pending(folder_path):
        logger.debug(f"[FOLDER_STATS_BG] Job already pending: {folder_path}")
        return False
    
    # Check if cache exists and is valid (unless force=True)
    if not force:
        conn = DataBase.get_conn()
        from scripts.iib.db.datamodel import FolderStats
        if not FolderStats.is_cache_expired(conn, folder_path):
            logger.debug(f"[FOLDER_STATS_BG] Cache valid, skipping: {folder_path}")
            return False
    
    # Add to pending jobs
    with _jobs_lock:
        if folder_path in _pending_jobs:
            logger.debug(f"[FOLDER_STATS_BG] Job already in pending set: {folder_path}")
            return False
        _pending_jobs.add(folder_path)
    
    # Submit the job
    logger.info(f"[FOLDER_STATS_BG] → Submitting job: {folder_path} (pending jobs: {len(_pending_jobs)})")
    _executor.submit(_compute_stats_task, folder_path, recursive, analysis_limit)
    return True


def batch_submit_folders(folder_paths: List[str], recursive: bool = True, 
                        analysis_limit: int = 500, force: bool = False) -> int:
    """
    Submit multiple folders for background processing.
    
    Args:
        folder_paths: List of folder paths
        recursive: Whether to analyze recursively
        analysis_limit: Maximum number of images to analyze
        force: Force recomputation even if cached
        
    Returns:
        Number of jobs submitted
    """
    if not _initialized:
        init_background_worker()
    
    submitted = 0
    for folder_path in folder_paths:
        if submit_folder_for_processing(folder_path, recursive, analysis_limit, force):
            submitted += 1
    
    return submitted


def get_pending_jobs() -> List[str]:
    """Get list of folder paths currently being processed"""
    with _jobs_lock:
        return list(_pending_jobs)


def get_pending_job_count() -> int:
    """Get number of pending jobs"""
    with _jobs_lock:
        return len(_pending_jobs)
