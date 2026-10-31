# 🎮 Game Market Intelligence

Auto-scanner for top mobile game charts — Google Play + App Store.

Chạy tự động **Thứ 2 + Thứ 5 lúc 8:30 sáng ICT** via GitHub Actions.

## Cấu trúc

```
├── market_scanner.py          # Scraper chính
├── data/
│   ├── latest.json            # Scan mới nhất
│   └── scan_YYYY-MM-DD.json   # Lịch sử từng ngày
└── .github/workflows/
    └── market_scan.yml        # Cron job config
```

## Data format (`data/latest.json`)

```json
{
  "scan_date": "2026-11-03",
  "total_games": 420,
  "games": [
    {
      "rank": 1,
      "store": "appstore",
      "country": "us",
      "title": "Sand Blocks",
      "developer": "Voodoo",
      "origin_country": "🇫🇷 France",
      "genre_tags": ["Puzzle", "Hyper-casual"],
      "icon_url": "...",
      "screenshots": [...],
      "rating": 4.5
    }
  ]
}
```

## Sources

- **App Store**: iTunes RSS feed (free, no API key) — US, VN, GB top 100
- **Google Play**: `gplay-scraper` library (free, no API key) — GAME, PUZZLE, CASUAL, ARCADE top 100

## Manual run

```bash
pip install gplay-scraper
python market_scanner.py
```
