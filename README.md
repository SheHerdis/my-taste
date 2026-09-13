# my taste — موقع ذوقك من Pinterest

موقع static يسحب boards حقك من Pinterest يومياً، يحلل الألوان والكلمات، ويعرض كل شي كـ scrapbook.

## الإعداد (مرة وحدة)

1. سوي repo جديد على GitHub (مثلاً `my-taste`) وارفعي كل هالملفات فيه.
2. Settings → Secrets and variables → Actions → New repository secret:
   - Name: `PINTEREST_TOKEN`
   - Value: توكن Pinterest (بصلاحيات `boards:read` و `pins:read`)
3. Settings → Pages → Source: `Deploy from a branch` → Branch: `main` / `(root)` → Save.
4. Actions → **Sync Pinterest** → Run workflow. أول مرة ياخذ دقيقة أو اثنتين.
5. الموقع يطلع على: `https://USERNAME.github.io/REPO/`

بعدها يحدّث نفسه كل يوم الساعة 3 فجراً UTC. تقدرين تشغلينه يدوياً من Actions بأي وقت.

## الملفات

| الملف | وظيفته |
|---|---|
| `config.json` | الـ boards والـ pins اللي ما تبينها تظهر + عنوان الموقع |
| `sync.py` | يسحب من Pinterest، ينزّل الصور، يحلل الألوان |
| `.github/workflows/sync.yml` | يشغّل `sync.py` تلقائياً ويحفظ النتيجة |
| `index.html` | الموقع نفسه |
| `data/pins.json` | النتيجة (يتولد تلقائياً) |
| `images/` | صور الـ pins (تتولد تلقائياً) |

## تخفي board أو pin

افتحي `config.json`:
```json
"exclude_boards": ["ads", "t-shirts"],
"exclude_pins": ["123456789"]
```
رقم الـ pin موجود بآخر رابطه على Pinterest.

## ملاحظات

- التوكن ينتهي كل 30 يوم — لما يوقف الـ sync، سوي توكن جديد وحدّثي الـ Secret.
- الـ repo public = الـ pins اللي بالموقع يشوفها أي أحد عنده الرابط.
- الصور تتخزن بالـ repo. لو تعدت 500 pin يصير الحجم كبير — قلّلي `image_width` في `config.json`.
