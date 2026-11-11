---
name: research-skill
description: "Research Skill: riset video dan channel YouTube berbasis data terukur, hasil akhirnya laporan analisa bahasa Indonesia. Stage 1 Style DNA: ukur satu video (file atau link) untuk format, jumlah dan panjang shot, gerak kamera, palet warna, LUFS, jeda hening, tempo bicara, plus lembar kontak per detik. Stage 2 riset channel tanpa API key (yt-dlp): semua video/Shorts, median, outlier, pivot format, velocity views/hari, views:subscriber, jadwal upload WIB, formula judul, transkrip dan hook, framework narasi (beat map + jatah kata untuk VO Indonesia user). Pakai skill ini setiap kali user menulis 'riset channel', 'analisa channel', 'bedah channel', 'research channel', 'cek kompetitor', 'kenapa channel ini viral', 'pelajari channel ini', 'cari formula judul', 'bandingkan channel', 'analisis video ini', 'petakan style/DNA video ini', 'Style DNA', '@research-skill', atau menempelkan link youtube.com/@... atau link video dan bertanya soal performa, gaya, judul, hook, atau strateginya. Tidak membuat pitch topik atau naskah (user mengerjakannya di ChatGPT dari laporan ini), tidak merender video, dan tidak membangun skill gaya baru (pakai style-cloner)."
---

# Research Skill

Skill ini meriset video atau channel YouTube dan menghasilkan **laporan analisa**. Semua kesimpulan berasal dari data yang diukur skrip (yt-dlp, ffmpeg, caption YouTube), lalu dibaca dan ditafsirkan olehmu. Kalau angka dan pengamatan bertentangan, sebutkan.

Laporan adalah produk akhir. User akan membawanya ke ChatGPT untuk mencari topik dan menulis naskah, jadi **jangan membuat pitch, ide video, atau naskah**. Sebaliknya, pastikan laporan memuat semua yang dibutuhkan untuk itu: formula judul, beat map dengan jatah kata, contoh hook asli, dan aturan gaya bahasa.

User membuat video animasi pendek berbahasa Indonesia dengan VO ElevenLabs. VO-nya terukur sekitar **2,25 kata/detik**, rata-rata dari 12 VO di `D:/basic-style-3/*/vo/timing.json`. Kalau user minta, ukur ulang dari VO terbarunya.

## Pilih stage dari permintaan

| Permintaan | Stage | Hasil |
|---|---|---|
| File video atau link satu video, "petakan style/DNA" | 1 | `Style_DNA_<judul>.md` |
| Link/handle channel, "riset/bedah channel", "cari formula judul", "bandingkan channel" | 2 (+1 untuk 1-2 video teratas kalau visual/editing ikut ditanyakan) | `Analisa channel <slug>.md` |

Untuk channel yang sudah pernah diriset, pakai ulang `research_notes/<slug>/` kecuali datanya lebih tua dari sekitar seminggu atau user minta data baru.

## Lokasi dan alat

- Skrip ada di `~/.claude/skills/research-skill/scripts/` (singkat `$S`). Jalankan dengan `PYTHONIOENCODING=utf-8` supaya judul ber-emoji tidak membuat konsol Windows error.
- Data mentah: `$HOME/OneDrive/Desktop/research_notes/<slug>/` (`<slug>` = handle tanpa `@`, huruf kecil).
- Laporan dan Style DNA: `$HOME/OneDrive/Desktop/reports/`.
- Kebutuhan: Python 3.12 dengan yt-dlp, numpy, dan Pillow; ffmpeg/ffprobe di PATH; faster-whisper (model tiny-medium sudah ter-cache) untuk video tanpa caption. Semuanya sudah terpasang.
- Kalau yt-dlp gagal karena YouTube berubah, perbarui dulu: `python -m pip install -U yt-dlp`.

## Stage 1: Style DNA

```bash
PYTHONIOENCODING=utf-8 python $S/style_dna.py <file.mp4 | link YouTube> --out "<notes>/style/<id-atau-nama>"
```

- Untuk file lokal tambahkan `--whisper` supaya tempo bicara terukur.
- Hasilnya `style_data.md` (angka) dan `sheet_*.jpg` (1 frame per detik, berlabel waktu). Prosesnya sekitar 20 detik per video 1 menit.

Lalu baca `references/style-dna.md`, buka **semua** lembar kontak, dan tulis `Style_DNA_<judul>.md`. Detektor shot menghitung pergantian komposisi (whip dan dissolve ikut terhitung) dan cenderung kurang hitung 10-15%; koreksi dengan lembar kontak.

## Stage 2: Riset channel

1. **Kumpulkan data**:
   ```bash
   PYTHONIOENCODING=utf-8 python $S/collect.py @handle --out "<notes>"
   ```
   - Hasilnya: semua judul dan views per tab; detail (tanggal, like, komentar, tag) untuk 15 terlaris + 30 terbaru per tab; 12 transkrip; thumbnail dan lembar kontaknya. Biasanya selesai di bawah 2 menit.
   - Input boleh berupa @handle, URL channel, ID UC..., atau URL salah satu video channel itu.
   - Opsi:
     - `--recent 60` atau `--all-details`: tanggal lebih lengkap
     - `--transcripts 20`: contoh hook lebih banyak
     - `--max 200`: channel yang sangat besar
     - `--workers 2`: kalau kena HTTP 429
2. **Statistik**: `python $S/analyze.py "<notes>"` menulis `stats.md`, berisi:
   - median, outlier, tren terbaru ke terlama (pivot format)
   - durasi vs views, ciri judul teratas vs terbawah
   - jadwal upload (WIB), velocity views/hari, views:subscriber
   - engagement, hook 8 detik pertama, kata per menit
3. **Bahan framework**: `python $S/framework.py "<notes>" --since <YYYYMMDD awal era sekarang>` menulis `framework_input.md`, berisi:
   - tempo pemenang terukur
   - pembuka kalimat yang berulang beserta posisinya
   - teks dan jumlah kata per 10% durasi untuk 5 pemenang dan 2 pembanding sepi (transkripnya diambil otomatis)
   - jatah kata untuk VO target

   Tentukan `--since` dari tabel tren di `stats.md`; tanpa itu, video era lama ikut tercampur. Opsi lain: `--ids` / `--contrast-ids` untuk memilih video sendiri, `--target-dur`, `--target-wps`.
4. **Baca bahan mentah.** Angka saja tidak menjelaskan *kenapa*. Baca:
   - `stats.md` dan `framework_input.md` seluruhnya
   - lembar kontak thumbnail
   - minimal 5 transkrip pemenang dan 2 yang sepi, dibaca utuh
5. **Opsional, Stage 1 untuk 1-2 video teratas** kalau user peduli visual atau editing.
6. **Tulis laporan** `Analisa channel <slug>.md` sesuai `references/channel-report.md`. Framework narasi (beat map, jatah kata versi channel dan versi VO user, aturan wajib, kenapa video sepi kalah) masuk ke dalam laporan, sehingga satu file sudah cukup dibawa ke ChatGPT.

Untuk membandingkan beberapa channel, jalankan langkah 1-3 per channel ke folder masing-masing, lalu tulis satu laporan perbandingan.

`references/case-ricksclips.md` berisi contoh hasil yang sudah diukur, untuk acuan bentuk. Bukan patokan channel lain.

## Cara menyerahkan hasil

Di chat, beri 4-6 poin temuan terpenting dengan angka, lalu link ke laporan dan folder data. Jangan menempel seluruh laporan. Tidak perlu menawarkan pitch atau naskah.

## Kalau ada masalah

- **Tab tidak ada** ("does not have a videos tab"): normal, tab lain tetap diambil.
- **HTTP 429 atau banyak detail gagal**: jalankan lagi dengan `--workers 2`, atau tunggu beberapa menit.
- **Video tanpa caption**: jalankan `style_dna.py --whisper`, atau unduh audionya lalu transkripsi dengan faster-whisper.
- **Unduhan video gagal**: minta user mengirim file videonya, lalu jalankan Stage 1 pada file itu.
- **Views Shorts dibulatkan**: angka di daftar Shorts dibulatkan YouTube; angka dari detail lebih tepat dan otomatis menimpanya.
- **Video baru**: video berumur kurang dari seminggu jangan dicap gagal; nilai dari views/hari.
