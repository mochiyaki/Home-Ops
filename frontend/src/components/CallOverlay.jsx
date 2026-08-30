import { useEffect, useRef } from "react";

const STATE_LABEL = {
  dialing: "Dialing…",
  "in-call": "Live",
  done: "Call ended",
  failed: "No answer",
};

// The outbound shop call happens server-side on a real phone line. This sheet
// mirrors it into the app: state up top, transcript streaming turn by turn.
export function CallOverlay({ call, turns, onClose }) {
  const bottom = useRef(null);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [turns.length, call?.state]);

  if (!call) return null;
  const live = call.state === "dialing" || call.state === "in-call";
  const shop = String(call.shop_name || "the shop").replace(/^\[MOCK\]\s*/i, "");

  return (
    <section className="call-sheet" aria-label="Outbound call">
      <header className="call-sheet-head">
        <span
          className={`call-dot${live ? " live" : ""}${
            call.state === "done" && call.booked ? " booked" : ""
          }`}
        />
        <div className="call-sheet-title">
          <strong>Ops ↔ {shop}</strong>
          <span>
            {call.state === "done"
              ? call.booked
                ? `Booked${call.appointment ? ` · ${call.appointment}` : ""}`
                : "Done — not booked"
              : STATE_LABEL[call.state] || call.state}
          </span>
        </div>
        <button type="button" className="call-sheet-close" onClick={onClose} aria-label="Hide call">
          ×
        </button>
      </header>

      <ol className="call-turns">
        {turns.map((t) => (
          <li key={t.seq} className={t.speaker === "agent" ? "from-ops" : "from-shop"}>
            <span className="who">{t.speaker === "agent" ? "Ops" : shop}</span>
            {t.text}
          </li>
        ))}
        {live && !turns.length ? (
          <li className="from-ops ringing">
            <span className="who">Ops</span>
            Ringing…
          </li>
        ) : null}
        <li ref={bottom} aria-hidden="true" />
      </ol>

      {call.state === "done" && (call.summary || call.quote) ? (
        <footer className="call-sheet-result">
          <p>{String(call.summary || call.quote).replace(/^\[MOCK\]\s*/i, "")}</p>
        </footer>
      ) : null}
    </section>
  );
}
