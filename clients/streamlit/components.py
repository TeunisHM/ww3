"""Offline, keyboard-operable SVG interaction using Streamlit's component API.

API reference: https://docs.streamlit.io/develop/api-reference/custom-components/st.components.v2.component
Only our escaped map renderer supplies HTML. No external assets or services.
"""

import streamlit as st

def command_map(**kwargs):
    """Register once per rendered map, including fresh test/server runtimes."""
    renderer = st.components.v2.component(
        "ww3_command_map",
        html='<div id="map" role="region" aria-label="Strategic world map; scroll horizontally on narrow screens" tabindex="0"></div>',
        css="""
            #map {max-width:100%; overflow-x:auto; padding:2px 2px 10px; overscroll-behavior-x:contain;}
            #map:focus-visible {outline:2px solid #9ff1db; outline-offset:-2px;}
            svg {display:block; width:100%; min-width:880px; height:auto;}
            [data-front] {cursor:pointer; outline:none;}
            [data-front]:hover .target {fill:#233d49;}
            [data-front]:focus .target {stroke:#fff; stroke-width:4;}
            @media (prefers-reduced-motion: reduce) {* {transition:none;}}
        """,
        js="""
            export default function({data, parentElement, setTriggerValue}) {
                const map = parentElement.querySelector('#map');
                const focused = parentElement.activeElement?.getAttribute('data-front');
                const scrollLeft = map.scrollLeft;
                const previousSelection = map.dataset.selection;
                map.innerHTML = data.svg;
                map.querySelectorAll('[data-front]').forEach(button => {
                    const select = () => setTriggerValue('select', button.getAttribute('data-front'));
                    button.onclick = select;
                    button.onkeydown = event => {
                        if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault();
                            select();
                        }
                    };
                    if (focused === button.getAttribute('data-front')) button.focus();
                });
                const selected = map.querySelector('[data-front][aria-pressed="true"]');
                const selection = selected?.getAttribute('data-front');
                map.dataset.selection = selection || '';
                const centerSelection = () => {
                    const current = map.querySelector('[data-front][aria-pressed="true"]');
                    if (!current) return;
                    const card = current.querySelector('.target').getBoundingClientRect();
                    const viewport = map.getBoundingClientRect();
                    map.scrollLeft += card.left - viewport.left - (map.clientWidth - card.width) / 2;
                };
                if (selected && selection !== previousSelection) {
                    centerSelection();
                } else {
                    map.scrollLeft = scrollLeft;
                }
                if (!map.resizeObserver) {
                    map.viewportWidth = map.clientWidth;
                    map.resizeObserver = new ResizeObserver(() => {
                        if (!map.isConnected) {
                            map.resizeObserver.disconnect();
                            return;
                        }
                        const width = map.clientWidth;
                        if (width !== map.viewportWidth) {
                            map.viewportWidth = width;
                            centerSelection();
                        }
                    });
                    map.resizeObserver.observe(map);
                }
            }
        """,
    )
    return renderer(**kwargs)
