# AI Powered Student Career Guidance Intelligence & ATS Resume Builder
**Streamlit + MongoDB edition** – a Python port of the React/Supabase project `ai-career-inteligence`.

All 6 modules of the original app are included: Auth + demo profiles, Intake Wizard, Reality Check,
Zero-Cost Courses, 3-Phase Roadmap, ATS Resume Builder (live preview, AI bullet enhancer, PDF export),
Resume Comparator and Mock Interview Simulator.

## 1. Requirements
* Python 3.10 or newer
* MongoDB Community Server running on your PC (default port 27017) — or a free MongoDB Atlas cluster

## 2. Setup (Windows / Linux / macOS)
```bash
cd career_app
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt

copy .env.example .env            # Linux/macOS:  cp .env.example .env
# open .env and check MONGO_URI (default works for local MongoDB; paste your Atlas URI if you use Atlas)
```

## 3. Run
```bash
streamlit run app.py
```
The browser opens at http://localhost:8501.
The database `ai_career`, its collections and indexes are created automatically on first start.
You can browse the data with MongoDB Compass (connect to `mongodb://localhost:27017`).

Click any **demo profile** on the first page to explore instantly, or create your own account.

## 4. Files
| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI (all screens) |
| `engine.py` | Scoring / recommendation logic (port of `mockData.ts`) |
| `data/career_data.json` | Streams, courses, roadmaps, interview questions, sample resumes (exported from `mockData.ts`) |
| `db.py` | MongoDB layer (pymongo) – users, profiles, roadmaps, resumes, interview_results |
| `pdf_export.py` | ATS-friendly PDF / printable HTML resume |

## 5. MongoDB collections
`users` (replaces Supabase auth) · `profiles` · `roadmaps` (task progress) · `resumes` · `interview_results`

## 6. Troubleshooting
* **"Cannot connect to MongoDB"** – start the MongoDB service (`mongod`) and check `MONGO_URI` in `.env`.
* **Atlas** – add your IP address under *Network Access* in the Atlas dashboard.
* **Port busy** – `streamlit run app.py --server.port 8600`
