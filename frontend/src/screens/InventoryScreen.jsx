import { useMemo, useState } from "react";
import { Icon, ItemArt } from "../components/Icons.jsx";
import { roomLabel } from "../house.js";

export default function InventoryScreen({
  house,
  fileError,
  onPhoto,
  openItem,
  setScreen,
  onAddRoom,
}) {
  const [q, setQ] = useState("");
  const [room, setRoom] = useState("all");
  const [addingRoom, setAddingRoom] = useState(false);
  const [roomName, setRoomName] = useState("");
  const rooms = house.rooms || [];
  const items = useMemo(() => {
    return house.assets.filter((a) => {
      const hay = `${a.brand} ${a.model} ${a.category} ${a.serial}`.toLowerCase();
      if (q && !hay.includes(q.toLowerCase())) return false;
      if (room !== "all" && a.roomId !== room) return false;
      return true;
    });
  }, [house.assets, q, room]);

  return (
    <div className="page">
      <header className="title-block">
        <h1>Inventory</h1>
        <p className="quiet">Photos, serials, warranties, manuals</p>
      </header>

      <div className="search">
        <Icon name="search" size={18} />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search brand or serial"
        />
      </div>

      <div className="pills">
        <button type="button" className={room === "all" ? "on" : ""} onClick={() => setRoom("all")}>
          All
        </button>
        {rooms.map((r) => (
          <button
            key={r.id}
            type="button"
            className={room === r.id ? "on" : ""}
            onClick={() => setRoom(r.id)}
          >
            {r.name}
          </button>
        ))}
        {addingRoom ? (
          <input
            className="pill-input"
            autoFocus
            placeholder="Room name"
            value={roomName}
            onChange={(e) => setRoomName(e.target.value)}
            onBlur={() => {
              if (roomName.trim()) onAddRoom(roomName.trim());
              setRoomName("");
              setAddingRoom(false);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") e.currentTarget.blur();
            }}
          />
        ) : (
          <button type="button" className="ghost-pill" onClick={() => setAddingRoom(true)}>
            + Room
          </button>
        )}
      </div>

      <div className="toolbar">
        <label className="btn">
          <Icon name="camera" size={18} />
          Add photo
          <input type="file" accept="image/*" capture="environment" onChange={onPhoto} hidden />
        </label>
        <button type="button" className="btn ghost" onClick={() => setScreen("chat")}>
          Ask Ops to catalog
        </button>
      </div>
      {fileError ? <p className="err">{fileError}</p> : null}

      {items.length ? (
        <div className="photo-grid">
          {items.map((a) => (
            <button type="button" className="photo-card" key={a.id} onClick={() => openItem(a.id)}>
              <ItemArt asset={a} />
              <div className="photo-copy">
                <strong>
                  {a.brand || "Unnamed"} {a.model || a.category}
                </strong>
                <em>
                  {roomLabel(house, a.roomId)}
                  {a.warrantyUntil ? ` · ${a.warrantyUntil}` : ""}
                </em>
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="empty-card">
          <Icon name="box" size={28} />
          <p>Nothing in this filter yet. Snap a photo or ask Ops to catalog what’s in the room.</p>
        </div>
      )}
    </div>
  );
}
