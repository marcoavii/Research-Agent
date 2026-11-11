# Research Agent

Skill Claude Code untuk meriset video dan channel YouTube berbasis **data terukur**, dengan hasil akhir **laporan analisa berbahasa Indonesia**. Laporannya siap dibawa ke ChatGPT (atau tempat lain) untuk mencari topik dan menulis naskah.

Gabungan dan versi lanjutan dari [Research-Skill-Agent](https://github.com/marcoavii/Research-Skill-Agent). Semua pengukuran sekarang dikerjakan skrip (yt-dlp, ffmpeg, caption YouTube), bukan JavaScript manual di browser.

## Yang dikerjakan

**Stage 1: Style DNA** (satu video, file lokal atau link YouTube)
- format, jumlah shot, panjang shot, gerak kamera per detik
- palet warna, saturasi, kecerahan
- loudness (LUFS), true peak, jeda hening
- tempo bicara dari caption YouTube atau faster-whisper
- lembar kontak 1 frame per detik berlabel waktu

**Stage 2: Riset channel** (tanpa API key)
- semua video, Shorts, dan live beserta views
- median, outlier, tren dari terbaru ke terlama (kapan channel ganti format)
- velocity (views per hari) dan rasio views:subscriber
- durasi vs views, ciri judul teratas vs terbawah, jadwal upload (WIB), engagement
- transkrip, hook 8 detik pertama, tempo bicara
- **framework narasi**: pembuka kalimat yang berulang beserta posisinya, kata per 10% durasi, dan beat map dengan jatah kata untuk VO target

Hasil akhirnya satu file `Analisa channel <nama>.md`. Contohnya ada di [`examples/`](examples/).

Skill ini tidak membuat pitch topik, naskah, atau video.

## Pasang

```bash
git clone https://github.com/marcoavii/Research-Agent.git
cp -r Research-Agent/research-skill ~/.claude/skills/
```

Kebutuhan: Python 3.10+ dengan `yt-dlp`, `numpy`, `Pillow`, serta `ffmpeg`/`ffprobe` di PATH. Opsional: `faster-whisper` untuk video tanpa caption.

```bash
python -m pip install -U yt-dlp numpy Pillow faster-whisper
```

## Pakai

Di Claude Code, cukup tulis:

- `riset channel @RicksClips3000`
- `bedah channel ini https://www.youtube.com/@namachannel`
- `bandingkan channel @a dan @b`
- `petakan Style DNA video ini https://youtu.be/...`

Skripnya juga bisa dijalankan langsung:

```bash
S=~/.claude/skills/research-skill/scripts
python $S/collect.py @handle --out notes/handle          # data channel
python $S/analyze.py notes/handle                        # stats.md
python $S/framework.py notes/handle --since 20261007     # framework_input.md
python $S/style_dna.py https://youtu.be/ID --out notes/handle/style/ID
```

Di Windows, jalankan dengan `PYTHONIOENCODING=utf-8` supaya judul ber-emoji tidak membuat konsol error.

## Struktur

```text
research-skill/
├── SKILL.md                    alur kerja dan aturan
├── scripts/
│   ├── collect.py              data channel lewat yt-dlp
│   ├── analyze.py              statistik, velocity, jadwal, judul, hook
│   ├── framework.py            bahan beat map + jatah kata
│   └── style_dna.py            ukur gaya satu video
└── references/
    ├── channel-report.md       template laporan (framework ada di dalamnya)
    ├── style-dna.md            cara menulis Style DNA
    └── case-ricksclips.md      contoh hasil ukur
examples/
└── Analisa channel ricksclips3000.md
```

## Catatan akurasi

- **Deteksi shot** membandingkan komposisi 0,4 detik sebelum dan sesudah tiap titik, jadi whip pan dan dissolve ikut terhitung. Di "Why Perfect Railroads Don't Work" metode ini menangkap 13 dari sekitar 15 pergantian shot di 24 detik pertama; scene-detect ffmpeg 0.09 hanya menangkap 3.
- **Tempo bicara** dari caption YouTube cocok dengan faster-whisper: keduanya menghitung 224 kata untuk video yang sama.
- **Jatah kata default** memakai VO Indonesia 2,25 kata/detik, rata-rata dari 12 VO ElevenLabs. Ganti dengan `--target-wps` kalau tempo VO-mu berbeda.
