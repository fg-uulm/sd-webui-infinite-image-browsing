#!/usr/bin/env python3
"""
Test script for Folder Statistics functionality.

This script demonstrates basic usage of the folder statistics functions.
Run this from the project root directory.
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from scripts.iib.db.datamodel import DataBase
from scripts.iib.folder_stats import (
    compute_folder_stats,
    get_cached_or_compute_stats,
    get_stopwords,
    save_stopwords,
    DEFAULT_STOPWORDS
)


def test_folder_stats(folder_path: str):
    """Test folder statistics computation"""
    
    print("=" * 80)
    print(f"Testing Folder Statistics for: {folder_path}")
    print("=" * 80)
    
    # Check if folder exists
    if not os.path.exists(folder_path):
        print(f"❌ Error: Folder does not exist: {folder_path}")
        return
    
    print("\n1. Computing fresh statistics (no cache)...")
    try:
        stats = compute_folder_stats(
            folder_path=folder_path,
            recursive=True,
            include_metadata=True,
            analysis_limit=100  # Limit for testing
        )
        
        print(f"✓ Folder Path: {stats['folder_path']}")
        print(f"✓ File Count: {stats['file_count']}")
        print(f"✓ Subfolder Count: {stats['subfolder_count']}")
        print(f"✓ Total Size: {stats['total_size_bytes']:,} bytes")
        print(f"✓ Media Files: {stats['media_file_count']}")
        
        print("\nMedia Statistics:")
        media_stats = stats['media_stats']
        print(f"  - Images: {media_stats['total_images']}")
        print(f"  - Videos: {media_stats['total_videos']}")
        print(f"  - Indexed: {media_stats['indexed_media']}")
        print(f"  - Tagged: {media_stats['tagged_images']}")
        print(f"  - Untagged: {media_stats['untagged_images']}")
        
        if stats['top_tags']:
            print("\nTop 5 Tags:")
            for i, tag in enumerate(stats['top_tags'][:5], 1):
                print(f"  {i}. {tag['tag_name']} ({tag['tag_type']}): {tag['count']} times ({tag['percentage']}%)")
        else:
            print("\nNo tags found.")
        
        prompt_analysis = stats['prompt_analysis']
        if prompt_analysis['top_words']:
            print(f"\nPrompt Analysis ({prompt_analysis['total_prompts_analyzed']} prompts):")
            print("Top 10 Words:")
            for i, word_info in enumerate(prompt_analysis['top_words'][:10], 1):
                print(f"  {i}. '{word_info['word']}': {word_info['count']} times ({word_info['percentage']}%)")
        else:
            print("\nNo prompt data found.")
        
        metadata = stats['metadata_summary']
        if metadata.get('models'):
            print("\nTop Models:")
            for model, count in list(metadata['models'].items())[:5]:
                print(f"  - {model}: {count} images")
        
        if metadata.get('sizes'):
            print("\nTop Image Sizes:")
            for size, count in list(metadata['sizes'].items())[:5]:
                print(f"  - {size}: {count} images")
        
    except Exception as e:
        print(f"❌ Error computing stats: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 80)
    print("2. Testing cached statistics...")
    try:
        cached_stats = get_cached_or_compute_stats(
            folder_path=folder_path,
            recursive=True,
            force_refresh=False,
            analysis_limit=100
        )
        
        cache_info = cached_stats.get('cache_info', {})
        if cache_info.get('is_cached'):
            print(f"✓ Retrieved from cache (computed at: {cache_info.get('computed_at')})")
        else:
            print("✓ Computed fresh statistics (not cached)")
        
    except Exception as e:
        print(f"❌ Error with cached stats: {e}")
    
    print("\n" + "=" * 80)
    print("3. Testing stopwords...")
    try:
        conn = DataBase.get_conn()
        stopwords = get_stopwords(conn)
        print(f"✓ Current stopwords count: {len(stopwords)}")
        print(f"  Default count: {len(DEFAULT_STOPWORDS)}")
        print(f"  Sample stopwords: {list(stopwords)[:10]}")
    except Exception as e:
        print(f"❌ Error with stopwords: {e}")
    
    print("\n" + "=" * 80)
    print("✅ Test completed!")
    print("=" * 80)


def main():
    """Main test function"""
    
    # Check if folder path is provided
    if len(sys.argv) < 2:
        print("Usage: python test_folder_stats.py <folder_path>")
        print("\nExample:")
        print("  python test_folder_stats.py /path/to/your/images")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    test_folder_stats(folder_path)


if __name__ == "__main__":
    main()
