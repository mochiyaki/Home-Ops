import { useEffect, useState } from "react";

export function IPhoneFrame({ children }) {
  const [time, setTime] = useState("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const hours = now.getHours();
      const minutes = String(now.getMinutes()).padStart(2, "0");
      const displayHours = hours % 12 || 12;
      setTime(`${displayHours}:${minutes}`);
    };
    updateTime();
    const interval = setInterval(updateTime, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="iphone-outer-wrapper">
      <div className="iphone-device">
        {/* Hardware side buttons */}
        <div className="iphone-button button-action" title="Action Button" />
        <div className="iphone-button button-volume-up" title="Volume Up" />
        <div className="iphone-button button-volume-down" title="Volume Down" />
        <div className="iphone-button button-power" title="Side Button" />

        {/* Outer Titanium Bezel */}
        <div className="iphone-bezel">
          {/* Subtle antenna bands */}
          <div className="antenna-band antenna-top-left" />
          <div className="antenna-band antenna-top-right" />
          <div className="antenna-band antenna-bottom-left" />
          <div className="antenna-band antenna-bottom-right" />

          {/* Screen Glass Area */}
          <div className="iphone-screen">
            {/* iOS Status Bar */}
            <header className="ios-status-bar" aria-hidden="true">
              <span className="ios-time">{time || "9:41"}</span>

              {/* Dynamic Island */}
              <div className="dynamic-island">
                <span className="island-camera" />
                <span className="island-sensor" />
              </div>

              {/* Status Icons: Cellular, Wifi, Battery */}
              <div className="ios-status-icons">
                <svg className="ios-icon" viewBox="0 0 17 12" width="17" height="12" fill="currentColor">
                  <rect x="0.5" y="8" width="2.5" height="4" rx="0.8" />
                  <rect x="4.5" y="5.5" width="2.5" height="6.5" rx="0.8" />
                  <rect x="8.5" y="3" width="2.5" height="9" rx="0.8" />
                  <rect x="12.5" y="0.5" width="2.5" height="11.5" rx="0.8" />
                </svg>
                <svg className="ios-icon" viewBox="0 0 16 12" width="16" height="12" fill="currentColor">
                  <path d="M8 9.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Zm-4.5-3.5a6.3 6.3 0 0 1 9 0 .8.8 0 0 1-1.1 1.1 4.7 4.7 0 0 0-6.8 0 .8.8 0 0 1-1.1-1.1Zm-3-3a10.5 10.5 0 0 1 15 0 .8.8 0 1 1-1.1 1.1 9 9 0 0 0-12.8 0 .8.8 0 0 1-1.1-1.1Z" />
                </svg>
                <div className="ios-battery">
                  <div className="ios-battery-body">
                    <div className="ios-battery-level" />
                  </div>
                  <div className="ios-battery-cap" />
                </div>
              </div>
            </header>

            {/* Inner App Container */}
            <div className="iphone-app-content">
              {children}
            </div>

            {/* iOS Home Indicator Bar */}
            <footer className="ios-home-indicator" aria-hidden="true">
              <div className="ios-home-bar" />
            </footer>
          </div>
        </div>
      </div>
    </div>
  );
}
