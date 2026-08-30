export function Icon({ name, size = 22 }) {
  const props = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.7,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": true,
  };
  const paths = {
    home: <path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z" />,
    box: (
      <>
        <path d="M3 8.5 12 4l9 4.5v11L12 20 3 19.5z" />
        <path d="M12 20V9.5M3 8.5l9 1 9-1" />
      </>
    ),
    folder: (
      <path d="M3 7.5A1.5 1.5 0 0 1 4.5 6h4L11 8.5h8.5A1.5 1.5 0 0 1 21 10v8.5a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5z" />
    ),
    chat: <path d="M5 18.5 3 21V7.5A2.5 2.5 0 0 1 5.5 5h13A2.5 2.5 0 0 1 21 7.5v9A2.5 2.5 0 0 1 18.5 19H8z" />,
    plus: <path d="M12 5v14M5 12h14" />,
    camera: (
      <>
        <path d="M4 8.5h3l1.5-2h7l1.5 2h3v11H4z" />
        <circle cx="12" cy="13.5" r="3.2" />
      </>
    ),
    search: (
      <>
        <circle cx="11" cy="11" r="6" />
        <path d="m20 20-3.5-3.5" />
      </>
    ),
    chevron: <path d="m9 6 6 6-6 6" />,
    back: <path d="M15 5 8 12l7 7" />,
    phone: (
      <path d="M7 3.5h3.5l1 4L9.5 9.5a12 12 0 0 0 5 5l2-2 4 1V19a1.5 1.5 0 0 1-1.5 1.5A16 16 0 0 1 3.5 7 1.5 1.5 0 0 1 5 5.5H7z" />
    ),
    spark: (
      <>
        <path d="M12 3v4M12 17v4M5 12H3M21 12h-2M6.2 6.2 4.8 4.8M19.2 19.2l-1.4-1.4M17.8 6.2l1.4-1.4M6.2 17.8 4.8 19.2" />
        <circle cx="12" cy="12" r="3" />
      </>
    ),
    wrench: (
      <path d="M14.5 6.5a4 4 0 0 0-5.6 5.6L4 16.9 7.1 20l5-5a4 4 0 0 0 5.6-5.6L15.5 11.5z" />
    ),
    pin: (
      <>
        <path d="M12 21s7-5.4 7-11a7 7 0 1 0-14 0c0 5.6 7 11 7 11z" />
        <circle cx="12" cy="10" r="2.2" />
      </>
    ),
    star: (
      <path d="m12 3.5 2.4 5 5.5.6-4.1 3.7 1.2 5.4L12 15.8 7 18.2l1.2-5.4L4.1 9.1l5.5-.6z" />
    ),
    send: <path d="M5 12h14M13 6l6 6-6 6" />,
    mic: (
      <>
        <rect x="9" y="3.5" width="6" height="11" rx="3" />
        <path d="M6.5 11.5a5.5 5.5 0 0 0 11 0M12 17v3.5" />
      </>
    ),
  };
  return <svg {...props}>{paths[name]}</svg>;
}

export function ItemArt({ asset }) {
  if (asset.photoDataUrl) {
    return <img src={asset.photoDataUrl} alt="" />;
  }
  const kind = asset.category || "appliance";
  return (
    <div className={`art art-${kind}`} aria-hidden>
      {kind === "fridge" ? (
        <svg viewBox="0 0 64 64" fill="none">
          <rect x="18" y="8" width="28" height="48" rx="4" stroke="currentColor" strokeWidth="2" />
          <path d="M18 28h28" stroke="currentColor" strokeWidth="2" />
          <path d="M40 16v6M40 34v10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      ) : kind === "dishwasher" ? (
        <svg viewBox="0 0 64 64" fill="none">
          <rect x="12" y="14" width="40" height="36" rx="4" stroke="currentColor" strokeWidth="2" />
          <circle cx="32" cy="32" r="10" stroke="currentColor" strokeWidth="2" />
          <circle cx="44" cy="22" r="2" fill="currentColor" />
        </svg>
      ) : kind === "fixture" ? (
        <svg viewBox="0 0 64 64" fill="none">
          <path d="M18 28h20a8 8 0 0 1 8 8v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          <path d="M26 28V18h8v10" stroke="currentColor" strokeWidth="2" />
          <path d="M42 44v6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      ) : kind === "cooktop" ? (
        <svg viewBox="0 0 64 64" fill="none">
          <rect x="12" y="16" width="40" height="32" rx="4" stroke="currentColor" strokeWidth="2" />
          <circle cx="24" cy="30" r="6" stroke="currentColor" strokeWidth="2" />
          <circle cx="40" cy="30" r="6" stroke="currentColor" strokeWidth="2" />
          <circle cx="24" cy="42" r="2" fill="currentColor" />
          <circle cx="32" cy="42" r="2" fill="currentColor" />
          <circle cx="40" cy="42" r="2" fill="currentColor" />
        </svg>
      ) : kind === "washer" ? (
        <svg viewBox="0 0 64 64" fill="none">
          <rect x="14" y="10" width="36" height="44" rx="4" stroke="currentColor" strokeWidth="2" />
          <circle cx="32" cy="34" r="11" stroke="currentColor" strokeWidth="2" />
          <circle cx="32" cy="34" r="6" stroke="currentColor" strokeWidth="1.5" />
          <circle cx="24" cy="18" r="2" fill="currentColor" />
          <rect x="30" y="16" width="12" height="4" rx="1" fill="currentColor" />
        </svg>
      ) : (
        <svg viewBox="0 0 64 64" fill="none">
          <rect x="14" y="18" width="36" height="28" rx="4" stroke="currentColor" strokeWidth="2" />
          <path d="M14 28h36" stroke="currentColor" strokeWidth="2" />
        </svg>
      )}
    </div>
  );
}

export function StatusChip({ status }) {
  const label = {
    intake: "Intake",
    quoting: "Quotes",
    booked: "Booked",
    planning: "Planning",
    done: "Done",
  }[status] || status;
  return <span className={`chip chip-${status || "intake"}`}>{label}</span>;
}
