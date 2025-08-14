# app.py
# UnterhaltPro 2025 — Düsseldorfer Tabelle calculator (Wizard + Expertenmodus)
# DISCLAIMER: Informational use only. No legal advice.

import math
import io
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import streamlit as st

# Optional: pip install reportlab
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

APP_NAME = "UnterhaltPro 2025"
APP_TAGLINE = "Schritt-für-Schritt-Rechner (Düsseldorfer Tabelle 2025, Leitlinien, BGB §§ 1601 ff.)"
APP_LOGO_SVG = """
<svg width="56" height="56" viewBox="0 0 56 56" xmlns="http://www.w3.org/2000/svg" aria-label="UnterhaltPro 2025">
  <defs><linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="#0ea5e9"/><stop offset="1" stop-color="#0891b2"/></linearGradient></defs>
  <rect x="3" y="3" width="50" height="50" rx="12" fill="url(#g)"/>
  <path d="M14 34c8 5 20 5 28 0" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/>
  <circle cx="20" cy="20" r="5" fill="#fff"/>
  <circle cx="36" cy="20" r="5" fill="#fff"/>
</svg>
"""

# ------------- UI polish -------------
st.set_page_config(page_title=APP_NAME, page_icon="👨‍👩‍👧", layout="wide")
st.markdown("""
<style>
html, body, [class*="css"] { font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans"; }
h1, h2, h3 { letter-spacing: 0.2px; }
.block-container { padding-top: 1.2rem; padding-bottom: 2.2rem; }
.st-expander, .stAlert, .stMetric, .stSidebar, .stButton>button, .stNumberInput, .stSelectbox, .stRadio, .stTextInput { border-radius: 12px !important; }
.st-expander { border: 1px solid #e6e6e6; }
.stAlert { box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
.stButton>button { border: 1px solid #d9d9d9; padding: 0.6rem 1.0rem; }
.stButton>button:hover { border-color: #bfbfbf; }
.progress-wrap { display:flex; gap:8px; align-items:center; margin: 6px 0 16px; flex-wrap:wrap }
.step { padding:6px 10px; border:1px solid #e7e7e7; border-radius:999px; font-size:12px; background:#fafafa; cursor:default; }
.step.active { background:#eef6ff; border-color:#cfe6ff; color:#0a66c2; font-weight:600; }
.small { font-size: 0.9rem; color: #444; }
.badge { display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; background:#eef6ff; color:#0a66c2; border:1px solid #d6e9ff; margin-left:6px;}
.hero { display:flex; gap:28px; align-items:center; padding:14px 18px; border:1px solid #e9eef3; border-radius:16px;
        background:linear-gradient(180deg, #fbfdff 0%, #f6fbff 100%); }
.hero h1 { margin:0; }
.hero-cta { display:flex; gap:10px; align-items:center; }
.hero-pill { display:inline-block; padding:2px 10px; background:#eef6ff; border:1px solid #d6e9ff; color:#0a66c2; border-radius:999px; font-size:12px; }
.navbtn > div > button { padding: 0.25rem 0.6rem !important; font-size: 12px !important; }
.child-card { border:1px solid #e9eef3; padding:10px 12px; border-radius:12px; margin-bottom:10px; background:#fbfdff; }
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

def tabellenbetrag(group: int, age_band: str, *, lives_at_home: bool = True) -> int:
    """Returns Tabellenbetrag for minors by band, and for 18+ (693€ at home / 990€ out of home) — all scaled by group percentage."""
    p = DT2025_PERCENTS[group - 1]
    if age_band == "18+":
        base = MIN_NEED_2025["18+"] if lives_at_home else ADULT_NEED_OUT_OF_HOME
    else:
        base = MIN_NEED_2025[age_band]
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

def compute_child_need_for_group(child: ChildInput, group: int) -> Dict[str, float]:
    if child.age >= 18:
        # Volljährige: Tabellenbedarf (693 zu Hause / 990 auswärts) wird gruppenweise prozentual skaliert; volles Kindergeld wird angerechnet.
        tb = tabellenbetrag(group, "18+", lives_at_home=child.lives_at_home)
        kg_ded = KG_2025
        zahl = max(0.0, tb - kg_ded)
        return {"basis": "volljährig", "tabellenbetrag": tb, "kg_deduction": kg_ded, "zahlbetrag_before_budget": zahl}
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
if "step" not in st.session_state:
    st.session_state.step = 0  # Landing page first
if "expert_mode" not in st.session_state:
    st.session_state.expert_mode = False
if "n_children" not in st.session_state:
    st.session_state.n_children = 1

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
    <div class="hero-cta">
      <span>✅ Klar. ✅ Nachvollziehbar. ✅ Professionell.</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
        st.markdown("### Was Sie erwartet")
        st.markdown("""
- **Geführter Assistent**: Schritt für Schritt zu einem belastbaren Ergebnis.  
- **Detaillierte Rechenschritte**: Auf Wunsch alle Prüfungen (BKB, SB, Mangelfall‑Quote).  
- **PDF‑Report**: Ihr Ergebnis als strukturiertes Schreiben mit Begründungen.  
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
        # Live preview of Altersstufe
        preview_band = ("0-5" if age <=5 else "6-11" if age <=11 else "12-17" if age <=17 else "18+")
        c1.caption(f"Altersstufe: **{preview_band}**")

        if age >= 18:
            c2.checkbox("Lebt im Haushalt eines Elternteils?", key=f"home{i}",
                        help="Volljährig: 693 € (zu Hause) vs. 990 € (auswärts); beide steigen gruppenweise prozentual.")
        else:
            st.session_state[f"home{i}"] = True
            c2.write("Wohnsitz: im Haushalt (Residenzmodell)")
        c3.checkbox("KG an betreuenden Elternteil?", key=f"kg{i}",
                    help="Minderjährige: Abzug ½ KG; wenn Zahler KG erhält: voller KG-Abzug.")

    with st.expander("ℹ️ Hinweise"):
        st.markdown("""
- **Altersstufe** steuert den Tabellenbetrag (0–5 / 6–11 / 12–17 / 18+).  
- **18+**: Bedarf (693 € im Haushalt / 990 € auswärts) steigt **gruppenweise prozentual**; volles KG wird angerechnet.  
- **Kindergeld‑Anrechnung**: Minderjährige ½ KG (sofern KG beim Betreuenden); Volljährige volles KG.  
- **Wohnsitz** nur relevant bei Volljährigen (693 € Zuhause / 990 € auswärts).
        """)

    col_b, col_n = st.columns(2)
    if col_b.button("◀ Zurück", key="back3"):
        st.session_state.step = 2
        st.rerun()
    if col_n.button("Weiter ➜", key="next3"):
        st.session_state.step = 4
        st.rerun()

# ------- STEP 4: Leitlinien (no manual adjustments) -------
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
    children_objs: List[ChildInput] = []
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

    # Determine base group from income
    base_group = group_from_income(derived_payer_net)

    # Apply Leitlinien downshift automatically
    preset_map = LEITLINIEN_PRESETS[st.session_state.get("leitlinie","NRW (OLG Düsseldorf)")] ["auto_group_downsteps"]
    adj_group_base = apply_leitlinien_group_adjustment(base_group, n_children, preset_map)

    # Heraufstufung (1 Kind): try +1 group if BKB holds after payment
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

    # BKB-driven step-down loop
    chosen_group, per_child_breakdown, pre_amounts, pre_sum, groups_tried = \
        choose_group_by_bkb_after_payment(derived_payer_net, start_group, children_objs)
    bkb_of_chosen = DT2025_BKB.get(chosen_group) or 0
    after_payment = derived_payer_net - pre_sum

    # Scale in group 1 if SB would be undershot (Mangelfall / quotierte Verteilung)
    post_amounts = pre_amounts.copy()
    scale_factor = 1.0
    scaled = False
    if chosen_group == 1 and after_payment < payer_sb:
        post_amounts, scale_factor = scale_to_selbstbehalt_if_needed_in_group1(derived_payer_net, payer_sb, pre_amounts)
        scaled = (scale_factor < 0.999999)

    # Mehr-/Sonderbedarf (Quote)
    def avail(net: float, sb: float) -> float: return max(0.0, (net or 0) - (sb or 0))
    mb_total = float(st.session_state.get("mb_daycare", 0.0) + st.session_state.get("mb_health", 0.0) +
                     st.session_state.get("mb_school", 0.0) + st.session_state.get("mb_travel", 0.0) +
                     st.session_state.get("mb_more", 0.0))
    tot_avail = avail(derived_payer_net, payer_sb) + avail(recv_net, recv_sb)
    q_payer = 0.0 if tot_avail <= 0 else avail(derived_payer_net, payer_sb) / tot_avail
    q_recv  = 0.0 if tot_avail <= 0 else avail(recv_net, recv_sb) / tot_avail
    payer_mb_share = round(mb_total * q_payer, 2)
    recv_mb_share = round(mb_total * q_recv, 2)

    # Friendly summary paragraph (formal, neutral, concise)
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

    # Output blocks
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
            ab = child_age_band(ch.age) if ch.age < 18 else ("volljährig (zu Hause)" if ch.lives_at_home else "volljährig (auswärts)")
            tb = d["tabellenbetrag"]; kgd = d["kg_deduction"]
            st.markdown(
                "**Kind {0}** – {1}  \n"
                "• Tabellenbetrag (Gr. {2} / {3}%): **{4} €**  \n"
                "• KG‑Abzug: **-{5:.2f} €**  \n"
                "• Vor Quote: **{6:.2f} €**  \n"
                "• **Final**: **{7:.2f} €**".format(
                    i+1, ab, chosen_group, DT2025_PERCENTS[chosen_group-1], tb, kgd, pre, post
                )
            )
        st.markdown("---")
        st.markdown(
            "**Mehr-/Sonderbedarf (gesamt):** {0:.2f} € / Monat  \n"
            "**Haftungsquote**: Zahler **{1:.2%}**, Betreuender **{2:.2%}**  \n"
            "→ Anteil Zahler: **{3:.2f} €**; Anteil Betreuender: **{4:.2f} €**"
            .format(mb_total, q_payer, q_recv, payer_mb_share, recv_mb_share)
        )

        if st.session_state.expert_mode:
            st.markdown("---")
            st.subheader("🔬 Experten‑Zusatzinformationen")
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

    # Details
    with st.expander("🔍 Detaillierte Rechenschritte"):
        st.markdown("**Geprüfte Gruppenfolge:** {0}".format(", ".join(map(str, groups_tried))))
        st.markdown("- Summe Zahlbeträge (gewählte Gruppe {0}): **{1:.2f} €**".format(chosen_group, sum(pre_amounts)))
        st.markdown("- Rest nach Zahlung: **{0:.2f} €** {1}".format(after_payment, "(≥ BKB)" if after_payment >= bkb_of_chosen else "(BKB unterschritten)"))
        if herauf_applied:
            st.markdown("- **Heraufstufung** angesetzt (Start mit Gruppe {0}).".format(start_group))
        if chosen_group == 1 and scaled:
            st.markdown("**Quotierung**: Gesamt {0:.2f} € → verfügbar {1:.2f} € → Faktor **{2:.6f}**"
                        .format(sum(pre_amounts), max(0.0, derived_payer_net - payer_sb), scale_factor))
            for i, (pre, post) in enumerate(zip(pre_amounts, post_amounts)):
                st.markdown("  • Kind {0}: {1:.2f} € × {2:.6f} = **{3:.2f} €**".format(i+1, pre, scale_factor, post))

    # PDF Export
    def export_pdf(buffer: io.BytesIO, include_details: bool, expert_mode: bool):
        c = canvas.Canvas(buffer, pagesize=A4)
        W, H = A4; x, y = 40, H - 60
        def line(txt, dy=16, bold=False):
            nonlocal y
            if y < 60:
                c.showPage(); y = H - 60
            c.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
            c.drawString(x, y, txt); y -= dy

        line(APP_NAME + " – Ergebnis", bold=True)
        line("Leitlinien: {0}".format(st.session_state.get('leitlinie','NRW (OLG Düsseldorf)')))
        line("Bereinigtes Netto (Zahler): {0:,.2f} €; SB: {1:,.2f} €".format(derived_payer_net, payer_sb))
        line("Gruppe Basis→Angepasst: {0} → {1}".format(group_from_income(derived_payer_net), adj_group_base))
        if herauf_applied:
            line("Heraufstufung (1 Kind): Startgruppe {0}".format(start_group))
        line("BKB geprüft; gewählt Gruppe {0} (BKB {1} €)".format(chosen_group, (bkb_of_chosen if bkb_of_chosen>0 else 0)))
        line("Kindergeld 2025: {0:.2f} €".format(KG_2025))

        line("Pro‑Kind‑Berechnung:", bold=True)
        for i, (ch, d, pre, post) in enumerate(zip(children_objs, per_child_breakdown, pre_amounts, post_amounts)):
            ab = child_age_band(ch.age) if ch.age < 18 else ("volljährig (zu Hause)" if ch.lives_at_home else "volljährig (auswärts)")
            line("Kind {0} – {1}".format(i+1, ab))
            line("  Tabellenbetrag (Gr. {0}): {1} €".format(chosen_group, d['tabellenbetrag']))
            line("  KG‑Abzug: -{0:.2f} €".format(d['kg_deduction']))
            line("  Vor Quote: {0:.2f} €".format(pre))
            line("  Final: {0:.2f} €".format(post))

        total_regular = sum(post_amounts)
        line("Mehr-/Sonderbedarf:", bold=True)
        line("Gesamt MB: {0:.2f} € | Quote: Zahler {1:.2%} / Betreuender {2:.2%}".format(mb_total, q_payer, q_recv))
        line("Anteil Zahler: {0:.2f} € | Anteil Betreuender: {1:.2f} €".format(payer_mb_share, recv_mb_share))

        line("Zusammenfassung", bold=True)
        line("Regelmäßiger Unterhalt (Summe): {0:.2f} € / Monat".format(total_regular))
        line("Gesamtzahlung (inkl. MB‑Anteil Zahler): {0:,.2f} € / Monat".format(total_regular + payer_mb_share))

        if include_details or expert_mode:
            line("Anhang: Prüfungen", bold=True)
            line("Geprüfte Gruppen: {0}".format(groups_tried))
            line("Summe vor Quote: {0:.2f} €; Rest nach Zahlung: {1:.2f} €".format(sum(pre_amounts), after_payment))
            if herauf_applied:
                line("Heraufstufung angewandt (Start {0})".format(start_group))
            if chosen_group == 1 and scaled:
                line("Quotierung – Faktor: {0:.6f}".format(scale_factor))
            line("Kurzverweise – Rechtsgrundlagen", bold=True)
            line("BGB §§ 1601 ff. – Verwandtenunterhalt")
            line("Düsseldorfer Tabelle 2025 – Mindestunterhalt, Prozente, KG‑Abzug, BKB")
            line("OLG‑Leitlinien – Herab-/Heraufstufung, Abzüge, Pauschalierungen")

        line("Quellen:", bold=True)
        line("OLG Düsseldorf – Düsseldorfer Tabelle & Leitlinien (2025) – https://www.olg-duesseldorf.nrw.de")
        line("BGB §§ 1601 ff. – Verwandtenunterhalt")
        c.showPage(); c.save()

    c1, c2, _ = st.columns([1,1,6])
    with c1:
        include_details = st.checkbox("PDF: detaillierten Anhang einfügen?", value=False)
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
