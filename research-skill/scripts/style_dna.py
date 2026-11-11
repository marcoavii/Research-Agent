#!/usr/bin/env python3
"""Stage 1, Style DNA: ukur gaya satu video (file lokal atau link YouTube).

Mengukur, bukan menebak:
  format    resolusi, rasio, FPS, durasi, codec
  potongan  deteksi cut dari selisih frame 10 fps (lebih peka dari scene-detect 0.09
            yang terbukti undercount di video kamera-bergerak), panjang shot, gerak kamera
  warna     palet dominan, saturasi dan kecerahan per detik
  audio     loudness terintegrasi (LUFS), true peak, LRA, jeda hening
  bicara    kata per detik dan jeda, dari caption YouTube atau faster-whisper (--whisper)
  frame     lembar kontak 1 frame/detik berlabel waktu untuk dibaca langsung

  python style_dna.py https://youtu.be/7xS87iActkU --out "<notes>/style/railroads"
  python style_dna.py "D:/ref/video.mp4" --out "<folder>" --whisper
"""
import argparse
import json
import re
import statistics as st
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- input
def get_video(src, out):
    """Kembalikan (path_video, video_id_atau_None)."""
    p = Path(src)
    if p.exists():
        return p, None
    import yt_dlp
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", src) or re.fullmatch(r"([\w-]{11})", src)
    if not m:
        sys.exit(f"Bukan file atau link YouTube: {src}")
    vid = m.group(1)
    have = list(out.glob(f"{vid}.mp4"))
    if have:
        return have[0], vid
    log(f"Unduh {vid} (<= 480p) ...")
    opts = {"quiet": True, "no_warnings": True, "noprogress": True, "format": "bv*+ba/b", "format_sort": ["res:480", "ext:mp4:m4a"],
            "merge_output_format": "mp4", "outtmpl": str(out / "%(id)s.%(ext)s")}
    with yt_dlp.YoutubeDL(opts) as y:
        y.download(["https://www.youtube.com/watch?v=" + vid])
    return out / f"{vid}.mp4", vid


def probe(path):
    r = run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)])
    j = json.loads(r.stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    num, den = (v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1").split("/")
    w, h = int(v["width"]), int(v["height"])
    rot = abs(int((v.get("tags") or {}).get("rotate", 0) or 0))
    if rot in (90, 270):
        w, h = h, w
    return {"width": w, "height": h, "fps": round(int(num) / max(1, int(den)), 2),
            "duration": float(j["format"]["duration"]), "vcodec": v.get("codec_name"),
            "acodec": a.get("codec_name") if a else None,
            "ratio": "9:16" if h > w * 1.5 else "16:9" if w > h * 1.5 else f"{w}:{h}"}


# ---------------------------------------------------------------- frames
def decode(path, fps, width, info):
    h = int(round(width * info["height"] / info["width"] / 2) * 2)
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={fps},scale={width}:{h}",
                        "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, np.uint8)
    n = a.size // (width * h * 3)
    return a[: n * width * h * 3].reshape(n, h, width, 3)


def detect_cuts(frames, fps, thr=0.25, prom=0.12):
    """Pergantian shot = komposisi 0,4 s sebelum dan sesudah titik ini berbeda.

    Membandingkan rata-rata beberapa frame di tiap sisi (struktur gambar + histogram warna),
    jadi whip pan dan dissolve ikut tertangkap, sedangkan dolly/orbit dalam satu shot tidak.
    Dikalibrasi di "Why Perfect Railroads Don't Work": 13 dari ~15 pergantian di 24 s pertama.
    """
    f = frames.astype(np.float32)
    motion = np.abs(np.diff(f.mean(axis=3), axis=0)).mean(axis=(1, 2))
    g = f.mean(axis=3).reshape(len(f), -1)
    g = (g - g.mean(1, keepdims=True)) / (g.std(1, keepdims=True) + 1e-3)
    H = np.array([np.concatenate([np.histogram(x[..., c], bins=8, range=(0, 256))[0] for c in range(3)]) for x in frames], float)
    H /= H.sum(1, keepdims=True)
    k, n = 4, len(f)
    d = np.zeros(n)
    for i in range(k, n - k):
        c = np.corrcoef(g[i - k:i].mean(0), g[i:i + k].mean(0))[0, 1]
        d[i] = (1 - c) / 2 + np.abs(H[i - k:i].mean(0) - H[i:i + k].mean(0)).sum() / 2
    cuts, sep = [], 4
    for i in range(n):
        lo, hi = max(0, i - sep), min(n, i + sep + 1)
        if d[i] < thr or d[i] < d[lo:hi].max():
            continue
        l2, h2 = max(0, i - 10), min(n, i + 11)
        left = d[l2:i].min() if i > l2 else 0
        right = d[i + 1:h2].min() if h2 > i + 1 else 0
        if d[i] - max(left, right) >= prom:
            cuts.append(round(i / fps, 2))
    return cuts, motion, d


def palette(frames, k=8):
    small = [Image.fromarray(fr).resize((48, max(1, int(48 * fr.shape[0] / fr.shape[1])))) for fr in frames]
    w = small[0].width
    strip = Image.new("RGB", (w, sum(s.height for s in small)))
    y = 0
    for s in small:
        strip.paste(s, (0, y))
        y += s.height
    q = strip.quantize(k, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: 3 * k]
    counts = sorted(q.getcolors(), reverse=True)
    total = sum(c for c, _ in counts)
    return [(f"#{pal[3*i]:02x}{pal[3*i+1]:02x}{pal[3*i+2]:02x}", 100 * c / total) for c, i in counts]


def hsv_stats(frames):
    s, v = [], []
    for fr in frames:
        hsv = np.asarray(Image.fromarray(fr).convert("HSV")).reshape(-1, 3)
        s.append(hsv[:, 1].mean() / 2.55)
        v.append(hsv[:, 2].mean() / 2.55)
    return s, v


def sheets(path, out, info, step=1.0, per=24, cols=6):
    fdir = out / "frames"
    fdir.mkdir(exist_ok=True)
    for old in fdir.glob("f_*.jpg"):
        old.unlink()
    run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps=1/{step},scale=270:-2", str(fdir / "f_%04d.jpg")])
    files = sorted(fdir.glob("f_*.jpg"))
    try:
        font = ImageFont.truetype("arialbd.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    outs = []
    for s in range(0, len(files), per):
        chunk = files[s: s + per]
        ims = [Image.open(p) for p in chunk]
        cw, ch = ims[0].width, ims[0].height
        rows = (len(ims) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (cw + 4), rows * (ch + 4)), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for n, im in enumerate(ims):
            x, y = (n % cols) * (cw + 4), (n // cols) * (ch + 4)
            sheet.paste(im, (x, y))
            t = (s + n) * step
            label = f"{int(t // 60)}:{t % 60:04.1f}"
            d.rectangle((x, y, x + 70, y + 24), fill=(0, 0, 0))
            d.text((x + 4, y + 2), label, fill=(255, 220, 0), font=font)
        p = out / f"sheet_{s // per + 1:02d}.jpg"
        sheet.save(p, quality=85)
        outs.append(p)
    return outs


# ---------------------------------------------------------------- audio
def audio_stats(path, dur):
    r = run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"])
    txt = r.stderr
    summ = txt[txt.rfind("Summary:"):] if "Summary:" in txt else txt

    def grab(pat):
        m = re.search(pat, summ)
        return float(m.group(1)) if m else None
    res = {"lufs": grab(r"I:\s+(-?[\d.]+) LUFS"), "lra": grab(r"LRA:\s+(-?[\d.]+) LU"),
           "true_peak": grab(r"Peak:\s+(-?[\d.]+) dBFS")}
    r = run(["ffmpeg", "-nostats", "-i", str(path), "-af", "silencedetect=noise=-35dB:d=0.3", "-f", "null", "-"])
    sil = [float(x) for x in re.findall(r"silence_duration: ([\d.]+)", r.stderr)]
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    res["silences"] = list(zip(starts, sil))
    res["silence_total"] = sum(sil)
    return res


# ---------------------------------------------------------------- speech
def speech_from_captions(vid, out, dur):
    from collect import fetch_detail
    d = fetch_detail(vid, True, out)
    tr = d.get("transcript")
    if not tr:
        return None
    lines = []
    for ln in Path(tr["file"]).read_text(encoding="utf-8").splitlines():
        m = re.match(r"\[(\d+):([\d.]+)\] (.*)", ln)
        if m:
            lines.append((int(m.group(1)) * 60 + float(m.group(2)), re.sub(r"\[\w+\]", "", m.group(3)).strip()))
    words = sum(len(t.split()) for _, t in lines)
    start = lines[0][0] if lines else 0
    return {"source": f"caption YouTube ({tr['lang']}, {tr['kind']})", "words": words,
            # caption otomatis terlambat 1-3 s, jadi tempo dihitung atas durasi penuh
            "wps": words / dur, "start": start, "pauses": None, "file": tr["file"],
            "title": d.get("title"), "views": d.get("view_count")}


def speech_from_whisper(path, out, model="small"):
    from faster_whisper import WhisperModel
    log(f"Whisper {model} ...")
    m = WhisperModel(model, device="cpu", compute_type="int8")
    segs, info = m.transcribe(str(path), word_timestamps=True, vad_filter=True)
    words = [w for s in segs for w in (s.words or [])]
    if not words:
        return None
    gaps = [b.start - a.end for a, b in zip(words, words[1:])]
    p = out / "transcript_whisper.txt"
    with open(p, "w", encoding="utf-8") as f:
        for w in words:
            f.write(f"{w.start:7.2f} {w.end:7.2f} {w.word.strip()}\n")
    span = words[-1].end - words[0].start
    return {"source": f"faster-whisper {model} ({info.language})", "words": len(words), "wps": len(words) / span,
            "start": words[0].start, "pauses": sum(g > 0.5 for g in gaps), "longest_pause": max(gaps or [0]),
            "file": str(p)}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="file video atau link/ID YouTube")
    ap.add_argument("--out", required=True)
    ap.add_argument("--whisper", action="store_true", help="transkripsi dengan faster-whisper (untuk file lokal)")
    ap.add_argument("--model", default="small")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    path, vid = get_video(a.src, out)
    info = probe(path)
    log(f"{info['width']}x{info['height']} {info['fps']} fps {info['duration']:.1f} s")

    afps = 10
    frames = decode(path, afps, 32, info)
    cuts, motion, hdiff = detect_cuts(frames, afps)
    bounds = [0.0] + cuts + [info["duration"]]
    shots = [b - a for a, b in zip(bounds, bounds[1:]) if b - a > 0.05]
    per_sec = [float(np.mean(motion[i * afps:(i + 1) * afps])) for i in range(int(len(motion) / afps))]

    f1 = decode(path, 1, 160, info)
    pal = palette(f1)
    sat, val = hsv_stats(f1)
    sheet_files = sheets(path, out, info)
    au = audio_stats(path, info["duration"])

    sp = None
    if a.whisper:
        sp = speech_from_whisper(path, out, a.model)
    elif vid:
        sp = speech_from_captions(vid, out, info["duration"])

    L = [f"# Data Style DNA: {sp.get('title') if sp and sp.get('title') else path.name}\n",
         f"Sumber: {a.src}  " + (f"(views {sp['views']:,})" if sp and sp.get("views") else ""),
         "", "## Format", "",
         f"- {info['width']}x{info['height']} ({info['ratio']}), {info['fps']} FPS, {info['duration']:.1f} detik, "
         f"video {info['vcodec']}, audio {info['acodec']}",
         "- Catatan: kalau diunduh dari YouTube, FPS dan resolusi adalah versi unduhan, bukan master aslinya.",
         "", "## Potongan dan kamera", "",
         f"- **Sekitar {len(shots)} shot** (perkiraan, cenderung sedikit kurang), rata-rata {st.mean(shots):.2f} s, median {st.median(shots):.2f} s, "
         f"terpendek {min(shots):.2f} s, terpanjang {max(shots):.2f} s.",
         f"- Cut per 10 detik: " + ", ".join(
             f"{i * 10}-{i * 10 + 10}s: {sum(1 for c in cuts if i * 10 <= c < i * 10 + 10)}"
             for i in range(int(info["duration"] // 10) + 1)),
         f"- Waktu cut: " + ", ".join(f"{c:.1f}" for c in cuts),
         f"- Gerak per detik (selisih piksel antar frame, 0 = kamera diam, >15 = gerak cepat/whip): "
         + " ".join(f"{m:.0f}" for m in per_sec),
         f"- Median gerak {st.median(per_sec):.1f}. Detik nyaris diam (< 3): {sum(m < 3 for m in per_sec)} dari {len(per_sec)}.",
         "- Deteksi cut ini heuristik. Cocokkan dengan lembar kontak: kalau dua sel berurutan komposisinya beda "
         "tapi tidak ada cut tercatat, itu transisi halus (whip/dissolve) atau cut yang terlewat.",
         "", "## Warna", "",
         "- Palet dominan: " + ", ".join(f"{h} ({p:.0f}%)" for h, p in pal),
         f"- Saturasi rata-rata {st.mean(sat):.0f}% (rentang {min(sat):.0f}-{max(sat):.0f}), "
         f"kecerahan rata-rata {st.mean(val):.0f}% (rentang {min(val):.0f}-{max(val):.0f}).",
         "- Saturasi per detik: " + " ".join(f"{x:.0f}" for x in sat),
         "- Kecerahan per detik: " + " ".join(f"{x:.0f}" for x in val),
         "", "## Audio", "",
         f"- Loudness terintegrasi {au['lufs']} LUFS, true peak {au['true_peak']} dBFS, LRA {au['lra']} LU.",
         f"- Jeda hening (< -35 dB, >= 0,3 s): {len(au['silences'])} kali, total {au['silence_total']:.1f} s"
         + (": " + ", ".join(f"{s:.1f}s ({d:.1f})" for s, d in au["silences"][:12]) if au["silences"] else
            " (audio penuh dari awal sampai akhir)."),
         "", "## Bicara", ""]
    if sp:
        L += [f"- Sumber: {sp['source']}. {sp['words']} kata, **{sp['wps']:.2f} kata/detik** "
              f"({sp['wps'] * 60:.0f} kata/menit), kata pertama di {sp['start']:.1f} s.",
              f"- Transkrip: {sp['file']}"]
        if sp.get("pauses") is not None:
            L.append(f"- Jeda bicara > 0,5 s: {sp['pauses']} kali, terpanjang {sp['longest_pause']:.2f} s.")
    else:
        L.append("- Tidak ada transkrip. Jalankan ulang dengan --whisper.")
    L += ["", "## Lembar kontak (1 frame per detik, label = waktu)", ""] + [f"- {p}" for p in sheet_files]
    (out / "style_data.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    json.dump({"info": info, "cuts": cuts, "shots": shots, "motion_per_sec": per_sec, "palette": pal,
               "sat": sat, "val": val, "audio": au, "speech": sp},
              open(out / "style_data.json", "w", encoding="utf-8"), indent=1, default=str)
    print(out / "style_data.md")


if __name__ == "__main__":
    main()
