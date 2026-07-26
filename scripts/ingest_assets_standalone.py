#!/usr/bin/env python3
"""
Standalone BrightBean Asset Ingestion Script

Uploads assets directly to Cloudflare R2 using boto3 (no Django required).
Creates a manifest JSON for later MediaAsset creation via API/UI.

Usage:
    export S3_ENDPOINT_URL="https://<account-id>.r2.cloudflarestorage.com"
    export S3_ACCESS_KEY_ID="<your-access-key>"
    export S3_SECRET_ACCESS_KEY="<your-secret-key>"
    export S3_BUCKET_NAME="brightbean-assets"
    export S3_REGION_NAME="auto"

    python scripts/ingest_assets_standalone.py --dry-run   # Preview
    python scripts/ingest_assets_standalone.py              # Actual upload
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, asdict

try:
    import boto3
    from botocore.config import Config
except ImportError:
    print("❌ boto3 not installed. Run: pip install boto3")
    sys.exit(1)


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


@dataclass
class AssetRecord:
    """Record of an uploaded asset for manifest."""
    filename: str
    title: str
    project: str
    asset_type: str
    sha256: str
    file_size: int
    r2_key: str
    r2_url: str
    mime_type: str


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
                if filepath.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".webm"}:
                    assets.append({
                        "path": filepath,
                        "filename": filepath.name,
                        "relative_path": filepath.relative_to(src_dir),
                    })
    return assets


def get_s3_client():
    """Create S3 client for R2."""
    endpoint = os.environ.get("S3_ENDPOINT_URL")
    access_key = os.environ.get("S3_ACCESS_KEY_ID")
    secret_key = os.environ.get("S3_SECRET_ACCESS_KEY")
    region = os.environ.get("S3_REGION_NAME", "auto")

    if not all([endpoint, access_key, secret_key]):
        print("❌ Missing R2 credentials. Set these environment variables:")
        print("   S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com")
        print("   S3_ACCESS_KEY_ID=<your-access-key>")
        print("   S3_SECRET_ACCESS_KEY=<your-secret-key>")
        print("   S3_BUCKET_NAME=brightbean-assets")
        print("   S3_REGION_NAME=auto")
        sys.exit(1)

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=Config(signature_version="s3v4"),
    )


def ingest_assets(dry_run: bool = False) -> Dict:
    """Upload assets to R2 and create manifest."""
    # Validate credentials
    bucket = os.environ.get("S3_BUCKET_NAME", "brightbean-assets")
    s3 = get_s3_client()

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
    manifest = []

    for asset in unique_assets:
        metadata = ASSET_METADATA.get(asset["filename"], {})
        title = metadata.get("title", asset["filename"])
        project = metadata.get("project", "general")
        asset_type = metadata.get("type", "image" if asset["filename"].endswith((".png", ".jpg", ".jpeg", ".webp")) else "video")

        r2_key = f"assets/{project}/{asset['sha256'][:8]}/{asset['filename']}"
        r2_url = f"{os.environ['S3_ENDPOINT_URL']}/{bucket}/{r2_key}"
        file_size = asset["path"].stat().st_size
        mime_type = "video/mp4" if asset_type == "video" else "image/png"

        print(f"  📤 Uploading: {asset['filename']} ({title})")

        if dry_run:
            print(f"     [DRY RUN] Would upload to R2: {r2_key}")
            results["uploaded"] += 1
            manifest.append(AssetRecord(
                filename=asset["filename"],
                title=title,
                project=project,
                asset_type=asset_type,
                sha256=asset["sha256"],
                file_size=file_size,
                r2_key=r2_key,
                r2_url=r2_url,
                mime_type=mime_type,
            ))
            continue

        try:
            # Upload to R2
            with open(asset["path"], "rb") as f:
                s3.upload_fileobj(
                    f,
                    bucket,
                    r2_key,
                    ExtraArgs={"ContentType": mime_type}
                )

            print(f"     ✅ Uploaded to R2: {r2_key}")

            record = AssetRecord(
                filename=asset["filename"],
                title=title,
                project=project,
                asset_type=asset_type,
                sha256=asset["sha256"],
                file_size=file_size,
                r2_key=r2_key,
                r2_url=r2_url,
                mime_type=mime_type,
            )
            manifest.append(record)
            results["uploaded"] += 1

        except Exception as e:
            error_msg = f"Failed to upload {asset['filename']}: {e}"
            print(f"     ❌ {error_msg}")
            results["errors"].append(error_msg)

    # Save manifest
    manifest_path = Path("asset_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump([asdict(r) for r in manifest], f, indent=2)
    print(f"\n📋 Manifest saved to: {manifest_path}")

    return results, manifest


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Upload assets to Cloudflare R2")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    args = parser.parse_args()

    print("=" * 60)
    print("BrightBean Asset Ingestion (Standalone R2 Upload)")
    print("=" * 60)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()

    results, manifest = ingest_assets(dry_run=args.dry_run)

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
        print("\n💡 Run without --dry-run to perform actual upload")
        print("📋 After upload, use the manifest to create MediaAsset records via:")
        print("   - BrightBean API: POST /api/v1/media")
        print("   - Django admin: /admin/media_library/mediaasset/")
        print("   - BrightBean UI: Media Library → Add")

    sys.exit(0 if not results["errors"] else 1)


if __name__ == "__main__":
    main()