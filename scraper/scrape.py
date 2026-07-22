#!/usr/bin/env python3
"""
Dhaw ضو — Scraper des annonces de coupures STEG.

La STEG publie ses communiqués de délestage sur son site et sa page Facebook ;
les médias tunisiens les relaient en quelques minutes via leurs flux RSS.
Ce script :
  1. lit les flux RSS des principaux médias tunisiens,
  2. filtre les articles "coupure / délestage / STEG",
  3. télécharge chaque article et en extrait horaires + localités,
  4. fait correspondre les localités aux 264 délégations,
  5. fusionne avec data/annonces.json (dédoublonné, 48 h glissantes).

Exécuté toutes les 10 min par GitHub Actions (.github/workflows/scrape.yml).
"""

from __future__ import annotations
import json, re, sys, unicodedata, html
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import feedparser
from bs4 import BeautifulSoup

TZ = ZoneInfo("Africa/Tunis")
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "annonces.json"

UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/126.0.0.0 Safari/537.36"),
      "Accept-Language": "fr-FR,fr;q=0.9,ar;q=0.8"}
TIMEOUT = 20

# ---------------------------------------------------------------- sources RSS
FEEDS = [
    ("Webdo",            "https://www.webdo.tn/fr/rss"),
    ("La Presse",        "https://lapresse.tn/feed/"),
    ("Gnet",             "https://news.gnet.tn/feed/"),
    ("Business News",    "https://www.businessnews.com.tn/rss.xml"),
    ("Tunisie Tribune",  "https://www.tunisie-tribune.com/feed/"),
    ("L'Economiste Maghrébin", "https://www.leconomistemaghrebin.com/feed/"),
]

KW_MUST = re.compile(r"steg|électricité|electricite|courant", re.I)
KW_CUT  = re.compile(r"coupure|délestage|delestage|interruption", re.I)

# ------------------------------------------------------- délégations & alias
def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

DELEG = json.loads((DATA / "delegations.json").read_text(encoding="utf-8"))
NAME_IDX = {norm(f["properties"]["fr"]): f["properties"]["id"] for f in DELEG["features"]}

ALIAS = {
    "el kram": "TN11K", "le kram": "TN11K", "kram": "TN11K",
    "la goulette": "TN11J", "goulette": "TN11J",
    "el menzah": "TN118", "menzah": "TN118", "el manar": "TN118",
    "la marsa": "TN11L", "ain zaghouan": "TN11L",
    "jardins de carthage": "TN111", "carthage": "TN111", "le bardo": "TN11A",
    "ksar said": "TN141", "la manouba": "TN141", "manouba": "TN141", "mannouba": "TN141",
    "djedeida": "TN146", "jedaida": "TN146", "jedeida": "TN146",
    "tebourba": "TN147", "sidi thabet": "TN125",
    "ariana": "TN121", "la soukra": "TN122", "soukra": "TN122", "raoued": "TN123",
    "borj louzir": "TN122", "ennasr": "TN121", "cite ettadhamen": "TN126",
    "ettadhamen": "TN126", "mnihla": "TN127", "el mnihla": "TN127",
    "kalaat el andalous": "TN124",
    "soliman": "TN15B", "sliman": "TN15B",
    "grombalia": "TN15E", "grombelia": "TN15E",
    "el haouaria": "TN159", "haouaria": "TN159", "el houaria": "TN159",
    "hammam ghzez": "TN158", "hammam el ghezaz": "TN158", "hammam el guezaz": "TN158",
    "dar chaabane": "TN152", "dar chaabane el fehri": "TN152",
    "beni khiar": "TN153", "el maamoura": "TN153",
    "takelsa": "TN15A", "teklesa": "TN15A",
    "beni khalled": "TN15D", "beni khaled": "TN15D",
    "bou argoub": "TN15F", "bouargoub": "TN15F", "el mida": "TN156",
    "korba": "TN154", "kelibia": "TN157", "menzel temime": "TN155",
    "menzel bouzelfa": "TN15C", "hammamet": "TN15G", "nabeul": "TN151",
    "mrezga": "TN151",
}

# candidats = tous les noms de délégations + alias, triés du plus long au plus court
CANDIDATES = sorted(set(list(NAME_IDX.keys()) + list(ALIAS.keys())),
                    key=len, reverse=True)

def match_zones(text: str) -> tuple[list[str], list[str]]:
    """Retourne (ids de délégations, localités reconnues) trouvés dans le texte."""
    t = " " + norm(text) + " "
    ids, found = [], []
    for cand in CANDIDATES:
        if len(cand) < 4:
            continue
        if f" {cand} " in t or f" {cand}," in t:
            _id = ALIAS.get(cand) or NAME_IDX.get(cand)
            if _id and _id not in ids:
                ids.append(_id)
                found.append(cand)
            t = t.replace(f" {cand} ", " § ")  # évite les doubles comptages
    return ids, found

# ------------------------------------------------------------- extraction
RE_RANGE = re.compile(
    r"(?:de|entre|dès|a partir de|à partir de)?\s*(\d{1,2})\s*h\s*(\d{2})?\s*"
    r"(?:à|a|et|jusqu'à|jusqu'a|->|–|-)\s*(\d{1,2})\s*h\s*(\d{2})?", re.I)

def extract_times(text: str) -> tuple[str | None, str | None]:
    m = RE_RANGE.search(text)
    if not m:
        return None, None
    h1, m1, h2, m2 = m.groups()
    return f"{int(h1):02d}:{m1 or '00'}", f"{int(h2):02d}:{m2 or '00'}"

def article_text(url: str) -> str:
    r = requests.get(url, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    node = soup.find("article") or soup.find("main") or soup.body or soup
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True))

def entry_body(entry) -> str:
    """Texte le plus complet disponible dans le flux RSS lui-même
    (les flux WordPress incluent souvent l'article entier en content:encoded)."""
    parts = []
    for c in entry.get("content", []) or []:
        parts.append(c.get("value", ""))
    parts.append(entry.get("summary", ""))
    txt = BeautifulSoup(" ".join(parts), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", txt)

# ------------------------------------------------------------------ pipeline
def run() -> int:
    now = datetime.now(TZ)
    horizon = now - timedelta(hours=48)

    existing = {"items": []}
    if OUT.exists():
        try:
            existing = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            pass
    known_urls = {it.get("url") for it in existing.get("items", [])}

    new_items = []
    for source, feed_url in FEEDS:
        try:
            feed = feedparser.parse(requests.get(feed_url, headers=UA,
                                                 timeout=TIMEOUT).content)
        except Exception as e:
            print(f"[warn] flux {source}: {e}", file=sys.stderr)
            continue
        for entry in feed.entries[:25]:
            title = html.unescape(entry.get("title", ""))
            summary = html.unescape(entry.get("summary", ""))
            head = f"{title} {summary}"
            if not (KW_MUST.search(head) and KW_CUT.search(head)):
                continue
            url = entry.get("link", "")
            if not url or url in known_urls:
                continue
            # date de publication
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            if pub:
                pub_dt = datetime(*pub[:6], tzinfo=ZoneInfo("UTC")).astimezone(TZ)
            else:
                pub_dt = now
            if pub_dt < horizon:
                continue
            # texte : flux RSS d'abord, page article si le flux est tronqué
            body = title + " " + entry_body(entry)
            if len(body) < 400:
                try:
                    body = title + " " + article_text(url)
                except Exception as e:
                    print(f"[warn] article {url}: {e}", file=sys.stderr)
            # on coupe avant les blocs "articles liés" pour ne pas matcher leurs zones
            body = re.split(r"Lire aussi|À lire aussi|A lire aussi|Articles? similaires?"
                            r"|Sur le même sujet|Les plus récents|Les plus populaires",
                            body, 1)[0]
            start, end = extract_times(body) or (None, None)
            ids, found = match_zones(body)
            # sûreté : sans horaire explicite, on liste l'info mais on ne colore pas la carte
            if start is None:
                ids, found = [], []
            kind = ("Délestage tournant" if re.search(r"délestage|delestage|tournant", body, re.I)
                    else "Coupure programmée")
            new_items.append({
                "date": pub_dt.strftime("%Y-%m-%d"),
                "start": start or "00:00",
                "end": end or "23:59",
                "type": kind,
                "titre": title[:110],
                "zones": ", ".join(sorted(found))[:400],
                "ids": ids,
                "source": source,
                "url": url,
                "via": "scraper",
                "fetched_at": now.isoformat(timespec="seconds"),
            })
            known_urls.add(url)
            print(f"[new] {source} · {title[:70]} · {len(ids)} délégations")

    # fusion : nouveaux d'abord, on garde 48 h, max 15
    merged = new_items + existing.get("items", [])
    merged = [it for it in merged
              if it.get("date", "1970-01-01") >= horizon.strftime("%Y-%m-%d")]
    merged = merged[:15]

    OUT.write_text(json.dumps({
        "generated_at": now.isoformat(timespec="seconds"),
        "items": merged,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[ok] {len(new_items)} nouvelles annonces, {len(merged)} au total.")
    return 0

if __name__ == "__main__":
    sys.exit(run())
