"""
AI Powered Student Career Guidance Intelligence & ATS Resume Builder
Streamlit + MongoDB edition  (port of the React/Supabase app "ai-career-inteligence")

Run:  streamlit run app.py
"""
import html
import uuid
from copy import deepcopy

import streamlit as st

import db
import engine as E
import pdf_export

st.set_page_config(page_title="AI Career Intelligence", page_icon="🧭", layout="wide",
                   initial_sidebar_state="auto")

# ----------------------------------------------------------------------------
# Styling
# ----------------------------------------------------------------------------
st.markdown("""
<style>
.block-container{padding-top:4rem;max-width:1200px}
.grad{background:linear-gradient(90deg,#818cf8,#34d399,#fbbf24);-webkit-background-clip:text;background-clip:text;
      color:transparent;font-weight:800}
.pill{display:inline-block;border:1px solid rgba(99,102,241,.35);background:rgba(99,102,241,.12);color:#a5b4fc;
      border-radius:999px;padding:4px 14px;font-size:.78rem;font-weight:600;margin-bottom:14px}
.card{border:1px solid #1e293b;background:rgba(15,23,42,.55);border-radius:16px;padding:18px 20px;margin-bottom:14px}
.card h4{margin:0 0 6px 0;font-size:1rem}
.muted{color:#94a3b8;font-size:.86rem}
.hl{border-radius:14px;padding:14px 16px;border:1px solid;height:100%;min-height:104px}
.hl .l{font-size:.75rem;color:#94a3b8;margin-bottom:4px}.hl .v{font-size:.92rem;font-weight:700}
.hl.good{border-color:rgba(16,185,129,.35);background:rgba(16,185,129,.06)}.hl.good .v{color:#34d399}
.hl.warn{border-color:rgba(245,158,11,.35);background:rgba(245,158,11,.06)}.hl.warn .v{color:#fbbf24}
.hl.bad{border-color:rgba(244,63,94,.35);background:rgba(244,63,94,.06)}.hl.bad .v{color:#fb7185}
.badge{display:inline-block;border-radius:999px;padding:2px 12px;font-size:.72rem;font-weight:700;border:1px solid}
.b-Critical{color:#fb7185;border-color:rgba(244,63,94,.4);background:rgba(244,63,94,.1)}
.b-High{color:#fbbf24;border-color:rgba(245,158,11,.4);background:rgba(245,158,11,.1)}
.b-Medium{color:#a5b4fc;border-color:rgba(99,102,241,.4);background:rgba(99,102,241,.1)}
.b-Basic{color:#34d399;border-color:rgba(16,185,129,.4);background:rgba(16,185,129,.1)}
.b-Intermediate{color:#fbbf24;border-color:rgba(245,158,11,.4);background:rgba(245,158,11,.1)}
.b-Advanced{color:#fb7185;border-color:rgba(244,63,94,.4);background:rgba(244,63,94,.1)}
.res{display:inline-block;margin:4px 8px 4px 0;padding:5px 12px;border:1px solid #334155;border-radius:10px;
     font-size:.82rem;text-decoration:none!important;color:#cbd5e1!important;background:rgba(30,41,59,.5)}
.res:hover{border-color:#6366f1;color:#fff!important}
.res small{color:#64748b;margin-left:6px}
.term{background:#05080f;border:1px solid #1e293b;border-radius:12px;padding:16px 18px;
      font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.85rem;line-height:1.55;margin-bottom:12px}
.term .p{color:#818cf8}.term .q{color:#e2e8f0;font-weight:600}.term .a{color:#94a3b8;margin-left:14px}
.term .ok{color:#34d399}.term .mid{color:#fbbf24}.term .low{color:#fb7185}.term .fb{color:#94a3b8;margin-left:14px}
.paper{background:#fff;border-radius:12px;padding:26px 28px;border:1px solid #1e293b}
.fixrow{display:grid;grid-template-columns:130px 1fr 1fr;gap:10px;border:1px solid #1e293b;border-radius:10px;
        padding:10px 12px;margin-bottom:8px;background:rgba(15,23,42,.35);font-size:.82rem}
.fixrow .cat{background:#1e293b;border-radius:6px;padding:2px 8px;height:fit-content;font-weight:600;color:#cbd5e1}
div[data-testid="stRadio"] label{font-size:.9rem}
footer{visibility:hidden}
</style>
""", unsafe_allow_html=True)

esc = html.escape


# ----------------------------------------------------------------------------
# Database bootstrap
# ----------------------------------------------------------------------------
@st.cache_resource(show_spinner="Connecting to MongoDB…")
def _bootstrap():
    db.init_db()
    return True


def _db_error_page(err: Exception):
    st.markdown("## 🍃 Cannot connect to MongoDB")
    st.error(str(err))
    st.markdown(f"""
The app could not reach the MongoDB server. Please check:

1. **MongoDB is running** (Windows: open *Services* → start `MongoDB Server`, or start `mongod`;
   or use a free MongoDB Atlas cluster).
2. **`MONGO_URI` in your `.env` file** is correct (copy `.env.example` to `.env` and edit it).
   Current settings → URI `{esc(db.mongo_uri().split('@')[-1])}`, database `{esc(db.db_name())}`.

The database `{esc(db.db_name())}` and its collections are created automatically. Then refresh this page.
""")
    if st.button("🔄 Retry connection"):
        st.cache_resource.clear()
        st.rerun()


try:
    _bootstrap()
except Exception as exc:  # noqa: BLE001
    _db_error_page(exc)
    st.stop()


# ----------------------------------------------------------------------------
# Session helpers
# ----------------------------------------------------------------------------
def _uid() -> str:
    return uuid.uuid4().hex[:8]


def current_user():
    return st.session_state.get("user")


def refresh_profile():
    u = current_user()
    st.session_state.profile = db.get_profile(u["id"]) if u else None


def login_user(user: dict):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.session_state.user = user
    refresh_profile()


def logout():
    for k in list(st.session_state.keys()):
        del st.session_state[k]


def P(key, default=None):
    p = st.session_state.get("profile") or {}
    return p.get(key) or default


# ----------------------------------------------------------------------------
# Landing page (hero + auth)
# ----------------------------------------------------------------------------
def landing():
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.markdown("<div class='pill'>✨ Universal AI Career Intelligence Engine v4.2</div>", unsafe_allow_html=True)
        st.markdown(
            "<h1 style='font-size:3rem;line-height:1.1;margin:0 0 14px 0'>Your Career, <span class='grad'>"
            "Built for Real-World Success</span></h1>", unsafe_allow_html=True)
        st.markdown(
            "<p style='font-size:1.08rem;color:#cbd5e1;max-width:560px'>Next-generation AI career guidance for every "
            "student — Intermediate, ITI, Diploma, Degree and Engineering. Get an honest skill-gap analysis, "
            "zero-cost course roadmaps and an ATS-optimised resume.</p>", unsafe_allow_html=True)
        st.markdown("<p class='muted'>🟢 26 streams &nbsp;&nbsp; 🟣 100% free resources &nbsp;&nbsp; 🟡 MongoDB-backed</p>",
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        feats = [("🎯 Reality Check", "Unvarnished market analysis: demand, salary ceiling, competitive gap."),
                 ("📚 Zero-Cost Courses", "Skill gaps mapped to YouTube, NPTEL and official docs."),
                 ("🗺️ 3-Phase Roadmap", "A 6-month timeline with trackable tasks."),
                 ("📄 ATS Resume Builder", "Stream-adaptive layout, live preview, PDF export."),
                 ("🆚 Resume Comparator", "See how the AI resume beats your old one."),
                 ("💬 Mock Interviews", "Terminal-style technical interview with scoring.")]
        for i, (t, d) in enumerate(feats):
            (c1 if i % 2 == 0 else c2).markdown(f"<div class='card'><h4>{t}</h4><span class='muted'>{d}</span></div>",
                                                unsafe_allow_html=True)

    with right:
        with st.container(border=True):
            tab_in, tab_up = st.tabs(["Sign in", "Create account"])
            with tab_in:
                with st.form("login_form"):
                    email = st.text_input("Email", placeholder="you@email.com")
                    pw = st.text_input("Password", type="password")
                    go = st.form_submit_button("Sign In", type="primary", use_container_width=True)
                if go:
                    try:
                        login_user(db.authenticate(email, pw))
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
            with tab_up:
                with st.form("signup_form"):
                    name = st.text_input("Full name", placeholder="Your name")
                    email2 = st.text_input("Email ", placeholder="you@email.com")
                    pw2 = st.text_input("Password (min 6 characters)", type="password")
                    go2 = st.form_submit_button("Create Account", type="primary", use_container_width=True)
                if go2:
                    if not name.strip():
                        st.error("Please enter your name.")
                    else:
                        try:
                            login_user(db.create_user(email2, pw2, name))
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))

            st.markdown("<div class='muted' style='text-align:center;margin:10px 0 6px'>— or try a demo profile —</div>",
                        unsafe_allow_html=True)
            for d in E.DEMO_PROFILES:
                if st.button(f"⚡ {d['name']}  ·  {d['stream']}  ·  {d['status']}", key=f"demo_{d['key']}",
                             use_container_width=True):
                    login_user(db.load_demo_user(d))
                    st.rerun()


# ----------------------------------------------------------------------------
# Intake wizard
# ----------------------------------------------------------------------------
def wizard():
    prof = st.session_state.get("profile") or {}
    wiz = st.session_state.setdefault("wiz", {
        "stream_detail": prof.get("stream_detail") or None, "status": prof.get("status") or None,
        "academic_score": prof.get("academic_score") or "", "ambition": prof.get("ambition") or None,
        "budget": prof.get("budget") or None, "strengths": prof.get("strengths") or [],
        "weaknesses": prof.get("weaknesses") or []})
    step = st.session_state.setdefault("wiz_step", 0)

    st.markdown("<div style='text-align:center'><div class='pill'>🧠 AI Intake Wizard</div>"
                "<h2 style='margin:0'>Tell us about yourself</h2>"
                "<p class='muted'>Two quick steps to unlock your personalised career intelligence</p></div>",
                unsafe_allow_html=True)
    st.progress((step + 1) / 2, text=f"Step {step + 1} of 2")
    _, mid, _ = st.columns([0.6, 2, 0.6])
    with mid:
        if step == 0:
            keys = [s["key"] for s in E.ALL_STREAMS]
            with st.form("wiz1"):
                sk = st.selectbox("🎓 Educational stream & background", keys,
                                  index=keys.index(wiz["stream_detail"]) if wiz["stream_detail"] in keys else None,
                                  format_func=lambda k: f"{E.stream_group(k)}  ›  {E.stream_label(k)}",
                                  placeholder="Choose your stream")
                status = st.radio("Current status", E.STATUSES, horizontal=True,
                                  index=E.STATUSES.index(wiz["status"]) if wiz["status"] in E.STATUSES else None)
                score = st.text_input("Academic performance (CGPA / percentage)", value=wiz["academic_score"],
                                      placeholder="e.g. 8.5 CGPA or 85%")
                nxt = st.form_submit_button("Next  →", type="primary", use_container_width=True)
            if nxt:
                if not (sk and status and score.strip()):
                    st.warning("Please choose your stream, status and enter your academic score.")
                else:
                    wiz.update(stream_detail=sk, status=status, academic_score=score.strip())
                    st.session_state.wiz_step = 1
                    st.rerun()
            if prof.get("stream_detail") and st.button("Cancel"):
                st.session_state.pop("wiz", None); st.session_state.pop("wiz_step", None)
                st.session_state.editing_intake = False
                st.rerun()
        else:
            with st.form("wiz2"):
                amb = st.radio("🎯 Primary ambition", E.AMBITIONS,
                               index=E.AMBITIONS.index(wiz["ambition"]) if wiz["ambition"] in E.AMBITIONS else None)
                bud = st.radio("💰 Financial constraints", E.BUDGETS, horizontal=True,
                               index=E.BUDGETS.index(wiz["budget"]) if wiz["budget"] in E.BUDGETS else None)
                c1, c2 = st.columns(2)
                stg = c1.multiselect("⚡ Strengths", E.STRENGTH_OPTIONS,
                                     default=[s for s in wiz["strengths"] if s in E.STRENGTH_OPTIONS])
                wk = c2.multiselect("🧩 Weaknesses", E.WEAKNESS_OPTIONS,
                                    default=[s for s in wiz["weaknesses"] if s in E.WEAKNESS_OPTIONS])
                b1, b2 = st.columns(2)
                back = b1.form_submit_button("←  Back", use_container_width=True)
                done = b2.form_submit_button("Generate My Analysis  →", type="primary", use_container_width=True)
            if back:
                wiz.update(ambition=amb, budget=bud, strengths=stg, weaknesses=wk)
                st.session_state.wiz_step = 0
                st.rerun()
            if done:
                if not (amb and bud and stg and wk):
                    st.warning("Please pick an ambition, a budget, and at least one strength and weakness.")
                else:
                    db.save_profile(current_user()["id"], {
                        "stream": E.stream_group(wiz["stream_detail"]), "stream_detail": wiz["stream_detail"],
                        "status": wiz["status"], "academic_score": wiz["academic_score"],
                        "ambition": amb, "budget": bud, "strengths": stg, "weaknesses": wk})
                    for k in ("wiz", "wiz_step", "editing_intake", "rm_ctx", "rb_user", "iv"):
                        st.session_state.pop(k, None)
                    refresh_profile()
                    st.rerun()


# ----------------------------------------------------------------------------
# Tab: Reality check
# ----------------------------------------------------------------------------
def tab_reality():
    chk = E.get_reality_check(P("stream_detail", E.DEFAULT_STREAM), P("status", "Final Year"),
                              P("academic_score", "75%"), P("ambition", E.DEFAULT_AMBITION))
    st.markdown(f"<div class='card' style='border-color:rgba(245,158,11,.35)'><h4>⚠️ AI Reality Check</h4>"
                f"<div class='muted' style='margin-bottom:10px'>Unvarnished analysis against 2026 market standards</div>"
                f"<div style='color:#e2e8f0'>{esc(chk['verdict'])}</div></div>", unsafe_allow_html=True)
    cols = st.columns(4)
    for col, h in zip(cols, chk["highlights"]):
        col.markdown(f"<div class='hl {h['tone']}'><div class='l'>{esc(h['label'])}</div>"
                     f"<div class='v'>{esc(h['value'])}</div></div>", unsafe_allow_html=True)
    st.write("")
    a, b = st.columns(2)
    a.markdown(f"<div class='card'><h4>📈 Market Demand</h4><span style='color:#cbd5e1'>{esc(chk['marketDemand'])}</span></div>",
               unsafe_allow_html=True)
    b.markdown(f"<div class='card'><h4>₹ Salary Range</h4><span style='color:#cbd5e1'>{esc(chk['salaryRange'])}</span></div>",
               unsafe_allow_html=True)
    st.markdown(f"<div class='card' style='border-color:rgba(244,63,94,.3)'><h4>🎯 Your Competitive Gap</h4>"
                f"<span style='color:#cbd5e1'>{esc(chk['competitiveGap'])}</span></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='card' style='border-color:rgba(99,102,241,.3)'><h4>💡 Key Takeaway</h4>"
                f"<span style='color:#cbd5e1'>Your readiness score of <b style='color:#fff'>{chk['readiness']}/100</b> means "
                f"you're {E.readiness_takeaway(chk['readiness'])}. Use the roadmap and course recommendations to close "
                f"your gaps systematically.</span></div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Tab: Courses
# ----------------------------------------------------------------------------
def tab_courses():
    budget = P("budget", E.DEFAULT_BUDGET)
    recs = E.get_course_recommendations(P("stream_detail", E.DEFAULT_STREAM), budget)
    low = " Filtered for zero-cost learning only." if "Low" in budget else ""
    st.markdown(f"<div class='card' style='border-color:rgba(16,185,129,.3)'><b style='color:#34d399'>100% Free Resources.</b> "
                f"<span style='color:#cbd5e1'>Every recommendation below costs you nothing.{low}</span></div>",
                unsafe_allow_html=True)
    for i, r in enumerate(recs, 1):
        links = "".join(
            f"<a class='res' href='{esc(x['url'], quote=True)}' target='_blank' rel='noopener'>↗ {esc(x['name'])}"
            f"<small>{esc(x['type'])}</small></a>" for x in r["resources"]) or "<span class='muted'>No free resources listed.</span>"
        st.markdown(
            f"<div class='card'><div style='display:flex;justify-content:space-between;gap:10px;align-items:center'>"
            f"<h4>{i}. {esc(r['skill'])}</h4><span class='badge b-{r['priority']}'>{r['priority']}</span></div>"
            f"<p style='color:#cbd5e1;margin:8px 0 4px'><b style='color:#fff'>Why it matters:</b> {esc(r['why'])}</p>"
            f"<p style='color:#cbd5e1;margin:4px 0 8px'><b style='color:#fff'>How to master it:</b> {esc(r['how'])}</p>"
            f"{links}</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Tab: Roadmap (progress saved in MongoDB)
# ----------------------------------------------------------------------------
def _save_roadmap():
    phases = st.session_state.rm_phases
    for pi, ph in enumerate(phases):
        for ii, it in enumerate(ph["items"]):
            it["done"] = bool(st.session_state.get(f"rm_{pi}_{ii}", False))
    db.save_roadmap(current_user()["id"], f"Roadmap – {E.stream_label(P('stream_detail', E.DEFAULT_STREAM))}", phases)


def tab_roadmap():
    stream, amb = P("stream_detail", E.DEFAULT_STREAM), P("ambition", E.DEFAULT_AMBITION)
    ctx = (current_user()["id"], stream, amb)
    if st.session_state.get("rm_ctx") != ctx:
        phases = E.get_roadmap(stream, amb)
        saved = db.get_roadmap(current_user()["id"]) or []
        done_tasks = {it["task"] for ph in saved for it in ph.get("items", []) if it.get("done")}
        for pi, ph in enumerate(phases):
            for ii, it in enumerate(ph["items"]):
                it["done"] = it["task"] in done_tasks
                st.session_state[f"rm_{pi}_{ii}"] = it["done"]
        st.session_state.rm_phases, st.session_state.rm_ctx = phases, ctx
    phases = st.session_state.rm_phases
    total = sum(len(p["items"]) for p in phases)
    done = sum(1 for pi, p in enumerate(phases) for ii, _ in enumerate(p["items"]) if st.session_state.get(f"rm_{pi}_{ii}"))
    pct = round(done / total * 100) if total else 0
    st.markdown(f"<div class='card' style='border-color:rgba(99,102,241,.3)'><b>Roadmap Progress</b> "
                f"<span style='float:right;color:#818cf8;font-weight:800'>{pct}%</span></div>", unsafe_allow_html=True)
    st.progress(pct / 100)
    for pi, ph in enumerate(phases):
        with st.container(border=True):
            st.markdown(f"#### {pi + 1}. {ph['title']}  \n<span class='muted'>📅 {esc(ph['duration'])}</span>",
                        unsafe_allow_html=True)
            for ii, it in enumerate(ph["items"]):
                st.checkbox(f"**{it['task']}**", key=f"rm_{pi}_{ii}", on_change=_save_roadmap)
                st.caption(it["detail"])


# ----------------------------------------------------------------------------
# Tab: Resume builder
# ----------------------------------------------------------------------------
def _to_state(r: dict) -> dict:
    s = deepcopy(r)
    for e in s["experience"]:
        e["id"] = _uid()
        e["bullets"] = [{"id": _uid(), "text": b} for b in e["bullets"]]
    for p in s["projects"]:
        p["id"] = _uid()
    s["skills_text"] = ", ".join(s["skills"])
    s["certs_text"] = "\n".join(s["certifications"])
    s["trade_text"] = ", ".join(s.get("tradeSkills") or [])
    return s


def _from_state(s: dict) -> dict:
    return {
        "name": s["name"], "email": s["email"], "phone": s["phone"], "location": s["location"], "summary": s["summary"],
        "experience": [{"title": e["title"], "company": e["company"], "duration": e["duration"],
                        "bullets": [b["text"] for b in e["bullets"] if b["text"].strip()]} for e in s["experience"]],
        "education": s["education"],
        "skills": [x.strip() for x in s["skills_text"].split(",") if x.strip()],
        "certifications": [x.strip() for x in s["certs_text"].splitlines() if x.strip()],
        "projects": [{"name": p["name"], "description": p["description"], "tech": p["tech"]} for p in s["projects"]],
        "tradeSkills": [x.strip() for x in s["trade_text"].split(",") if x.strip()],
        "apprenticeships": s.get("apprenticeships") or [],
    }


def _rb_init(force_sample: bool = False):
    u, stream = current_user(), P("stream_detail", E.DEFAULT_STREAM)
    ver = st.session_state.get("rb_ver", 0) + 1
    saved = None if force_sample else db.get_resume(u["id"])
    base = saved["data"] if saved else E.get_sample_resume(stream, P("full_name", u["full_name"]) or "Your Name")
    base.setdefault("tradeSkills", []); base.setdefault("apprenticeships", [])
    st.session_state.rb = _to_state(base)
    st.session_state.rb_ver = ver
    st.session_state.rb_user = (u["id"], stream)


def _rb_add_exp():
    st.session_state.rb["experience"].append(
        {"id": _uid(), "title": "", "company": "", "duration": "", "bullets": [{"id": _uid(), "text": ""}]})


def _rb_del_exp(i):
    st.session_state.rb["experience"] = [e for e in st.session_state.rb["experience"] if e["id"] != i]


def _rb_add_bullet(eid):
    for e in st.session_state.rb["experience"]:
        if e["id"] == eid:
            e["bullets"].append({"id": _uid(), "text": ""})


def _rb_del_bullet(eid, bid):
    for e in st.session_state.rb["experience"]:
        if e["id"] == eid:
            e["bullets"] = [b for b in e["bullets"] if b["id"] != bid]


def _rb_enhance(key):
    st.session_state[key] = E.enhance_bullet(st.session_state.get(key, ""))


def _rb_add_proj():
    st.session_state.rb["projects"].append({"id": _uid(), "name": "", "description": "", "tech": ""})


def _rb_del_proj(i):
    st.session_state.rb["projects"] = [p for p in st.session_state.rb["projects"] if p["id"] != i]


def tab_resume():
    u, stream = current_user(), P("stream_detail", E.DEFAULT_STREAM)
    if st.session_state.get("rb_user") != (u["id"], stream):
        _rb_init()
    s, v = st.session_state.rb, st.session_state.rb_ver
    trade = E.is_trade(stream)

    left, right = st.columns(2, gap="large")
    with left:
        with st.expander("👤 Personal info", expanded=True):
            s["name"] = st.text_input("Full name", s["name"], key=f"rb{v}_name")
            c1, c2 = st.columns(2)
            s["email"] = c1.text_input("Email", s["email"], key=f"rb{v}_email")
            s["phone"] = c2.text_input("Phone", s["phone"], key=f"rb{v}_phone")
            s["location"] = st.text_input("Location", s["location"], key=f"rb{v}_loc")
        with st.expander("📝 Professional summary", expanded=True):
            s["summary"] = st.text_area("Summary", s["summary"], height=110, key=f"rb{v}_sum",
                                        label_visibility="collapsed")
        with st.expander("💼 Experience", expanded=True):
            for n, e in enumerate(s["experience"]):
                with st.container(border=True):
                    h1, h2 = st.columns([5, 1])
                    h1.caption(f"Experience #{n + 1}")
                    h2.button("🗑", key=f"rb{v}_delexp_{e['id']}", on_click=_rb_del_exp, args=(e["id"],),
                              help="Remove this experience")
                    c1, c2 = st.columns(2)
                    e["title"] = c1.text_input("Title", e["title"], key=f"rb{v}_et_{e['id']}")
                    e["company"] = c2.text_input("Company", e["company"], key=f"rb{v}_ec_{e['id']}")
                    e["duration"] = st.text_input("Duration", e["duration"], key=f"rb{v}_ed_{e['id']}")
                    for b in e["bullets"]:
                        k = f"rb{v}_b_{b['id']}"
                        if k not in st.session_state:
                            st.session_state[k] = b["text"]
                        c1, c2, c3 = st.columns([8, 1.3, 1])
                        b["text"] = c1.text_input("Bullet", key=k, label_visibility="collapsed",
                                                  placeholder="Achievement bullet…")
                        c2.button("✨", key=f"rb{v}_enh_{b['id']}", on_click=_rb_enhance, args=(k,),
                                  help="AI-enhance this bullet (action verb + metric)")
                        c3.button("✕", key=f"rb{v}_delb_{b['id']}", on_click=_rb_del_bullet, args=(e["id"], b["id"]))
                    st.button("＋ Add bullet", key=f"rb{v}_addb_{e['id']}", on_click=_rb_add_bullet, args=(e["id"],))
            st.button("＋ Add experience", key=f"rb{v}_addexp", on_click=_rb_add_exp)
        with st.expander("🛠 Skills", expanded=True):
            s["skills_text"] = st.text_area("Skills (comma separated)", s["skills_text"], height=80, key=f"rb{v}_sk")
            if trade:
                s["trade_text"] = st.text_input("Trade skills (comma separated)", s["trade_text"], key=f"rb{v}_ts")
        with st.expander("🚀 Projects", expanded=True):
            for p in s["projects"]:
                with st.container(border=True):
                    h1, h2 = st.columns([5, 1])
                    p["name"] = h1.text_input("Name", p["name"], key=f"rb{v}_pn_{p['id']}")
                    h2.write(""); h2.write("")
                    h2.button("🗑", key=f"rb{v}_delp_{p['id']}", on_click=_rb_del_proj, args=(p["id"],))
                    p["description"] = st.text_area("Description", p["description"], height=70, key=f"rb{v}_pd_{p['id']}")
                    p["tech"] = st.text_input("Tech stack", p["tech"], key=f"rb{v}_pt_{p['id']}")
            st.button("＋ Add project", key=f"rb{v}_addp", on_click=_rb_add_proj)
        with st.expander("🎓 Certifications & education", expanded=False):
            s["certs_text"] = st.text_area("Certifications (one per line)", s["certs_text"], height=90, key=f"rb{v}_ce")
            for n, ed in enumerate(s["education"]):
                c1, c2 = st.columns([3, 1])
                ed["degree"] = c1.text_input(f"Degree #{n + 1}", ed["degree"], key=f"rb{v}_edg_{n}")
                ed["year"] = c2.text_input("Year", ed["year"], key=f"rb{v}_eyr_{n}")
                c1, c2 = st.columns([3, 1])
                ed["institution"] = c1.text_input("Institution", ed["institution"], key=f"rb{v}_ein_{n}")
                ed["score"] = c2.text_input("Score", ed["score"], key=f"rb{v}_esc_{n}")

    resume = _from_state(s)
    score = E.calculate_ats_score(resume, stream)
    tone = "#34d399" if score >= 80 else "#fbbf24" if score >= 60 else "#fb7185"

    with right:
        st.markdown(f"<div class='card' style='display:flex;justify-content:space-between;align-items:center'>"
                    f"<div><b>ATS Resume Builder</b><br><span class='muted'>{'Trade Skills format' if trade else 'Technical format'} · live preview</span></div>"
                    f"<div style='text-align:right'><span class='muted'>ATS score</span><br>"
                    f"<span style='font-size:1.9rem;font-weight:800;color:{tone}'>{score}</span>"
                    f"<span class='muted'>/100</span></div></div>", unsafe_allow_html=True)
        b1, b2, b3, b4 = st.columns(4)
        if b1.button("💾 Save", use_container_width=True, type="primary"):
            db.save_resume(u["id"], resume, score)
            refresh_profile()
            st.toast("Resume saved to MongoDB ✔", icon="✅")
        b2.download_button("⬇ PDF", pdf_export.resume_to_pdf(resume, trade),
                           file_name=f"{(resume['name'] or 'resume').replace(' ', '_')}_ATS.pdf",
                           mime="application/pdf", use_container_width=True)
        b3.download_button("🖨 HTML", pdf_export.resume_to_html(resume, trade, full_page=True),
                           file_name="resume_printable.html", mime="text/html", use_container_width=True,
                           help="Open in your browser and press Ctrl+P to print / save as PDF")
        if b4.button("↺ Reset", use_container_width=True, help="Discard edits and reload the sample resume"):
            _rb_init(force_sample=True)
            st.rerun()
        st.markdown(f"<div class='paper'>{pdf_export.resume_to_html(resume, trade)}</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Tab: Comparator
# ----------------------------------------------------------------------------
def _dial(label, score, color):
    circ = 2 * 3.14159265 * 40
    off = circ - score / 100 * circ
    return (f"<div style='text-align:center'><svg width='120' height='120' viewBox='0 0 100 100'>"
            f"<circle cx='50' cy='50' r='40' stroke='#1e293b' stroke-width='9' fill='none'/>"
            f"<circle cx='50' cy='50' r='40' stroke='{color}' stroke-width='9' fill='none' stroke-linecap='round' "
            f"stroke-dasharray='{circ:.1f}' stroke-dashoffset='{off:.1f}' transform='rotate(-90 50 50)'/>"
            f"<text x='50' y='56' text-anchor='middle' fill='#fff' font-size='22' font-weight='700'>{score}</text></svg>"
            f"<div class='muted'>{label}</div></div>")


def tab_comparator():
    stream = P("stream_detail", E.DEFAULT_STREAM)
    new = E.get_sample_resume(stream, P("full_name", "AI Resume"))
    new_score, old_score = E.calculate_ats_score(new, stream), E.get_old_resume_score()
    st.markdown("<div class='card' style='border-color:rgba(99,102,241,.3)'><h4>🆚 Side-by-Side Resume Comparator</h4>"
                "<span class='muted'>Paste your old resume below and see how the AI-optimised version stacks up</span></div>",
                unsafe_allow_html=True)
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown(f"**Old resume (paste here)** &nbsp; <span class='badge b-Critical'>ATS: {old_score}/100</span>",
                    unsafe_allow_html=True)
        st.text_area("old", key="old_resume", height=330, label_visibility="collapsed",
                     value="John Doe\nEmail: john@email.com\n\nObjective: Looking for a job in software development.\n\n"
                           "Experience:\n- Worked at ABC company\n- Did some coding work\n- Used some tools\n\n"
                           "Education:\n- B.Tech from some college\n\nSkills:\n- Java\n- C++")
    with b:
        st.markdown(f"**AI-optimised resume** &nbsp; <span class='badge b-Basic'>ATS: {new_score}/100</span>",
                    unsafe_allow_html=True)
        proj = f"<p><b>Projects:</b> {esc(', '.join(p['name'] for p in new['projects']))}</p>" if new["projects"] else ""
        st.markdown(f"<div class='card' style='font-size:.85rem;color:#cbd5e1;min-height:330px'>"
                    f"<b style='color:#fff'>{esc(new['name'])}</b><br><span class='muted'>{esc(new['email'])} · {esc(new['phone'])}</span>"
                    f"<p><b>Summary:</b> {esc(new['summary'])}</p><p><b>Skills:</b> {esc(' · '.join(new['skills']))}</p>{proj}"
                    f"<p><b>Certifications:</b> {esc(', '.join(new['certifications']))}</p></div>", unsafe_allow_html=True)

    st.markdown("<div class='card'><h4>ATS Score Comparison</h4><div style='display:flex;justify-content:center;gap:48px;align-items:center'>"
                f"{_dial('Old Resume', old_score, '#f43f5e')}"
                f"<div style='color:#34d399;font-weight:800;font-size:1.3rem'>➜ +{new_score - old_score} pts</div>"
                f"{_dial('AI Resume', new_score, '#10b981')}</div></div>", unsafe_allow_html=True)
    st.markdown("#### Detailed breakdown of fixes")
    for f in E.get_comparison_fixes():
        st.markdown(f"<div class='fixrow'><span class='cat'>{esc(f['category'])}</span>"
                    f"<span style='color:#94a3b8'>❌ {esc(f['old'])}</span><span style='color:#cbd5e1'>✅ {esc(f['fix'])}</span></div>",
                    unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Tab: Interview simulator
# ----------------------------------------------------------------------------
def _cls(score):
    return "ok" if score >= 80 else "mid" if score >= 50 else "low"


def _iv_reset():
    st.session_state.iv = {"started": False, "idx": 0, "phase": "asking", "results": [], "stream": P("stream_detail", E.DEFAULT_STREAM)}


def tab_interview():
    stream = P("stream_detail", E.DEFAULT_STREAM)
    if "iv" not in st.session_state or st.session_state.iv["stream"] != stream:
        _iv_reset()
    iv = st.session_state.iv
    questions = E.get_interview_questions(stream)
    u = current_user()

    if not iv["started"]:
        st.markdown(f"<div class='card' style='border-color:rgba(99,102,241,.3)'><h4>💬 AI Mock Interview Simulator</h4>"
                    f"<span class='muted'>Interactive terminal-style interview with stream-specific technical questions "
                    f"for <b>{esc(E.stream_label(stream))}</b>. Get real-time evaluation and feedback.</span></div>",
                    unsafe_allow_html=True)
        st.markdown(f"**What to expect**\n- {len(questions)} technical questions from Basic to Advanced\n"
                    "- Each answer is scored on concept coverage (70%) and depth (30%)\n"
                    "- Instant feedback with a model answer after every question\n"
                    "- Your final score is saved to your account\n\n"
                    "> **Tip:** Type detailed answers and include key technical terms.")
        if st.button("▶ Start Interview", type="primary"):
            iv["started"] = True
            st.rerun()
        hist = db.list_interviews(u["id"], 5)
        if hist:
            st.markdown("##### Your recent interviews")
            st.dataframe([{"Date": h["created_at"].strftime("%d %b %Y %H:%M"), "Stream": E.stream_label(h["stream"] or ""),
                           "Score": f"{h['score']}/100"} for h in hist], hide_index=True, use_container_width=True)
        return

    if iv["phase"] == "done":
        avg = round(sum(r["score"] for r in iv["results"]) / len(iv["results"]))
        st.markdown(f"<div class='card' style='text-align:center;border-color:rgba(16,185,129,.35)'><h3>🏆 Interview Complete</h3>"
                    f"<div class='muted'>Your overall technical accuracy score</div>"
                    f"<div style='font-size:3.2rem;font-weight:800' class='grad'>{avg}</div></div>", unsafe_allow_html=True)
        for i, r in enumerate(iv["results"], 1):
            st.markdown(f"<div class='fixrow' style='grid-template-columns:40px 1fr 60px'><span>Q{i}</span>"
                        f"<span style='color:#cbd5e1'>{esc(r['question'][:90])}</span>"
                        f"<b class='term {_cls(r['score'])}' style='background:none;border:0;padding:0'>{r['score']}</b></div>",
                        unsafe_allow_html=True)
        if st.button("↺ Restart interview"):
            _iv_reset()
            st.rerun()
        return

    idx = iv["idx"]
    q = questions[idx]
    st.progress(idx / len(questions), text=f"Technical interview · question {idx + 1} of {len(questions)}")
    log = ["<div class='term'><span class='p'>interview@ai-mastermind:~$</span> start --stream " + esc(stream)]
    for i, r in enumerate(iv["results"], 1):
        log.append(f"<br><br><span class='q'>Q{i}. {esc(r['question'])}</span><br><span class='p'>&gt;</span> "
                   f"<span class='a'>{esc(r['answer'])}</span><br><span class='{_cls(r['score'])}'>&nbsp;&nbsp;Score: {r['score']}/100</span>"
                   f"<br><span class='fb'>{esc(r['feedback'])}</span>")
    if iv["phase"] == "asking":
        log.append(f"<br><br><span class='q'>Q{idx + 1}. {esc(q['question'])}</span> "
                   f"<span class='badge b-{q['difficulty']}'>{q['difficulty']}</span>")
    log.append("</div>")
    st.markdown("".join(log), unsafe_allow_html=True)

    if iv["phase"] == "asking":
        ans = st.text_area("Your answer", key=f"iv_ans_{idx}", height=140, placeholder="Type your answer here…")
        if st.button("Submit answer ➤", type="primary"):
            if not ans.strip():
                st.warning("Type an answer first — even a partial one counts.")
            else:
                ev = E.evaluate_answer(ans, q)
                iv["results"].append({"question": q["question"], "answer": ans, **ev})
                iv["phase"] = "feedback"
                st.rerun()
    else:
        last = idx + 1 >= len(questions)
        if st.button("Finish interview ✔" if last else "Next question ➜", type="primary"):
            if last:
                avg = round(sum(r["score"] for r in iv["results"]) / len(iv["results"]))
                db.save_interview(u["id"], stream, avg, iv["results"])
                iv["phase"] = "done"
            else:
                iv["idx"], iv["phase"] = idx + 1, "asking"
            st.rerun()


# ----------------------------------------------------------------------------
# Dashboard shell
# ----------------------------------------------------------------------------
TABS = {"🎯 Reality Check": ("AI Reality Check Engine", "Unvarnished analysis of your real-world standing against 2026 market standards", tab_reality),
        "📚 Courses": ("Zero-Cost Course & Resource Recommender", "Exact free learning channels with WHY each skill matters and HOW to master it", tab_courses),
        "🗺️ Roadmap": ("3-Phase Execution Roadmap", "From fundamentals to job applications — a 6-month actionable timeline", tab_roadmap),
        "📄 Resume Builder": ("ATS Resume Builder", "Stream-adaptive layout with live preview, AI bullet enhancer and PDF export", tab_resume),
        "🆚 Comparator": ("Resume Comparator", "See exactly how your AI-optimised resume beats your old one", tab_comparator),
        "💬 Interview": ("AI Mock Interview Simulator", "Stream-specific technical questions with real-time evaluation", tab_interview)}


def dashboard():
    u, prof = current_user(), st.session_state.profile
    chk = E.get_reality_check(P("stream_detail", E.DEFAULT_STREAM), P("status", "Final Year"),
                              P("academic_score", "75%"), P("ambition", E.DEFAULT_AMBITION))
    with st.sidebar:
        st.markdown("### 🧭 AI Mastermind")
        st.markdown(f"**{esc(P('full_name', u['full_name']))}**  \n<span class='muted'>{esc(u['email']).replace('@', '&#64;')}</span>", unsafe_allow_html=True)
        st.markdown(f"<span class='muted'>{esc(E.stream_group(prof['stream_detail']))} · {esc(E.stream_label(prof['stream_detail']))}<br>"
                    f"{esc(prof['status'] or '')} · {esc(prof['academic_score'] or '')}</span>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.metric("Readiness", f"{chk['readiness']}")
        c2.metric("ATS score", f"{prof.get('ats_score') or 0}")
        if st.button("✏️ Edit intake", use_container_width=True):
            st.session_state.editing_intake = True
            st.session_state.pop("wiz", None); st.session_state.pop("wiz_step", None)
            st.rerun()
        if st.button("Sign out", use_container_width=True):
            logout()
            st.rerun()
        st.caption("Data stored in MongoDB · v4.2")

    choice = st.radio("nav", list(TABS), horizontal=True, label_visibility="collapsed", key="nav")
    title, sub, fn = TABS[choice]
    st.markdown(f"<h2 style='margin:.6rem 0 0'>{title}</h2><p class='muted' style='margin-bottom:1.2rem'>{sub}</p>",
                unsafe_allow_html=True)
    fn()


# ----------------------------------------------------------------------------
# Router
# ----------------------------------------------------------------------------
if not current_user():
    landing()
else:
    if "profile" not in st.session_state:
        refresh_profile()
    if st.session_state.get("editing_intake") or not P("stream_detail"):
        wizard()
    else:
        dashboard()
