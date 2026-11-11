#!/usr/bin/env python3
"""Kumpulkan data satu channel YouTube dengan yt-dlp (tanpa API key, tanpa unduh video).

Hasil di folder --out:
  data.json            semua angka (daftar video per tab, detail, transkrip)
  transcripts/<id>.txt transkrip bertimestamp (dari caption YouTube)
  thumbs/<id>.jpg      thumbnail
  thumbs_top.jpg       lembar kontak thumbnail video terlaris
  thumbs_recent.jpg    lembar kontak thumbnail video terbaru

Contoh:
  python collect.py @RicksClips3000 --out "D:/riset/ricksclips"
  python collect.py https://www.youtube.com/@kurzgesagt/videos --top 20 --recent 30
  python collect.py https://youtu.be/VIDEO_ID           (channel diambil dari video itu)
"""
import argparse
import html
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    sys.exit("yt-dlp belum terpasang: python -m pip install -U yt-dlp")

TABS = ["videos", "shorts", "streams"]
BASE_OPTS = {"quiet": True, "no_warnings": True, "skip_download": True}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- channel URL
def resolve_channel(arg):
    s = arg.strip()
    is_video = re.search(r"(watch\?v=|youtu\.be/|/shorts/[\w-]{6,})", s)
    if is_video:
        with yt_dlp.YoutubeDL({**BASE_OPTS, "noplaylist": True}) as y:
            info = y.extract_info(s, download=False, process=False)
        url = info.get("uploader_url") or info.get("channel_url")
        if not url:
            sys.exit("Tidak bisa menemukan channel dari video itu.")
        return url.rstrip("/")
    if s.startswith("@"):
        return "https://www.youtube.com/" + s
    if not s.startswith("http"):
        if re.fullmatch(r"UC[\w-]{22}", s):
            return "https://www.youtube.com/channel/" + s
        return "https://www.youtube.com/@" + s
    s = s.split("?")[0].rstrip("/")
    return re.sub(r"/(videos|shorts|streams|featured|about|playlists|community|posts)$", "", s)


def flat_tab(base, tab, limit):
    opts = {**BASE_OPTS, "extract_flat": "in_playlist", "ignoreerrors": True}
    if limit:
        opts["playlistend"] = limit
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(f"{base}/{tab}", download=False)
    except Exception as e:  # tab tidak ada
        log(f"  tab {tab}: tidak ada ({str(e)[:80]})")
        return None, []
    if not info:
        return None, []
    # Kalau tab tidak ada, YouTube kadang mengembalikan halaman lain; cek URL.
    wurl = (info.get("webpage_url") or "").rstrip("/")
    if wurl and not wurl.endswith("/" + tab):
        log(f"  tab {tab}: tidak ada")
        return info, []
    rows = []
    for pos, e in enumerate(info.get("entries") or []):
        if not e or not e.get("id"):
            continue
        rows.append({
            "id": e["id"],
            "title": e.get("title"),
            "views": e.get("view_count"),
            "duration": e.get("duration"),
            "pos": pos,  # 0 = paling baru
            "tab": tab,
        })
    return info, rows


# ---------------------------------------------------------------- captions
def pick_caption(info):
    lang = (info.get("language") or "").split("-")[0]
    subs = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    order = []
    if lang:
        order += [(subs, lang, "manual"), (auto, lang + "-orig", "auto"), (auto, lang, "auto")]
    order += [(auto, k, "auto") for k in auto if k.endswith("-orig")]
    order += [(subs, k, "manual") for k in subs if k != "live_chat"]
    order += [(auto, "en", "auto"), (auto, "id", "auto")]
    for d, key, kind in order:
        fmts = d.get(key) or []
        for f in fmts:
            if f.get("ext") == "vtt" and f.get("url"):
                return key, kind, f["url"]
    return None


def parse_vtt(text):
    cues, cur = [], None
    for line in text.splitlines():
        m = re.match(r"(?:(\d+):)?(\d+):(\d+)\.(\d+)\s+-->", line)
        if m:
            t = int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4)) / 1000
            cur = {"t": t, "lines": []}
            cues.append(cur)
            continue
        if cur is None:
            continue
        if not line.strip():
            cur = None
            continue
        clean = html.unescape(re.sub(r"<[^>]+>", "", line)).strip()
        if clean:
            cur["lines"].append(clean)
    out, recent = [], []
    for c in cues:  # caption otomatis YouTube berulang (rolling); buang baris yang baru saja muncul
        for l in c["lines"]:
            if l in recent:
                continue
            out.append((c["t"], l))
            recent = (recent + [l])[-4:]
    return out


# ---------------------------------------------------------------- detail
KEEP = ["id", "title", "description", "upload_date", "timestamp", "duration", "view_count",
        "like_count", "comment_count", "tags", "categories", "language", "thumbnail",
        "live_status", "chapters", "width", "height"]


def fetch_detail(vid, want_caps, tdir):
    with yt_dlp.YoutubeDL({**BASE_OPTS, "noplaylist": True}) as y:
        info = y.extract_info("https://www.youtube.com/watch?v=" + vid, download=False)
        d = {k: info.get(k) for k in KEEP}
        if d.get("chapters"):
            d["chapters"] = [{"t": c.get("start_time"), "title": c.get("title")} for c in d["chapters"]]
        if want_caps:
            cap = pick_caption(info)
            if cap:
                key, kind, url = cap
                try:
                    raw = y.urlopen(url).read().decode("utf-8", "replace")
                    lines = parse_vtt(raw)
                    if lines:
                        p = tdir / f"{vid}.txt"
                        with open(p, "w", encoding="utf-8") as f:
                            f.write(f"# {d['title']}\n# https://youtu.be/{vid}  caption: {key} ({kind})\n\n")
                            for t, l in lines:
                                f.write(f"[{int(t // 60):02d}:{t % 60:04.1f}] {l}\n")
                        d["transcript"] = {"file": str(p), "lang": key, "kind": kind,
                                           "words": sum(len(l.split()) for _, l in lines)}
                except Exception as e:
                    d["transcript_error"] = str(e)[:120]
    return d


# ---------------------------------------------------------------- thumbnails
def get_thumb(vid, url, tdir):
    p = tdir / f"{vid}.jpg"
    if p.exists():
        return p
    for u in [url, f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg", f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"]:
        if not u:
            continue
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=30).read()
            if len(data) < 2000:
                continue
            from io import BytesIO
            from PIL import Image
            Image.open(BytesIO(data)).convert("RGB").save(p, quality=90)
            return p
        except Exception:
            continue
    return None


def human(n):
    if n is None:
        return "?"
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= div:
            return f"{n / div:.1f}{suf}"
    return str(n)


def contact_sheet(items, paths, out, title, vertical=False):
    from PIL import Image, ImageDraw, ImageFont
    items = [(i, paths[i["id"]]) for i in items if paths.get(i["id"])]
    if not items:
        return
    cols, cw, ih, th = (6, 240, 400, 46) if vertical else (4, 360, 300, 46)
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw, 50 + rows * (ih + th)), (24, 24, 24))
    dr = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 15)
        big = ImageFont.truetype("arialbd.ttf", 22)
    except OSError:
        font = big = ImageFont.load_default()
    dr.text((12, 12), title, fill=(255, 255, 255), font=big)
    for n, (it, p) in enumerate(items):
        x, y = (n % cols) * cw, 50 + (n // cols) * (ih + th)
        im = Image.open(p)
        if vertical and im.width > im.height:  # thumbnail Shorts = frame 9:16 di tengah gambar lebar
            w = round(im.height * 9 / 16)
            im = im.crop(((im.width - w) // 2, 0, (im.width + w) // 2, im.height))
        im.thumbnail((cw - 12, ih - 8))
        sheet.paste(im, (x + (cw - im.width) // 2, y + (ih - im.height) // 2))
        t, lim = it.get("title") or "", (cw - 16) // 8
        t = t if len(t) <= lim else t[: lim - 1] + "…"
        dr.text((x + 8, y + ih), f"#{n + 1}  {human(it.get('views'))} views", fill=(255, 210, 60), font=font)
        dr.text((x + 8, y + ih + 20), t, fill=(230, 230, 230), font=font)
    sheet.save(out, quality=88)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("channel", help="@handle, URL channel, ID UC..., atau URL salah satu videonya")
    ap.add_argument("--out", required=True, help="folder hasil")
    ap.add_argument("--max", type=int, default=0, help="batas jumlah video per tab dari daftar (0 = semua)")
    ap.add_argument("--top", type=int, default=15, help="video terlaris per tab yang diambil detailnya")
    ap.add_argument("--recent", type=int, default=30, help="video terbaru per tab yang diambil detailnya")
    ap.add_argument("--all-details", action="store_true", help="ambil detail semua video (lambat)")
    ap.add_argument("--transcripts", type=int, default=12, help="jumlah transkrip per tab (terlaris + terbaru)")
    ap.add_argument("--thumbs", type=int, default=12, help="jumlah thumbnail per kelompok per tab")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    out = Path(a.out)
    tdir, hdir = out / "transcripts", out / "thumbs"
    for d in (out, tdir, hdir):
        d.mkdir(parents=True, exist_ok=True)

    base = resolve_channel(a.channel)
    log(f"Channel: {base}")
    channel, tabs = {}, {}
    for tab in TABS:
        log(f"Daftar {tab} ...")
        info, rows = flat_tab(base, tab, a.max)
        tabs[tab] = rows
        if info and not channel:
            channel = {
                "name": info.get("channel") or info.get("uploader"),
                "id": info.get("channel_id"),
                "handle": info.get("uploader_id"),
                "url": info.get("channel_url") or base,
                "subscribers": info.get("channel_follower_count"),
                "description": info.get("description"),
                "tags": info.get("tags"),
            }
        log(f"  {len(rows)} video")
    if not any(tabs.values()):
        sys.exit("Tidak ada video ditemukan. Cek URL/handle channel.")

    # Pilih video untuk detail: terlaris + terbaru di tiap tab
    want, caps = {}, set()
    for tab, rows in tabs.items():
        if not rows:
            continue
        by_views = sorted([r for r in rows if r["views"] is not None], key=lambda r: -r["views"])
        chosen = rows if a.all_details else by_views[:a.top] + rows[:a.recent]
        for r in chosen:
            want[r["id"]] = r
        half = max(1, a.transcripts // 2)
        for r in by_views[: a.transcripts - half] + rows[:half]:
            caps.add(r["id"])
    log(f"Detail {len(want)} video ({len(caps)} dengan transkrip) ...")

    details, t0 = {}, time.time()
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(fetch_detail, vid, vid in caps, tdir): vid for vid in want}
        for n, f in enumerate(as_completed(futs), 1):
            vid = futs[f]
            try:
                details[vid] = f.result()
            except Exception as e:
                details[vid] = {"id": vid, "error": str(e)[:160]}
            if n % 10 == 0 or n == len(futs):
                log(f"  {n}/{len(futs)}  ({time.time() - t0:.0f} s)")

    # Lengkapi daftar flat dengan angka detail (views terbaru, durasi, tanggal)
    for rows in tabs.values():
        for r in rows:
            d = details.get(r["id"])
            if d and not d.get("error"):
                r["views"] = d.get("view_count") or r["views"]
                r["duration"] = d.get("duration") or r["duration"]
                r["upload_date"] = d.get("upload_date")

    # Thumbnail + lembar kontak
    log("Thumbnail ...")
    paths = {}
    groups = {}
    for tab, rows in tabs.items():
        if not rows:
            continue
        top = sorted([r for r in rows if r["views"] is not None], key=lambda r: -r["views"])[: a.thumbs]
        groups[(tab, "top")] = top
        groups[(tab, "recent")] = rows[: a.thumbs]
    jobs = {r["id"]: (details.get(r["id"]) or {}).get("thumbnail") for g in groups.values() for r in g}
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(get_thumb, vid, u, hdir): vid for vid, u in jobs.items()}
        for f in as_completed(futs):
            paths[futs[f]] = f.result()
    sheets = []
    for (tab, kind), items in groups.items():
        p = out / f"thumbs_{tab}_{kind}.jpg"
        label = "terlaris" if kind == "top" else "terbaru"
        contact_sheet(items, paths, p, f"{channel.get('name')} - {tab} {label}", vertical=(tab == "shorts"))
        if p.exists():
            sheets.append(str(p))

    data = {
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": a.channel,
        "channel": channel,
        "tabs": tabs,
        "details": details,
        "contact_sheets": sheets,
    }
    with open(out / "data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    log(f"Selesai: {out / 'data.json'}")
    errs = [d for d in details.values() if d.get("error")]
    if errs:
        log(f"  {len(errs)} video gagal diambil detailnya (lihat 'error' di data.json)")


if __name__ == "__main__":
    main()
