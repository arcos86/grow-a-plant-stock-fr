#!/usr/bin/env python3
"""Check verified stock ages and add new, unique verified snapshots to history.
No Roblox scraping, no invented stock readings, no credential handling.
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'stocks.json'
STATUS = ROOT / 'stocks_status.json'
HISTORY = ROOT / 'stocks_history.json'
STALE_AFTER = timedelta(minutes=20)
VALID_ITEMS = (
    'Void Seed Pack', 'Celestial Seed Pack', 'Spooky Seed Pack',
    'Inferno Egg', 'Solar Egg', 'Sealed Eye Egg', 'Abyss Egg',
)

def load_json(path, default):
    if not path.exists():
        return default
    with path.open(encoding='utf-8') as f:
        return json.load(f)

def parse_utc(text):
    if not isinstance(text, str):
        return None
    try:
        dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except ValueError:
        return None

def write_if_changed(path, obj):
    content = json.dumps(obj, ensure_ascii=False, indent=2) + '\n'
    if path.exists() and path.read_text(encoding='utf-8') == content:
        return False
    path.write_text(content, encoding='utf-8')
    return True

def main():
    now = datetime.now(timezone.utc)
    data = load_json(SOURCE, {})
    items = data.get('items', {}) if isinstance(data, dict) else {}
    if not isinstance(items, dict):
        items = {}
    hist = load_json(HISTORY, {'records': []})
    if not isinstance(hist, dict) or not isinstance(hist.get('records'), list):
        raise ValueError('Invalid stocks_history.json format')
    records = hist['records']
    known = {(r.get('item'), r.get('verified_at'), r.get('stock'))
             for r in records if isinstance(r, dict)}
    out = {}
    new_count = 0
    for name in VALID_ITEMS:
        entry = items.get(name, {})
        if not isinstance(entry, dict):
            entry = {}
        quantity = entry.get('stock')
        verified_at = entry.get('verified_at')
        source = entry.get('source')
        dt = parse_utc(verified_at)
        verified = (type(quantity) is int and quantity >= 0 and dt is not None
                    and dt <= now + timedelta(minutes=2)
                    and source == 'capture_validee_manuellement')
        # Public status never promotes a stale/unknown value to a live stock.
        freshness = 'non_verifie'
        if verified:
            freshness = 'recent' if now - dt <= STALE_AFTER else 'ancien'
            key = (name, verified_at, quantity)
            if key not in known:
                records.append({'item': name, 'stock': quantity,
                                'verified_at': verified_at, 'source': source})
                known.add(key)
                new_count += 1
        out[name] = {'status': freshness,
                     'verified_at': verified_at if verified else None}
    write_if_changed(STATUS, {'game': 'Grow a Plant',
                              'live': False,
                              'stale_after_minutes': int(STALE_AFTER.total_seconds() // 60),
                              'items': out})
    # Save history only on genuinely new confirmed snapshots.
    write_if_changed(HISTORY, {'records': records})
    print(f'Checked {len(VALID_ITEMS)} objects; {new_count} new verified records. No Roblox data fetched.')

if __name__ == '__main__':
    main()
