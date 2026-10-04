"""The opening world briefing: local artwork and accessible, selectable text."""

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st


ARTWORK = Path(__file__).resolve().parents[1] / "assets" / "intro-war-room.png"


@lru_cache(maxsize=2)
def _artwork_uri(modified_ns):
    """Keep the embedded artwork local, refreshing it if the file changes."""
    return "data:image/png;base64," + base64.b64encode(ARTWORK.read_bytes()).decode("ascii")


STYLE = """
<style>
.st-key-opening_briefing {
    position:relative; overflow:hidden; isolation:isolate;
    padding:clamp(1.5rem, 4.4vw, 4rem); border:1px solid #334650;
    border-radius:16px; background-color:#08121d;
    background-size:cover; background-position:center center;
    box-shadow:0 24px 80px #0005;
}
.st-key-opening_briefing::before {
    content:""; position:absolute; inset:0; z-index:-1; pointer-events:none;
    background:linear-gradient(90deg, #07111bf5 0%, #07111be8 34%, #07111ba6 62%, #07111b14 100%),
        linear-gradient(0deg, #07111bf0 0%, transparent 55%, #07111b40 100%);
}
.ww3-opening-topline {
    display:flex; justify-content:space-between; align-items:center;
    flex-wrap:wrap; gap:.8rem 1.5rem; margin-bottom:2.4rem;
    color:#b8d0da; font-size:.7rem; font-weight:600; letter-spacing:.16em;
    text-transform:uppercase;
}
.ww3-opening-brand {display:flex; gap:.9rem; align-items:center; color:#ecf6f8;}
.ww3-opening-mark {font-size:1.4rem; color:#8ce1d0; line-height:1;}
.ww3-opening-classification {color:#acc5cb; font-size:.65rem; letter-spacing:.12em;}
.ww3-opening-kicker {color:#e5b779; font-size:.72rem; font-weight:650; letter-spacing:.18em; margin:0 0 .85rem; text-transform:uppercase;}
.ww3-opening h1 {
    max-width:780px; color:#f2f7f9; font-size:clamp(2.6rem, 4.6vw, 4.4rem) !important;
    line-height:1.04; letter-spacing:-.045em; font-weight:750 !important;
    padding:0; margin:0 0 1.4rem; text-wrap:balance;
}
.ww3-opening-text {max-width:660px; color:#d3dfe6;}
.ww3-opening-text p {font-size:.96rem; line-height:1.66; margin:0 0 1rem; text-wrap:pretty;}
.ww3-opening-text strong {font-weight:650; color:#edf5f7;}
.ww3-opening-mandate {color:#edf5f7 !important; border-left:2px solid #85d9c6; padding-left:1rem; margin-top:1.25rem !important;}
.ww3-opening-status {
    display:flex; align-items:center; flex-wrap:wrap; gap:.6rem 1.5rem;
    border-top:1px solid #8cb9c22e; max-width:660px;
    margin-top:1.5rem; padding-top:1rem; color:#a6bec7;
    font-size:.65rem; letter-spacing:.12em; text-transform:uppercase;
}
.ww3-opening-status span:first-child {color:#8fe0d1;}
.ww3-opening-status i {display:inline-block; width:5px; height:5px; background:#8fe0d1; border-radius:50%; margin-right:.45rem; vertical-align:middle;}
.st-key-opening_actions {max-width:660px; margin-top:.2rem;}
.st-key-opening_actions button {min-height:3rem; font-weight:650; border-radius:6px;}
.st-key-opening_actions [data-testid="stBaseButton-secondary"] {background:#0b1a27bf; border-color:#638493; color:#e6f0f4;}
.st-key-opening_actions button:focus-visible {outline:3px solid #e5b779; outline-offset:3px;}
.st-key-opening_actions [data-testid="stCaptionContainer"] {color:#adc1ca; font-size:.74rem;}
@media (max-width:900px) {
    .st-key-opening_briefing {background-position:62% center;}
    .st-key-opening_briefing::before {background:linear-gradient(90deg,#07111bed,#07111bc9 68%,#07111b80),linear-gradient(0deg,#07111bf0,transparent);}
    .ww3-opening-topline {margin-bottom:2rem;}
}
@media (max-width:640px) {
    .st-key-opening_briefing {padding:1.5rem 1.25rem; border-radius:10px; background-position:65% top;}
    .ww3-opening-topline {margin-bottom:2.3rem; gap:.7rem; font-size:.64rem;}
    .ww3-opening-classification {font-size:.6rem;}
    .ww3-opening h1 {font-size:2.65rem !important; line-height:1.08;}
    .ww3-opening-text p {font-size:.95rem; line-height:1.66;}
    .ww3-opening-status {gap:.6rem 1rem; font-size:.61rem;}
}
</style>
"""


BRIEFING = """
<div class="ww3-opening">
    <div class="ww3-opening-topline">
        <div class="ww3-opening-brand"><span class="ww3-opening-mark" aria-hidden="true">◈</span> GEOPOLITICS / WW3</div>
        <div class="ww3-opening-classification">World briefing / Fictional scenario</div>
    </div>
    <p class="ww3-opening-kicker">Opening briefing · 2026</p>
    <h1>POWER HAS A PRICE.</h1>
    <div class="ww3-opening-text">
        <p>In 2026, the world's fault lines run through mine shafts, power grids and data centers.
        <strong>Minerals</strong> build the machines of war. <strong>Energy</strong> keeps them running.
        <strong>Compute</strong> feeds research and cyber warfare; <strong>innovation</strong> strengthens industry and armies.
        Each year's <strong>productivity</strong> is a chance that cannot be banked.</p>
        <p>The European Union must secure Eastern Europe, roll back Russian influence and preserve Arctic balance.
        The United States seeks Arctic dominance, a check on China's Pacific strength, and South America free of foreign forces.
        China seeks command of the Pacific and Arctic. Russia demands near-total military control in Eastern Europe and a commanding Arctic presence.</p>
        <p>Behind every deployment stands an economy. Taxes test public contentment. Construction consumes reserves;
        deployed forces drain the treasury. Trade can share industrial advantages. Alliances combine armies whose ambitions may never align.
        Unused compute expires. Uncovered operating shortfalls become debt, and debt keeps charging interest.</p>
        <p class="ww3-opening-mandate">All four powers resolve their annual orders together. Military shares can change;
        territorial influence survives withdrawal. In the standard objective campaign, secure every national objective for
        <strong>three consecutive years</strong> to claim victory. The next balance of power begins with your orders.</p>
    </div>
    <div class="ww3-opening-status" aria-label="Game format">
        <span><i aria-hidden="true"></i> Command ready</span>
        <span>04 powers</span><span>04 fronts</span><span>Simultaneous turns</span>
    </div>
</div>
"""


def render_opening():
    """Render the hero; its native Streamlit actions live in the same container."""
    st.markdown(STYLE, unsafe_allow_html=True)
    try:
        artwork = _artwork_uri(ARTWORK.stat().st_mtime_ns)
    except OSError:
        # The briefing and campaign controls still work if artwork is unavailable.
        artwork = ""
    if artwork:
        st.markdown(f'<style>.st-key-opening_briefing {{background-image:url("{artwork}");}}</style>', unsafe_allow_html=True)
    st.markdown(BRIEFING, unsafe_allow_html=True)
