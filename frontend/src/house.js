export const STORAGE_KEY = "homeops-house-v5";

export const SAMPLE = {
  address: "1428 Folsom St, San Francisco, CA",
  rooms: [
    { id: "r1", name: "Kitchen" },
    { id: "r2", name: "Bathroom" },
    { id: "r3", name: "Laundry" },
    { id: "r4", name: "Living" },
  ],
  drawings: [{ id: "d1", name: "bathroom-plan.png", roomId: "r2", dataUrl: "/floor-plan.jpg" }],
  assets: [
    {
      id: "a1",
      roomId: "r1",
      category: "fridge",
      brand: "Samsung",
      model: "RF28R7351SR",
      serial: "SM-884219",
      photoDataUrl: "/inventory/samsung-french-door-fridge.jpg",
      warrantyUntil: "Oct 2027",
      purchased: "Oct 2022",
      exaSummary: "28 cu. ft. Smart 4-Door Flex French Door with FlexZone & AutoFill Pitcher",
    },
    {
      id: "a2",
      roomId: "r1",
      category: "dishwasher",
      brand: "Bosch",
      model: "SHPM88Z75N",
      serial: "FD-881240",
      photoDataUrl: "/inventory/bosch-800-series-dishwasher.jpg",
      warrantyUntil: "Nov 2026",
      purchased: "Nov 2021",
      exaSummary: "800 Series, CrystalDry technology, 42 dBA, third rack layout",
    },
    {
      id: "a3",
      roomId: "r1",
      category: "cooktop",
      brand: "Wolf",
      model: "GR366",
      serial: "WF-994320",
      photoDataUrl: "/inventory/wolf-gas-cooktop-range.jpg",
      warrantyUntil: "Jan 2028",
      purchased: "Jan 2023",
      exaSummary: "36-inch Dual-Stacked Burner Gas Range with signature red knobs",
    },
    {
      id: "a4",
      roomId: "r2",
      category: "fixture",
      brand: "Kohler",
      model: "Purist K-14402",
      serial: "KH-001924",
      photoDataUrl: "/inventory/kohler-purist-faucet.jpg",
      warrantyUntil: "Lifetime finish",
      purchased: "Aug 2021",
      exaSummary: "Matte Black Widespread Bathroom Sink Faucet with lever handles",
    },
    {
      id: "a5",
      roomId: "r3",
      category: "washer",
      brand: "LG",
      model: "WM4000HBA",
      serial: "LG-773190",
      photoDataUrl: "/inventory/lg-front-load-washer.jpg",
      warrantyUntil: "Apr 2027",
      purchased: "Apr 2022",
      exaSummary: "4.5 cu. ft. Ultra Large Capacity Smart Front Load Washer with TurboWash 360",
    },
  ],
  details: [
    { id: "n0", label: "Homeowner", value: "Alex Rivera" },
    { id: "n1", label: "Bathroom paint", value: "Benjamin Moore OC-17 White Dove" },
    { id: "n2", label: "Kitchen backsplash", value: "Fireclay 3x6 white, stacked" },
  ],
  contractors: [
    {
      id: "c1",
      name: "City Plumbing",
      trade: "Plumber",
      phone: "(415) 555-0142",
      lastJob: "Supply line, 2019",
    },
  ],
  maintenance: [
    { id: "m1", title: "HVAC filter", due: "Sep 2026", room: "Utility" },
    { id: "m2", title: "Water heater flush", due: "Nov 2026", room: "Utility" },
  ],
  projects: [
    {
      id: "p1",
      title: "Bathroom refresh",
      kind: "reno",
      status: "quoting",
      budget: "$12,000",
      roomId: "r2",
      notes: "Keep the existing layout. Walls stay White Dove.",
      bids: [
        {
          name: "Bay Tile Co",
          phone: "(415) 555-0190",
          rating: "4.8 · 120 reviews",
          quote: "Tile + labor $9,400. Three weeks.",
        },
        {
          name: "Folsom Bath",
          phone: "(415) 555-0118",
          rating: "4.6 · 88 reviews",
          quote: "",
        },
      ],
    },
  ],
};

export function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export function todayLine() {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });
}

export function uid() {
  return Math.random().toString(36).slice(2, 8);
}

export function emptyHouse() {
  return {
    address: "",
    rooms: [],
    drawings: [],
    assets: [],
    details: [],
    contractors: [],
    maintenance: [],
    projects: [],
  };
}

export function loadHouse() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return structuredClone(SAMPLE);
    const parsed = JSON.parse(raw);
    return {
      ...emptyHouse(),
      address: parsed.address || "",
      rooms: parsed.rooms || [],
      drawings: parsed.drawings || [],
      assets: parsed.assets || [],
      details: parsed.details || [],
      contractors: parsed.contractors || [],
      maintenance: parsed.maintenance || [],
      projects: parsed.projects || [],
    };
  } catch {
    return structuredClone(SAMPLE);
  }
}

export function roomLabel(house, id) {
  return house.rooms.find((r) => r.id === id)?.name || "Room";
}

export function houseSnapshot(house) {
  const rooms = house.rooms.map((r) => r.name).join(", ") || "none";
  const drawings =
    house.drawings
      .map((d) => `${d.name}${d.roomId ? ` (${roomLabel(house, d.roomId)})` : ""}`)
      .join("; ") || "none";
  const assets =
    house.assets
      .map((a) => {
        const bits = [roomLabel(house, a.roomId), a.brand, a.model || a.category]
          .filter(Boolean)
          .join(" ");
        const extra = [a.serial && `serial ${a.serial}`, a.warrantyUntil && `warranty ${a.warrantyUntil}`]
          .filter(Boolean)
          .join(", ");
        const line = extra ? `${bits} (${extra})` : bits;
        return a.exaSummary ? `${line} — ${a.exaSummary}` : line;
      })
      .join("; ") || "none";
  const details =
    (house.details || []).map((d) => `${d.label}: ${d.value}`).join("; ") || "none";
  return `Address: ${house.address || "unset"}\nRooms: ${rooms}\nDrawings: ${drawings}\nInventory: ${assets}\nHome details: ${details}`;
}

export function drawingNotes(house, hint = "") {
  const wantBath = /bath/i.test(hint);
  const rows = house.drawings.filter((d) => {
    if (!wantBath) return true;
    const room = roomLabel(house, d.roomId);
    return /bath/i.test(room) || /bath/i.test(d.name);
  });
  const use = rows.length ? rows : house.drawings;
  if (!use.length) return "";
  return use
    .map((d) => {
      const room = d.roomId ? roomLabel(house, d.roomId) : "";
      return `${d.name}${room ? ` for ${room}` : ""}`;
    })
    .join("; ");
}

export function knownAssetLine(house, text) {
  const lower = text.toLowerCase();
  const hit = house.assets.find((a) => {
    const brand = (a.brand || "").toLowerCase();
    const model = (a.model || "").toLowerCase();
    const cat = (a.category || "").toLowerCase();
    return (
      (brand && lower.includes(brand)) ||
      (model && lower.includes(model)) ||
      (cat && lower.includes(cat)) ||
      (/fridge|refrigerat/i.test(text) && /fridge|refrigerat/i.test(`${a.category} ${a.model}`))
    );
  });
  if (!hit) return "";
  return [hit.brand, hit.model || hit.category, hit.warrantyUntil && `warranty ${hit.warrantyUntil}`, hit.exaSummary]
    .filter(Boolean)
    .join(" ");
}

export function pickRoom(house, hint) {
  const match = house.rooms.find((r) =>
    new RegExp(r.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i").test(hint)
  );
  if (match) return match;
  if (/kitchen|fridge|refrigerat|oven|stove|dishwasher/i.test(hint)) {
    return house.rooms.find((r) => /kitchen/i.test(r.name)) || house.rooms[0];
  }
  if (/bath|leak|plumb|toilet/i.test(hint)) {
    return house.rooms.find((r) => /bath/i.test(r.name)) || house.rooms[0];
  }
  return house.rooms[0] || { id: "r1", name: "Room" };
}

const MAX_DATA_URL = 180_000;

export function readDrawing(file) {
  if (file.type === "application/pdf" || /\.pdf$/i.test(file.name)) {
    return readAsDataUrl(file).then((dataUrl) =>
      dataUrl.length > MAX_DATA_URL ? "" : dataUrl
    );
  }
  return resizeImage(file, 800);
}

function readAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Could not read file"));
    reader.readAsDataURL(file);
  });
}

function resizeImage(file, max) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, max / Math.max(img.width, img.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(img.width * scale));
      canvas.height = Math.max(1, Math.round(img.height * scale));
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      let dataUrl = canvas.toDataURL("image/jpeg", 0.7);
      if (dataUrl.length > MAX_DATA_URL) {
        dataUrl = canvas.toDataURL("image/jpeg", 0.5);
      }
      resolve(dataUrl.length > MAX_DATA_URL ? "" : dataUrl);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Could not read image"));
    };
    img.src = url;
  });
}

export function captureFrame(video) {
  if (!video || !video.videoWidth) return undefined;
  const canvas = document.createElement("canvas");
  const w = 320;
  const scale = w / video.videoWidth;
  canvas.width = w;
  canvas.height = Math.max(1, Math.round(video.videoHeight * scale));
  canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.6);
}
