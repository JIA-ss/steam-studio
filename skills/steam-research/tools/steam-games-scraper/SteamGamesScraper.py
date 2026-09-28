########################################################################################################################
# Copyright (c) Martin Bustos @FronkonGames <fronkongames@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
########################################################################################################################
# Adapted for steam-studio; see UPSTREAM.md for provenance and changes.
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time

import requests

SCHEMA_VERSION = 1
STORE_URL = "https://store.steampowered.com/api/appdetails/"
REVIEWS_URL = "https://store.steampowered.com/appreviews/"
SPY_URL = "https://steamspy.com/api.php"
CATALOG_URL = "https://api.steampowered.com/IStoreService/GetAppList/v1/"


def utcnow():
    return datetime.now(timezone.utc).isoformat()


class FetchError(Exception):
    """A bounded, credential-safe upstream failure."""


class Client:
    def __init__(self, interval=1.5, retries=3, timeout=20, session=None,
                 sleep=time.sleep, clock=time.monotonic):
        self.interval = interval
        self.retries = retries
        self.timeout = timeout
        self.session = session if session is not None else requests.Session()
        self.session.headers.update({"User-Agent": "steam-studio/0.1 (+https://github.com/JIA-ss/steam-studio)"})
        self.sleep = sleep
        self.clock = clock
        self.last_request = None

    def get(self, url, params=None):
        for attempt in range(self.retries + 1):
            if self.last_request is not None:
                self.sleep(max(0, self.interval - (self.clock() - self.last_request)))
            self.last_request = self.clock()
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                # requests exceptions may contain a URL with an API key; never print them.
                if isinstance(exc, requests.exceptions.ProxyError):
                    error = "network_proxy_error"
                elif isinstance(exc, requests.exceptions.SSLError):
                    error = "network_tls_error"
                elif isinstance(exc, requests.Timeout):
                    error = "network_timeout"
                else:
                    error = "network_error"
                response = None
            else:
                if response.status_code == 200:
                    try:
                        return response.json()
                    except ValueError:
                        error = "invalid_json"
                elif response.status_code == 429 or response.status_code >= 500:
                    error = f"http_{response.status_code}"
                else:
                    raise FetchError(f"http_{response.status_code}")
            if attempt == self.retries:
                raise FetchError(error)
            delay = min(2 ** (attempt + 1), 30)
            if response is not None and response.status_code == 429:
                # Stop rather than retry earlier than a long Retry-After window.
                try:
                    delay = max(delay, float(response.headers.get("Retry-After", "60")))
                except ValueError:
                    raise FetchError("rate_limited_retry_later") from None
                if not math.isfinite(delay) or delay > 60:
                    raise FetchError("rate_limited_retry_later")
            self.sleep(delay)
        raise FetchError("exhausted")


def save_json(data, path):
    """Atomic replace in the same directory: interruption cannot truncate the old file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="." + path.name, delete=False) as out:
            name = out.name
            json.dump(data, out, ensure_ascii=False, indent=2, allow_nan=False)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def load_json(path, default):
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else default


def SanitizeText(text):
  '''
  Removes HTML codes, escape codes and URLs.
  '''
  text = text.replace('\n\r', ' ')
  text = text.replace('\r\n', ' ')
  text = text.replace('\r \n', ' ')
  text = text.replace('\r', ' ')
  text = text.replace('\n', ' ')
  text = text.replace('\t', ' ')
  text = text.replace('&quot;', "'")
  text = re.sub(r'(https|http)?:\/\/(\w|\.|\/|\?|\=|\&|\%)*\b', '', text, flags=re.MULTILINE)
  text = re.sub('<[^<]+?>', ' ', text)
  text = re.sub(' +', ' ', text)
  text = text.lstrip(' ')

  return text

def ParseSteamGame(app):
  '''
  Parse game info.
  '''
  game = {}
  game['name'] = app['name'].strip()
  game['release_date'] = app.get('release_date', {}).get('date')
  game['coming_soon'] = app.get('release_date', {}).get('coming_soon')
  game['is_free'] = app.get('is_free')
  game['required_age'] = int(str(app['required_age']).replace('+', '')) if 'required_age' in app else 0

  price = app.get('price_overview') or {}
  game['price_final_minor'] = price.get('final')
  game['price_initial_minor'] = price.get('initial')
  game['currency'] = price.get('currency')
  game['price_display'] = price.get('final_formatted')
  game['discount_percent'] = price.get('discount_percent')
  # No float conversion: Steam returns integer price units; formatted strings vary by locale.
  # Free status is independent from whether a price payload exists.

  game['dlc_count'] = len(app['dlc']) if 'dlc' in app else 0
  game['detailed_description'] = app['detailed_description'].strip() if 'detailed_description' in app else ''
  game['about_the_game'] = app['about_the_game'].strip() if 'about_the_game' in app else ''
  game['short_description'] = app['short_description'].strip() if 'short_description' in app else ''
  game['reviews'] = app['reviews'].strip() if 'reviews' in app else ''
  game['header_image'] = app['header_image'].strip() if 'header_image' in app and app['header_image'] else ''
  game['website'] = app['website'].strip() if 'website' in app and app['website'] is not None else ''
  game['support_url'] = app['support_info'].get('url', '').strip() if 'support_info' in app else ''
  game['support_email'] = app['support_info'].get('email', '').strip() if 'support_info' in app else ''
  game['windows'] = True if app.get('platforms', {}).get('windows') else False
  game['mac'] = True if app.get('platforms', {}).get('mac') else False
  game['linux'] = True if app.get('platforms', {}).get('linux') else False
  game['metacritic_score'] = int(app['metacritic']['score']) if 'metacritic' in app else None
  game['metacritic_url'] = app['metacritic']['url'] if 'metacritic' in app else ''
  game['achievements'] = int(app['achievements']['total']) if 'achievements' in app else None
  game['recommendations'] = app['recommendations']['total'] if 'recommendations' in app else None
  game['notes'] = app['content_descriptors']['notes'] if 'content_descriptors' in app and app['content_descriptors']['notes'] is not None else ''

  game['supported_languages'] = []
  game['full_audio_languages'] = []

  if 'supported_languages' in app:
    languagesApp = app['supported_languages']
    languagesApp = re.sub('<[^<]+?>', '', languagesApp)
    languagesApp = languagesApp.replace('languages with full audio support', '')

    languages = languagesApp.split(', ')
    for lang in languages:
      if '*' in lang:
        game['full_audio_languages'].append(lang.replace('*', ''))
      game['supported_languages'].append(lang.replace('*', ''))

  game['packages'] = []
  if 'package_groups' in app:
    for package in app['package_groups']:
      subs = []
      if 'subs' in package:
        for sub in package['subs']:
          subs.append({'text': SanitizeText(sub['option_text']),
                       'description': sub['option_description'],
                       'price': round(float(sub['price_in_cents_with_discount']) * 0.01, 2) }) 

      game['packages'].append({'title': SanitizeText(package['title']), 'description': SanitizeText(package['description']), 'subs': subs})

  game['developers'] = []
  if 'developers' in app:
    for developer in app['developers']:
      game['developers'].append(developer.strip())

  game['publishers'] = []
  if 'publishers' in app:
    for publisher in app['publishers']:
      game['publishers'].append(publisher.strip())

  game['categories'] = []
  if 'categories' in app:
    for category in app['categories']:
      game['categories'].append(category['description'])

  game['genres'] = []
  if 'genres' in app:
    for genre in app['genres']:
      game['genres'].append(genre['description'])

  game['screenshots'] = []
  if 'screenshots' in app:
    for screenshot in app['screenshots']:
      game['screenshots'].append(screenshot['path_full'])

  game['movies'] = []
  if 'movies' in app:
    for movie in app['movies']:
      if 'mp4' in movie:
        game['movies'].append(movie['mp4']['max'])

  game['detailed_description'] = SanitizeText(game['detailed_description'])
  game['about_the_game'] = SanitizeText(game['about_the_game'])
  game['short_description'] = SanitizeText(game['short_description'])
  game['reviews'] = SanitizeText(game['reviews'])
  game['notes'] = SanitizeText(game['notes'])

  return game


def catalog(client, key):
    if not key:
        raise FetchError("STEAM_API_KEY_required_for_catalog")
    apps = {}
    last = 0
    while True:
        data = client.get(CATALOG_URL, {"key": key, "max_results": 50000,
                                      "include_games": "true", "include_dlc": "false",
                                      "include_software": "false", "last_appid": last})
        result = data.get("response") if isinstance(data, dict) else None
        if not isinstance(result, dict) or not isinstance(result.get("apps"), list):
            raise FetchError("invalid_catalog")
        for item in result["apps"]:
            if not isinstance(item, dict) or not isinstance(item.get("appid"), int) or item["appid"] <= 0:
                raise FetchError("invalid_catalog_item")
            apps[str(item["appid"])] = item
        if not result.get("have_more_results"):
            return {"schema_version": SCHEMA_VERSION, "fetched_at": utcnow(),
                    "source": CATALOG_URL, "apps": list(apps.values())}
        next_id = result.get("last_appid")
        if not isinstance(next_id, int) or next_id <= last:
            raise FetchError("catalog_cursor_did_not_advance")
        last = next_id


def fetch_record(client, appid, country, language, use_spy, raw_dir):
    sources = {}

    def fetch(source, url, params):
        fetched_at = utcnow()
        try:
            payload = client.get(url, params)
        except FetchError as error:
            sources[source] = {"status": "error", "error": str(error), "fetched_at": fetched_at,
                               "url": url, "params": params}
            return None
        save_json({"fetched_at": fetched_at, "url": url, "params": params, "payload": payload},
                  raw_dir / f"{appid}.{source}.json")
        sources[source] = {"status": "ok", "fetched_at": fetched_at, "url": url, "params": params,
                           "raw_file": f"raw/{appid}.{source}.json"}
        return payload

    payload = fetch("steam_store", STORE_URL, {"appids": appid, "cc": country, "l": language})
    envelope = payload.get(str(appid)) if isinstance(payload, dict) else None
    if not isinstance(envelope, dict) or envelope.get("success") is not True or not isinstance(envelope.get("data"), dict):
        return None, {"status": "error", "reason": "store_unavailable", "sources": sources}
    app = envelope["data"]
    if app.get("type") != "game":
        return None, {"status": "excluded", "reason": "not_game", "sources": sources}
    try:
        game = ParseSteamGame(app)
    except (KeyError, TypeError, ValueError, AttributeError):
        return None, {"status": "error", "reason": "invalid_store_schema", "sources": sources}
    game.update({"appid": appid, "schema_version": SCHEMA_VERSION, "country": country,
                 "language": language, "fetched_at": utcnow(), "sources": sources,
                 "review_summary": None, "steamspy": None, "tags": None})
    # Store 'reviews' is editorial copy, not user-review sentiment. Keep that distinction explicit.
    game["editorial_reviews"] = game.pop("reviews", "")
    summary = fetch("steam_reviews", REVIEWS_URL + str(appid),
                    {"json": 1, "language": "all", "purchase_type": "all",
                     "filter": "all", "num_per_page": 0})
    if isinstance(summary, dict) and summary.get("success") == 1 and isinstance(summary.get("query_summary"), dict):
        q = summary["query_summary"]
        fields = ("total_positive", "total_negative", "total_reviews")
        if all(type(q.get(f)) is int and q[f] >= 0 for f in fields) and q["total_positive"] + q["total_negative"] == q["total_reviews"]:
            game["review_summary"] = {f: q.get(f) for f in (*fields, "review_score", "review_score_desc")}
        else:
            sources["steam_reviews"].update(status="error", error="invalid_review_counts")
    elif sources["steam_reviews"]["status"] == "ok":
        sources["steam_reviews"].update(status="error", error="invalid_review_schema")
    if use_spy:
        spy = fetch("steamspy", SPY_URL, {"request": "appdetails", "appid": appid})
        if isinstance(spy, dict) and str(spy.get("appid")) == str(appid):
            # Preserve estimates as provided, never substitute zeros or equate owners with sales.
            game["steamspy"] = {"owners_estimate_range": spy.get("owners"),
                                "peak_ccu_yesterday_reported": spy.get("ccu")}
            tags = spy.get("tags")
            if isinstance(tags, dict) and all(isinstance(k, str) and type(v) is int and v >= 0 for k, v in tags.items()):
                game["tags"] = tags
            else:
                sources["steamspy"].update(status="error", error="missing_or_invalid_tags")
        elif sources["steamspy"]["status"] == "ok":
            sources["steamspy"].update(status="error", error="invalid_steamspy_schema")
    status = "partial" if any(s["status"] == "error" for s in sources.values()) else "ok"
    game["status"] = status
    return game, {"status": status, "sources": sources}


def collect(client, ids, data_dir, country="us", language="english", use_spy=False, refresh=False):
    data_dir = Path(data_dir)
    games_path = data_dir / "games.json"
    existing = load_json(games_path, {})
    if not isinstance(existing, dict):
        raise ValueError("games.json must be an object")
    manifest = {"schema_version": SCHEMA_VERSION, "started_at": utcnow(), "status": "running",
                "country": country, "language": language, "steamspy_requested": use_spy,
                "selected_count": len(ids), "results": {}}
    manifest_path = data_dir / "run.json"
    save_json(manifest, manifest_path)
    interrupted = False
    try:
        for appid in ids:
            old = existing.get(str(appid), {})
            if not refresh and old.get("schema_version") == SCHEMA_VERSION and old.get("status") == "ok" and old.get("country") == country and old.get("language") == language and (not use_spy or old.get("sources", {}).get("steamspy", {}).get("status") == "ok"):
                result = {"status": "skipped", "reason": "existing_snapshot", "fetched_at": old.get("fetched_at")}
            else:
                game, result = fetch_record(client, appid, country, language, use_spy, data_dir / "raw")
                if game is not None:
                    existing[str(appid)] = game
                    save_json(existing, games_path)
                elif str(appid) in existing:
                    # Failed refresh preserves the last snapshot but marks it stale; never silently current.
                    existing[str(appid)]["status"] = "stale"
                    save_json(existing, games_path)
            manifest["results"][str(appid)] = result
            save_json(manifest, manifest_path)
            print(json.dumps({"appid": appid, "status": result["status"]}), flush=True)
    except KeyboardInterrupt:
        interrupted = True
    except (OSError, ValueError, TypeError, KeyError):
        manifest.update(status="failed", finished_at=utcnow(),
                        error="invalid_input_or_local_io", processed_count=len(manifest["results"]))
        try:
            save_json(manifest, manifest_path)
        except OSError:
            pass
        raise
    manifest["finished_at"] = utcnow()
    manifest["processed_count"] = len(manifest["results"])
    manifest["status"] = "interrupted" if interrupted else ("partial" if any(r["status"] in ("error", "partial") for r in manifest["results"].values()) else "complete")
    save_json(manifest, manifest_path)
    return 130 if interrupted else (2 if manifest["status"] == "partial" else 0)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only Steam research collector (adapted from FronkonGames).")
    parser.add_argument("--data-dir", type=Path, default=Path("data/steam-research"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--appids", nargs="+", type=int, help="Explicit app IDs; no API key required")
    mode.add_argument("--catalog", action="store_true", help="Fetch catalog then sample (STEAM_API_KEY required)")
    mode.add_argument("--catalog-only", action="store_true", help="Fetch catalog without per-game requests")
    mode.add_argument("--catalog-file", type=Path, help="Use a previously saved catalog.json")
    parser.add_argument("--limit", type=int, default=20, help="Max games per run (default 20)")
    parser.add_argument("--all", action="store_true", help="Explicitly remove per-run game limit")
    parser.add_argument("--country", default="us", help="Store country code, not a currency code")
    parser.add_argument("--language", default="english")
    parser.add_argument("--steamspy", action="store_true", help="Add SteamSpy tags/ownership estimates")
    parser.add_argument("--refresh", action="store_true", help="Re-fetch successful existing snapshots")
    parser.add_argument("--interval", type=float, default=1.5, help="Minimum seconds between HTTP attempts")
    parser.add_argument("--retries", type=int, default=3, help="Extra attempts, 0 disables retries")
    args = parser.parse_args(argv)
    if args.limit <= 0 or not math.isfinite(args.interval) or args.interval < 1.5 or args.retries < 0 or args.retries > 5:
        parser.error("require limit > 0, interval >= 1.5, and 0 <= retries <= 5")
    if args.appids and any(i <= 0 for i in args.appids):
        parser.error("app IDs must be positive")
    args.country = args.country.lower()
    if not re.fullmatch(r"[a-z]{2}", args.country):
        parser.error("country must be a two-letter code")
    client = Client(args.interval, args.retries)
    try:
        if args.appids:
            ids = args.appids
        else:
            if args.catalog_file:
                cat = load_json(args.catalog_file, None)
            else:
                cat = catalog(client, os.environ.get("STEAM_API_KEY"))
                save_json(cat, args.data_dir / "catalog.json")
            if not isinstance(cat, dict) or not isinstance(cat.get("apps"), list):
                raise ValueError("invalid catalog file")
            if args.catalog_only:
                print(json.dumps({"status": "complete", "apps": len(cat["apps"])}))
                return 0
            ids = [int(a["appid"]) for a in cat["apps"]]
        ids = list(dict.fromkeys(ids))
        if any(i <= 0 for i in ids):
            raise ValueError("invalid app ID")
        if not args.all:
            ids = ids[:args.limit]
        if not ids:
            raise ValueError("no app IDs selected")
        return collect(client, ids, args.data_dir, args.country, args.language, args.steamspy, args.refresh)
    except FetchError as error:
        print(json.dumps({"status": "failed", "error": str(error)}), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"status": "failed", "error": "invalid_input_or_local_io"}), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
