#!/usr/bin/env python3
"""
Game Market Intelligence Scanner
Scrapes Google Play + App Store top charts for Puzzle/Casual/Hyper-casual games
Outputs structured JSON to data/scan_YYYY-MM-DD.json
"""

import json
import time
import datetime
import os
import re
from pathlib import Path

# ── Apple App Store (iTunes RSS, no API key needed) ──────────────────────────

ITUNES_GENRES = {
    "Games":           6014,
    "Puzzle":          7012,
    "Casual":          7003,
    "Family":          6016,
}

ITUNES_COUNTRIES = ["us", "gb", "vn", "br", "de", "fr", "jp", "kr"]

def fetch_appstore_top(country="us", genre_id=6014, limit=100):
    """Fetch top free games from iTunes RSS feed."""
    import urllib.request
    url = f"https://itunes.apple.com/{country}/rss/topfreeapplications/limit={limit}/genre={genre_id}/json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        entries = data.get("feed", {}).get("entry", [])
        results = []
        for i, entry in enumerate(entries):
            app_id = entry.get("id", {}).get("attributes", {}).get("im:id", "")
            name = entry.get("im:name", {}).get("label", "")
            developer = entry.get("im:artist", {}).get("label", "")
            category = entry.get("category", {}).get("attributes", {}).get("label", "")
            icon_urls = entry.get("im:image", [])
            icon = icon_urls[-1].get("label", "") if icon_urls else ""
            # Icon → higher res
            icon = icon.replace("53x53", "512x512").replace("100x100", "512x512")
            bundle = entry.get("id", {}).get("label", "")

            results.append({
                "rank": i + 1,
                "store": "appstore",
                "country": country,
                "app_id": app_id,
                "bundle_id": bundle,
                "title": name,
                "developer": developer,
                "category": category,
                "icon_url": icon,
                "rating": None,
                "installs": None,
                "screenshots": [],
                "origin_country": infer_origin(developer, bundle),
                "genre_tags": classify_genre(name, category, ""),
            })
        return results
    except Exception as e:
        print(f"  ✗ AppStore {country}/{genre_id}: {e}")
        return []


# ── Google Play (gplay-scraper) ───────────────────────────────────────────────

GPLAY_CATEGORIES = [
    ("GAME", "TOP_FREE"),
    ("GAME_PUZZLE", "TOP_FREE"),
    ("GAME_CASUAL", "TOP_FREE"),
    ("GAME_ARCADE", "TOP_FREE"),
]

GPLAY_FIELDS = [
    "title", "appId", "developer", "developerId", "genre",
    "score", "ratings", "installs", "icon", "screenshots",
    "summary", "description",
]

def fetch_gplay_top(category="GAME", collection="TOP_FREE", country="us", count=100):
    """Fetch top games from Google Play via gplay-scraper."""
    try:
        from gplay_scraper import GPlayScraper
        scraper = GPlayScraper()
        results_raw = scraper.list_get_fields(
            collection,
            GPLAY_FIELDS,
            category=category,
            count=count,
            lang="en",
            country=country,
        )
        results = []
        for i, app in enumerate(results_raw):
            screenshots = app.get("screenshots", []) or []
            results.append({
                "rank": i + 1,
                "store": "gplay",
                "country": country,
                "app_id": app.get("appId", ""),
                "bundle_id": app.get("appId", ""),
                "title": app.get("title", ""),
                "developer": app.get("developer", ""),
                "category": app.get("genre", ""),
                "icon_url": app.get("icon", ""),
                "rating": app.get("score"),
                "installs": app.get("installs"),
                "screenshots": screenshots[:5],
                "origin_country": infer_origin(
                    app.get("developer", ""),
                    app.get("appId", ""),
                    app.get("developerId", ""),
                ),
                "genre_tags": classify_genre(
                    app.get("title", ""),
                    app.get("genre", ""),
                    app.get("description", "") or app.get("summary", ""),
                ),
            })
        return results
    except ImportError:
        print("  ✗ gplay-scraper not installed — pip install gplay-scraper")
        return []
    except Exception as e:
        print(f"  ✗ GPlay {category}/{collection}/{country}: {e}")
        return []


# ── Origin country inference ──────────────────────────────────────────────────

DEVELOPER_ORIGIN_MAP = {
    # Publisher → Country
    "voodoo": "🇫🇷 France",
    "kwalee": "🇬🇧 UK",
    "supersonic": "🇮🇱 Israel",
    "lion studios": "🇺🇸 USA",
    "lion studio": "🇺🇸 USA",
    "rollic": "🇹🇷 Turkey",
    "dreamgames": "🇹🇷 Turkey",
    "dream games": "🇹🇷 Turkey",
    "gram games": "🇹🇷 Turkey",
    "zynga": "🇺🇸 USA",
    "scopely": "🇺🇸 USA",
    "king": "🇬🇧 UK",
    "imangi": "🇺🇸 USA",
    "outfit7": "🇸🇮 Slovenia",
    "miniclip": "🇨🇭 Switzerland",
    "playtika": "🇮🇱 Israel",
    "crazy labs": "🇮🇱 Israel",
    "crazylabs": "🇮🇱 Israel",
    "kolibri games": "🇩🇪 Germany",
    "goodgame studios": "🇩🇪 Germany",
    "habby": "🇸🇬 Singapore",
    "crunchyroll": "🇺🇸 USA",
    "netease": "🇨🇳 China",
    "tencent": "🇨🇳 China",
    "moonton": "🇨🇳 China",
    "mixi": "🇯🇵 Japan",
    "colopl": "🇯🇵 Japan",
    "gungho": "🇯🇵 Japan",
    "com2us": "🇰🇷 Korea",
    "nc soft": "🇰🇷 Korea",
    "ncsoft": "🇰🇷 Korea",
    "krafton": "🇰🇷 Korea",
    "nexon": "🇰🇷 Korea",
    "vng": "🇻🇳 Vietnam",
    "amanotes": "🇻🇳 Vietnam",
    "gameduell": "🇩🇪 Germany",
    "playgendary": "🇩🇪 Germany",
    "hypercell": "🇫🇷 France",
    "madbox": "🇫🇷 France",
    "homa": "🇫🇷 France",
    "greenpanda": "🇫🇷 France",
    "lessmore": "🇭🇺 Hungary",
    "tactile games": "🇩🇰 Denmark",
    "sybo": "🇩🇰 Denmark",
    "noodlecake": "🇨🇦 Canada",
    "roblox": "🇺🇸 USA",
    "big fish": "🇺🇸 USA",
    "kabam": "🇺🇸 USA",
    "plarium": "🇮🇱 Israel",
    "ironhide": "🇺🇾 Uruguay",
}

BUNDLE_PREFIX_ORIGIN = {
    "com.voodoo": "🇫🇷 France",
    "com.supersonic": "🇮🇱 Israel",
    "com.crazylabs": "🇮🇱 Israel",
    "com.plarium": "🇮🇱 Israel",
    "com.rollic": "🇹🇷 Turkey",
    "com.dreamgames": "🇹🇷 Turkey",
    "com.gramgames": "🇹🇷 Turkey",
    "com.habby": "🇸🇬 Singapore",
    "com.netease": "🇨🇳 China",
    "com.tencent": "🇨🇳 China",
    "com.miHoYo": "🇨🇳 China",
    "com.vng": "🇻🇳 Vietnam",
    "com.amanotes": "🇻🇳 Vietnam",
    "com.noodlecake": "🇨🇦 Canada",
    "games.kwalee": "🇬🇧 UK",
    "com.kwalee": "🇬🇧 UK",
    "com.king": "🇬🇧 UK",
    "com.miniclip": "🇨🇭 Switzerland",
    "com.kolibrigames": "🇩🇪 Germany",
    "com.goodgamestudios": "🇩🇪 Germany",
    "com.zynga": "🇺🇸 USA",
    "com.scopely": "🇺🇸 USA",
    "com.roblox": "🇺🇸 USA",
    "com.lionStudios": "🇺🇸 USA",
    "air.com.lion": "🇺🇸 USA",
}

def infer_origin(developer="", bundle_id="", developer_id=""):
    """Infer country of origin from developer name and bundle ID."""
    dev_lower = developer.lower()
    for key, country in DEVELOPER_ORIGIN_MAP.items():
        if key in dev_lower:
            return country
    bundle_lower = bundle_id.lower()
    for prefix, country in BUNDLE_PREFIX_ORIGIN.items():
        if bundle_lower.startswith(prefix.lower()):
            return country
    return "🌍 Unknown"


# ── Genre classification ──────────────────────────────────────────────────────

GENRE_KEYWORDS = {
    "Hyper-casual": ["hop", "jump", "run", "dash", "shoot", "smash", "hit", "ball", "slice", "cut", "flip", "stack", "drop", "tap", "click", "idle"],
    "Puzzle": ["puzzle", "match", "sort", "merge", "connect", "flow", "pipe", "block", "tile", "word", "sudoku", "jigsaw", "brain", "logic", "unscrew", "bolt", "sand", "color"],
    "Casual": ["farm", "cafe", "cook", "bake", "dress", "decor", "home", "design", "pet", "garden", "story", "adventure", "build", "craft", "manage"],
    "Simulation": ["sim", "tycoon", "factory", "truck", "drive", "park", "city", "build", "construct", "warehouse", "loader", "conveyor"],
    "Action": ["battle", "fight", "war", "shoot", "gun", "sword", "hero", "clash", "strike", "attack", "defend"],
    "Strategy": ["strategy", "tower", "defense", "base", "kingdom", "empire", "clan", "squad", "deploy"],
    "Sports": ["soccer", "football", "basketball", "tennis", "golf", "racing", "race", "car", "bike"],
}

def classify_genre(title="", category="", description=""):
    """Classify game into genre tags based on title + description keywords."""
    text = f"{title} {category} {description}".lower()
    tags = []
    for genre, keywords in GENRE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            tags.append(genre)
    if not tags:
        tags = ["Casual"]
    return tags[:3]  # max 3 tags


# ── Dedup & merge ─────────────────────────────────────────────────────────────

def dedup_games(games):
    """Deduplicate by bundle_id, keeping first occurrence (highest rank)."""
    seen = set()
    out = []
    for g in games:
        key = g["bundle_id"].lower() or g["title"].lower()
        if key and key not in seen:
            seen.add(key)
            out.append(g)
    return out


# ── Main scan ─────────────────────────────────────────────────────────────────

def run_scan():
    today = datetime.date.today().isoformat()
    print(f"\n🎮 Game Market Scanner — {today}")
    print("=" * 50)

    all_games = []

    # App Store — US + VN top games
    for country in ["us", "vn", "gb"]:
        print(f"\n📱 App Store [{country.upper()}] top 100 games...")
        games = fetch_appstore_top(country=country, genre_id=6014, limit=100)
        print(f"   → {len(games)} games fetched")
        all_games.extend(games)
        time.sleep(1)

    # Google Play — multiple categories
    for (category, collection) in GPLAY_CATEGORIES:
        print(f"\n🤖 Google Play [{category}]...")
        games = fetch_gplay_top(category=category, collection=collection, country="us", count=100)
        print(f"   → {len(games)} games fetched")
        all_games.extend(games)
        time.sleep(2)

    print(f"\n✅ Total raw: {len(all_games)} entries")
    deduped = dedup_games(all_games)
    print(f"✅ After dedup: {len(deduped)} unique games")

    # Sort by rank within each store
    output = {
        "scan_date": today,
        "scan_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "total_games": len(deduped),
        "games": deduped,
        "metadata": {
            "sources": ["appstore_us", "appstore_vn", "appstore_gb", "gplay_game", "gplay_puzzle", "gplay_casual", "gplay_arcade"],
            "scanner_version": "1.0.0",
        }
    }

    # Save to data/
    Path("data").mkdir(exist_ok=True)
    out_path = f"data/scan_{today}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Saved → {out_path}")
    print(f"   {len(deduped)} games, {os.path.getsize(out_path) // 1024} KB")

    # Also write latest.json for easy access
    with open("data/latest.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"   Also saved → data/latest.json")

    return out_path


if __name__ == "__main__":
    run_scan()
