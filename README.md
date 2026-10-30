# Unblur

Unblur image online. The page is a free AI image upscaler. No account and no watermark.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app:app --reload
```

Set `REPLICATE_API_TOKEN` before an upscale can run. Keep `FREE_MODE=1` so the tool stays free. Set `SITE_URL` to the public address before launch so the canonical URL and sitemap point at the live site.

PythonAnywhere can load `wsgi.py`. The callable is `application`.
