# BrightBean Social Readiness — Plants and Chairs

Re-derived 2026-07-18 (kimi) after the original file was lost. Sources: ingestion script
`scripts/ingest_assets.py` (branch `fix-brightbean-llms-setup`), live filesystem audit, and a
full Airtable DAM scan (base `appjU8WwLSSaSNJxC`, table `🎞 Digital assets`).

## 1. Verified source directories (live audit 2026-07-18)

| Directory | Media files |
|---|---|
| `agency-os/output/social-ready-2026-06-25/feed` | 26 |
| `agency-os/output/content-pool-2026-06-23` | 255 (incl. `reels/` with the 2 mp4s) |
| `~/Downloads/pac_store-ites_3d/item_1` | 142 |
| `agency-os/reels` | 0 (empty; reels live in content-pool) |

All 30 files mapped in `ASSET_METADATA` are present on disk (30/30). The two mp4s were
found at `content-pool-2026-06-23/reels/`, not `agency-os/reels/`.

## 2. DAM audit (Airtable, 2026-07-18)

- 2,120 total records. 936 have valid local paths, 114 point to missing files, 1,070 have
  no Local Path at all.
- Valid by project: UNIVERZE 358, PNC-MERCH 198, PC-1985 60, PC-WFF 56, PC-007B 31,
  PC-FLEA 30.
- Missing by project: PNC 53, PC-1985 15, SJB-EXPLORER 12, PC-SEAVITA 9.
- Full dump: `/tmp/dam_audit.json` (regenerate via the Airtable API when needed).

## 3. Ingestion candidate set (30 files, all verified present)

- Hero photos: `IMG_1761.png` (Plants Over Chairs hero), `IMG_1634.png` (Plants and Jeeps
  hero), both in `pac_store-ites_3d/item_1`.
- Reels: `new-01-screenprint-process.mp4` (screen-print process),
  `new-03-beach-lifestyle.mp4` (studio/place), both in `content-pool-2026-06-23/reels/`.
- Social-ready feed set (26 PNGs in `social-ready-2026-06-25/feed`): s01-s10 heroes and
  grids, v2 series (stone, payasotee, vanlife, dotcap, barlogo), v3 cards (petstore,
  productos, mialma, scatter pink), post-2..5 (flowers, vanlife royal, payaso tote,
  beanie), cap-dir3 streetwear, cap-dir4 AR.

Runbook: `python scripts/ingest_assets.py --dry-run` first, then real run. The script
dedupes by SHA-256, uploads to R2 via Django storage, and creates MediaAsset rows.
**Blocker before any run: rotate the exposed R2 credentials, then set the new pair as Fly
secrets (`S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`).**

## 4. Eight-post draft calendar (drafts only; nothing posts without Eric)

Cadence Tue/Fri, starting after accounts connect. All copy is placeholder direction for
the brand check, not final copy.

| # | Date | Asset | Format | Direction |
|---|------|-------|--------|-----------|
| 1 | Tue 2026-07-21 | `s01-iconic-hero.png` | IG feed | Iconic cap hero. Re-introduce the drop. |
| 2 | Fri 2026-07-24 | `new-01-screenprint-process.mp4` | Reel | Process video: screen-print behind the scenes. |
| 3 | Tue 2026-07-28 | `v2-01-stone-hero.png` | IG feed | Stone colorway hero. |
| 4 | Fri 2026-07-31 | `s06-iconic-grid2.png` | IG feed | Grid/detail post. |
| 5 | Tue 2026-08-04 | `v2-02-payasotee.png` | IG feed | Payaso tee graphic feature. |
| 6 | Fri 2026-08-07 | `new-03-beach-lifestyle.mp4` | Reel | Lifestyle/place reel. |
| 7 | Tue 2026-08-11 | `cap-dir3-streetwear-post.png` | IG feed | Streetwear styling post. |
| 8 | Fri 2026-08-14 | `s08-scatter-sky.png` | IG feed | Scatter print, soft closer for the run. |

Crosspost: once Bluesky/Mastodon are connected, mirror 1, 3, 5, 7 as stills. Captions go
through the QA/brand gate and Eric approval before scheduling.

## 5. Account connection status (2026-07-18)

- Instagram: blocked at Meta SMS 2FA in the token-generation step (PAC-337, needs Eric).
  App credentials (`PLATFORM_INSTAGRAM_APP_ID/SECRET`) are set as Fly secrets.
- Bluesky: no account yet. Needs studio handle + App Password (agent connects it).
- Mastodon: no instance/account yet.
- LinkedIn, Pinterest, TikTok, Google/YouTube: app credentials exist in
  `brightbean-studio/.env`; each still needs its OAuth grant flow.
- R2/S3: Fly secrets present but the pair is exposed; rotate before uploads.
