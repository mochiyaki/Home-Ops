import { ConfirmButton } from "../components/ConfirmButton.jsx";
import { Icon, ItemArt } from "../components/Icons.jsx";
import { roomLabel } from "../house.js";

export default function ItemScreen({ house, asset, onBack, onChange, onDelete, askAbout, onBroke }) {
  if (!asset) {
    return (
      <div className="page">
        <button type="button" className="back" onClick={onBack}>
          <Icon name="back" size={20} /> Inventory
        </button>
        <div className="empty-card">
          <p>That item isn’t on file anymore.</p>
        </div>
      </div>
    );
  }
  const set = (key) => (e) => onChange({ ...asset, [key]: e.target.value });
  const title = `${asset.brand || "Item"} ${asset.model || ""}`.trim();

  return (
    <div className="page">
      <button type="button" className="back" onClick={onBack}>
        <Icon name="back" size={20} /> Inventory
      </button>
      <div className="hero-art">
        <ItemArt asset={asset} />
      </div>
      <h1 className="item-title">{title}</h1>
      <p className="quiet">
        {roomLabel(house, asset.roomId)}
        {asset.warrantyUntil ? ` · Warranty ${asset.warrantyUntil}` : ""}
      </p>

      <div className="group fields-ios">
        <label className="group-field">
          Brand
          <input value={asset.brand || ""} onChange={set("brand")} placeholder="GE" />
        </label>
        <label className="group-field">
          Model
          <input value={asset.model || ""} onChange={set("model")} placeholder="GTS18" />
        </label>
        <label className="group-field">
          Serial
          <input value={asset.serial || ""} onChange={set("serial")} placeholder="Optional" />
        </label>
        <label className="group-field">
          Category
          <select value={asset.category || "appliance"} onChange={set("category")}>
            <option value="appliance">Appliance</option>
            <option value="fridge">Fridge</option>
            <option value="dishwasher">Dishwasher</option>
            <option value="cooktop">Cooktop / Range</option>
            <option value="washer">Washer / Dryer</option>
            <option value="fixture">Fixture</option>
          </select>
        </label>
        <label className="group-field">
          Room
          <select value={asset.roomId || ""} onChange={set("roomId")}>
            {!asset.roomId ? <option value="">Unassigned</option> : null}
            {house.rooms.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </label>
        <label className="group-field">
          Warranty
          <input value={asset.warrantyUntil || ""} onChange={set("warrantyUntil")} placeholder="Mar 2027" />
        </label>
        <label className="group-field">
          Purchased
          <input value={asset.purchased || ""} onChange={set("purchased")} placeholder="Mar 2022" />
        </label>
      </div>

      {asset.exaSummary ? <p className="note">{asset.exaSummary}</p> : null}
      {asset.exaUrl ? (
        <a className="manual" href={asset.exaUrl} target="_blank" rel="noreferrer">
          Open manual
        </a>
      ) : null}

      <div className="stack-actions">
        <button type="button" className="btn wide" onClick={() => askAbout(asset)}>
          Ask Ops about this
        </button>
        <button type="button" className="btn ghost wide" onClick={() => onBroke(asset)}>
          This item broke
        </button>
        <ConfirmButton
          label="Remove from house"
          confirmLabel="Tap again to remove"
          onConfirm={() => onDelete(asset.id)}
        />
      </div>
    </div>
  );
}
