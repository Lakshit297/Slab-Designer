# One-Way Slab Designer (IS 456:2000)

Files
- calc.py   : calculation engine (pure Python, formulas live here)
- app.py    : Streamlit web interface
- requirements.txt

Run locally
    pip install -r requirements.txt
    streamlit run app.py

Deploy free (Streamlit Community Cloud)
1. Push these 4 files to a public GitHub repo.
2. Go to https://share.streamlit.io -> sign in with GitHub -> New app.
3. Pick the repo, branch main, main file = app.py -> Deploy.
You get a public URL like https://your-app.streamlit.app that opens in Chrome.
