"""
engine.py - Career-intelligence logic (Python port of src/lib/mockData.ts).

All static content (streams, courses, roadmaps, interview questions, sample
resumes, reality-check text) lives in data/career_data.json, which was
exported from the original TypeScript file.  The scoring / filtering rules
below are line-for-line ports of the original functions.
"""
import json
import random
import re
from copy import deepcopy
from pathlib import Path

_DATA = json.loads((Path(__file__).parent / "data" / "career_data.json").read_text(encoding="utf-8"))

STREAM_GROUPS = _DATA["STREAM_GROUPS"]
STATUSES = _DATA["STATUSES"]
AMBITIONS = _DATA["AMBITIONS"]
BUDGETS = _DATA["BUDGETS"]
STRENGTH_OPTIONS = _DATA["STRENGTH_OPTIONS"]
WEAKNESS_OPTIONS = _DATA["WEAKNESS_OPTIONS"]
DEMO_PROFILES = _DATA["DEMO_PROFILES"]
ALL_STREAMS = [
    {**s, "group": g["group"]} for g in STREAM_GROUPS for s in g["streams"]
]
DEFAULT_STREAM = "btech-cse"
DEFAULT_BUDGET = "Low (Needs 100% free resources)"
DEFAULT_AMBITION = "Immediate Job / Earning"


def stream_label(key: str) -> str:
    return next((s["label"] for s in ALL_STREAMS if s["key"] == key), "your field")


def stream_group(key: str) -> str:
    return next((s["group"] for s in ALL_STREAMS if s["key"] == key), "")


def is_trade(stream_key: str) -> bool:
    return "iti" in stream_key or "diploma" in stream_key


def _parse_float(text: str) -> float:
    """JavaScript-style parseFloat: '8.5 CGPA' -> 8.5, '85%' -> 85, 'abc' -> 0."""
    m = re.match(r"\s*[-+]?(\d+\.?\d*|\.\d+)", text or "")
    return float(m.group(0)) if m else 0.0


# --------------------------------------------------------------------------
# Reality check
# --------------------------------------------------------------------------
def get_reality_check(stream_key: str, status: str, score: str, ambition: str) -> dict:
    static = _DATA["reality"].get(stream_key, {})
    label = stream_label(stream_key)

    is_tech = any(t in stream_key for t in ("cse", "ai", "ds", "copa", "bca"))
    is_trade_ = any(t in stream_key for t in ("iti", "diploma", "fitter", "welder"))
    is_final = status in ("Final Year", "Recent Graduate")

    base = 62 if is_tech else 55 if is_trade_ else 48
    score_num = _parse_float(score)
    boost = 12 if score_num > 80 else 6 if score_num > 60 else 0
    readiness = min(95, base + boost + (5 if is_final else 0))

    demand = static.get("marketDemand", "Moderate")
    salary = static.get("salaryRange", "Varies by role and location")
    gap = static.get(
        "competitiveGap",
        f"In {label}, practical skills and portfolio matter more than your degree. Build proof of work.",
    )
    parts = salary.split("→")
    ceiling = parts[1].strip() if len(parts) > 1 else salary

    if readiness > 75:
        verdict = "Strong position — but don't get comfortable. Top 10% candidates still outcompete you on projects and communication."
    elif readiness > 55:
        verdict = "You're in the middle of the pack. That's the danger zone — you need to differentiate fast with real skills and proof of work."
    else:
        verdict = ("You are currently below the employability bar. Without immediate upskilling and a portfolio, "
                   "interviews will be rare. The good news: 90 days of focused work can change this.")

    return {
        "readiness": readiness,
        "marketDemand": demand,
        "salaryRange": salary,
        "competitiveGap": gap,
        "verdict": verdict,
        "highlights": [
            {"label": "Market Demand", "value": demand, "tone": "good"},
            {"label": "Salary Ceiling", "value": ceiling, "tone": "warn"},
            {"label": "Readiness Score", "value": f"{readiness}/100",
             "tone": "good" if readiness > 70 else "warn" if readiness > 50 else "bad"},
            {"label": "Primary Gap", "value": re.split(r"\.(?:\s|$)", gap)[0] or "Portfolio & practical skills", "tone": "bad"},
        ],
    }


def readiness_takeaway(readiness: int) -> str:
    if readiness > 75:
        return "well-positioned but need to maintain momentum"
    if readiness > 55:
        return "in the competitive middle — differentiation is urgent"
    return "below the bar — immediate upskilling is critical"


# --------------------------------------------------------------------------
# Courses & roadmap
# --------------------------------------------------------------------------
_FREE_TYPES = ("YouTube", "Free", "Official", "Interactive", "Practice", "Reading", "Newsletter", "Site")


def get_course_recommendations(stream_key: str, budget: str) -> list:
    recs = deepcopy(_DATA["courses"][stream_key])
    if "Low" in (budget or ""):
        for r in recs:
            r["resources"] = [
                res for res in r["resources"] if any(t in res["type"] for t in _FREE_TYPES)
            ]
    return recs


def get_roadmap(stream_key: str, ambition: str) -> list:
    phases = deepcopy(_DATA["roadmap"][stream_key])
    extra = []
    if "Higher" in (ambition or ""):
        extra.append({"task": "Prepare for GATE/GRE/GMAT",
                      "detail": "If pursuing higher studies, start exam prep in parallel. Solve previous papers. Join free prep communities."})
    if "Govt" in (ambition or ""):
        extra.append({"task": "Start govt exam preparation",
                      "detail": "Identify target exams (SSC, Banking, RRB, PSC). Get syllabus. Start daily current affairs + quantitative aptitude practice."})
    phases[-1]["items"].extend(extra)
    return phases


# --------------------------------------------------------------------------
# Interview
# --------------------------------------------------------------------------
def get_interview_questions(stream_key: str) -> list:
    return deepcopy(_DATA["questions"][stream_key])


def evaluate_answer(answer: str, question: dict) -> dict:
    if not answer.strip():
        return {"score": 0, "feedback": "No answer provided. Even a partial attempt is better than silence."}
    lower = answer.lower()
    keywords = question["expectedKeywords"]
    matched = [k for k in keywords if k.lower() in lower]
    ratio = len(matched) / len(keywords)
    length_score = min(len(answer) / 200, 1)
    score = int(round((ratio * 0.7 + length_score * 0.3) * 100))
    n, total = len(matched), len(keywords)
    model = question["modelAnswer"]
    if score >= 80:
        fb = f"Excellent! You covered {n}/{total} key concepts. Your answer shows strong understanding. Model answer for comparison: {model}"
    elif score >= 50:
        missing = ", ".join(k for k in keywords if k not in matched)
        fb = f"Good attempt — you mentioned {n}/{total} key points. Missing: {missing}. Model answer: {model}"
    else:
        fb = f"Needs work. You covered {n}/{total} key concepts. Key points to include: {', '.join(keywords)}. Model answer: {model}"
    return {"score": score, "feedback": fb}


# --------------------------------------------------------------------------
# Resume
# --------------------------------------------------------------------------
def calculate_ats_score(resume: dict, stream_key: str) -> int:
    score = 40
    summary = resume.get("summary", "")
    experience = resume.get("experience", [])
    skills = [s for s in resume.get("skills", [])]
    if summary and len(summary) > 50:
        score += 8
    if experience:
        score += 10
    if any(re.search(r"\d", b) for e in experience for b in e.get("bullets", [])):
        score += 8
    if len(skills) >= 5:
        score += 8
    if len(skills) >= 10:
        score += 4
    if resume.get("education"):
        score += 6
    if resume.get("projects"):
        score += 8
    if resume.get("certifications"):
        score += 4
    if resume.get("email") and re.search(r"\S+@\S+\.\S+", resume["email"]):
        score += 2
    if resume.get("phone") and len(resume["phone"]) >= 10:
        score += 2
    if is_trade(stream_key):
        if resume.get("tradeSkills"):
            score += 6
        if resume.get("apprenticeships"):
            score += 6
    return min(100, score)


_VERBS = ["Led", "Built", "Developed", "Optimized", "Implemented", "Designed",
          "Streamlined", "Automated", "Achieved", "Delivered"]
_METRICS = ["reducing processing time by 35%", "serving 500+ users", "improving accuracy to 98%",
            "cutting costs by 20%", "increasing throughput by 40%"]
_STARTS = re.compile(r"^(Led|Built|Developed|Optimized|Implemented|Designed|Streamlined|Automated|"
                     r"Achieved|Delivered|Created|Managed|Spearheaded)", re.I)


def enhance_bullet(text: str) -> str:
    if not text.strip():
        return text
    metric = "" if re.search(r"\d", text) else " " + random.choice(_METRICS)
    cleaned = text[0].upper() + text[1:]
    if _STARTS.match(cleaned):
        return cleaned + metric
    return f"{random.choice(_VERBS)} {cleaned.lower()}{metric}"


def get_sample_resume(stream_key: str, name: str) -> dict:
    r = deepcopy(_DATA["resume"][stream_key])
    r["name"] = name
    r["email"] = re.sub(r"\s", ".", name.lower()) + "@email.com"
    return r


def get_old_resume_score() -> int:
    return _DATA["OLD_SCORE"]


def get_comparison_fixes() -> list:
    return _DATA["FIXES"]
