import { useEffect, useRef, useState } from "react";

// Destructive actions arm on first tap and only fire on a second tap
// within the window — no blocking dialog, still no accidental deletes.
export function ConfirmButton({ label, confirmLabel = "Tap again to confirm", onConfirm }) {
  const [armed, setArmed] = useState(false);
  const timer = useRef(null);

  useEffect(() => () => clearTimeout(timer.current), []);

  const handleClick = () => {
    if (armed) {
      clearTimeout(timer.current);
      setArmed(false);
      onConfirm();
      return;
    }
    setArmed(true);
    timer.current = setTimeout(() => setArmed(false), 2600);
  };

  return (
    <button
      type="button"
      className={armed ? "text-danger armed" : "text-danger"}
      onClick={handleClick}
    >
      {armed ? confirmLabel : label}
    </button>
  );
}
