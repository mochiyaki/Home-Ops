const SpeechRecognition =
  typeof window !== "undefined"
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null;

let recognition = null;
let speaking = false;
let closed = true;

// Guava's widget owns its own conversation - there is no JS channel to push
// text or context into a live session. Both of these are kept so callers do
// not have to branch; typed input falls through to the local turn engine.
export function injectOpsContext() {}

export function sendOpsText() {
  return false;
}

export function stopOpsVoice() {
  closed = true;
  speaking = false;
  try {
    recognition?.stop();
  } catch {
    /* ignore */
  }
  recognition = null;
  if (typeof window !== "undefined") window.speechSynthesis?.cancel();
}

const GUAVA_WIDGET_SRC =
  "https://app.goguava.ai/static/build/webrtc-widgets/guava-widget-audio-orb.js";
let guavaScript = null;

// The Guava widget is self-contained: it injects its own orb + audio UI and
// handles all WebRTC signaling. We only have to load it once with the code.
function startGuavaWidget(code) {
  if (guavaScript) {
    guavaScript.dataset.webrtcCode = code;
    return Promise.resolve();
  }
  return new Promise((resolve, reject) => {
    const el = document.createElement("script");
    el.src = GUAVA_WIDGET_SRC;
    el.setAttribute("data-webrtc-code", code);
    el.async = true;
    el.onload = () => {
      guavaScript = el;
      resolve();
    };
    el.onerror = () => reject(new Error("Guava widget failed to load"));
    document.body.appendChild(el);
  });
}

export async function startOpsVoice({
  webrtcCode,
  mode,
  onState,
  onTranscript,
  onError,
}) {
  stopOpsVoice();
  closed = false;
  onState?.("connecting");

  if (mode === "guava" && webrtcCode) {
    try {
      await startGuavaWidget(webrtcCode);
      onState?.("listening");
      return "guava";
    } catch (err) {
      onError?.(
        err.message || "Guava voice failed to load - using talk-to-type voice."
      );
      if (closed) return "off";
    }
  }

  await startBrowserVoice({ onState, onTranscript, onError });
  return "browser";
}

async function startBrowserVoice({ onState, onTranscript, onError }) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  stream.getTracks().forEach((t) => t.stop());
  if (!SpeechRecognition) {
    throw new Error("This browser has no speech recognition. Type instead, or configure Guava voice.");
  }
  const rec = new SpeechRecognition();
  rec.continuous = true;
  rec.interimResults = true;
  rec.lang = "en-US";
  rec.onstart = () => {
    if (!closed && !speaking) onState?.("listening");
  };
  rec.onerror = (event) => {
    if (event.error === "no-speech" || event.error === "aborted") return;
    onError?.(event.error || "Mic error");
  };
  rec.onend = () => {
    if (!closed && !speaking) {
      try {
        rec.start();
      } catch {
        /* already started */
      }
    }
  };
  rec.onresult = (event) => {
    if (speaking || closed) return;
    let finalText = "";
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      if (event.results[i].isFinal) finalText += event.results[i][0].transcript;
    }
    finalText = finalText.trim();
    if (finalText) onTranscript?.("You", finalText);
  };
  recognition = rec;
  rec.start();
  onState?.("listening");
}

export function speakOps(text, { onStart, onEnd } = {}) {
  if (!text || typeof window === "undefined" || !window.speechSynthesis) {
    onEnd?.();
    return;
  }
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 1.02;
  utter.pitch = 1;
  utter.onstart = () => {
    speaking = true;
    try {
      recognition?.stop();
    } catch {
      /* ignore */
    }
    onStart?.();
  };
  utter.onend = () => {
    speaking = false;
    onEnd?.();
    if (!closed) {
      try {
        recognition?.start();
      } catch {
        /* ignore */
      }
    }
  };
  window.speechSynthesis.speak(utter);
}
