#!/usr/bin/env python3
"""Ubah data.json dari collect.py jadi stats.md: angka, pola judul, jadwal upload, hook.

  python analyze.py "D:/riset/ricksclips"        (folder yang berisi data.json)
"""
import json
import re
import statistics as st
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

STOP = set("""a an the of to in on for and or is are was were be been it its this that with as at by from
how why what when who which you your i my we our they their he she his her them me us not no do does did
can will just so but if then than into out up about all one new more most very too
yang dan di ke dari ini itu untuk dengan pada adalah ada tidak bisa jadi kita kamu aku saya mereka
dia akan sudah juga atau karena saat lalu tapi agar oleh para sang si""".split())
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\U0001F000-\U0001F2FF]")
WIB = timezone(timedelta(hours=7))
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def human(n):
    if n is None:
        return "?"
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= div:
            return f"{n / div:.1f}{suf}"
    return f"{n:.0f}"


def dur(s):
    if not s:
        return "?"
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def date(d):
    return f"{d[:4]}-{d[4:6]}-{d[6:]}" if d else "?"


def med(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else None


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(c).replace("|", "/") for c in r) + " |" for r in rows]
    return "\n".join(out)


def title_traits(titles):
    n = len(titles) or 1
    words = [len(t.split()) for t in titles]
    return {
        "jumlah": len(titles),
        "rata2 kata": f"{st.mean(words):.1f}" if words else "?",
        "rata2 huruf": f"{st.mean(len(t) for t in titles):.0f}" if titles else "?",
        "ada angka": f"{100 * sum(bool(re.search(r'\d', t)) for t in titles) / n:.0f}%",
        "tanda tanya": f"{100 * sum('?' in t for t in titles) / n:.0f}%",
        "tanda seru": f"{100 * sum('!' in t for t in titles) / n:.0f}%",
        "emoji": f"{100 * sum(bool(EMOJI.search(t)) for t in titles) / n:.0f}%",
        "KATA KAPITAL": f"{100 * sum(bool(re.search(r'\b[A-Z]{3,}\b', t)) for t in titles) / n:.0f}%",
        "hashtag": f"{100 * sum('#' in t for t in titles) / n:.0f}%",
    }


def tab_section(tab, rows, details):
    L = []
    views = [r["views"] for r in rows if r.get("views") is not None]
    if not views:
        return f"## Tab {tab}\n\nTidak ada data views.\n"
    m = st.median(views)
    L.append(f"## Tab {tab} ({len(rows)} video)\n")
    L.append(table(["median", "rata-rata", "p90", "tertinggi", "total views"],
                   [[human(m), human(st.mean(views)), human(sorted(views)[int(0.9 * (len(views) - 1))]),
                     human(max(views)), human(sum(views))]]))

    # Tren per posisi (0 = terbaru) — kelihatan pivot walau tanggal tidak lengkap
    L.append("\n### Tren dari terbaru ke terlama (median views per kelompok)\n")
    buckets = [(0, 10), (10, 30), (30, 60), (60, 100), (100, 200), (200, 10 ** 9)]
    trow = []
    for a, b in buckets:
        chunk = [r for r in rows if a <= r["pos"] < b]
        if not chunk:
            continue
        ds = [r.get("upload_date") for r in chunk if r.get("upload_date")]
        span = f"{date(min(ds))} s/d {date(max(ds))}" if ds else "-"
        trow.append([f"#{a + 1}-{a + len(chunk)}", len(chunk), human(med([r['views'] for r in chunk])), span])
    L.append(table(["urutan (1 = terbaru)", "jumlah", "median views", "tanggal (yang diketahui)"], trow))

    # Terlaris
    top = sorted([r for r in rows if r.get("views") is not None], key=lambda r: -r["views"])[:20]
    L.append(f"\n### 20 terlaris\n")
    L.append(table(["#", "judul", "views", "x median", "durasi", "tanggal", "link"],
                   [[i + 1, r["title"], human(r["views"]), f"{r['views'] / m:.1f}x", dur(r.get("duration")),
                     date(r.get("upload_date")), f"youtu.be/{r['id']}"] for i, r in enumerate(top)]))

    out_ = [r for r in rows if r.get("views") and r["views"] >= 3 * m]
    L.append(f"\n**Outlier** (>= 3x median): {len(out_)} dari {len(rows)} video "
             f"({100 * len(out_) / len(rows):.0f}%).")
    flop = sorted([r for r in rows if r.get("views") is not None], key=lambda r: r["views"])[:8]
    L.append("\n### 8 paling sepi\n")
    L.append(table(["judul", "views", "urutan", "tanggal"],
                   [[r["title"], human(r["views"]), r["pos"] + 1, date(r.get("upload_date"))] for r in flop]))

    # Durasi
    ds = [r for r in rows if r.get("duration")]
    if ds:
        edges = [0, 20, 40, 60, 90, 181] if tab == "shorts" else [0, 300, 600, 1200, 2400, 10 ** 9]
        lab = (lambda a, b: f"{a}-{b - 1} dtk") if tab == "shorts" else (lambda a, b: f"{a // 60}-{b // 60} mnt" if b < 10 ** 8 else f">{a // 60} mnt")
        rws = []
        for a, b in zip(edges, edges[1:]):
            c = [r for r in ds if a <= r["duration"] < b]
            if c:
                rws.append([lab(a, b), len(c), human(med([r['views'] for r in c]))])
        L.append("\n### Durasi vs views\n")
        L.append(table(["durasi", "jumlah", "median views"], rws))

    # Judul: terlaris vs paling sepi
    srt = sorted([r for r in rows if r.get("views") is not None], key=lambda r: -r["views"])
    k = max(5, len(srt) // 4)
    tt, bt = title_traits([r["title"] or "" for r in srt[:k]]), title_traits([r["title"] or "" for r in srt[-k:]])
    L.append(f"\n### Ciri judul: {k} teratas vs {k} terbawah\n")
    L.append(table(["ciri", "teratas", "terbawah"], [[key, tt[key], bt[key]] for key in tt]))
    first = Counter(" ".join((r["title"] or "").split()[:2]).lower() for r in rows)
    first1 = Counter(((r["title"] or "").split() or [""])[0].lower() for r in rows)
    words = Counter(w for r in rows for w in re.findall(r"[a-zA-Z\u00C0-\u024F']{3,}", (r["title"] or "").lower())
                    if w not in STOP)
    L.append("\n**Kata pembuka judul:** " + ", ".join(f"{w} ({c})" for w, c in first1.most_common(10)))
    L.append("\n**Dua kata pembuka:** " + ", ".join(f"\"{w}\" ({c})" for w, c in first.most_common(10) if c > 1))
    L.append("\n**Kata paling sering:** " + ", ".join(f"{w} ({c})" for w, c in words.most_common(25)))
    return "\n".join(L) + "\n"


def main():
    folder = Path(sys.argv[1])
    data = json.load(open(folder / "data.json", encoding="utf-8"))
    ch, tabs, details = data["channel"], data["tabs"], data["details"]
    good = {k: v for k, v in details.items() if not v.get("error")}
    L = [f"# Statistik channel: {ch.get('name')}\n",
         f"- URL: {ch.get('url')}  ({ch.get('handle')})",
         f"- Subscriber: {human(ch.get('subscribers'))}",
         f"- Diambil: {data['collected_at']}",
         f"- Jumlah video: " + ", ".join(f"{t} {len(r)}" for t, r in tabs.items() if r),
         f"- Deskripsi channel: {(ch.get('description') or '-').strip()[:400]}",
         f"- Detail lengkap diambil untuk {len(good)} video (terlaris + terbaru). Angka bulanan, jadwal, dan "
         f"engagement di bawah hanya dari video itu, jadi condong ke video terlaris.\n"]
    for tab, rows in tabs.items():
        if rows:
            L.append(tab_section(tab, rows, good))

    # Jadwal upload: hanya deretan video terbaru yang tanggalnya diketahui tanpa celah
    # (video lama terlaris juga punya tanggal, tapi akan merusak hitungan frekuensi).
    dated = sorted([v for v in good.values() if v.get("timestamp")], key=lambda v: -v["timestamp"])
    recent = []
    for rows in tabs.values():
        for r in sorted(rows, key=lambda r: r["pos"]):
            t = (good.get(r["id"]) or {}).get("timestamp")
            if not t:
                break
            recent.append(t)
    recent = sorted(recent, reverse=True)
    if len(recent) >= 3:
        L.append("## Jadwal upload (deretan video terbaru)\n")
        ts = recent
        gaps = [(a - b) / 86400 for a, b in zip(recent, recent[1:])]
        span = (recent[0] - recent[-1]) / 86400 or 1
        L.append(f"- {len(recent)} upload terbaru: rentang {span:.0f} hari, kira-kira {7 * (len(recent) - 1) / span:.1f} "
                 f"video per minggu, jeda median {st.median(gaps):.1f} hari.")
        now = datetime.fromisoformat(data["collected_at"]).timestamp()
        for days in (30, 90):
            n = sum(1 for t in ts if now - t <= days * 86400)
            if len(ts) > n or days == 30:
                L.append(f"- {days} hari terakhir: {n} upload ({7 * n / days:.1f} per minggu).")
        last = datetime.fromtimestamp(ts[0], WIB)
        L.append(f"- Upload terakhir: {last:%Y-%m-%d %H:%M} WIB.")
        wd = Counter(HARI[datetime.fromtimestamp(t, WIB).weekday()] for t in recent)
        hr = Counter(datetime.fromtimestamp(t, WIB).hour for t in recent)
        L.append("- Hari (WIB): " + ", ".join(f"{d} {c}" for d, c in wd.most_common()))
        L.append("- Jam (WIB): " + ", ".join(f"{h:02d}:00 {c}" for h, c in hr.most_common(6)))
        months = {}
        for v in dated:
            months.setdefault(v["upload_date"][:6], []).append(v["view_count"])
        L.append("\n### Per bulan (video yang diketahui tanggalnya)\n")
        L.append(table(["bulan", "jumlah", "median views"],
                       [[f"{m[:4]}-{m[4:]}", len(v), human(med(v))] for m, v in sorted(months.items(), reverse=True)]))
        L.append("")

    # Velocity: views per hari dan rasio views:subscriber untuk video yang tanggalnya diketahui
    nowdt = datetime.fromisoformat(data["collected_at"])
    subs = ch.get("subscribers")
    vel = []
    for rows in tabs.values():
        for r in rows:
            v = good.get(r["id"])
            if not v or not v.get("timestamp") or not r.get("views"):
                continue
            age = max(0.5, (nowdt.timestamp() - v["timestamp"]) / 86400)
            vel.append((r, age, r["views"] / age))
    if vel:
        L.append("## Velocity (views per hari sejak upload)\n")
        L.append("Video umur < 7 hari masih naik; bandingkan dengan video lain di umur yang sama, bukan dengan total views.\n")
        fresh = sorted([x for x in vel if x[1] <= 14], key=lambda x: x[1])
        best = sorted(vel, key=lambda x: -x[2])[:10]
        hd = ["judul", "umur (hari)", "views", "views/hari"] + (["views : subs"] if subs else [])

        def fmt(x):
            row = [x[0]["title"], f"{x[1]:.1f}", human(x[0]["views"]), human(x[2])]
            return row + ([f"{x[0]['views'] / subs:.1f}x"] if subs else [])
        if fresh:
            L.append("### Video 14 hari terakhir\n")
            L.append(table(hd, [fmt(x) for x in fresh]))
        L.append("\n### Velocity tertinggi\n")
        L.append(table(hd, [fmt(x) for x in best]))
        if subs:
            ratios = [x[0]["views"] / subs for x in vel]
            L.append(f"\nMedian views : subscriber = {st.median(ratios):.1f}x. Jauh di atas 1x artinya views datang dari "
                     f"feed/rekomendasi, bukan dari subscriber.")
        L.append("")

    # Engagement
    eng =[v for v in good.values() if v.get("view_count")]
    if eng:
        lk = [100 * v["like_count"] / v["view_count"] for v in eng if v.get("like_count")]
        cm = [100 * v["comment_count"] / v["view_count"] for v in eng if v.get("comment_count")]
        L.append("## Engagement (video yang diambil detailnya)\n")
        if lk:
            L.append(f"- Like per view: median {st.median(lk):.2f}%")
        if cm:
            L.append(f"- Komentar per view: median {st.median(cm):.3f}%")
        tags = Counter(t.lower() for v in good.values() for t in (v.get("tags") or []))
        if tags:
            L.append("- Tag terbanyak: " + ", ".join(f"{t} ({c})" for t, c in tags.most_common(20)))
        cats = Counter(c for v in good.values() for c in (v.get("categories") or []))
        if cats:
            L.append("- Kategori: " + ", ".join(f"{t} ({c})" for t, c in cats.most_common()))
        langs = Counter(v.get("language") or "?" for v in good.values())
        L.append("- Bahasa audio: " + ", ".join(f"{t} ({c})" for t, c in langs.most_common()))
        L.append("")

    # Transkrip: hook + tempo bicara
    tr = [v for v in good.values() if v.get("transcript")]
    if tr:
        L.append("## Transkrip dan hook\n")
        L.append("Hook = kalimat pada 8 detik pertama. Tempo = kata per menit (jumlah kata / durasi video).\n")
        rows = []
        for v in sorted(tr, key=lambda v: -(v.get("view_count") or 0)):
            lines = Path(v["transcript"]["file"]).read_text(encoding="utf-8").splitlines()
            hook = []
            for ln in lines:
                m = re.match(r"\[(\d+):([\d.]+)\] (.*)", ln)
                if m and int(m.group(1)) * 60 + float(m.group(2)) <= 8:
                    hook.append(m.group(3))
            wpm = v["transcript"]["words"] / (v["duration"] / 60) if v.get("duration") else None
            rows.append([v["title"], human(v.get("view_count")), f"{wpm:.0f}" if wpm else "?", " ".join(hook)[:220],
                         Path(v["transcript"]["file"]).name])
        L.append(table(["judul", "views", "kata/menit", "hook (8 dtk pertama)", "file"], rows))
        L.append("")
    no_tr = [v for v in good.values() if v.get("transcript_error")]
    if no_tr:
        L.append(f"_{len(no_tr)} transkrip gagal diunduh._\n")

    if data.get("contact_sheets"):
        L.append("## Lembar kontak thumbnail\n")
        L += [f"- {p}" for p in data["contact_sheets"]]

    (folder / "stats.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(folder / "stats.md")


if __name__ == "__main__":
    main()
