#!/usr/bin/env python3
"""Stage 2d, bahan framework narasi: ukur struktur naskah video pemenang vs video sepi.

Dari transkrip (caption YouTube) di folder hasil collect.py:
  - tempo bicara terukur (kata/detik) per video
  - teks dan jumlah kata per 10% durasi (desil) untuk memetakan beat
  - kalimat pembuka yang berulang lintas video ("You see,", "Then, one ...") + posisi median
  - hook (kalimat pertama), penutup, kalimat per video, sapaan orang kedua, dialog, angka
  - jatah kata per desil untuk VO target (default: 60 s x 2,25 kata/detik = VO Indonesia user)

  python framework.py "<notes>" --since 20261007
  python framework.py "<notes>" --ids VS1Z_Q-Klt8 7xS87iActkU --contrast-ids ABC123xyz00
"""
import argparse
import json
import re
import statistics as st
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

YOU = re.compile(r"\b(you|your|you're|yours|kamu|kau|lu|lo|loe|elo|anda|kalian)\b", re.I)


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def load_lines(path):
    out = []
    for ln in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"\[(\d+):([\d.]+)\] (.*)", ln)
        if m:
            txt = re.sub(r"\[(music|applause|laughter|musik)\]", "", m.group(3), flags=re.I).strip()
            if txt:
                out.append((int(m.group(1)) * 60 + float(m.group(2)), txt))
    return out


def timed_words(lines, dur):
    """Sebar kata tiap baris caption rata di antara waktu baris itu dan baris berikutnya."""
    words = []
    for i, (t, txt) in enumerate(lines):
        nxt = lines[i + 1][0] if i + 1 < len(lines) else min(dur, t + 3)
        ws = txt.split()
        step = max(0.05, (nxt - t)) / max(1, len(ws))
        words += [(t + j * step, w) for j, w in enumerate(ws)]
    return words


def sentences(words):
    out, cur, t0 = [], [], None
    for t, w in words:
        if t0 is None:
            t0 = t
        cur.append(w)
        if re.search(r"[.?!][\"'”]?$", w):
            out.append((t0, " ".join(cur)))
            cur, t0 = [], None
    if cur:
        out.append((t0, " ".join(cur)))
    return out


def opener(s, n=2):
    ws = re.findall(r"[\w']+", s.lower())
    return " ".join(ws[:n])


def measure(vid, d, tfile):
    dur = d.get("duration") or 60
    lines = load_lines(tfile)
    if not lines:
        return None
    words = timed_words(lines, dur)
    sents = sentences(words)
    start = words[0][0]
    deciles = defaultdict(list)
    for t, w in words:
        deciles[min(9, int(10 * t / dur))].append(w)
    text = " ".join(w for _, w in words)
    return {
        "id": vid, "title": d.get("title"), "views": d.get("view_count"), "date": d.get("upload_date"),
        # Caption otomatis terlambat 1-3 s dari suara, jadi tempo dihitung atas seluruh durasi.
        "dur": dur, "words": len(words), "wps": len(words) / dur, "start": start,
        "sentences": len(sents), "wpsent": len(words) / max(1, len(sents)),
        "you": len(YOU.findall(text)), "quotes": text.count('"') // 2, "numbers": len(re.findall(r"\d", text)),
        "hook": sents[0][1] if sents else "", "hook_end": (sents[1][0] if len(sents) > 1 else dur),
        "ending": sents[-1][1] if sents else "", "ends_clean": bool(re.search(r"[.?!][\"'”]?$", words[-1][1])),
        "deciles": {k: " ".join(v) for k, v in deciles.items()},
        "first90": " ".join(w for t, w in words if t <= 90),
        "dec_words": [len(deciles.get(k, [])) for k in range(10)],
        "openers": [(100 * t / dur, opener(s), opener(s, 3)) for t, s in sents],
    }


def human(n):
    if n is None:
        return "?"
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= div:
            return f"{n / div:.1f}{suf}"
    return str(n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("notes")
    ap.add_argument("--top", type=int, default=5, help="jumlah video pemenang")
    ap.add_argument("--contrast", type=int, default=2, help="jumlah video sepi sebagai pembanding")
    ap.add_argument("--since", help="hanya video sejak YYYYMMDD (era format sekarang)")
    ap.add_argument("--tab", default=None, help="videos/shorts; default tab dengan video terbanyak")
    ap.add_argument("--ids", nargs="*", help="pilih video pemenang manual")
    ap.add_argument("--contrast-ids", nargs="*", help="pilih video pembanding manual")
    ap.add_argument("--target-dur", type=float, default=60)
    ap.add_argument("--target-wps", type=float, default=2.25, help="tempo VO target (VO Indonesia user = 2,25)")
    a = ap.parse_args()

    folder = Path(a.notes)
    data = json.load(open(folder / "data.json", encoding="utf-8"))
    tab = a.tab or max(data["tabs"], key=lambda t: len(data["tabs"][t]))
    rows = data["tabs"][tab]
    det = data["details"]
    now = datetime.fromisoformat(data["collected_at"]).strftime("%Y%m%d")

    def ok(r):
        d = det.get(r["id"]) or {}
        dt = d.get("upload_date") or r.get("upload_date")
        if a.since and (not dt or dt < a.since):
            return False
        return r.get("views") is not None

    pool = sorted([r for r in rows if ok(r)], key=lambda r: -r["views"])
    if a.ids:
        win = [r for r in rows if r["id"] in a.ids]
    else:
        win = pool[: a.top]
    if a.contrast_ids:
        con = [r for r in rows if r["id"] in a.contrast_ids]
    else:  # video sepi yang sudah cukup umur (>= 7 hari) supaya adil
        old = [r for r in pool if (det.get(r["id"]) or {}).get("upload_date") and
               (datetime.strptime(now, "%Y%m%d") - datetime.strptime(det[r["id"]]["upload_date"], "%Y%m%d")).days >= 7]
        con = sorted(old, key=lambda r: r["views"])[: a.contrast]

    tdir = folder / "transcripts"
    from collect import fetch_detail
    res = {"win": [], "con": []}
    for key, group in (("win", win), ("con", con)):
        for r in group:
            d = det.get(r["id"]) or {}
            tf = (d.get("transcript") or {}).get("file")
            if not tf or not Path(tf).exists():
                log(f"Ambil transkrip {r['id']} ...")
                d = fetch_detail(r["id"], True, tdir)
                det[r["id"]] = d
                tf = (d.get("transcript") or {}).get("file")
            if not tf:
                log(f"  {r['id']}: tidak ada caption, lewati")
                continue
            m = measure(r["id"], d, tf)
            if m:
                res[key].append(m)
    json.dump(data, open(folder / "data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    W, C = res["win"], res["con"]
    if not W:
        sys.exit("Tidak ada transkrip video pemenang.")

    L = [f"# Bahan framework: {data['channel'].get('name')} ({tab})\n",
         f"Pemenang: {len(W)} video" + (f" sejak {a.since}" if a.since else "") + f". Pembanding: {len(C)} video sepi.\n",
         "## Ringkasan per video\n",
         "Kolom 'tanpa titik di akhir' dibaca dari tanda baca caption otomatis; cek manual di teks desil terakhir.\n",
         "| | judul | views | durasi | kata | kata/dtk | kalimat | kata/kalimat | sapaan 'you/kamu' | dialog | hook selesai | tanpa titik di akhir |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for tag, grp in (("menang", W), ("sepi", C)):
        for m in grp:
            L.append(f"| {tag} | {m['title']} | {human(m['views'])} | {m['dur']:.0f}s | {m['words']} | {m['wps']:.2f} | "
                     f"{m['sentences']} | {m['wpsent']:.1f} | {m['you']} | {m['quotes']} | {m['hook_end']:.1f}s | "
                     f"{'ya' if not m['ends_clean'] else 'tidak'} |")
    mw = st.median(m["wps"] for m in W)
    L.append(f"\n**Tempo pemenang: median {mw:.2f} kata/detik ({mw * 60:.0f} kata/menit).** "
             f"Panjang kalimat median {st.median(m['wpsent'] for m in W):.1f} kata.")

    # Kalimat pembuka yang berulang
    seen = defaultdict(lambda: {"vids": set(), "pos": []})
    for m in W:
        for pct, o2, o3 in m["openers"]:
            for o in {o2, o3}:
                seen[o]["vids"].add(m["id"])
                seen[o]["pos"].append(pct)
    # Frasa khas = muncul di setengah pemenang atau lebih, tapi jarang di tiap video (<= 3x rata-rata).
    # Frasa yang muncul belasan kali per video ("and the", "so if") hanya kebiasaan bicara, bukan jangkar beat.
    rec = sorted([(o, v) for o, v in seen.items()
                  if len(v["vids"]) >= max(2, len(W) // 2) and len(v["pos"]) / len(v["vids"]) <= 3],
                 key=lambda x: (-len(x[1]["vids"]), x[0]))
    L.append("\n## Pembuka kalimat yang berulang di video pemenang\n")
    if st.median(m["dur"] for m in W) > 180:
        L.append("_Video panjang: tabel ini didominasi kebiasaan bicara. Fokus ke 90 detik pertama dan struktur bab._\n")
    if rec:
        L.append("| pembuka | muncul di | posisi (% durasi) |")
        L.append("|---|---|---|")
        for o, v in rec[:20]:
            L.append(f"| \"{o}\" | {len(v['vids'])}/{len(W)} video | " + ", ".join(f"{p:.0f}" for p in sorted(v["pos"])) + " |")
    else:
        L.append("Tidak ada pembuka yang berulang di setengah video atau lebih.")

    # Distribusi kata per desil + jatah kata target
    share = [st.mean(m["dec_words"][k] / max(1, m["words"]) for m in W) for k in range(10)]
    total = a.target_dur * a.target_wps
    L.append(f"\n## Distribusi kata per 10% durasi dan jatah untuk VO target\n")
    L.append(f"Target: {a.target_dur:.0f} detik x {a.target_wps} kata/detik = **{total:.0f} kata**. "
             f"Jatah = porsi kata pemenang di desil itu x total target.\n")
    L.append("| desil | detik (target) | porsi kata pemenang | jatah kata |")
    L.append("|---|---|---|---|")
    for k in range(10):
        L.append(f"| {k * 10}-{k * 10 + 10}% | {a.target_dur * k / 10:.0f}-{a.target_dur * (k + 1) / 10:.0f} | "
                 f"{100 * share[k]:.0f}% | {share[k] * total:.0f} |")

    L.append("\n## Teks per desil (untuk memetakan beat)\n")
    for tag, grp in (("MENANG", W), ("SEPI", C)):
        for m in grp:
            L.append(f"### [{tag}] {m['title']} ({human(m['views'])}, {m['dur']:.0f}s, {m['date']})\n")
            L.append(f"- Hook: {m['hook']}")
            L.append(f"- Penutup: {m['ending']}\n")
            long = m["dur"] > 180  # video panjang: tampilkan 90 detik pertama utuh, desil dipotong
            if long:
                L.append(f"- **90 detik pertama:** {m['first90']}\n")
            for k in range(10):
                txt = m["deciles"].get(k, "")
                if long and len(txt.split()) > 60:
                    txt = " ".join(txt.split()[:60]) + " ..."
                L.append(f"- **{k * 10}%** ({m['dur'] * k / 10:.0f}s, {m['dec_words'][k]} kata): {txt}")
            L.append("")
    (folder / "framework_input.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(folder / "framework_input.md")


if __name__ == "__main__":
    main()
