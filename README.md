# Sistem Audit Tafsir — fī sabīlillāh (QS al-Tawbah [9]:60)

Aplikasi web offline untuk audit forensik akurasi *tafsīr bi al-maʾthūr* respons AI,
dengan ground truth tiga kitab klasik: al-Ṭabarī (*Jāmiʿ al-Bayān*), Ibn Kathīr
(*Tafsīr al-Qurʾān al-ʿAẓīm*), dan al-Qurṭubī (*al-Jāmiʿ li-Aḥkām al-Qurʾān*).
Menggantikan workbook Excel `Workbook_Audit_fi_sabilillah_CoT.xlsx`.

## Cara pakai
Buka **`index.html`** di browser (cukup klik dua kali — tidak perlu server/internet).
Semua teks respons & ground truth sudah tertanam di dalam file.

### Empat tab
1. **Ringkasan** — KPI, prompt CoT, daftar ground truth, taksonomi 3 pilar / 10 kategori.
2. **Koding (Kualitatif)** — dua lapis penilaian per respons:
   - **(a) Temuan error** — catat: kategori (→ pilar otomatis), severity, kutipan verbatim,
     cek sumber (kitab/jilid/hlm), status, koder, catatan.
   - **(b) Rubrik Kualitas** — 8 dimensi *positif* (skala 0–2): cakupan tiga mufasir,
     ketepatan makna inti (jihād/ghazw), penyajian khilāf haji, kehadiran sanad/atsar,
     pemeliharaan struktur riwāyah, ketepatan atribusi, akurasi kutipan, disiplin genre.
   - Ground truth tampil berdampingan dengan toggle **Arab ↔ Terjemahan** untuk tiap kitab.
   - Tombol **⚡ Isi otomatis** (per respons / semua 28) — lihat di bawah.
3. **Kuantitatif** — tiga keluaran:
   - **Frekuensi error** per kategori / pilar / model.
   - **Indeks Akurasi 0–100** (penalti): `100 − (Σ severity × bobot_pilar × faktor_status) × K`.
     Faktor status: Terkonfirmasi = 1 · Diragukan = ½ · Perlu cek ulang = ¼ · Tidak terbukti = 0.
     Bobot pilar (P1/P2/P3) dan K bisa diubah langsung di tab ini.
   - **Skor Kualitas 0–100** (rubrik): rata-rata 8 dimensi (0–2) dinormalkan ke %.
4. **Ekspor / Impor** — auto-isi semua, hapus temuan AUTO, ekspor Temuan+Rubrik (JSON),
   Temuan (CSV), Skor+Rubrik (CSV); impor JSON (gabung dua koder); hapus semua.

## Isi otomatis (heuristik)
Tombol ⚡ memindai tiap respons untuk **sinyal jelas** lalu menandai kandidat:
- klaim ijmāʿ/kesepakatan → *False Consensus*
- perluasan makna ke ranah modern (pendidikan, infrastruktur, sosial) → *Anachronistic Expansion*
- rujukan jilid/halaman → *Citation Fabrication* (verifikasi ke edisi sumber)
- tidak ada penanda sanad/atsar → *Essay-ization*
- skor rubrik awal r1–r5 + r8 dari sinyal teks (r6, r7 dibiarkan untuk manual).

Semua temuan auto berstatus **"Perlu cek ulang"** (koder = `auto`, badge AUTO) dan
**wajib diverifikasi manual** — heuristik regex bukan pengganti penilaian koder. Menjalankan
ulang akan mengganti hasil AUTO lama; **temuan manual tetap aman**.

## Sinkron bersama (Google Sheet) — penilaian kolaboratif
Agar banyak penilai berbagi **satu database** yang tersinkron otomatis (bukan tersimpan
terpisah di tiap browser):

1. Buat **Google Sheet** baru → menu **Extensions → Apps Script**.
2. Tempel seluruh isi `AppsScript_Code.gs`, lalu **Deploy → New deployment → Web app**:
   *Execute as: Me* · *Who has access: Anyone*. Salin **Web app URL** (diakhiri `/exec`).
3. Buka app → tab **Ekspor/Impor → Sinkron bersama** → tempel URL + isi **nama koder** →
   **Simpan & sambungkan**.
4. Bagikan URL yang sama + nama-koder masing-masing ke tiap penilai.

Saat **ONLINE**: tiap tambah/hapus temuan & skor rubrik langsung tersimpan ke Sheet;
tombol **↻ Tarik terbaru** menarik kontribusi penilai lain. Dashboard Kuantitatif
**merata-rata rubrik semua koder** (mendukung penilaian banyak orang). Temuan auto
ber-ID deterministik sehingga tidak menggandakan walau di-seed berkali-kali.

> Catatan: Web App Apps Script dipanggil dari browser via `POST text/plain` (tanpa preflight CORS).
> Bila Sheet/URL belum diisi, app tetap jalan **offline** (localStorage) seperti biasa.

## Auto-fill saat dibuka
Saat app dibuka dan belum ada temuan, heuristik dijalankan **otomatis** sehingga penilai
langsung melihat kandidat awal (status "Perlu cek ulang") untuk dikoreksi.

## Penyimpanan data
- **Mode offline**: temuan & rubrik di `localStorage` browser. Pindah komputer / gabung dua
  koder: ekspor JSON lalu impor.
- **Mode online**: temuan & rubrik di Google Sheet bersama (lihat di atas).
- **Data respons & ground truth** (Arab + terjemahan) bersifat tetap, tertanam di `index.html`.

## Regenerasi data (jika menambah respons AI)
File sumber: `data.json` dibuat oleh `build_data.py` dari folder `DATA RESPON AI/`
(28 respons .docx, 7 model × 4 run). Ground truth: **teks Arab asli** dari folder
`Kitab Tafsir Arabic/` + **terjemahan** dari `thabari.docx`, `ibnu_katsir v2.docx`,
`qurtubi v2.docx`.

```bash
python3 build_data.py            # hasilkan data.json baru
# lalu suntikkan ke template:
python3 - <<'PY'
import json
d=json.load(open('data.json',encoding='utf-8'))
t=open('app_template.html',encoding='utf-8').read()
js=json.dumps(d,ensure_ascii=False).replace('</','<\\/')
open('index.html','w',encoding='utf-8').write(t.replace('__DATA__',js))
PY
```

## Taksonomi (dari workbook asli)
- **P1 Akuntabilitas Atribusi** — Named Entity Hallucination · Invented Hadith Attribution · Misattribution of Views · False Consensus (Ijmāʿ)
- **P2 Hierarki Struktur Riwāyah** — Structural Flattening · Riwāyah Hierarchy Missing/Inverted · Essay-ization
- **P3 Batas Genre** — Fiqh Interpolation · Conceptual Misframing · Interpretative Overreach
