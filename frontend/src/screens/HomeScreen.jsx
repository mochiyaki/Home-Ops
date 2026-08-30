import { useState } from "react";
import { Icon, ItemArt, StatusChip } from "../components/Icons.jsx";
import { greeting, roomLabel, todayLine } from "../house.js";

export default function HomeScreen({
  house,
  setScreen,
  openItem,
  openJob,
  startIssue,
  startJob,
  onAddPhoto,
  onAddress,
  onAsk,
}) {
  const [editingAddress, setEditingAddress] = useState(false);
  const openJobs = (house.projects || []).filter((p) => p.status !== "done");
  const rooms = house.rooms?.length || 0;

  return (
    <div className="page home-page">
      <header className="hero">
        <p className="eyebrow">{todayLine()}</p>
        <h1>{greeting()}</h1>
        {editingAddress ? (
          <input
            className="address-edit"
            autoFocus
            defaultValue={house.address}
            onBlur={(e) => {
              onAddress(e.target.value.trim());
              setEditingAddress(false);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") e.currentTarget.blur();
            }}
          />
        ) : (
          <button type="button" className="address-btn" onClick={() => setEditingAddress(true)}>
            <Icon name="pin" size={16} />
            <span className="address-text">{house.address || "Add your address"}</span>
          </button>
        )}
        <p className="hero-meta">
          {rooms} rooms · {house.assets.length} items on file
        </p>
      </header>

      <div className="actions-3">
        <button type="button" className="tile" onClick={onAddPhoto}>
          <span className="tile-icon sage">
            <Icon name="camera" size={20} />
          </span>
          Add item
        </button>
        <button type="button" className="tile" onClick={startIssue}>
          <span className="tile-icon clay">
            <Icon name="wrench" size={20} />
          </span>
          Something broke
        </button>
        <button type="button" className="tile" onClick={startJob}>
          <span className="tile-icon ink">
            <Icon name="folder" size={20} />
          </span>
          New project
        </button>
      </div>

      {openJobs.length ? (
        <section>
          <div className="section-head">
            <h2>Open work</h2>
            <button type="button" className="link" onClick={() => setScreen("projects")}>
              Projects
            </button>
          </div>
          {openJobs.map((job) => (
            <button type="button" className="work-card" key={job.id} onClick={() => openJob(job.id)}>
              <div>
                <div className="work-top">
                  <strong>{job.title}</strong>
                  <StatusChip status={job.status} />
                </div>
                <span>
                  {job.kind === "reno" ? "Renovation" : "Repair"}
                  {job.roomId ? ` · ${roomLabel(house, job.roomId)}` : ""}
                  {` · ${job.budget || "No budget"}`}
                </span>
                <span className="work-bids">{job.bids?.length || 0} bids on file</span>
              </div>
              <Icon name="chevron" size={18} />
            </button>
          ))}
        </section>
      ) : null}

      {house.assets.length ? (
      <section>
        <div className="section-head">
          <h2>In the house</h2>
          <button type="button" className="link" onClick={() => setScreen("inventory")}>
            Inventory
          </button>
        </div>
        <div className="photo-grid home-grid">
          {house.assets.slice(0, 4).map((asset) => (
            <button type="button" className="photo-card" key={asset.id} onClick={() => openItem(asset.id)}>
              <ItemArt asset={asset} />
              <div className="photo-copy">
                <strong>
                  {asset.brand || "Item"} {asset.model || asset.category}
                </strong>
                <em>{roomLabel(house, asset.roomId)}</em>
              </div>
            </button>
          ))}
        </div>
      </section>
      ) : null}

      {(house.maintenance || []).length ? (
      <section>
        <h2>Up next</h2>
        <div className="group">
          {(house.maintenance || []).map((item) => (
            <button
              type="button"
              className="group-row tap"
              key={item.id}
              onClick={() => onAsk(`How do I handle ${item.title}? It's due ${item.due} in the ${item.room}.`)}
            >
              <div>
                <strong>{item.title}</strong>
                <span>{item.room}</span>
              </div>
              <em>{item.due}</em>
            </button>
          ))}
        </div>
      </section>
      ) : null}

      {(house.details || []).length || (house.contractors || []).length ? (
      <section>
        <h2>House memory</h2>
        <div className="group">
          {(house.details || []).map((detail) => (
            <button
              type="button"
              className="group-row tap"
              key={detail.id}
              onClick={() => onAsk(`What's the ${detail.label}?`)}
            >
              <strong>{detail.label}</strong>
              <span className="end">{detail.value}</span>
            </button>
          ))}
          {(house.contractors || []).map((pro) => (
            <a className="group-row tap" key={pro.id} href={`tel:${pro.phone}`}>
              <div>
                <strong>{pro.name}</strong>
                <span>{pro.trade}</span>
              </div>
              <em>{pro.phone}</em>
            </a>
          ))}
        </div>
      </section>
      ) : null}
    </div>
  );
}
