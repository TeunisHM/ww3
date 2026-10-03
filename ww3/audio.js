// Original short sine-tone cues; no recordings, network requests, or external assets.
// User-gesture activation follows https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Best_practices
export default function({data, parentElement}) {
    const state = window.__ww3Audio ??= {context: null, master: null, lastEvent: null};
    const button = parentElement.querySelector('#test-sound');
    const status = parentElement.querySelector('#audio-status');
    const Audio = window.AudioContext || window.webkitAudioContext;
    const enabled = data.enabled === true && data.volume > 0;
    const updateStatus = () => {
        status.textContent = !Audio ? 'Audio is unavailable in this browser.' : !enabled ? 'Sound is muted.' :
            state.context?.state === 'running' ? 'Sound ready.' : 'Use Test sound or interact with the game to enable audio.';
    };
    const unlock = async () => {
        if (!enabled || !Audio) return;
        try {
            if (!state.context || state.context.state === 'closed') {
                state.context = new Audio();
                state.master = state.context.createGain();
                state.master.connect(state.context.destination);
            }
            state.master.gain.setValueAtTime(Math.max(0, Math.min(1, data.volume / 100)) * .12, state.context.currentTime);
            if (state.context.state === 'suspended') await state.context.resume();
            updateStatus();
        } catch (_) {status.textContent = 'Audio could not start. The game remains playable with sound off.';}
    };
    const play = kind => {
        if (!enabled || state.context?.state !== 'running') return;
        const notes = {
            order: [440], commit: [440, 554], resolve: [330, 440, 660],
            warning: [220, 185], victory: [330, 440, 554, 660]
        }[kind] || [440];
        const now = state.context.currentTime;
        notes.forEach((frequency, i) => {
            const oscillator = state.context.createOscillator();
            const envelope = state.context.createGain();
            const start = now + i * .09;
            oscillator.type = 'sine';
            oscillator.frequency.value = frequency;
            envelope.gain.setValueAtTime(0, start);
            envelope.gain.linearRampToValueAtTime(.5, start + .012);
            envelope.gain.linearRampToValueAtTime(0, start + .13);
            oscillator.connect(envelope);
            envelope.connect(state.master);
            oscillator.onended = () => {oscillator.disconnect(); envelope.disconnect();};
            oscillator.start(start);
            oscillator.stop(start + .14);
        });
    };
    // One audio context per page survives component rerenders. Listeners are
    // removed on every cleanup; no handlers accumulate while planning.
    if (state.master) state.master.gain.setValueAtTime(enabled ? Math.min(1, data.volume / 100) * .12 : 0, state.context.currentTime);
    button.disabled = !enabled || !Audio;
    button.onclick = async () => {await unlock(); play('resolve');};
    document.addEventListener('pointerdown', unlock);
    document.addEventListener('keydown', unlock);
    const event = data.event;
    if (event && event.id !== state.lastEvent) {
        state.lastEvent = event.id; // Muted/suspended cues are dropped, never queued for later.
        play(event.kind);
    }
    updateStatus();
    return () => {
        document.removeEventListener('pointerdown', unlock);
        document.removeEventListener('keydown', unlock);
        button.onclick = null;
    };
}
