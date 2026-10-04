"""Local presentation preferences and original synthesized action sounds."""

from pathlib import Path
from uuid import uuid4

import streamlit as st

from ww3.persistence.preferences import DEFAULTS, TEXT_SCALES


def cue(kind):
    st.session_state.audio_event = {"id": uuid4().hex, "kind": kind}


def preference_changed(name):
    st.session_state[name] = st.session_state[f"setting_{name}"]


def settings_controls():
    with st.sidebar.expander("Sound & display"):
        for name, value in DEFAULTS.items():
            st.session_state.setdefault(name, value)
            st.session_state.setdefault(f"setting_{name}", st.session_state[name])
        st.checkbox("Sound effects", key="setting_sound_enabled", on_change=preference_changed, args=("sound_enabled",))
        st.slider("Effects volume (%)", 0, 100, key="setting_sound_volume", on_change=preference_changed, args=("sound_volume",))
        st.select_slider("Text size", TEXT_SCALES, format_func=lambda value: f"{value}%", key="setting_text_scale", on_change=preference_changed, args=("text_scale",))
        st.checkbox("Reduce motion", key="setting_reduce_motion", on_change=preference_changed, args=("reduce_motion",))
        st.caption("Sounds mark draft edits, commitments and resolved years. All information is also shown on screen. Turn reviews always advance manually.")
        return st.container()


def apply_display():
    scale = st.session_state.get("text_scale", 100)
    if scale not in TEXT_SCALES:
        scale = 100
    motion = "*,*::before,*::after {animation-duration:.01ms !important; transition-duration:.01ms !important; scroll-behavior:auto !important;}"
    css = f"html {{font-size:{16 * scale / 100}px;}}"
    css += f"@media (prefers-reduced-motion: reduce) {{{motion}}}"
    if st.session_state.get("reduce_motion", True):
        css += motion
    if scale >= 130:
        css += "div:has(> .st-key-planning_summary) {position:static;}"
    css += "@media (max-width:640px) {h1 {font-size:2rem !important;} .resource-summary {font-size:.85rem;}}"
    css += ".resource-scroll:focus-visible {outline:2px solid #71d6bc; outline-offset:2px;}"
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_audio(slot):
    with slot:
        component = st.components.v2.component("ww3_audio", html='<button id="test-sound" type="button">Test sound</button><p id="audio-status" role="status"></p>',
            css="""button {background:transparent; color:var(--st-text-color); font:inherit; border:1px solid #526476; border-radius:6px; padding:.4rem .7rem; cursor:pointer;}
            button:focus-visible {outline:2px solid #71d6bc;} button:disabled {opacity:.5; cursor:default;} p {font: .8rem sans-serif; color:var(--st-text-color); margin:.5rem 0;}""",
            js=Path(__file__).with_name("audio.js").read_text())
        component(key="audio_runtime", data={"enabled": st.session_state.get("sound_enabled", False),
            "volume": st.session_state.get("sound_volume", 30), "event": st.session_state.get("audio_event")})
