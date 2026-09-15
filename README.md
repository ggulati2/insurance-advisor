# Do I Actually Need This Insurance?

A free, unbiased tool that gives expats and residents in Germany a personalized
breakdown of which insurance types they actually need, based on their life
situation — no commission-driven agent involved.

**Educational tool only — not licensed financial or insurance advice.**

## Live app

**[insurance-advisor-gg.streamlit.app](https://insurance-advisor-gg.streamlit.app/)**

## How it works

1. You answer a handful of quick questions about your housing, work, family,
   what you own, and your risk tolerance.
2. The app sends your answers to an LLM (via [OpenRouter](https://openrouter.ai),
   free-tier model) alongside a fixed reference knowledge block about standard
   German insurance types.
3. The result is rendered as three color-coded categories: **Essential**,
   **Worth Considering**, and **Usually Skippable** — each with a one-sentence,
   situation-specific reason.

No accounts, no database, no data is stored. Each session is independent.

## Tech stack

- **App**: [Streamlit](https://streamlit.io) (Python)
- **LLM**: [OpenRouter](https://openrouter.ai) API, free-tier model
  (`liquid/lfm-2.5-2.6b:free` — fast and reliable at structured JSON output;
  verify this slug is still available on your OpenRouter dashboard before
  redeploying, since free-tier model availability changes over time)
- **Hosting**: [Streamlit Community Cloud](https://share.streamlit.io) (free)

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` (already gitignored) with your own key:

```toml
OPENROUTER_API_KEY = "sk-or-..."
```

Then run:

```bash
streamlit run app.py
```

## Deployment (Streamlit Community Cloud)

1. Push this repo to GitHub (do **not** commit `.streamlit/secrets.toml`).
2. Go to [share.streamlit.io](https://share.streamlit.io), connect your GitHub
   account, and create a new app pointing at this repo with entry point
   `app.py`.
3. In the app's **Settings → Secrets**, add:
   ```toml
   OPENROUTER_API_KEY = "sk-or-..."
   ```
4. Deploy. The app will be live at `https://<app-name>.streamlit.app`.

## Project structure

```
insurance-advisor/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
└── .streamlit/
    ├── config.toml        # theme settings (committed)
    └── secrets.toml       # API key (gitignored, local only)
```
