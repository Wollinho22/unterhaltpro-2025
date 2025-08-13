# app.py
# UnterhaltPro 2025 — Düsseldorfer Tabelle calculator (Wizard + Expertenmodus)
# DISCLAIMER: Informational use only. No legal advice.
# UI/Content update 2025-08-13:
# - Landing page: replace "Kostenlos" with "PDF‑Report".
# - Modernized visual design (clean, minimal, slightly futuristic).
# - PDF: letter-style multi-paragraph report with bold+underlined key data.
# NOTE: Calculation logic unchanged per user instruction.

import math
import io
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import textwrap
import streamlit as st

# Optional: pip install reportlab
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

APP_NAME = "UnterhaltPro 2025"
APP_TAGLINE = "Schritt-für-Schritt-Rechner (Düsseldorfer Tabelle 2025, Leitlinien, BGB §§ 1601 ff.)"
APP_LOGO_SVG = """
<svg width="56" height="56" viewBox="0 0 56 56" xmlns="http://www.w3.org/2000/svg" aria-label="UnterhaltPro 2025">
  <defs>
    <linearGradient id="g2" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0ea5e9"/>
      <stop offset="1" stop-color="#38bdf8"/>
    </linearGradient>
    <filter id="glow"><feGaussianBlur stdDeviation="1.2"/></filter>
  </defs>
  <rect x="3" y="3" width="50" height="50" rx="14" fill="url(#g2)"/>
  <g stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round" filter="url(#glow)">
    <path d="M14 35c8 5 20 5 28 0"/>
  </g>
  <circle cx="20" cy="20" r="5" fill="#fff"/>
  <circle cx="36" cy="20" r="5" fill="#fff"/>
</svg>
"""

# ------------- UI polish -------------
st.set_page_config(page_title=APP_NAME, page_icon="👨‍👩‍👧", layout="wide")
st.markdown("""
<style>
:root{
  --bg:#0b0c0f;
  --card:rgba(255,255,255,0.60);
  --cardBorder:rgba(255,255,255,0.35);
  --ink:#0b1220;
  --ink-soft:#3b4455;
  --brand:#0ea5e9;
  --brand-2:#38bdf8;
  --accent:#e2f3ff;
  --ring:#bfe6ff;
  --radius:14px;
}
html, body, [class*="css"] {
  font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans";
}
.block-container { padding-top: 1.0rem; padding-bottom: 2.0rem; }

h1, h2, h3 { letter-spacing: .2px; }
.stButton>button, .stDownloadButton>button, .stCheckbox, .stNumberInput, .stSelectbox, .stRadio, .stTextInput { border-radius: var(--radius) !important; }
.stButton>button, .stDownloadButton>button { border:1px solid #cfd8e3; padding:.60rem 1.0rem; transition: all .2s ease; }
.stButton>button:hover, .stDownloadButton>button:hover { border-color:#b4c6de; box-shadow:0 6px 18px rgba(14,165,233,.15); }
.stAlert { border-radius: var(--radius) !important; box-shadow: 0 8px 24px rgba(15,23,42,.05); }
.st-expander { border-radius: var(--radius) !important; border: 1px solid #e6eaf1; background: #fcfdff; }
.stMetric { border-radius: var(--radius) !important; }
.progress-wrap { display:flex; gap:8px; align-items:center; margin: 6px 0 16px; flex-wrap:wrap }
.step { padding:6px 12px; border:1px solid #e9edf3; border-radius:999px; font-size:12px; background:#fbfdff; color:#0f172a; }
.step.active { background:#f0faff; border-color:#cfe8ff; color:#0a66c2; font-weight:600; }
.small { font-size:.92rem; color:#334155; }
.badge { display:inline-block; padding:2px 10px; border-radius:999px; font-size:12px; background:#f0faff; color:#075985; border:1px solid #cfe8ff; margin-left:6px;}
.hero {
  display:flex; gap:28px; align-items:center; padding:18px 20px;
  border:1px solid #e6ebf2; border-radius:18px;
  background:linear-gradient(180deg, #fbfeff 0%, #f7fbff 100%);
}
.hero h1 { margin:0; }
.hero-cta { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
.hero-pill { display:inline-block; padding:2px 12px; background:#f0faff; border:1px solid #d6ebff; color:#0a66c2; border-radius:999px; font-size:12px; }
.navbtn > div > button { padding: .28rem .65rem !important; font-size: 12px !important; border-radius: 999px !important; }
.child-card { border:1px solid #e6ebf2; padding:12px 14px; border-radius:14px; margin-bottom:12px; background:rgba(255,255,255,.86); backdrop-filter: blur(6px); }
.kit { display:flex; gap:12px; align-items:center; }
.kit .chip { padding:2px 10px; border:1px solid #d7e6f7; border-radius:999px; background:#f7fbff; color:#0b3a63; font-size:12px;}
.hr { height:1px; background:linear-gradient(90deg,#fff, #e9edf3, #fff); border:0; margin:16px 0;}
</style>
""", unsafe_allow_html=True)

# ------------- Legal constants -------------
KG_2025 = 255.0
KG_2025_HALF = KG_2025 / 2.0
MIN_NEED_2025 = {"0-5": 482, "6-11": 554, "12-17": 649, "18+": 693}
ADULT_NEED_OUT_OF_HOME = 990  # volljährig, auswärts (inkl. Unterkunft)

DT2025_PERCENTS = [100, 105, 110, 115, 120, 128, 136, 144, 152, 160, 168, 176, 184, 192, 200]
DT2025_BKB = {
    1: None, 2: 1750, 3: 1850, 4: 1950, 5: 2050, 6: 2150, 7: 2250, 8: 2350, 9: 2450,
    10: 2550, 11: 2850, 12: 3250, 13: 3750, 14: 4350, 15: 5050
}
DT2025_INCOME_BRACKETS = [
    (1,   0,    2100), (2,   2101, 2500), (3,   2501, 2900), (4,   2901, 3300),
    (5,   3301, 3700), (6,   3701, 4100), (7,   4101, 4500), (8,   4501, 4900),
    (9,   4901, 5300), (10,  5301, 5700), (11,  5701, 6400), (12,  6401, 7200),
    (13,  7201, 8200), (14,  8201, 9700), (15,  9701, 11200),
]

# Leitlinien presets (automatic; no manual tuning UI)
LEITLINIEN_PRESETS = {
    "NRW (OLG Düsseldorf)": {"auto_group_downsteps": {1: 0, 2: 0, 3: 1, 4: 2}},
    "Frankfurt/Main":       {"auto_group_downsteps": {1: 0, 2: 0, 3: 1, 4: 2}},
    "Dresden":              {"auto_group_downsteps": {1: 0, 2: 0, 3: 1, 4: 2}},
}

# Selbstbehalt defaults (fixed; not user-editable)
SB_EMPLOYED = 1450
SB_UNEMPLOYED = 1200
SB_ADULT = 1750

# ------------- Helpers & data classes -------------
def ceil_euro(x: float) -> int:
    return int(math.ceil(float(x)))

def child_age_band(age: int) -> str:
    if age <= 5: return "0-5"
    if age <= 11: return "6-11"
    if age <= 17: return "12-17"
    return "18+"

def tabellenbetrag(group: int, age_band: str) -> int:
    p = DT2025_PERCENTS[group - 1]
    base = MIN_NEED_2025["18+" if age_band == "18+" else age_band]
    return ceil_euro(base * p / 100.0)

def group_from_income(net_income: float) -> int:
    if net_income is None or net_income <= 0:
        return 1
    for g, lo, hi in DT2025_INCOME_BRACKETS:
        if lo <= net_income <= hi:
            return g
    return 15 if net_income > DT2025_INCOME_BRACKETS[-1][2] else 1

def apply_leitlinien_group_adjustment(group: int, n_berechtigte: int, preset_map: Dict[int, int]) -> int:
    key = min(max(n_berechtigte, 1), max(preset_map.keys()))
    auto_down = preset_map.get(key, 0)
    return max(1, min(15, group - auto_down))

@dataclass
class ChildInput:
    age: int
    lives_at_home: bool = True
    kg_to_receiving_parent: bool = True
    is_minor: bool = field(init=False)
    def __post_init__(self): self.is_minor = self.age < 18

@dataclass
class ParentIncome:
    bereinigtes_netto: float
    selbstbehalt: float

# ----------------- Calculation functions (UNCHANGED) -----------------
def compute_child_need_for_group(child: ChildInput, group: int) -> Dict[str, float]:
    # Minderjährige: gruppenweise pro Altersband; Volljährige im Haushalt: 693 € × Gruppenprozentsatz; auswärts: 990 € fix
    if child.age >= 18:
        if child.lives_at_home:
            tb = tabellenbetrag(group, "18+")
            kg_ded = KG_2025
            zahl = max(0.0, tb - kg_ded)
            return {"basis": "18+ (zu Hause, gruppenweise)", "tabellenbetrag": tb, "kg_deduction": kg_ded, "zahlbetrag_before_budget": zahl}
        else:
            need = ADULT_NEED_OUT_OF_HOME
            kg_ded = KG_2025
            zahl = max(0.0, need - kg_ded)
            return {"basis": "18+ (auswärts, fix 990 €)", "tabellenbetrag": need, "kg_deduction": kg_ded, "zahlbetrag_before_budget": zahl}
    else:
        ab = child_age_band(child.age)
        tb = tabellenbetrag(group, ab)
        kg_ded = KG_2025_HALF if child.kg_to_receiving_parent else KG_2025
        zahl = max(0.0, tb - kg_ded)
        return {"basis": ab, "tabellenbetrag": tb, "kg_deduction": kg_ded, "zahlbetrag_before_budget": zahl}

def sum_zahlbetraege_for_group(children: List[ChildInput], group: int) -> Tuple[List[Dict[str, float]], List[float], float]:
    breakdown = [compute_child_need_for_group(ch, group) for ch in children]
    pre = [d["zahlbetrag_before_budget"] for d in breakdown]
    return breakdown, pre, sum(pre)

def choose_group_by_bkb_after_payment(payer_net: float, start_group: int, children: List[ChildInput]) -> Tuple[int, List[Dict[str, float]], List[float], float, List[int]]:
    tried = []
    g = start_group
    while g >= 1:
        tried.append(g)
        bkb = DT2025_BKB.get(g) or 0
        breakdown, pre_list, pre_sum = sum_zahlbetraege_for_group(children, g)
        after = payer_net - pre_sum
        if bkb == 0 or after >= bkb:
            return g, breakdown, pre_list, pre_sum, tried
        g -= 1
    g = 1
    breakdown, pre_list, pre_sum = sum_zahlbetraege_for_group(children, g)
    tried.append(g)
    return g, breakdown, pre_list, pre_sum, tried

def scale_to_selbstbehalt_if_needed_in_group1(payer_net: float, payer_sb: float, pre_list: List[float]) -> Tuple[List[float], float]:
    total = sum(pre_list)
    allowed = max(0.0, payer_net - payer_sb)
    if total <= 0 or total <= allowed:
        return pre_list, 1.0
    factor = allowed / total
    return [round(x * factor, 2) for x in pre_list], factor

# ---------- Tiny helper: progress bar renderer ----------
def render_progress(current_step: int):
    parts = ["<div class='progress-wrap'>"]
    parts.append('<span class="step{}">Home</span>'.format(" active" if current_step == 0 else ""))
    parts.append('<span class="step{}">Schritt 1: Einkommen</span>'.format(" active" if current_step == 1 else ""))
    parts.append('<span class="step{}">Schritt 2: Anzahl Kinder</span>'.format(" active" if current_step == 2 else ""))
    parts.append('<span class="step{}">Schritt 3: Kinderdetails</span>'.format(" active" if current_step == 3 else ""))
    parts.append('<span class="step{}">Schritt 4: Leitlinien</span>'.format(" active" if current_step == 4 else ""))
    parts.append('<span class="step{}">Schritt 5: Mehr-/Sonderbedarf</span>'.format(" active" if current_step == 5 else ""))
    parts.append('<span class="step{}">Schritt 6: Ergebnis & PDF</span>'.format(" active" if current_step == 6 else ""))
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)

# ------------- Header & Disclaimer -------------
col_logo, col_title = st.columns([1, 6])
with col_logo: st.markdown(APP_LOGO_SVG, unsafe_allow_html=True)
with col_title:
    st.title(APP_NAME)
    st.caption(APP_TAGLINE)

with st.expander("⚠️ Wichtiger Hinweis (Disclaimer)"):
    st.markdown("""
**Kein Ersatz für Rechtsberatung.** Dieses Tool liefert eine **unverbindliche**, schematische Berechnung des Kindesunterhalts
nach der **Düsseldorfer Tabelle 2025** (OLG Düsseldorf), den **Leitlinien** und den Grundsätzen aus **BGB §§ 1601 ff.**  
Prüfen Sie im Zweifel die Originalquellen bzw. lassen Sie sich beraten.
    """)

# =============== Wizard + Expert State ===============
if "step" not in st.session_state:
    st.session_state.step = 0
if "expert_mode" not in st.session_state:
    st.session_state.expert_mode = False
if "n_children" not in st.session_state:
    st.session_state.n_children = 1
if "children" not in st.session_state:
    st.session_state.children = []  # snapshot from Step 3

# Expert toggle
st.markdown("---")
ex_cols = st.columns([1,6,1])
with ex_cols[0]:
    st.session_state.expert_mode = st.checkbox(
        "🔬 Expertenmodus", value=st.session_state.expert_mode,
        help="Blendet detaillierte Rechenwege, Prüfungen und Kurzverweise auf Rechtsgrundlagen ein."
    )

# Top clickable step navigation
nav = st.columns(7)
labels = ["Home", "Schritt 1", "Schritt 2", "Schritt 3", "Schritt 4", "Schritt 5", "Schritt 6"]
for idx, col in enumerate(nav):
    with col:
        if st.button(labels[idx], key=f"nav_{idx}", help="Direkt zu diesem Schritt springen."):
            st.session_state.step = idx
            st.rerun()

# Draw progress
render_progress(st.session_state.step)

# =============== Pages ===============

# ------- STEP 0: Landing Page -------
if st.session_state.step == 0:
    left, right = st.columns([7,5])
    with left:
        st.markdown(f"""
<div class="hero">
  <div>{APP_LOGO_SVG}</div>
  <div>
    <div class="hero-pill">Aktuell: Düsseldorfer Tabelle 2025 • Kindergeld 255 €</div>
    <h1>{APP_NAME}</h1>
    <p class="small">Schnelle & transparente Berechnung von Kindesunterhalt nach der Düsseldorfer Tabelle (2025),
    inkl. BKB‑Prüfung, Selbstbehalt, Herauf-/Herabstufung, Mehr-/Sonderbedarf und PDF‑Export.</p>
    <div class="hero-cta kit">
      <span class="chip">✅ Klar</span>
      <span class="chip">✅ Nachvollziehbar</span>
      <span class="chip">✅ PDF‑Report</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
        st.markdown("### Was Sie erwartet")
        st.markdown("""
- **Geführter Assistent**: Schritt für Schritt zu einem belastbaren Ergebnis.  
- **Detaillierte Rechenschritte**: Auf Wunsch alle Prüfungen (BKB, SB, Mangelfall‑Quote).  
- **PDF‑Export**: Ergebnis und Begründungen als übersichtliches Dokument.  
- **Offizielle Grundlagen**: Düsseldorfer Tabelle 2025, OLG‑Leitlinien, BGB §§ 1601 ff.
        """)
        if st.button("🚀 Jetzt starten", key="start_btn"):
            st.session_state.step = 1
            st.rerun()
    with right:
        st.info("""
**Hinweis:** Dieses Tool ersetzt **keine Rechtsberatung**.
Komplexe Sachverhalte (wechselndes Einkommen, besondere Bedarfe, Betreuungwechsel, etc.) gehören in fachkundige Hände.

**Quellen:**  
• OLG Düsseldorf – Düsseldorfer Tabelle 2025  
• Leitlinien der OLG  
• BGB §§ 1601 ff.
        """)
    st.stop()

# ------- STEP 1: Einkommen -------
if st.session_state.step == 1:
    st.header("Schritt 1 – Einkommen")
    st.radio(
        "Eingabeart",
        ["Bereinigtes Netto direkt", "Brutto + Absetzungsfähige Ausgaben (Assistent)"],
        horizontal=True, key="income_mode",
        help="Direktwert eingeben oder per Assistent aus Brutto und Abzügen ableiten."
    )

    colA, colB, colC = st.columns(3)
    if st.session_state.income_mode == "Bereinigtes Netto direkt":
        with colA:
            st.number_input("Bereinigtes Nettoeinkommen (Zahler) €/Monat", min_value=0.0, step=50.0, format="%.2f", key="payer_net")
        with colB:
            st.number_input("Bereinigtes Nettoeinkommen (Betreuender) €/Monat (optional)", min_value=0.0, step=50.0, format="%.2f", key="recv_net")
        with colC:
            st.checkbox("Zahler erwerbstätig?", value=True, key="payer_employed")
            st.checkbox("Betreuender erwerbstätig?", value=True, key="recv_employed")
            st.checkbox("Kindergeld an betreuenden Elternteil?", value=True, key="kg_default")
        derived_payer_net = float(st.session_state.get("payer_net", 0.0))
    else:
        with colA:
            st.number_input("Bruttoeinkommen (€/Monat)", min_value=0.0, step=100.0, format="%.2f", key="gross")
            st.checkbox("Zahler erwerbstätig?", value=True, key="payer_employed")
        with colB:
            st.number_input("Bereinigtes Nettoeinkommen (Betreuender) €/Monat (optional)", min_value=0.0, step=50.0, format="%.2f", key="recv_net")
            st.checkbox("Betreuender erwerbstätig?", value=True, key="recv_employed")
        with colC:
            st.checkbox("Kindergeld an betreuenden Elternteil?", value=True, key="kg_default")

        st.subheader("Absetzungsfähige Ausgaben (Monat) – Assistent")
        b1, b2 = st.columns(2)
        with b1:
            st.number_input("Steuern & Sozialabgaben (Pflicht)", min_value=0.0, step=50.0, format="%.2f", key="ded_tax_ss")
            st.number_input("Fahrtkosten (berufsbedingt)", min_value=0.0, step=10.0, format="%.2f", key="ded_work_commute")
            st.number_input("Arbeitsmittel/Telefon/Internet (anteilig)", min_value=0.0, step=10.0, format="%.2f", key="ded_work_tools")
        with b2:
            st.number_input("Fort-/Weiterbildung (berufsbedingt)", min_value=0.0, step=10.0, format="%.2f", key="ded_work_training")
            st.number_input("Doppelter Haushalt (falls einschlägig)", min_value=0.0, step=10.0, format="%.2f", key="ded_work_doublehome")
            st.number_input("Zusätzliche Altersvorsorge (angemessen)", min_value=0.0, step=10.0, format="%.2f", key="ded_retirement_extra")
            st.number_input("Schulden/Verbindlichkeiten (anerkannt)", min_value=0.0, step=10.0, format="%.2f", key="ded_debts")
            st.number_input("Kranken-/Pflege-Zusatz / Versicherungen", min_value=0.0, step=10.0, format="%.2f", key="ded_health_extra")

        st.number_input("Weitere abzugsfähige Posten", min_value=0.0, step=10.0, format="%.2f", key="ded_other")
        deductions_sum = sum([
            st.session_state.get("ded_tax_ss", 0.0),
            st.session_state.get("ded_work_commute", 0.0),
            st.session_state.get("ded_work_tools", 0.0),
            st.session_state.get("ded_work_training", 0.0),
            st.session_state.get("ded_work_doublehome", 0.0),
            st.session_state.get("ded_retirement_extra", 0.0),
            st.session_state.get("ded_debts", 0.0),
            st.session_state.get("ded_health_extra", 0.0),
            st.session_state.get("ded_other", 0.0),
        ])
        derived_payer_net = max(0.0, st.session_state.get("gross", 0.0) - deductions_sum)

        st.success(f"Bereinigtes Netto (abgeleitet): {derived_payer_net:,.2f} €")
        st.markdown("<div class='badge'>Brutto {0:,.2f} € − Abzüge {1:,.2f} €</div>".format(st.session_state.get('gross',0.0), deductions_sum), unsafe_allow_html=True)

    can_go_next = (derived_payer_net > 0.0)
    if not can_go_next:
        st.error("Bitte geben Sie ein positives (bereinigtes) Nettoeinkommen an.")
    if st.button("Weiter ➜", key="next_step1_noform", disabled=not can_go_next):
        st.session_state.derived_payer_net = float(derived_payer_net)
        st.session_state.step = 2
        st.rerun()

# ------- STEP 2: Anzahl der Kinder -------
elif st.session_state.step == 2:
    st.header("Schritt 2 – Anzahl der Kinder")
    n_current = int(st.session_state.get("n_children", 1))
    n_new = st.number_input("Wie viele Kinder sind unterhaltsberechtigt (gleiche Rangstufe)?",
                            min_value=1, max_value=10, step=1, value=n_current, key="n_children_input")
    col_b, col_n = st.columns(2)
    if col_b.button("◀ Zurück", key="back2"):
        st.session_state.step = 1
        st.rerun()
    if col_n.button("Weiter ➜", key="next2"):
        st.session_state.n_children = int(n_new)
        for i in range(st.session_state.n_children):
            st.session_state.setdefault(f"age{i}", 7 if i == 0 else 3)
            st.session_state.setdefault(f"home{i}", True)
            st.session_state.setdefault(f"kg{i}", st.session_state.get("kg_default", True))
        st.session_state.children = []
        st.session_state.step = 3
        st.rerun()

# ------- STEP 3: Kinderdetails (Alter, KG, Wohnsitz) -------
elif st.session_state.step == 3:
    st.header("Schritt 3 – Kinderdetails (Alter, Kindergeld, Wohnsitz)")
    n_children = int(st.session_state.get("n_children", 1))

    for i in range(n_children):
        st.markdown(f"<div class='child-card'><strong>Kind {i+1}</strong></div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.number_input("Alter (Jahre)", min_value=0, max_value=30, step=1, key=f"age{i}")
        age = int(st.session_state.get(f"age{i}", 0))
        if age >= 18:
            c2.checkbox("Lebt im Haushalt eines Elternteils?", key=f"home{i}",
                        help="Volljährig: 693 € (zu Hause, gruppenweise) vs. 990 € (auswärts, fix).")
        else:
            st.session_state[f"home{i}"] = True
            c2.write("Wohnsitz: im Haushalt (Residenzmodell)")
        c3.checkbox("KG an betreuenden Elternteil?", key=f"kg{i}",
                    help="Minderjährige: Abzug ½ KG; wenn Zahler KG erhält: voller KG-Abzug.")

        home_flag = True if age < 18 else bool(st.session_state.get(f"home{i}", True))
        if age < 18:
            band = child_age_band(age)
            label = f"Altersstufe: {band}"
        else:
            label = "Altersstufe: 18+ (zu Hause)" if home_flag else "Altersstufe: 18+ (auswärts)"
        st.markdown(f"<div class='small'>Stufe: <span class='badge'>{label}</span></div>", unsafe_allow_html=True)

    with st.expander("ℹ️ Hinweise"):
        st.markdown("""
- **Altersstufe** steuert den Tabellenbetrag (0–5 / 6–11 / 12–17 / 18+).  
- **18+ im Haushalt**: steigt gruppenweise mit (Basis 693 € × Prozentsatz).  
- **18+ auswärts**: pauschal 990 € (fix).  
- **Kindergeld‑Anrechnung**: Minderjährige ½ KG (sofern KG beim Betreuenden); Volljährige volles KG.  
        """)

    col_b, col_n = st.columns(2)
    if col_b.button("◀ Zurück", key="back3"):
        st.session_state.step = 2
        st.rerun()
    if col_n.button("Weiter ➜", key="next3"):
        children_saved = []
        for i in range(n_children):
            age = int(st.session_state.get(f"age{i}", 0))
            home = True if age < 18 else bool(st.session_state.get(f"home{i}", True))
            kg_to_recv = bool(st.session_state.get(f"kg{i}", st.session_state.get("kg_default", True)))
            children_saved.append({"age": age, "home": home, "kg": kg_to_recv})
        st.session_state.children = children_saved
        st.session_state.step = 4
        st.rerun()

# ------- STEP 4: Leitlinien -------
elif st.session_state.step == 4:
    st.header("Schritt 4 – Leitlinien")
    with st.form("form_step4"):
        st.selectbox("Leitlinien auswählen", list(LEITLINIEN_PRESETS.keys()), key="leitlinie",
                     help="Steuert die (automatische) Herabstufung bei mehreren gleichrangigen Berechtigten.")
        with st.expander("ℹ️ Hintergrund"):
            st.markdown("""
- Die Düsseldorfer Tabelle ist auf **zwei** gleichrangige Berechtigte ausgelegt.  
- Bei mehreren Berechtigten erfolgt nach Leitlinien eine **automatische Herabstufung** (hier je nach Leitlinie vorbelegt).  
- Zahlt der Pflichtige **nur für ein Kind**, erfolgt regelmäßig eine **Heraufstufung** um **eine Gruppe**, **sofern** der **Bedarfskontrollbetrag (BKB)** nach Zahlung gewahrt bleibt.  
- Selbstbehalt (2025): erwerbstätig **1.450 €**, nicht erwerbstätig **1.200 €**, ggü. volljährig nicht privilegierten **1.750 €**.
            """)
        back4 = st.form_submit_button("◀ Zurück")
        next4 = st.form_submit_button("Weiter ➜")
        if back4:
            st.session_state.step = 3
            st.rerun()
        if next4:
            st.session_state.step = 5
            st.rerun()

# ------- STEP 5: Mehr-/Sonderbedarf -------
elif st.session_state.step == 5:
    st.header("Schritt 5 – Mehr- & Sonderbedarf (optional)")
    with st.form("form_step5"):
        c1, c2 = st.columns(2)
        c1.number_input("Kita/OGS/Betreuung (€ / Monat)", min_value=0.0, step=10.0, key="mb_daycare")
        c1.number_input("Gesundheit/Versicherungen/Zuzahlungen (€ / Monat)", min_value=0.0, step=10.0, key="mb_health")
        c1.number_input("Schule/Studium/Material/AGs (€ / Monat)", min_value=0.0, step=10.0, key="mb_school")
        c2.number_input("Umgangs-/Reisekosten (€ / Monat)", min_value=0.0, step=10.0, key="mb_travel")
        c2.number_input("Weitere anerkannte Bedarfe (€ / Monat)", min_value=0.0, step=10.0, key="mb_more")

        with st.expander("ℹ️ Was gehört dazu?"):
            st.markdown("""
- **Mehrbedarf:** regelmäßig wiederkehrende, **zusätzliche** Kosten (z. B. Kita, Krankenversicherung, Nachhilfe), die nicht im Tabellenbetrag enthalten sind.  
- **Sonderbedarf:** **außergewöhnliche**, **unvorhergesehene** Einmalbeträge (z. B. teure Klassenfahrt).  
- Verteilung i. d. R. **quotenmäßig** nach bereinigten Einkommen **abzgl.** Selbstbehalt.
            """)

        back5 = st.form_submit_button("◀ Zurück")
        next5 = st.form_submit_button("Weiter ➜")
        if back5:
            st.session_state.step = 4
            st.rerun()
        if next5:
            st.session_state.step = 6
            st.rerun()

# ------- STEP 6: Ergebnis & PDF -------
else:
    st.header("Schritt 6 – Ergebnis & PDF")

    # Gather inputs
    derived_payer_net = float(st.session_state.get("derived_payer_net", st.session_state.get("payer_net", 0.0)))
    n_children = int(st.session_state.get("n_children", 1))

    # Children snapshot (from Step 3)
    children_objs: List[ChildInput] = []
    if st.session_state.get("children"):
        for saved in st.session_state.children:
            age = int(saved.get("age", 0))
            lives_at_home = True if age < 18 else bool(saved.get("home", True))
            kg_to_recv = bool(saved.get("kg", st.session_state.get("kg_default", True)))
            children_objs.append(ChildInput(age=age, lives_at_home=lives_at_home, kg_to_receiving_parent=kg_to_recv))
    else:
        for i in range(n_children):
            age = int(st.session_state.get(f"age{i}", 0))
            lives_at_home = True if age < 18 else bool(st.session_state.get(f"home{i}", True))
            kg_to_recv = bool(st.session_state.get(f"kg{i}", st.session_state.get("kg_default", True)))
            children_objs.append(ChildInput(age=age, lives_at_home=lives_at_home, kg_to_receiving_parent=kg_to_recv))

    payer_employed = bool(st.session_state.get("payer_employed", True))
    recv_employed = bool(st.session_state.get("recv_employed", True))
    recv_net = float(st.session_state.get("recv_net", 0.0))

    # Selbstbehalt (fixed defaults)
    any_non_priv_adult = all(ch.age >= 18 and not ch.lives_at_home for ch in children_objs) if children_objs else False
    payer_sb = (SB_EMPLOYED if payer_employed else SB_UNEMPLOYED) if not any_non_priv_adult else SB_ADULT
    recv_sb  = (SB_EMPLOYED if recv_employed else SB_UNEMPLOYED)

    # Determine group & Leitlinien
    base_group = group_from_income(derived_payer_net)
    preset_map = LEITLINIEN_PRESETS[st.session_state.get("leitlinie","NRW (OLG Düsseldorf)")] ["auto_group_downsteps"]
    adj_group_base = apply_leitlinien_group_adjustment(base_group, n_children, preset_map)

    # Heraufstufung (1 Kind)
    herauf_applied = False
    start_group = adj_group_base
    if n_children == 1:
        candidate_up = min(15, adj_group_base + 1)
        _, pre_list_up, pre_sum_up = sum_zahlbetraege_for_group(children_objs, candidate_up)
        bkb_up = DT2025_BKB.get(candidate_up) or 0
        after_up = derived_payer_net - pre_sum_up
        if bkb_up == 0 or after_up >= bkb_up:
            start_group = candidate_up
            herauf_applied = True

    # BKB loop
    chosen_group, per_child_breakdown, pre_amounts, pre_sum, groups_tried = \
        choose_group_by_bkb_after_payment(derived_payer_net, start_group, children_objs)
    bkb_of_chosen = DT2025_BKB.get(chosen_group) or 0
    after_payment = derived_payer_net - pre_sum

    # Mangelfall scaling if needed
    post_amounts = pre_amounts.copy()
    scale_factor = 1.0
    scaled = False
    if chosen_group == 1 and after_payment < payer_sb:
        post_amounts, scale_factor = scale_to_selbstbehalt_if_needed_in_group1(derived_payer_net, payer_sb, pre_amounts)
        scaled = (scale_factor < 0.999999)

    # Mehr-/Sonderbedarf Quote
    def avail(net: float, sb: float) -> float: return max(0.0, (net or 0) - (sb or 0))
    mb_total = float(st.session_state.get("mb_daycare", 0.0) + st.session_state.get("mb_health", 0.0) +
                     st.session_state.get("mb_school", 0.0) + st.session_state.get("mb_travel", 0.0) +
                     st.session_state.get("mb_more", 0.0))
    tot_avail = avail(derived_payer_net, payer_sb) + avail(recv_net, recv_sb)
    q_payer = 0.0 if tot_avail <= 0 else avail(derived_payer_net, payer_sb) / tot_avail
    q_recv  = 0.0 if tot_avail <= 0 else avail(recv_net, recv_sb) / tot_avail
    payer_mb_share = round(mb_total * q_payer, 2)
    recv_mb_share = round(mb_total * q_recv, 2)

    # Friendly summary
    total_regular = sum(post_amounts)
    st.markdown("""
**Zusammenfassung in Kürze:**  
Auf Basis Ihres **bereinigten Nettoeinkommens**, der **Einkommensgruppe** der Düsseldorfer Tabelle 2025, der
**Altersstufen** der Kinder sowie der **Kindergeld‑Anrechnung** wurde der **Zahlbetrag je Kind** ermittelt.
Anschließend wurde geprüft, ob der **Bedarfskontrollbetrag (BKB)** in der gewählten Gruppe **nach Zahlung** gewahrt bleibt;
falls nicht, erfolgte eine **Herabstufung**. Bei **nur einem Kind** wurde eine **Heraufstufung** geprüft und nur
übernommen, wenn der BKB weiterhin gewahrt blieb. Schließlich wurde der **Selbstbehalt** berücksichtigt; bei
Unterschreitung in **Gruppe 1** erfolgte eine **quotierte Verteilung**.  
Für wiederkehrende **Mehr-/Sonderbedarfe** wurde eine **Haftungsquote** gebildet und Ihr **Monatsanteil** ausgewiesen.  
**Weitere Detailinformationen** (Rechenschritte, Prüfungen und Kurzverweise auf Rechtsgrundlagen) finden Sie im **PDF**.
    """)

    left, right = st.columns([3,2])
    with left:
        st.subheader("Berechnung – Überblick")
        st.markdown(
            "- **Bereinigtes Netto (Zahler)**: **{0:,.2f} €**  \n"
            "- **Einkommensgruppe (Basis)**: **{1}**  \n"
            "- **Leitlinien‑Anpassung** (gleichrangige Berechtigte: {2}): **{3}** (Prozentstufe {4}%)  \n"
            "- **Startgruppe**: **{5}** {6}  \n"
            "- **BKB‑Prüfung**: getestet {7} → **gewählt: Gruppe {8}** (BKB {9} €)  \n"
            "- **Selbstbehalt (angesetzt)**: **{10:,.2f} €**"
            .format(
                derived_payer_net, group_from_income(derived_payer_net), n_children, adj_group_base,
                DT2025_PERCENTS[adj_group_base-1],
                start_group, "(Heraufstufung wegen 1 Kind)" if herauf_applied else "",
                ", ".join(map(str, groups_tried)), chosen_group, (bkb_of_chosen if bkb_of_chosen>0 else 0),
                payer_sb
            )
        )
        st.markdown("**Pro Kind:**")
        for i, (ch, d, pre, post) in enumerate(zip(children_objs, per_child_breakdown, pre_amounts, post_amounts)):
            if ch.age < 18:
                ab = child_age_band(ch.age)
            else:
                ab = "volljährig (zu Hause, gruppenweise)" if ch.lives_at_home else "volljährig (auswärts, 990 €)"
            tb = d["tabellenbetrag"]; kgd = d["kg_deduction"]
            st.markdown(
                "**Kind {0}** – {1} (Alter: {8})  \n"
                "• Tabellenbetrag (Gr. {2} / {3}%): **{4} €**  \n"
                "• KG‑Abzug: **-{5:.2f} €**  \n"
                "• Vor Quote: **{6:.2f} €**  \n"
                "• **Final**: **{7:.2f} €**".format(
                    i+1, ab, chosen_group, DT2025_PERCENTS[chosen_group-1], tb, kgd, pre, post, ch.age
                )
            )
        st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
        st.markdown(
            "**Mehr-/Sonderbedarf (gesamt):** {0:.2f} € / Monat  \n"
            "**Haftungsquote**: Zahler **{1:.2%}**, Betreuender **{2:.2%}**  \n"
            "→ Anteil Zahler: **{3:.2f} €**; Anteil Betreuender: **{4:.2f} €**"
            .format(mb_total, q_payer, q_recv, payer_mb_share, recv_mb_share)
        )

        if st.session_state.expert_mode:
            st.markdown("---")
            st.subheader("🔬 Experten‑Zusatzinformationen")
            age_band_lines = []
            for idx, ch in enumerate(children_objs, start=1):
                band = child_age_band(ch.age) if ch.age < 18 else ("18+ zu Hause (grupp.)" if ch.lives_at_home else "18+ auswärts (990)")
                age_band_lines.append(f"Kind {idx}: Alter {ch.age} → {band}")
            st.markdown("- **Alterszuordnung**: " + "; ".join(age_band_lines))
            st.markdown(
                "- Geprüfte Gruppenfolge: **{0}**  \n"
                "- Summe Zahlbeträge (gewählte Gruppe {1}): **{2:.2f} €**  \n"
                "- Rest nach Zahlung: **{3:.2f} €**  \n"
                "- BKB in Gruppe {1}: **{4} €**  \n"
                "{5}{6}"
                .format(
                    ", ".join(map(str, groups_tried)), chosen_group, sum(pre_amounts), after_payment,
                    (bkb_of_chosen if bkb_of_chosen>0 else 0),
                    ("- **Mangelfall‑Quotierung** aktiv: Faktor **{0:.6f}**  \n".format(scale_factor) if scaled else ""),
                    ("- **Heraufstufung angewandt** (1 Kind) → Startgruppe {0}  \n".format(start_group) if herauf_applied else "")
                )
            )
            st.markdown(
                "- Verfügbare Einkommen für Quote (nach SB): Zahler **{0:.2f} €**, Betreuender **{1:.2f} €**"
                .format(max(0.0, derived_payer_net - payer_sb), max(0.0, recv_net - recv_sb))
            )

    with right:
        st.subheader("Kurzfazit")
        st.metric("Regelmäßiger Unterhalt (Summe)", "{0:,.2f} € / Monat".format(total_regular))
        st.metric("Mehr-/Sonderbedarf (Anteil Zahler)", "{0:.2f} € / Monat".format(payer_mb_share))
        st.metric("Gesamtzahlung (Zahler)", "{0:,.2f} € / Monat".format(total_regular + payer_mb_share))
        if st.session_state.get("income_mode") == "Brutto + Absetzungsfähige Ausgaben (Assistent)":
            gross = st.session_state.get("gross", 0.0)
            abz = gross - derived_payer_net
            st.markdown("**Einkommenszusammenfassung**")
            st.markdown("- Brutto: **{0:,.2f} €**  \n- Abzüge gesamt: **{1:,.2f} €**  \n- **Bereinigtes Netto: {2:,.2f} €**".format(gross, abz, derived_payer_net))

    # -------- PDF Export (LETTER STYLE) --------
    def export_pdf(buffer: io.BytesIO, include_details: bool, expert_mode: bool):
        c = canvas.Canvas(buffer, pagesize=A4)
        W, H = A4
        margin_x, margin_y = 42, 60
        y = H - margin_y

        def draw_heading(txt):
            nonlocal y
            c.setFont("Helvetica-Bold", 12)
            c.setFillColor(colors.black)
            if y < 80: c.showPage(); y = H - margin_y
            c.drawString(margin_x, y, txt); y -= 18

        def draw_subheading(txt):
            nonlocal y
            c.setFont("Helvetica-Bold", 11)
            c.setFillColor(colors.black)
            if y < 80: c.showPage(); y = H - margin_y
            c.drawString(margin_x, y, txt); y -= 16

        def draw_para(txt, bold=False):
            nonlocal y
            c.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
            width = W - 2*margin_x
            wrapped = textwrap.wrap(txt, width=100)  # rough wrap
            for line in wrapped:
                if y < 80: c.showPage(); y = H - margin_y
                c.drawString(margin_x, y, line); y -= 14

        def draw_kv(label, value, underline=True, bold=True):
            """Key data line with bold+underline value."""
            nonlocal y
            base_font = "Helvetica"
            val_font = "Helvetica-Bold" if bold else "Helvetica"
            c.setFont(base_font, 10)
            if y < 80: c.showPage(); y = H - margin_y
            c.drawString(margin_x, y, f"{label}: ")
            label_width = c.stringWidth(f"{label}: ", base_font, 10)
            c.setFont(val_font, 10)
            c.drawString(margin_x + label_width, y, value)
            if underline:
                val_w = c.stringWidth(value, val_font, 10)
                c.setLineWidth(0.8)
                c.setStrokeColor(colors.black)
                c.line(margin_x + label_width, y - 1.5, margin_x + label_width + val_w, y - 1.5)
            y -= 16

        # Header
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin_x, y, f"{APP_NAME} – Berechnungsbericht"); y -= 10
        c.setFont("Helvetica", 9); c.setFillColor(colors.grey)
        c.drawString(margin_x, y, "Dieser Bericht dient der strukturierten Information. Er ersetzt keine Rechtsberatung."); y -= 18
        c.setFillColor(colors.black)

        # Anrede & Einleitung
        draw_para("Sehr geehrte*r Nutzer*in,", bold=False)
        draw_para(
            "nachfolgend erhalten Sie eine ausführliche Darstellung Ihrer individuellen Unterhaltsberechnung nach der Düsseldorfer Tabelle 2025. "
            "Alle wesentlichen Eingaben und Zwischenschritte wurden nachvollziehbar berücksichtigt."
        )

        # Abschnitt: Ihre Ausgangsdaten
        draw_heading("1. Ihre Ausgangsdaten")
        draw_kv("Bereinigtes Nettoeinkommen (Zahler)", f"{derived_payer_net:,.2f} €")
        draw_kv("Einkommensgruppe (Basis)", f"Gruppe {group_from_income(derived_payer_net)} ({DT2025_PERCENTS[group_from_income(derived_payer_net)-1]} %)")
        draw_kv("Anzahl gleichrangig Berechtigter", f"{n_children}")
        draw_kv("Gewählte Leitlinie", f"{st.session_state.get('leitlinie','NRW (OLG Düsseldorf)')}")
        if st.session_state.get("income_mode") == "Brutto + Absetzungsfähige Ausgaben (Assistent)":
            gross = st.session_state.get("gross", 0.0)
            abz = gross - derived_payer_net
            draw_kv("Brutto / Abzüge (Assistent)", f"{gross:,.2f} € / {abz:,.2f} €", underline=False)

        # Abschnitt: Einordnung in die Tabelle
        draw_heading("2. Einordnung in die Düsseldorfer Tabelle")
        draw_para(
            f"Aus Ihrem Einkommen ergibt sich zunächst die Basis-Einstufung in die Gruppe {group_from_income(derived_payer_net)} "
            f"({DT2025_PERCENTS[group_from_income(derived_payer_net)-1]} % des Mindestunterhalts). "
            f"Aufgrund der gewählten Leitlinie und der Zahl gleichrangig Berechtigter wird die Gruppe automatisch angepasst."
        )
        draw_kv("Leitlinien-Anpassung (Start)", f"Gruppe {adj_group_base} ({DT2025_PERCENTS[adj_group_base-1]} %)")
        if n_children == 1 and (start_group == adj_group_base + 1):
            draw_kv("Prüfung Heraufstufung (1 Kind)", f"erfolgreich → Startgruppe {start_group}", underline=False)
        else:
            draw_kv("Prüfung Heraufstufung (1 Kind)", "nicht einschlägig/ohne Änderung", underline=False)

        # Abschnitt: BKB-Prüfung
        draw_heading("3. Bedarfskontrollbetrag (BKB) – Prüfung")
        draw_para(
            "Es wurde geprüft, ob der Bedarfskontrollbetrag in der jeweiligen Gruppe nach Zahlung der kombinierten Zahlbeträge gewahrt bleibt. "
            "Erforderlichenfalls erfolgte eine Herabstufung um jeweils eine Gruppe."
        )
        draw_kv("Geprüfte Gruppenfolge", ", ".join(map(str, groups_tried)), underline=False)
        draw_kv("Gewählte Gruppe", f"Gruppe {chosen_group} ({DT2025_PERCENTS[chosen_group-1]} %)")
        draw_kv("BKB in gewählter Gruppe", f"{(bkb_of_chosen if bkb_of_chosen>0 else 0)} €", underline=False)
        draw_kv("Rest nach Zahlung", f"{after_payment:,.2f} €", underline=False)

        # Abschnitt: Selbstbehalt & Mangelfall
        draw_heading("4. Selbstbehalt & Mangelfall")
        draw_kv("Selbstbehalt (Zahler) angesetzt", f"{payer_sb:,.2f} €")
        if chosen_group == 1 and scaled:
            draw_para(
                f"Da der Selbstbehalt in Gruppe 1 ansonsten unterschritten würde, wurde eine quotenmäßige Anpassung vorgenommen "
                f"(Mangelfall). Der Verteilfaktor beträgt {scale_factor:.6f}.", bold=False
            )
        else:
            draw_para("Der Selbstbehalt bleibt nach Zahlung des ermittelten Unterhalts gewahrt.", bold=False)

        # Abschnitt: Ermittlung pro Kind
        draw_heading("5. Ermittlung pro Kind")
        for i, (ch, d, pre, post) in enumerate(zip(children_objs, per_child_breakdown, pre_amounts, post_amounts), start=1):
            ab = (child_age_band(ch.age) if ch.age < 18 else ("18+ (zu Hause, gruppenweise)" if ch.lives_at_home else "18+ (auswärts, 990 €)"))
            draw_subheading(f"Kind {i} – Alter {ch.age}, Stufe: {ab}")
            draw_kv("Tabellenbetrag (gewählte Gruppe)", f"{d['tabellenbetrag']} €", underline=True)
            draw_kv("Kindergeld-Anrechnung", f"-{d['kg_deduction']:.2f} €", underline=False)
            draw_kv("Zahlbetrag vor SB/BKB-Quote", f"{pre:.2f} €", underline=False)
            draw_kv("Zahlbetrag final", f"{post:.2f} €", underline=True)

        # Abschnitt: Mehr-/Sonderbedarf
        draw_heading("6. Mehr- & Sonderbedarf (Quote)")
        draw_kv("Mehr-/Sonderbedarf gesamt", f"{mb_total:.2f} €", underline=True)
        draw_kv("Haftungsquote Zahler / Betreuender", f"{q_payer:.2%} / {q_recv:.2%}", underline=False)
        draw_kv("Anteil Zahler / Anteil Betreuender", f"{payer_mb_share:.2f} € / {recv_mb_share:.2f} €", underline=True)

        # Abschnitt: Gesamtergebnis
        draw_heading("7. Gesamtergebnis")
        draw_kv("Regelmäßiger Unterhalt (Summe)", f"{sum(post_amounts):.2f} €", underline=True)
        draw_kv("Gesamtzahlung des Zahlers (inkl. Mehr-/Sonderbedarf)", f"{(sum(post_amounts)+payer_mb_share):.2f} €", underline=True)

        # Abschnitt: Hinweise & Unterhaltstitel
        draw_heading("8. Hinweise & Unterhaltstitel")
        draw_para(
            "Jedes unterhaltsberechtigte Kind hat grundsätzlich einen Anspruch auf einen Unterhaltstitel. "
            "Ein solcher Titel kann durch eine Urkunde beim Jugendamt oder Notar, oder durch Beschluss bei Gericht erwirkt werden. "
            "Dieser Bericht ist ein Informationsdokument und ersetzt keine Rechtsberatung."
        )

        # Optionaler Anhang (Detailtabellen)
        if include_details or expert_mode:
            draw_heading("Anhang: Rechen- und Prüfdetails")
            draw_para(f"Summe vor ggf. Mangelfall-Quote: {sum(pre_amounts):.2f} €.")
            if chosen_group == 1 and scaled:
                draw_para(f"Quotierungsfaktor (Mangelfall): {scale_factor:.6f}.")
            if n_children == 1 and herauf_applied:
                draw_para(f"Heraufstufung angewandt (Startgruppe {start_group}).")

            draw_subheading("Kurzverweise auf Rechtsgrundlagen")
            draw_para("BGB §§ 1601 ff. – Verwandtenunterhalt.")
            draw_para("Düsseldorfer Tabelle 2025 – Mindestunterhalt, Prozentsätze, Bedarfskontrollbeträge, Kindergeldanrechnung.")
            draw_para("Leitlinien der OLG – Herab-/Heraufstufung, Abzüge, Pauschalierungen.")

        # Schlussformel
        draw_para("Mit freundlichen Grüßen", bold=False)
        draw_para("Ihr UnterhaltPro‑2025‑Bericht", bold=True)

        c.showPage(); c.save()

    c1, c2, _ = st.columns([1,1,6])
    with c1:
        include_details = st.checkbox("PDF: detaillierten Anhang einfügen?", value=True)
    with c2:
        if st.button("📄 PDF exportieren", key="pdf_export"):
            buf = io.BytesIO(); export_pdf(buf, include_details, st.session_state.expert_mode)
            st.download_button("PDF herunterladen", data=buf.getvalue(),
                               file_name="unterhaltpro_2025_berechnung.pdf", mime="application/pdf", key="pdf_download")

    if st.button("◀ Zurück", key="back_step6"):
        st.session_state.step = 5
        st.rerun()

# Footer
st.markdown("---")
st.caption("© 2025 UnterhaltPro 2025 – Info-Tool, kein Rechtsrat. Prüfen Sie stets die aktuellen Veröffentlichungen des OLG Düsseldorf und der Leitlinien Ihres OLG.")
