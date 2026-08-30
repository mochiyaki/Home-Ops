import { useEffect, useRef } from "react";
import { Icon } from "../components/Icons.jsx";

const STATE_LINE = {
  idle: "Tap to talk. Ops knows this house.",
  connecting: "Connecting…",
  listening: "Listening — just talk.",
  speaking: "Ops is talking",
};

export default function ChatScreen({
  live,
  videoRef,
  mediaError,
  chat,
  setChat,
  sendChat,
  startLive,
  stopLive,
  transcript,
  busy,
  onSuggest,
  voiceState,
  voiceMode,
  voiceError,
  onTalk,
  onHangup,
}) {
  const bottom = useRef(null);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript, busy, voiceState]);

  const talking = voiceState === "listening" || voiceState === "speaking" || voiceState === "connecting";
  const compact = transcript.length > 0 && !talking;
  const suggestions = [
    { t: "What’s the dishwasher model?", d: "From inventory" },
    { t: "Bathroom paint color?", d: "House memory" },
    { t: "The fridge isn’t cooling. Budget $300 after 6.", d: "Find a pro" },
    { t: "I want to renovate the bathroom.", d: "Start a project" },
  ];

  return (
    <div className="chat-shell">
      <header className="chat-head">
        <div>
          <strong>Ops</strong>
          <span>
            {voiceMode === "guava"
              ? "Live voice · quotes only"
              : talking
                ? "Talk mode · quotes only"
                : "Voice first · or type"}
          </span>
        </div>
        <div className="chat-head-actions">
          {compact ? (
            <button type="button" className="icon-btn" onClick={onTalk} aria-label="Talk to Ops">
              <Icon name="mic" />
            </button>
          ) : null}
          <button
            type="button"
            className={live ? "icon-btn on" : "icon-btn"}
            onClick={live ? stopLive : startLive}
            aria-label={live ? "Stop camera" : "Start camera"}
          >
            <Icon name="camera" />
          </button>
        </div>
      </header>

      {live ? (
        <div className="cam-strip">
          <video ref={videoRef} autoPlay playsInline muted />
        </div>
      ) : (
        <video ref={videoRef} className="sr-only" autoPlay playsInline muted />
      )}
      {mediaError ? <p className="err pad">{mediaError}</p> : null}
      {voiceError ? <p className="err pad">{voiceError}</p> : null}

      {!compact ? (
        <div className="talk-stage">
          <button
            type="button"
            className={`talk-btn ${talking ? "live" : ""} ${voiceState === "speaking" ? "speaking" : ""}`}
            onClick={talking ? onHangup : onTalk}
            aria-label={talking ? "Hang up" : "Talk to Ops"}
          >
            <Icon name={talking ? "phone" : "mic"} size={32} />
          </button>
          <p className="talk-line">{STATE_LINE[voiceState] || STATE_LINE.idle}</p>
          {voiceMode === "browser" && talking ? (
            <p className="talk-meta">Browser voice · shop calls go out by phone</p>
          ) : null}
          {voiceMode === "guava" && talking ? (
            <p className="talk-meta">Live web voice</p>
          ) : null}
        </div>
      ) : null}

      <div className="thread">
        {!transcript.length && !talking ? (
          <div className="welcome">
            <p className="welcome-lead">Tap the mic. Ask about a model, a leak, or a remodel. Typing is backup.</p>
            <div className="suggest-grid">
              {suggestions.map((s) => (
                <button key={s.t} type="button" disabled={busy} onClick={() => onSuggest(s.t)}>
                  <strong>{s.d}</strong>
                  {s.t}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <ol className="bubbles">
            {transcript.map((line, i) => (
              <li key={i} className={line.who === "You" ? "me" : "ops"}>
                {line.who !== "You" ? <span className="who">Ops</span> : null}
                {line.text}
              </li>
            ))}
            {busy && voiceState !== "speaking" ? (
              <li className="ops typing">
                <span className="who">Ops</span>
                <span className="typing-dots" role="status" aria-label="Ops is working">
                  <span />
                  <span />
                  <span />
                </span>
              </li>
            ) : null}
            <li ref={bottom} />
          </ol>
        )}
      </div>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          sendChat();
        }}
      >
        <input
          value={chat}
          onChange={(e) => setChat(e.target.value)}
          placeholder={talking ? "Or type while you talk" : "Or type a message"}
          disabled={busy && !talking}
        />
        <button type="submit" className="send" disabled={busy || !chat.trim()} aria-label="Send">
          <Icon name="send" size={18} />
        </button>
      </form>
    </div>
  );
}
