import { useCallback, useEffect, useRef, useState } from "react";
import { STORAGE_KEY, loadHouse } from "./house.js";
import { getHouse, patchHouse } from "./api.js";

const HOUSE_KEYS = [
  "address", "rooms", "drawings", "details",
  "contractors", "maintenance", "projects",
];

/** Local-only house. Kept for offline use and as the fallback store. */
export function useLocalHouse() {
  const [house, setHouse] = useState(loadHouse);
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(house));
  }, [house]);
  return { house, setHouse };
}

/**
 * The server's house, which is the same record the Ops voice agent reads and
 * writes. Falls back to the local copy when the API is unreachable so the demo
 * still runs offline.
 */
export function useServerHouse() {
  const [house, setHouseState] = useState(loadHouse);
  const [synced, setSynced] = useState(false);
  const loaded = useRef(false);

  useEffect(() => {
    let cancelled = false;
    getHouse()
      .then((remote) => {
        if (cancelled) return;
        setHouseState((local) => ({ ...local, ...remote }));
        setSynced(true);
        loaded.current = true;
      })
      .catch(() => {
        if (!cancelled) setSynced(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Mirror to localStorage so a refresh is instant and an API outage is survivable.
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(house));
  }, [house]);

  const setHouse = useCallback((updater) => {
    setHouseState((prev) => {
      const next = typeof updater === "function" ? updater(prev) : updater;
      if (loaded.current) {
        const patch = {};
        HOUSE_KEYS.forEach((k) => {
          if (next[k] !== prev[k]) patch[k] = next[k];
        });
        // Assets have their own endpoints; the document fields patch together.
        if (Object.keys(patch).length) patchHouse(patch).catch(() => {});
      }
      return next;
    });
  }, []);

  return { house, setHouse, synced };
}
