# Deploying LeakFusion for free (Hugging Face Space + Cloudflare keep-alive)

One Docker container serves both the React UI (`/`) and the FastAPI backend (`/api/*`)
on Hugging Face's free CPU tier (2 vCPU, 16 GB RAM). A free Cloudflare Worker pings it
every 6 hours so it never hits the ~48 h inactivity sleep.

## 1. Get the models

Download the 5 model files from the Google Drive link in the main `README.md` into
`leakfusion/models/` (gitignored, so they never reach GitHub).

## 2. Create the Space (once)

1. huggingface.co → **New Space** → name `leakfusion`, SDK **Docker** (Blank),
   hardware **CPU basic (free)**, visibility **Public**.
2. huggingface.co/settings/tokens → create a token with **write** access.
3. Make sure `git-lfs` and `rsync` are installed (`sudo apt install git-lfs rsync`).

## 3. Push

```bash
deploy/push_to_hf.sh <your-hf-username>/leakfusion
```

When git asks: username = your HF username, password = the write token.
The Space builds automatically (~5–10 min the first time). Then open
`https://<your-hf-username>-leakfusion.hf.space`.

Re-run the same command after every change to redeploy.

## 4. Keep it awake (Cloudflare, free)

```bash
cd deploy/keepalive-worker
# edit SPACE_URL in wrangler.toml first
npx wrangler login
npx wrangler deploy
```

Open the Worker's `*.workers.dev` URL once to trigger a manual ping and check it
returns `"status": 200`.

## Test locally first (optional)

```bash
docker build -t leakfusion .
docker run --rm -p 7860:7860 leakfusion
# open http://localhost:7860
```

## Notes

- **Library versions vs. pickled models.** `.joblib` models only load reliably with
  the same scikit-learn / xgboost major versions they were trained with. If the Space
  logs show unpickling errors or `InconsistentVersionWarning`, pin the versions you
  trained with in `requirements-api.txt` (check with
  `python -c "import sklearn, xgboost; print(sklearn.__version__, xgboost.__version__)"`
  in your training env).
- **Space must be public** for the UI to work without a token. The GitHub repo stays private.
- **Disk is ephemeral** — fine here, the app only reads models and sample CSVs.
- The Streamlit UI is not included in this image; it's the React UI + API.
