# Unblur

Unblur image online. The page is an AI image upscaler: three tries are free, then ₹20 adds three more.

Set `IMAGE_MODEL` in `.env` before an upscale can run.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app:app --reload
```

Set `REPLICATE_API_TOKEN` before an upscale can run, and the Razorpay keys before ₹20 checkout works. Set `SITE_URL` to the public address before launch so the canonical URL and sitemap point at the live site.

PythonAnywhere can load `wsgi.py`. The callable is `application`.
