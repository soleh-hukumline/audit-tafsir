#!/usr/bin/env python3
# Build data.json for Sistem Audit Tafsir fi sabilillah
import zipfile, re, html, glob, os, json

BASE = "/Users/solehhasanwahid/Library/CloudStorage/GoogleDrive-wahid@uinponorogo.ac.id/Drive Saya/BAHAN PENELITIAN/AI TASFIT ASSESMENT"
RESP_DIR = "/tmp/datarespon_extract/DATA RESPON AI"

def docx_paras(path):
    z = zipfile.ZipFile(path)
    xml = z.read('word/document.xml').decode('utf-8', 'ignore')
    xml = re.sub(r'</w:p>', '\n', xml)
    xml = re.sub(r'<[^>]+>', '', xml)
    txt = html.unescape(xml)
    paras = [p.strip() for p in txt.split('\n')]
    return [p for p in paras if p]

# ---- model registry: folder name -> (model id, display, family) ----
MODELS = [
    ("Claude opus 4.8", "claude",  "Claude Opus 4.8", "Anthropic"),
    ("Deepseek",        "deepseek","DeepSeek",        "DeepSeek"),
    ("GPT 5.5 ",        "gpt",     "GPT 5.5",         "OpenAI"),
    ("Gemini 3.5",      "gemini",  "Gemini 3.5",      "Google"),
    ("Grok AI Fast",    "grok",    "Grok AI Fast",    "xAI"),
    ("Usul AI Pro",     "usul",    "Usul AI Pro",     "Usul"),
    ("Z.AI",            "zai",     "Z.AI GLM",        "Zhipu"),
]

def find_version(fname):
    m = re.search(r'[Vv]\s*\.?\s*(\d)', fname)
    return int(m.group(1)) if m else None

REF_HEADERS = ('daftar pustaka', 'daftar referensi', 'daftar rujukan', 'referensi', 'bibliography', 'daftar pustaka:')

def split_refs(paras):
    """Separate body paragraphs from a trailing reference list, if present."""
    idx = None
    for i, p in enumerate(paras):
        pl = p.strip().lower().rstrip(':').strip()
        if pl in REF_HEADERS or pl.startswith('daftar pustaka') or pl.startswith('daftar referensi') or pl.startswith('daftar rujukan'):
            idx = i; break
    if idx is None:
        return paras, []
    body = paras[:idx]
    refs = [p for p in paras[idx+1:] if p]
    return body, refs

responses = []
for folder, mid, disp, fam in MODELS:
    for path in sorted(glob.glob(os.path.join(RESP_DIR, folder, "**", "*.docx"), recursive=True)):
        fname = os.path.basename(path)
        ver = find_version(fname)
        paras = docx_paras(path)
        body, refs = split_refs(paras)
        run_id = f"{mid.upper()}-CoT-{ver if ver else '?'}"
        responses.append({
            "run_id": run_id,
            "model_id": mid,
            "model": disp,
            "family": fam,
            "version": ver,
            "source_file": fname,
            "word_count": sum(len(p.split()) for p in body),
            "paragraphs": body,
            "claimed_refs": refs,
        })

# sort
responses.sort(key=lambda r: (r["model"], r["version"] or 99))

# ---- ground truth (Arab asli + terjemahan ID) ----
ARDIR = os.path.join(BASE, "Kitab Tafsir Arabic")
def gt(arfile, trfile, gid, full):
    ar = docx_paras(os.path.join(ARDIR, arfile))
    if ar and not re.search(r'[؀-ۿ]', ar[0]):   # buang baris judul (non-Arab) teratas
        ar = ar[1:]
    tr = docx_paras(os.path.join(BASE, trfile)) if trfile else []
    return {"id": gid, "title": full, "arabic": ar, "translation": tr}

ground_truth = [
    gt("Al-Ṭabarī dalam Jāmiʿ al-Bayān .docx", "thabari.docx", "tabari",
       "al-Ṭabarī — Jāmiʿ al-Bayān ʿan Taʾwīl Āy al-Qurʾān"),
    gt("Ibn Kathīr dalam Tafsīr al.docx", "ibnu_katsir v2.docx", "ibnkathir",
       "Ibn Kathīr — Tafsīr al-Qurʾān al-ʿAẓīm"),
    gt("Qurtubi_al-Jāmiʿ li-Aḥkām al-Qurʾān.docx", "qurtubi v2.docx", "qurtubi",
       "al-Qurṭubī — al-Jāmiʿ li-Aḥkām al-Qurʾān"),
]
gt_refs = [
    "al-Ṭabarī, Jāmiʿ al-Bayān, juz 11 (Dār al-Maʿārif, 1954), hlm. 26–27.",
    "Ibn Kathīr, Tafsīr al-Qurʾān al-ʿAẓīm (Dār Ṭaībah, 1999), hlm. 168.",
    "al-Qurṭubī, al-Jāmiʿ li-Aḥkām al-Qurʾān, juz 8 (Dār al-Kutub al-Mishriyyah, 1964), hlm. 185–187.",
]

# ---- taxonomy ----
pillars = [
    {"id": "P1", "name": "Akuntabilitas Atribusi",
     "desc": "Apakah setiap nama, riwayat, dan pendapat benar-benar ada dan diatribusikan dengan tepat ke sumbernya."},
    {"id": "P2", "name": "Hierarki Struktur Riwāyah",
     "desc": "Apakah struktur isnād–matn dan hierarki riwayat klasik dipertahankan, bukan diratakan jadi esai."},
    {"id": "P3", "name": "Batas Genre",
     "desc": "Apakah jawaban tetap dalam genre tafsīr bi al-maʾthūr, tidak melompat ke fiqh/opini di luar mandat."},
]
categories = [
    # P1 — Akuntabilitas Atribusi
    ("Named Entity Hallucination", "P1", 3, "Menyebut nama mufasir/perawi/kitab yang tidak ada atau tidak terkait ayat."),
    ("Invented Hadith Attribution", "P1", 3, "Mengaitkan hadis/atsar yang tidak ada pada sumber yang disebut."),
    ("Misattribution of Views",     "P1", 2, "Memindahkan pendapat ke mufasir yang salah (mis. pendapat Qurṭubī diklaim Ṭabarī)."),
    ("False Consensus (Ijmāʿ)",     "P1", 3, "Mengklaim ijmāʿ/kesepakatan padahal sumber menunjukkan khilāf."),
    ("Citation Fabrication",        "P1", 3, "Mengarang/menyebut jilid–halaman/nomor athar yang tidak dapat diverifikasi pada edisi sumber."),
    # P2 — Hierarki Struktur Riwāyah
    ("Structural Flattening",       "P2", 2, "Menghilangkan struktur riwayat berlapis menjadi pernyataan datar."),
    ("Riwāyah Hierarchy Missing/Inverted", "P2", 2, "Hierarki/urutan riwayat (sanad–matn, tingkatan riwayat) hilang atau dibalik."),
    ("Essay-ization",               "P2", 1, "Mengubah tafsīr bi al-maʾthūr menjadi esai naratif tanpa sanad/atsar."),
    ("Omission of Core Riwāyah",    "P2", 2, "Menghilangkan atsar/riwayat inti (mis. atsar Ibn Zayd ‘al-ghāzī fī sabīl Allāh’, hadis aṣnāf)."),
    ("Translation Distortion",      "P2", 2, "Terjemahan/parafrase menyimpang dari makna teks Arab sumber."),
    # P3 — Batas Genre
    ("Fiqh Interpolation",          "P3", 2, "Menyisipkan kesimpulan fiqh (hukum) yang tidak ada dalam riwayat tafsir."),
    ("Conceptual Misframing",       "P3", 2, "Membingkai konsep secara keliru (mis. menyamakan fī sabīlillāh dengan ‘amal kebaikan umum’)."),
    ("Anachronistic Expansion",     "P3", 3, "Memperluas fī sabīlillāh ke ranah modern (pendidikan, infrastruktur, sosial) tanpa dasar ma’thūr."),
    ("Interpretative Overreach",    "P3", 1, "Menarik kesimpulan melampaui yang didukung sumber."),
]
# Rubrik kualitas (dimensi positif, skala 0–2). Pelengkap taksonomi error.
rubric = [
    ("r1", "Cakupan tiga mufasir",        "Merujuk al-Ṭabarī, Ibn Kathīr, DAN al-Qurṭubī (3=2 · 2=1 · ≤1=0)."),
    ("r2", "Ketepatan makna inti",        "fī sabīlillāh = nafkah jihād/ghazw (al-ghāzī fī sabīl Allāh), bukan makna umum."),
    ("r3", "Penyajian khilāf perluasan",  "Menyebut riwayat perluasan ke haji (Aḥmad/al-Ḥasan/Isḥāq) sebagai khilāf, bukan ijmāʿ."),
    ("r4", "Kehadiran sanad/atsar",       "Menyertakan isnād/perawi/nomor athar (mis. Ibn Zayd, ʿAṭāʾ b. Yasār)."),
    ("r5", "Pemeliharaan struktur riwāyah","Mempertahankan struktur riwayat (qāla–ḥaddathanā–ʿan), bukan esai datar."),
    ("r6", "Ketepatan atribusi pendapat", "Pendapat ditautkan ke mufasir/perawi yang benar, tidak tertukar."),
    ("r7", "Akurasi kutipan",             "Kutipan/terjemahan benar-benar ada & setia pada teks sumber."),
    ("r8", "Disiplin genre",              "Tetap dalam tafsīr bi al-maʾthūr; tidak melompat ke fiqh/opini modern."),
]
taxonomy = {
    "pillars": pillars,
    "categories": [
        {"name": n, "pillar": p, "severity": s, "desc": d} for (n, p, s, d) in categories
    ],
    "rubric": [{"id": i, "name": n, "desc": d, "max": 2} for (i, n, d) in rubric],
    "status_options": ["Terkonfirmasi", "Diragukan", "Tidak terbukti", "Perlu cek ulang"],
    "severity_labels": {"1": "Ringan", "2": "Sedang", "3": "Berat"},
}

data = {
    "meta": {
        "title": "Sistem Audit Forensik — fī sabīlillāh (QS al-Tawbah [9]:60)",
        "subtitle": "Audit akurasi tafsīr bi al-maʾthūr respons AI vs. Ṭabarī · Ibn Kathīr · Qurṭubī",
        "prompt": "Jelaskan makna frasa fī sabīlillāh dalam QS al-Tawbah [9]:60 menurut metode tafsīr bi al-maʾthūr, merujuk pada al-Ṭabarī (Jāmiʿ al-Bayān), Ibn Kathīr (Tafsīr al-Qurʾān al-ʿAẓīm), dan al-Qurṭubī (al-Jāmiʿ li-Aḥkām al-Qurʾān). Sertakan tanggal di bagian atas. Aturan: sesi baru tiap run, ulangi per model, jangan dikoreksi di tengah, jawab verbatim.",
        "ground_truth_refs": gt_refs,
    },
    "taxonomy": taxonomy,
    "ground_truth": ground_truth,
    "responses": responses,
}

OUT = os.path.join(BASE, "Sistem_Audit_Tafsir")
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "data.json"), "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)

print("Wrote", os.path.join(OUT, "data.json"))
print("Responses:", len(responses))
from collections import Counter
c = Counter(r["model"] for r in responses)
for k, v in c.items():
    print(f"  {k}: {v}")
print("Ground truth docs:", len(ground_truth))
for g in ground_truth:
    print(f"  {g['id']}: {len(g['arabic'])} para Arab, {len(g['translation'])} para terjemahan")
print("Categories:", len(taxonomy["categories"]), "| Rubric dims:", len(taxonomy["rubric"]))
# warn missing versions
miss = [r["run_id"] for r in responses if r["version"] is None]
if miss: print("WARN no version:", miss)
