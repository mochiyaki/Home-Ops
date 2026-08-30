import { useState } from "react";
import { ConfirmButton } from "../components/ConfirmButton.jsx";
import { Icon, StatusChip } from "../components/Icons.jsx";
import { roomLabel } from "../house.js";

export default function JobScreen({
  house,
  job,
  call,
  busy,
  onBack,
  onChange,
  onCall,
  onFindPros,
  onDelete,
}) {
  if (!job) {
    return (
      <div className="page">
        <button type="button" className="back" onClick={onBack}>
          <Icon name="back" size={20} /> Projects
        </button>
        <h1>New project</h1>
        <p className="quiet">Ops calls for quotes and books the first shop that fits your budget.</p>
        <NewJobForm house={house} onCancel={onBack} onSave={(data) => onChange(data, true)} />
      </div>
    );
  }
  const j = job;
  return (
    <div className="page">
      <button type="button" className="back" onClick={onBack}>
        <Icon name="back" size={20} /> Projects
      </button>
      <div className="job-head">
        <p className="kicker">{j.kind === "reno" ? "Renovation" : "Repair"}</p>
        <StatusChip status={j.status} />
      </div>
      <h1>{j.title}</h1>
      <p className="quiet">{j.roomId ? roomLabel(house, j.roomId) : "Whole home"}</p>

      <div className="group fields-ios">
        <label className="group-field">
          Budget
          <input
            value={j.budget || ""}
            onChange={(e) => onChange({ ...j, budget: e.target.value })}
            placeholder="$300"
          />
        </label>
        <label className="group-field stacked">
          Notes
          <textarea
            rows={3}
            value={j.notes || ""}
            onChange={(e) => onChange({ ...j, notes: e.target.value })}
            placeholder="What’s going on, access notes, timing…"
          />
        </label>
      </div>

      <button type="button" className="btn wide" disabled={busy} onClick={() => onFindPros(j)}>
        {busy ? "Searching…" : "Find local pros"}
      </button>
      {call ? <p className="status-pill">{call}</p> : null}

      <div className="section-head">
        <h2>Compare bids</h2>
        <span className="quiet">{(j.bids || []).length} shops</span>
      </div>
      <div className="bids">
        {(j.bids || []).length ? (
          (j.bids || []).map((b) => (
            <article className="bid" key={b.phone}>
              <div>
                <strong>{String(b.name).replace(/^\[MOCK\]\s*/i, "")}</strong>
                {b.rating ? (
                  <span className="rating">
                    <Icon name="star" size={14} /> {b.rating}
                  </span>
                ) : null}
                <span>{b.phone}</span>
                {b.booked ? (
                  <span className="chip chip-booked">
                    Booked{b.appointment ? ` · ${b.appointment}` : ""}
                  </span>
                ) : null}
                {b.quote ? <em>{b.quote}</em> : <em className="wait">No quote yet — call for one</em>}
              </div>
              <button type="button" className="btn ghost" disabled={busy} onClick={() => onCall(b)}>
                <Icon name="phone" size={16} /> Call
              </button>
            </article>
          ))
        ) : (
          <div className="empty-card">
            <p>No shops yet. Find local pros, or describe the job in chat. Ops books the first quote that fits your budget.</p>
          </div>
        )}
      </div>

      <div className="stack-actions">
        {j.status !== "done" ? (
          <button
            type="button"
            className="btn ghost wide"
            onClick={() => onChange({ ...j, status: "done" })}
          >
            Mark complete
          </button>
        ) : null}
        <ConfirmButton
          label="Delete project"
          confirmLabel="Tap again to delete"
          onConfirm={() => onDelete(j.id)}
        />
      </div>
    </div>
  );
}

function NewJobForm({ house, onCancel, onSave }) {
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState("repair");
  const [roomId, setRoomId] = useState(house.rooms[0]?.id || "");
  const [budget, setBudget] = useState("");
  const [notes, setNotes] = useState("");
  return (
    <form
      className="fields"
      onSubmit={(e) => {
        e.preventDefault();
        if (!title.trim()) return;
        onSave({
          title: title.trim(),
          kind,
          roomId,
          budget,
          notes,
          status: "intake",
          bids: [],
        });
      }}
    >
      <label>
        Title
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Bathroom leak" required />
      </label>
      <label>
        Type
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="repair">Repair</option>
          <option value="reno">Renovation</option>
        </select>
      </label>
      <label>
        Room
        <select value={roomId} onChange={(e) => setRoomId(e.target.value)}>
          {house.rooms.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Budget
        <input value={budget} onChange={(e) => setBudget(e.target.value)} placeholder="$300" />
      </label>
      <label>
        Notes
        <textarea
          rows={3}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="What’s wrong, when someone can come…"
        />
      </label>
      <div className="toolbar">
        <button type="submit" className="btn">
          Create project
        </button>
        <button type="button" className="btn ghost" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
