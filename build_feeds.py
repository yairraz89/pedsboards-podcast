#!/usr/bin/env python3
"""Build private podcast RSS feeds for the Peds Boards episodes.

Episodes are hosted as GitHub release assets (one release per language);
the feeds and cover art are served by GitHub Pages from docs/.

Usage: python3 build_feeds.py [--stage DIR]
  --stage DIR  also create DIR/<lang>/<asset>.mp3 symlinks to the originals,
               named the way they will be uploaded.
"""
import argparse
import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

SRC = "/Users/yairraz/Music/PedsBoards"
OWNER = "yairraz89"
REPO = "pedsboards-podcast"
PAGES = f"https://{OWNER}.github.io/{REPO}"
RELEASES = f"https://github.com/{OWNER}/{REPO}/releases/download"

SHOWS = {
    "en": {
        "m3u": "Peds Boards - English.m3u",
        "title": "Peds Boards (English)",
        "language": "en",
        "description": "Pediatrics board review, chapter by chapter. Private feed.",
    },
    "he": {
        "m3u": "Peds Boards - Hebrew.m3u",
        "title": "Peds Boards (עברית)",
        "language": "he",
        "description": "חזרה לבחינת הבורד ברפואת ילדים, פרק אחר פרק. פיד פרטי.",
    },
}

BASE_DATE = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
HERE = os.path.dirname(os.path.abspath(__file__))


def load_keywords():
    """Read keywords/*.txt -> ({topic: hebrew_topic}, {(topic, num): (en_kw, he_kw)}).

    Line format: '@Topic|Hebrew topic' starts a topic; 'NN|Hebrew title|en kw|he kw'
    is an episode. The Hebrew episode title column is kept for reference only:
    feed titles use the Hebrew topic name plus the English episode title.
    """
    topics, kws = {}, {}
    kdir = os.path.join(HERE, "keywords")
    for name in sorted(os.listdir(kdir)):
        if not name.endswith(".txt"):
            continue
        topic = None
        for n, line in enumerate(open(os.path.join(kdir, name), encoding="utf-8"), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if line.startswith("@"):
                topic = parts[0][1:]
                topics[topic] = parts[1]
            else:
                assert len(parts) == 4, f"{name}:{n}: expected 4 fields"
                kws[(topic, int(parts[0]))] = (parts[2].strip(), parts[3].strip())
    return topics, kws


TOPIC_HE, KEYWORDS = load_keywords()


def read_playlist(lang):
    """Return [(relpath, title, seconds)] in playlist order."""
    path = os.path.join(SRC, SHOWS[lang]["m3u"])
    items, pending = [], None
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        m = re.match(r"#EXTINF:(\d+),(.*)", line)
        if m:
            pending = (int(m.group(1)), m.group(2))
        elif line and not line.startswith("#"):
            secs, title = pending
            items.append((line, title, secs))
            pending = None
    return items


def hms(secs):
    return f"{secs // 3600}:{secs % 3600 // 60:02d}:{secs % 60:02d}"


def build(lang, stage):
    show = SHOWS[lang]
    episodes = read_playlist(lang)
    topics = []  # topic folder names in playlist order -> season numbers
    out = []
    for i, (rel, title, secs) in enumerate(episodes, 1):
        topic = rel.split("/")[1]
        if topic not in topics:
            topics.append(topic)
        season = topics.index(topic) + 1
        num = int(re.match(r"(\d+)", os.path.basename(rel)).group(1))
        asset = f"{lang}-{i:03d}.mp3"
        full = os.path.join(SRC, rel)
        size = os.path.getsize(full)
        if stage:
            d = os.path.join(stage, lang)
            os.makedirs(d, exist_ok=True)
            link = os.path.join(d, asset)
            if os.path.lexists(link):
                os.remove(link)
            os.symlink(full, link)
        pub = BASE_DATE + timedelta(hours=i)  # first episode is the oldest
        en_kw, he_kw = KEYWORDS[(topic, num)]
        topic_he = TOPIC_HE[topic]
        if lang == "he":
            ep_title = f"{topic_he} {num:02d} - {title}"
            desc = (f"{topic_he}, פרק {num}: {title}\n\n"
                    f"מילות חיפוש: {topic_he}, {he_kw}\n"
                    f"Keywords: {topic}, {en_kw}")
        else:
            ep_title = f"{topic} {num:02d}: {title}"
            desc = (f"{topic}, episode {num}: {title}\n\n"
                    f"Keywords: {topic}, {en_kw}\n"
                    f"מילות חיפוש: {topic_he}, {he_kw}")
        out.append(
            f"""    <item>
      <title>{escape(ep_title)}</title>
      <description>{escape(desc)}</description>
      <itunes:summary>{escape(desc)}</itunes:summary>
      <enclosure url="{RELEASES}/{lang}/{asset}" length="{size}" type="audio/mpeg"/>
      <guid isPermaLink="false">pedsboards-{asset}</guid>
      <pubDate>{format_datetime(pub)}</pubDate>
      <itunes:duration>{hms(secs)}</itunes:duration>
      <itunes:season>{season}</itunes:season>
      <itunes:episode>{num}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
    </item>"""
        )

    cover = f"{PAGES}/cover-{lang}.png"
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:googleplay="http://www.google.com/schemas/play-podcasts/1.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(show["title"])}</title>
    <link>{PAGES}/</link>
    <atom:link href="{PAGES}/{lang}.xml" rel="self" type="application/rss+xml"/>
    <description>{escape(show["description"])}</description>
    <language>{show["language"]}</language>
    <itunes:author>Peds Boards</itunes:author>
    <itunes:image href="{cover}"/>
    <image><url>{cover}</url><title>{escape(show["title"])}</title><link>{PAGES}/</link></image>
    <itunes:category text="Health &amp; Fitness"><itunes:category text="Medicine"/></itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>serial</itunes:type>
    <itunes:block>Yes</itunes:block>
    <googleplay:block>yes</googleplay:block>
{chr(10).join(out)}
  </channel>
</rss>
"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", f"{lang}.xml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(feed)
    print(f"{lang}: {len(episodes)} episodes, {len(topics)} topics -> {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage")
    args = ap.parse_args()
    for lang in SHOWS:
        build(lang, args.stage)
