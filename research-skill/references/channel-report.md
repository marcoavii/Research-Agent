# Stage 2: laporan analisa channel

Satu file `Analisa channel <slug>.md` adalah hasil akhir skill ini. User akan membawa laporan ini ke ChatGPT untuk pitch topik dan menulis naskah, jadi laporannya harus berdiri sendiri: semua formula, beat map, jatah kata, dan contoh kutipan ada di dalamnya. Jangan menulis pitch, ide video, atau naskah.

Bahasa Indonesia, sapa user dengan "kamu". Angka diambil dari `stats.md` dan `framework_input.md`, ukuran sampel disebut kalau kecil, dan fakta dibedakan dari dugaan ("kemungkinan", "datanya belum cukup").

## Cara membuat beat map (bagian Framework narasi)

1. Baca teks per desil semua video pemenang di `framework_input.md`. Tandai di desil mana tiap fungsi muncul: hook, konteks/taruhan, ejekan atau keraguan, tekanan naik, titik balik, penjelasan mekanisme, pembalasan, penutup.
2. Ambil rentang persentase yang konsisten di sebagian besar pemenang. Pembuka kalimat yang berulang (misalnya "You see," di 5-11% dan 66-81%) adalah jangkar beat.
3. Bandingkan dengan video sepi: beat mana yang tidak ada di sana.
4. Jatah kata tiap beat = `porsi durasi beat x durasi x tempo`. Tulis dua versi: tempo asli channel, dan tempo VO Indonesia user (2,25 kata/detik). Selisihnya menunjukkan berapa banyak isi yang harus dipangkas.

Kalau channel tidak bercerita (vlog, tutorial, podcast), buat beat map dari fungsi yang ada di sana (pembuka, janji, demonstrasi, hasil, ajakan) dan sebutkan bahwa formatnya bukan cerita.

## Template

```markdown
# Analisa channel <Nama> (@handle)
_Data diambil <tanggal>. <jumlah> video, <subscriber> subscriber, total <views>. Data mentah: <folder>._

## Ringkasan
3-5 poin: format, skala, apa yang paling menentukan views, satu hal yang paling layak ditiru.

## Profil dan angka utama
Tabel per era/tab:
- jumlah video, median views, % video di atas ambang tinggi (misalnya 5 juta), % di bawah ambang rendah
- median durasi, gaya judul, frekuensi upload
Tambah juga: like/view, komentar/view, median views:subscriber.

## Perjalanan channel
Dari tabel tren terbaru-ke-terlama, per bulan, dan daftar judul:
- kapan naik, kapan pivot (tanggal video pertama format baru)
- apa yang berubah: judul, durasi, topik, visual

## Velocity
Video 14 hari terakhir dan velocity tertinggi (views/hari). Video yang baru berumur beberapa hari dinilai dari views/hari, bukan total.

## Apa yang membuat video meledak
Tabel pemenang vs sepi: topik, sudut cerita, ada tokoh atau tidak, durasi, hook. Contoh konkret dengan judul, views, dan link.

## Formula judul
Template yang berulang (tulis sebagai pola, misalnya "Why [Kelompok] [Kebiasaan Aneh]") dengan contoh dan views-nya, panjang judul, ciri yang membedakan atas dan bawah, hal yang dihindari (emoji, hashtag, angka, dst).

## Framework narasi
_Dari <n> video pemenang (<judul + views>) dan <m> pembanding sepi. Era: sejak <tanggal>. Tempo channel <x> kata/detik; VO Indonesia kamu 2,25 kata/detik._

| # | Beat | % durasi | Detik (60 s) | Kata (tempo channel) | Kata (VO kamu) | Fungsi | Contoh kutipan |
|---|---|---|---|---|---|---|---|

- **Aturan wajib:** hal yang ada di semua pemenang (mulai di tengah aksi, satu tokoh pusat, penjelasan ditahan, tanpa CTA, dst).
- **Kenapa video sepi kalah:** beat yang hilang atau berbeda, dengan bukti.
- **Variasi yang boleh:** pola yang hanya ada di sebagian pemenang.
- **Gaya bahasa:** panjang kalimat, sapaan orang kedua, dialog, frasa khas beserta padanan Indonesia yang wajar.
- **Durasi lain:** jatah kata untuk 45 s dan 75 s.

## Contoh hook pemenang
5-10 kalimat pertama video teratas, apa adanya, dengan views. Bahan contoh yang bisa langsung dipakai saat menulis naskah di tempat lain.

## Visual dan audio
Dari Style DNA (Stage 1) kalau dijalankan; kalau tidak, dari lembar kontak thumbnail. Sebut skill produksi user yang paling mirip gayanya.

## Jadwal upload
Frekuensi 30/90 hari, hari dan jam (WIB), serta artinya untuk zona waktu penonton channel itu.

## Pelajaran untuk channel kamu
Hal konkret yang bisa dipakai, dikaitkan ke format atau skill produksi yang cocok. Tanpa daftar ide topik.

## Catatan data
Sampel detail, caption otomatis, video yang belum cukup umur, bagian yang masih dugaan.
```

Untuk perbandingan beberapa channel: tambahkan tabel berdampingan di awal dan bagian "Beda formula" sebelum "Pelajaran untuk channel kamu".
