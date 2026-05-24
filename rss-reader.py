#!/usr/bin/env python3
"""
rss-reader.py — CLI RSS/Atom feed reader

Fetch and display RSS/Atom feeds with clean terminal formatting.
Supports multiple feeds, filtering, and export options.

Usage:
    python rss-reader.py <feed_url>
    python rss-reader.py <feed_url> --count 10
    python rss-reader.py <feed_url> --json
    python rss-reader.py <feed_url> --summary
    python rss-reader.py --add <feed_url> <name>  # Save feed
    python rss-reader.py --list                   # List saved feeds
    python rss-reader.py --all                    # Read all saved feeds

Support: https://github.com/yourusername/rss-reader
"""

import sys
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.request import urlopen, Request
from pathlib import Path
import re

FEEDS_FILE = Path.home() / ".rss-reader-feeds.json"
MAX_ITEMS = 20


def fetch_feed(url):
    """Fetch and parse RSS/Atom feed"""
    req = Request(url, headers={"User-Agent": "rss-reader/1.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            
            try:
                root = ET.fromstring(content)
            except ET.ParseError:
                return {"error": "Failed to parse XML"}
            
            # Handle both RSS and Atom
            items = []
            
            # RSS 2.0
            channel = root.find('.//channel')
            if channel is not None:
                feed_title = channel.find('title')
                title = feed_title.text if feed_title is not None else "Unknown"
                
                for item in channel.findall('item'):
                    pub_date = item.find('pubDate')
                    pub = pub_date.text if pub_date is not None else ""
                    items.append({
                        'title': item.findtext('title', 'No title'),
                        'link': item.findtext('link', ''),
                        'pub_date': pub,
                        'description': item.findtext('description', '')[:200],
                    })
            
            # Atom
            else:
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                feed = root.find('atom:feed', ns)
                if feed is not None:
                    title = feed.findtext('atom:title', 'Unknown', ns)
                    
                    for entry in feed.findall('atom:entry', ns):
                        updated = entry.findtext('atom:updated', '', ns)
                        if updated:
                            # Clean up ISO date
                            updated = updated[:10]
                        items.append({
                            'title': entry.findtext('atom:title', 'No title', ns),
                            'link': entry.findtext('.//atom:{http://www.w3.org/2005/Atom}link[@rel="alternate"]/@href', ''),
                            'pub_date': updated,
                            'description': entry.findtext('atom:summary', '', ns)[:200],
                        })
            
            return {
                'title': title,
                'items': items[:MAX_ITEMS]
            }
            
    except Exception as e:
        return {"error": str(e)}


def display_feed(data, count=MAX_ITEMS, summary=False):
    """Display feed items"""
    if "error" in data:
        print(f"❌ Error: {data['error']}\n")
        return
    
    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║           📰 {data['title']:<52} ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝")
    print(f"  Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    items = data['items'][:count]
    
    for i, item in enumerate(items, 1):
        print(f"  [{i:>2}] {item['title']}")
        if item['pub_date']:
            print(f"      📅 {item['pub_date']}")
        if item['link']:
            print(f"      🔗 {item['link']}")
        if not summary and item['description']:
            # Clean up HTML tags
            desc = re.sub(r'<[^>]+>', '', item['description'])
            print(f"      {desc[:100]}...")
        print()
    
    print(f"  📦 Source: https://github.com/yourusername/rss-reader\n")


def display_json(data):
    """Output as JSON"""
    print(json.dumps(data, indent=2))


def save_feed(url, name):
    """Save feed to config"""
    feeds = load_feeds()
    feeds[name] = url
    with open(FEEDS_FILE, 'w') as f:
        json.dump(feeds, f, indent=2)
    print(f"✅ Saved {name} → {url}")


def load_feeds():
    """Load saved feeds"""
    if FEEDS_FILE.exists():
        with open(FEEDS_FILE) as f:
            return json.load(f)
    return {}


def main():
    args = sys.argv[1:]
    
    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return
    
    # Parse arguments
    flags = []
    urls = []
    i = 0
    while i < len(args):
        if args[i].startswith('--'):
            flags.append(args[i][2:])
            if args[i] in ('--add', '--count'):
                if i + 1 < len(args):
                    i += 1
                    if args[i] not in ('--' + f for f in flags):
                        urls.append(args[i])
        else:
            urls.append(args[i])
        i += 1
    
    if 'add' in flags and len(urls) >= 2:
        save_feed(urls[0], urls[1])
        return
    
    if 'list' in flags:
        feeds = load_feeds()
        if feeds:
            print("\n  Saved Feeds:")
            for name, url in feeds.items():
                print(f"  • {name}: {url}")
        else:
            print("  No feeds saved. Use --add <url> <name> to add feeds.")
        return
    
    if 'all' in flags:
        feeds = load_feeds()
        for name, url in feeds.items():
            data = fetch_feed(url)
            display_feed(data)
        return
    
    if urls:
        for url in urls:
            data = fetch_feed(url)
            count = int(args[args.index('--count') + 1]) if 'count' in flags else MAX_ITEMS
            display_feed(data, count, 'summary' in flags)
    else:
        print("❌ No feed URL provided\n")


if __name__ == "__main__":
    main()
