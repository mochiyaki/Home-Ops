import { useState } from "react";
import { Icon } from "../components/Icons.jsx";

export default function IssueScreen({ house, seed, onBack, onFind, onChat }) {
  const [problem, setProblem] = useState(seed || "");
  const [roomId, setRoomId] = useState(house.rooms[0]?.id || "");
  const [budget, setBudget] = useState("");
  const [when, setWhen] = useState("Evenings after 6");

  const payload = () => ({
    title: problem.trim().slice(0, 48) || "Something broke",
    notes: problem.trim(),
    roomId,
    budget: budget.trim(),
    when: when.trim(),
    kind: "repair",
  });

  return (
    <div className="page">
      <button type="button" className="back" onClick={onBack}>
        <Icon name="back" size={20} /> Home
      </button>
      <h1>Something broke</h1>
      <p className="quiet">Tell Ops what’s going on. We’ll call local shops and book the first quote that fits your budget.</p>

      <form
        className="fields"
        onSubmit={(e) => {
          e.preventDefault();
          if (!problem.trim()) return;
          onFind(payload());
        }}
      >
        <label>
          What’s going on?
          <textarea
            rows={4}
            value={problem}
            onChange={(e) => setProblem(e.target.value)}
            placeholder="The fridge isn’t cooling. Ice maker still runs."
            required
          />
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
          When can they come?
          <input value={when} onChange={(e) => setWhen(e.target.value)} />
        </label>
        <div className="stack-actions">
          <button type="submit" className="btn wide">
            Find a pro
          </button>
          <button
            type="button"
            className="btn ghost wide"
            onClick={() => {
              if (!problem.trim()) return;
              onChat(payload());
            }}
          >
            Ask Ops first
          </button>
        </div>
      </form>
    </div>
  );
}
