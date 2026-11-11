# Stage 1: menulis Style DNA

Bahan: `style_data.md` dari `scripts/style_dna.py` plus lembar kontak `sheet_*.jpg` (1 frame per detik, label waktu di pojok). Angka diambil dari data; kesan visual diambil dari lembar kontak yang benar-benar kamu buka. Kalau keduanya bertentangan, percayai lembar kontak dan catat perbedaannya.

## Cara membaca lembar kontak

Buka semua sheet dengan Read. Untuk tiap detik catat dalam hati: shot baru atau lanjutan, jenis shot (wide, medium, close-up, insert benda), arah gerak kamera, siapa di layar, posisi dan gaya caption. Cocokkan dengan waktu cut di data:

- dua sel berurutan beda komposisi dan ada cut di antaranya = pergantian shot terkonfirmasi
- beda komposisi tanpa cut tercatat = transisi halus atau cut yang terlewat (detektor cenderung kurang hitung 10-15%)
- satu cut tercatat tapi sel sebelum dan sesudah mirip = kamera bergerak cepat dalam satu shot

Sel yang kabur atau bergaris memanjang adalah whip pan / motion blur, ciri transisi yang penting dicatat.

## Angka acuan

- Gerak per detik: < 3 kamera diam (gaya kalem, misalnya Marc AHO), 5-15 dorong/orbit pelan, > 15 kamera terbang atau whip.
- Loudness Shorts umumnya -14 sampai -16 LUFS dengan true peak di bawah -1 dBFS. Nol jeda hening = audio penuh (VO + musik/SFX menutup setiap celah).
- Tempo bicara Inggris channel cerita cepat: 3,4-3,9 kata/detik. VO Indonesia milik user terukur 2,25 kata/detik (rata-rata 12 VO di `D:/basic-style-3/*/vo/timing.json`).
- Video dari YouTube biasanya 30 FPS hasil re-encode. Kalau gerak terasa sangat halus, sebutkan kemungkinan master aslinya 60 FPS.

## Format `Style_DNA_<judul>.md`

```markdown
# Style DNA: <judul video> (<channel>)
_Sumber: <link>, <views>, diukur <tanggal>. Data mentah: <folder>._

## Ringkasan gaya (3-5 baris)
Kalimat yang bisa dipakai sebagai brief: "kartun 2D bergaris tinta di dunia 3D jenuh, kamera terbang, ganti shot tiap ~1,8 s ..."

## 1. Format
Rasio, resolusi, FPS, durasi.

## 2. Visual
- Karakter: bentuk kepala/badan, wajah, outline, kostum, cara masuk frame.
- Dunia/set: lokasi per beat, material (painted, low-poly, foto), properti kunci.
- Warna: palet terukur (hex + %), saturasi/kecerahan rata-rata, pergeseran warna antar beat (lihat deret per detik).
- Cahaya: arah, keras/lembut, jam (siang, senja, malam).
- Teks di dunia: papan, koran, stempel, angka.

## 3. Kamera dan editing
- Jumlah shot, panjang shot median, cut per 10 detik (di mana paling rapat).
- Jenis gerak: dolly/orbit/terbang/whip, dari deret gerak per detik + lembar kontak.
- Transisi: hard cut, whip, dissolve, match cut. Sebut contoh dengan detiknya.

## 4. Caption
Jumlah kata per tampilan, font (perkiraan), warna, outline, posisi (tetap atau mengikuti komposisi), animasi masuk, kata kunci yang di-highlight.

## 5. Audio
LUFS, true peak, jeda hening, lapisan (VO, musik, SFX), tempo bicara terukur.

## 6. Narasi singkat
Hook, titik balik, penutup, dengan detik (rinci lengkapnya di framework channel).

## 7. Checklist produksi
Daftar centang yang bisa langsung dipakai saat render: rasio, FPS, shot rata-rata, transisi, palet, caption, loudness, tempo VO, aturan karakter.

## 8. Skill produksi yang paling mirip
Bandingkan dengan skill user dan sebut apa saja yang perlu disesuaikan:
- basic-rick-style: 2D tinta di dunia 3D jenuh, kamera terbang
- basic-style 1: peta parchment + chibi
- basic-style 2: tinta malam + gag UI game
- basic-style 3: 3D sinematik, kepala bulat mata cincin
- basic-style-4: stiker 2D di set 3D bersih, hard cut
- basic-style-5: desa low-poly, kepala bola krem
- basic-2d-vintage-character: kartun vintage
- basic-jkson-what-if-style: stick figure What If
- marc-aho: dialog persona + dino Claude

Kalau tidak ada yang cocok, sarankan style-cloner.
```
