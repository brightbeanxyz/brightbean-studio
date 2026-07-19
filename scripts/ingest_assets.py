#!/usr/bin/env python3
"""
BrightBean Asset Ingestion Script

Ingests verified assets from local filesystem into R2 storage and creates
PocketBase records with SHA-256 deduplication.

Run after R2 credentials are rotated and set as Fly secrets.

Usage:
    python scripts/ingest_assets.py --dry-run    # Preview what would be ingested
    python scripts/ingest_assets.py              # Actual ingestion
"""

import hashlib
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import requests
from django.conf import settings

# Setup Django
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

import django
django.setup()

from django.core.files.storage import default_storage
from apps.media_library.models import MediaAsset


# Verified source directories from brightbean-social-readiness.md
SOURCE_DIRS = [
    Path("/Users/mfdoom/Projects/agency-os/output/social-ready-2026-06-25/feed"),
    Path("/Users/mfdoom/Projects/agency-os/output/content-pool-2026-06-23"),
    Path("/Users/mfdoom/Downloads/pac_store-ites_3d/item_1"),
    Path("/Users/mfdoom/Projects/agency-os/reels"),
]

# Known asset mappings (filename -> metadata)
ASSET_METADATA = {
    "IMG_1761.png": {"title": "Plants Over Chairs hero", "project": "plants-over-chairs"},
    "IMG_1634.png": {"title": "Plants & Jeeps hero", "project": "plants-and-jeeps"},
    "new-01-screenprint-process.mp4": {"title": "Screen-print process Reel", "project": "plants-over-chairs", "type": "video"},
    "new-03-beach-lifestyle.mp4": {"title": "Studio/place Reel", "project": "studio", "type": "video"},
    # Social-ready set (26 files)
    "s01-iconic-hero.png": {"title": "Iconic hero", "project": "plants-over-chairs"},
    "s02-pink-hero.png": {"title": "Pink hero", "project": "plants-over-chairs"},
    "s03-royal-hero.png": {"title": "Royal hero", "project": "plants-over-chairs"},
    "s04-tote-hero.png": {"title": "Tote hero", "project": "plants-over-chairs"},
    "s05-beanie-hero.png": {"title": "Beanie hero", "project": "plants-over-chairs"},
    "s06-iconic-grid2.png": {"title": "Iconic grid 2", "project": "plants-over-chairs"},
    "s07-dot-grid2.png": {"title": "Dot grid 2", "project": "plants-over-chairs"},
    "s08-scatter-sky.png": {"title": "Scatter sky", "project": "plants-over-chairs"},
    "s09-scatter-bone.png": {"title": "Scatter bone", "project": "plants-over-chairs"},
    "s10-scatter-dark.png": {"title": "Scatter dark", "project": "plants-over-chairs"},
    "v2-01-stone-hero.png": {"title": "Stone hero", "project": "plants-over-chairs"},
    "v2-02-payasotee.png": {"title": "Payasotee", "project": "plants-over-chairs"},
    "v2-03-vanlife5.png": {"title": "Vanlife 5", "project": "plants-over-chairs"},
    "v2-04-dotcap-grid2.png": {"title": "Dotcap grid 2", "project": "plants-over-chairs"},
    "v2-05-scatter-bone.png": {"title": "Scatter bone v2", "project": "plants-over-chairs"},
    "v2-06-barlogo-hero.png": {"title": "Barlogo hero", "project": "plants-over-chairs"},
    "v3-s1-petstore-card.png": {"title": "Petstore card", "project": "plants-over-chairs"},
    "v3-s2-productos-card.png": {"title": "Productos card", "project": "plants-over-chairs"},
    "v3-s3-mialma-card.png": {"title": "Mialma card", "project": "plants-over-chairs"},
    "v3-s4-scatter-pink.png": {"title": "Scatter pink", "project": "plants-over-chairs"},
    "post-2-flowers-pink.png": {"title": "Flowers pink", "project": "plants-over-chairs"},
    "post-3-vanlife-royal.png": {"title": "Vanlife royal", "project": "plants-over-chairs"},
    "post-4-payaso-tote.png": {"title": "Payaso tote", "project": "plants-over-chairs"},
    "post-5-beanie.png": {"title": "Beanie", "project": "plants-over-chairs"},
    "cap-dir3-streetwear-post.png": {"title": "Streetwear post", "project": "plants-over-chairs"},
    "cap-dir4-ar-v2.png": {"title": "AR v2", "project": "plants-over-chairs"},
}


def compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def find_all_assets() -> List[Dict]:
    """Find all asset files in source directories."""
    assets = []
    for src_dir in SOURCE_DIRS:
        if not src_dir.exists():
            print(f"⚠️  Source directory not found: {src_dir}")
            continue
        for filepath in src_dir.rglob("*"):
            if filepath.is_file() and not filepath.name.startswith("."):
                # Skip non-media files
                if filepath.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".webm"}:
                    assets.append({
                        "path": filepath,
                        "filename": filepath.name,
                        "relative_path": filepath.relative_to(src_dir),
                    })
    return assets


def ingest_assets(dry_run: bool = False) -> Dict:
    """Ingest assets into R2 and create PocketBase records."""
    assets = find_all_assets()
    print(f"Found {len(assets)} candidate assets")

    # Deduplicate by SHA-256
    seen_hashes = {}
    unique_assets = []
    for asset in assets:
        sha256 = compute_sha256(asset["path"])
        if sha256 in seen_hashes:
            print(f"  ⏭️  Duplicate (SHA-256): {asset['filename']} -> {seen_hashes[sha256]}")
            continue
        seen_hashes[sha256] = asset["filename"]
        asset["sha256"] = sha256
        unique_assets.append(asset)

    print(f"Unique assets after deduplication: {len(unique_assets)}")

    results = {"uploaded": 0, "skipped": 0, "errors": []}

    for asset in unique_assets:
        metadata = ASSET_METADATA.get(asset["filename"], {})
        title = metadata.get("title", asset["filename"])
        project = metadata.get("project", "general")
        asset_type = metadata.get("type", "image" if asset["filename"].endswith((".png", ".jpg", ".jpeg", ".webp")) else "video")

        # Check if already exists in DB
        if MediaAsset.objects.filter(sha256=asset["sha256"]).exists():
            print(f"  ⏭️  Already in DB: {asset['filename']}")
            results["skipped"] += 1
            continue

        print(f"  📤 Uploading: {asset['filename']} ({title})")

        if dry_run:
            print(f"     [DRY RUN] Would upload to R2 and create MediaAsset record")
            results["uploaded"] += 1
            continue

        try:
            # Upload to R2 via Django storage
            with open(asset["path"], "rb") as f:
                # Use the storage backend to save
                saved_path = default_storage.save(
                    f"assets/{project}/{asset['sha256'][:8]}/{asset['filename']}",
                    f
                )

            # Create MediaAsset record
            media_asset = MediaAsset.objects.create(
                title=title,
                file=saved_path,
                sha256=asset["sha256"],
                file_size=asset["path"].stat().st_size,
                mime_type=asset_type,
                project=project,
                tags=[project],
                alt_text=title,
            )
            print(f"     ✅ Created MediaAsset #{media_asset.id}")
            results["uploaded"] += 1

        except Exception as e:
            error_msg = f"Failed to ingest {asset['filename']}: {e}"
            print(f"     ❌ {error_msg}")
            results["errors"].append(error_msg)

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ingest assets into BrightBean R2 + PocketBase")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    args = parser.parse_args()

    print("=" * 60)
    print("BrightBean Asset Ingestion")
    print("=" * 60)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()

    results = ingest_assets(dry_run=args.dry_run)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Uploaded: {results['uploaded']}")
    print(f"  Skipped:  {results['skipped']}")
    print(f"  Errors:   {len(results['errors'])}")
    if results["errors"]:
        for err in results["errors"]:
            print(f"    - {err}")

    if args.dry_run:
        print("\n💡 Run without --dry-run to perform actual ingestion")

    sys.exit(0 if not results["errors"] else 1)


if __name__ == "__main__":
    main()