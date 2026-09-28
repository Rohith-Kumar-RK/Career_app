"""Resume export helpers: ATS-friendly single-column PDF + printable HTML + on-screen preview."""
import html as _html

from fpdf import FPDF

_REPL = {"·": "|", "•": "-", "–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"',
         "₹": "Rs.", "…": "...", "→": "->", "\u00a0": " "}


def _s(text) -> str:
    text = "" if text is None else str(text)
    for a, b in _REPL.items():
        text = text.replace(a, b)
    return text.encode("latin-1", "replace").decode("latin-1")


def _clean(items):
    return [i.strip() for i in items if i and i.strip()]


def resume_to_pdf(r: dict, trade: bool) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_margins(16, 14, 16)
    pdf.set_auto_page_break(True, 14)
    pdf.add_page()

    def heading(t):
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, _s(t.upper()), new_x="LMARGIN", new_y="NEXT")
        y = pdf.get_y()
        pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
        pdf.ln(1.5)

    def body(t, style="", size=9.5, h=4.6):
        pdf.set_font("Helvetica", style, size)
        pdf.multi_cell(0, h, _s(t), new_x="LMARGIN", new_y="NEXT")

    def row(left, right, style="B"):
        pdf.set_font("Helvetica", style, 10)
        w = pdf.w - pdf.l_margin - pdf.r_margin
        pdf.cell(w * 0.72, 5, _s(left))
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(w * 0.28, 5, _s(right), align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 9, _s(r.get("name") or "Your Name"), new_x="LMARGIN", new_y="NEXT")
    contact = " | ".join(_clean([r.get("email"), r.get("phone"), r.get("location")]))
    body(contact, size=9)

    if r.get("summary"):
        heading("Summary")
        body(r["summary"])
    if r.get("experience"):
        heading("Work Experience & Apprenticeships" if trade else "Experience")
        for e in r["experience"]:
            row(e.get("title") or "Title", e.get("duration", ""))
            body(e.get("company", ""), size=9)
            for b in _clean(e.get("bullets", [])):
                body("- " + b, h=4.4)
            pdf.ln(1.5)
    if trade and r.get("tradeSkills"):
        heading("Trade Skills")
        body(" | ".join(r["tradeSkills"]))
    if r.get("skills"):
        heading("Skills")
        body(" | ".join(_clean(r["skills"])))
    if r.get("projects"):
        heading("Projects")
        for p in r["projects"]:
            body(p.get("name") or "Project Name", "B", 10)
            if p.get("tech"):
                body(p["tech"], "I", 9)
            if p.get("description"):
                body(p["description"])
            pdf.ln(1)
    if r.get("certifications"):
        heading("Certifications")
        for c in _clean(r["certifications"]):
            body("- " + c)
    if r.get("education"):
        heading("Education")
        for e in r["education"]:
            row(e.get("degree", ""), e.get("year", ""))
            body(f"{e.get('institution', '')} | {e.get('score', '')}", size=9)
    return bytes(pdf.output())


def resume_to_html(r: dict, trade: bool, full_page: bool = False) -> str:
    e = _html.escape
    out = []
    out.append(f"<h1 style='margin:0;font-size:24px'>{e(r.get('name') or 'Your Name')}</h1>")
    contact = " &nbsp;·&nbsp; ".join(e(x) for x in _clean([r.get("email"), r.get("phone"), r.get("location")]))
    out.append(f"<div class='c'>{contact}</div><hr style='border:0;border-top:2px solid #1e293b;margin:8px 0 10px'>")

    def h2(t):
        out.append(f"<h2>{e(t)}</h2>")

    if r.get("summary"):
        h2("Summary"); out.append(f"<p>{e(r['summary'])}</p>")
    if r.get("experience"):
        h2("Work Experience &amp; Apprenticeships" if trade else "Experience")
        for x in r["experience"]:
            out.append(f"<div class='row'><b>{e(x.get('title') or 'Title')}</b><span>{e(x.get('duration',''))}</span></div>"
                       f"<div class='s'>{e(x.get('company',''))}</div>")
            bl = "".join(f"<li>{e(b)}</li>" for b in _clean(x.get("bullets", [])))
            out.append(f"<ul>{bl}</ul>")
    if trade and r.get("tradeSkills"):
        h2("Trade Skills"); out.append(f"<p>{' · '.join(e(s) for s in r['tradeSkills'])}</p>")
    if r.get("skills"):
        h2("Skills"); out.append(f"<p>{' · '.join(e(s) for s in _clean(r['skills']))}</p>")
    if r.get("projects"):
        h2("Projects")
        for p in r["projects"]:
            out.append(f"<b>{e(p.get('name') or 'Project Name')}</b>")
            if p.get("tech"):
                out.append(f"<div class='s'>{e(p['tech'])}</div>")
            if p.get("description"):
                out.append(f"<p>{e(p['description'])}</p>")
    if r.get("certifications"):
        h2("Certifications")
        out.append("<ul>" + "".join(f"<li>{e(c)}</li>" for c in _clean(r["certifications"])) + "</ul>")
    if r.get("education"):
        h2("Education")
        for x in r["education"]:
            out.append(f"<div class='row'><b>{e(x.get('degree',''))}</b><span>{e(x.get('year',''))}</span></div>"
                       f"<div class='s'>{e(x.get('institution',''))} · {e(x.get('score',''))}</div>")
    style = ("<style>.resume{font-family:Arial,Helvetica,sans-serif;color:#111;line-height:1.45;font-size:12.5px}"
             ".resume h2{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:#334155;margin:14px 0 4px;"
             "border-bottom:1px solid #cbd5e1;padding-bottom:2px}.resume .row{display:flex;justify-content:space-between}"
             ".resume .s,.resume .c{color:#475569;font-size:11.5px}.resume p{margin:2px 0}.resume ul{margin:3px 0 8px 18px;padding:0}"
             ".resume li{margin:1px 0}</style>")
    body = f"{style}<div class='resume'>{''.join(out)}</div>"
    if not full_page:
        return body
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{e(r.get('name') or 'Resume')}</title>"
            f"<style>body{{margin:28px auto;max-width:800px}}@media print{{body{{margin:0}}}}</style></head>"
            f"<body>{body}</body></html>")
