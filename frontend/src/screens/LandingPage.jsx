import { useState } from "react";
import { Icon } from "../components/Icons.jsx";

export default function LandingPage({ onLaunchApp }) {
  const [activeTab, setActiveTab] = useState("inventory");

  const steps = [
    {
      id: "inventory",
      title: "1. Visual Inventory",
      badge: "Vision + Exa",
      image: "/appliance-scan.jpg",
      imageAlt: "Scanning appliance data plate with smartphone",
      desc: "Point your camera at any appliance or data plate. HomeOps identifies the brand, model, and serial number on sight, pulling official user manuals and parts diagrams automatically.",
      tag: "Zero-form cataloging",
    },
    {
      id: "triage",
      title: "2. Zero-Form Triage",
      badge: "Multimodal Agent",
      image: "/floor-plan.jpg",
      imageAlt: "Renovation blueprints and floor plan sketches",
      desc: "Tell HomeOps about a leaking faucet or a full bathroom renovation. It checks existing house memory, budget, and stored floor plans to craft a concise trade brief.",
      tag: "Contextual awareness",
    },
    {
      id: "calls",
      title: "3. Outbound Calls & Quotes",
      badge: "Guava Voice AI",
      image: "/trade-pro.jpg",
      imageAlt: "Professional local service contractor with tools",
      desc: "HomeOps searches top-rated local pros and places outbound phone calls to ask for quotes and arrival windows. It books the first shop whose quote fits your budget and availability — and brings back the numbers either way.",
      tag: "Real phone outreach",
    },
  ];

  const features = [
    {
      icon: "camera",
      title: "Camera-Powered Inventory",
      desc: "Detects GE, Bosch, Kohler, and other major brands automatically. No manual form typing required.",
    },
    {
      icon: "search",
      title: "Exa Manual & Specs Lookup",
      desc: "Instantly retrieves PDF user manuals, wiring schematics, and common spare part numbers via Exa search.",
    },
    {
      icon: "phone",
      title: "Autonomous Outbound Calls",
      desc: "HomeOps dials local trade shops using Guava voice agents, introducing itself clearly as an AI assistant.",
    },
    {
      icon: "wrench",
      title: "Books Within Your Budget",
      desc: "You set the budget and the time window. HomeOps calls down the list and books the first shop that fits — never a dollar over.",
    },
    {
      icon: "spark",
      title: "Emergency Safety Guardrails",
      desc: "Instantly flags gas leaks, active fires, or uncontrollable floods and directs you to 911 rather than calling vendors.",
    },
    {
      icon: "folder",
      title: "House Memory & Floor Plans",
      desc: "Keeps paint codes, past contractor history, warranty dates, and renovation architectural drawings in one place.",
    },
  ];

  return (
    <div className="landing-root">
      {/* Navigation Header */}
      <header className="landing-nav">
        <div className="nav-container">
          <a href="/" className="landing-logo" onClick={(e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: "smooth" }); }}>
            <span className="logo-badge"><Icon name="home" size={18} /></span>
            <span className="logo-text">HomeOps</span>
          </a>

          <nav className="nav-links">
            <a href="#workflow">How It Works</a>
            <a href="#features">Capabilities</a>
            <a href="#guardrails">Safety Guardrails</a>
            <a href="#architecture">Architecture</a>
          </nav>

          <div className="nav-actions">
            <button type="button" className="landing-btn primary" onClick={onLaunchApp}>
              Launch App
              <Icon name="chevron" size={14} />
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="landing-hero">
        <div className="hero-badge">
          <span className="live-dot-pulse" />
          <span>Autonomous AI House Super</span>
        </div>

        <h1 className="hero-headline">
          Your home’s memory.<br />
          <span className="gradient-text">A real voice call away.</span>
        </h1>

        <p className="hero-subhead">
          Point your camera to log appliances, explain repairs naturally, and let HomeOps
          search top-rated local pros and place outbound phone calls to bring back quotes.
          <strong> Booked within your budget, no database lock-in.</strong>
        </p>

        <div className="hero-cta-group">
          <button type="button" className="landing-btn hero-primary" onClick={onLaunchApp}>
            <span>Open Interactive App</span>
            <Icon name="chevron" size={18} />
          </button>
          <a href="#workflow" className="landing-btn hero-secondary">
            <span>See How It Works</span>
          </a>
        </div>

        <div className="hero-metrics">
          <div className="metric-chip">
            <Icon name="camera" size={16} />
            <span>Visual Appliance Detection</span>
          </div>
          <div className="metric-chip">
            <Icon name="search" size={16} />
            <span>Exa Specs & Manuals</span>
          </div>
          <div className="metric-chip">
            <Icon name="phone" size={16} />
            <span>Real Guava Phone Calls</span>
          </div>
          <div className="metric-chip">
            <Icon name="spark" size={16} />
            <span>Books Within Budget</span>
          </div>
        </div>

        {/* Hero Visual Showcase */}
        <div className="hero-showcase-wrapper" onClick={onLaunchApp} role="button" tabIndex={0}>
          <img
            src="/hero-home.jpg"
            alt="Modern home kitchen with intelligent appliance management"
            className="hero-showcase-img"
          />
          <div className="hero-showcase-overlay">
            <div className="showcase-chip">
              <span className="live-dot-pulse" />
              <span>Living Room & Kitchen · 1428 Folsom St</span>
            </div>
            <div className="showcase-meta">
              <span className="meta-tag">3 Appliances Cataloged</span>
              <span className="meta-tag">Floor Plans Active</span>
              <span className="meta-tag cta">Launch Demo →</span>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Teaser Banner */}
      <section className="app-teaser-section">
        <div className="teaser-card">
          <div className="teaser-left">
            <p className="eyebrow-chip">Live Mobile Experience</p>
            <h2>Built with a native iPhone interface</h2>
            <p className="teaser-desc">
              Experience the full HomeOps superintendent inside an interactive iPhone frame —
              switch between your house inventory, repair triage, local bids, and voice-assisted chat.
            </p>
            <ul className="teaser-list">
              <li>
                <span className="check-icon">✓</span>
                <span>Real-time camera feed & visual snapshot capture</span>
              </li>
              <li>
                <span className="check-icon">✓</span>
                <span>Side-by-side contractor bid comparisons</span>
              </li>
              <li>
                <span className="check-icon">✓</span>
                <span>Turn-taking AI assistant with house memory</span>
              </li>
            </ul>
            <button type="button" className="landing-btn primary teaser-btn" onClick={onLaunchApp}>
              Launch iPhone App
              <Icon name="chevron" size={16} />
            </button>
          </div>

          <div className="teaser-right" onClick={onLaunchApp} role="button" tabIndex={0}>
            <div className="mini-phone-preview">
              <div className="mini-phone-header">
                <span className="mini-time">9:41</span>
                <span className="mini-island" />
                <span className="mini-battery" />
              </div>
              <div className="mini-screen-content">
                <div className="mini-home-card">
                  <span className="mini-greeting">Good afternoon</span>
                  <span className="mini-address">1428 Folsom St, San Francisco</span>
                  <div className="mini-action-row">
                    <div className="mini-action-pill sage">Add item</div>
                    <div className="mini-action-pill clay">Broke</div>
                    <div className="mini-action-pill ink">Projects</div>
                  </div>
                </div>
                <div className="mini-bid-card">
                  <div className="mini-bid-title">
                    <strong>City Plumbing</strong>
                    <span className="mini-rating">★ 4.8</span>
                  </div>
                  <p className="mini-quote">“Supply line repair $240. Can come tomorrow 6pm.”</p>
                </div>
              </div>
              <div className="mini-click-overlay">
                <span>Click to open full app →</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it Works / Workflow */}
      <section id="workflow" className="workflow-section">
        <div className="section-header">
          <p className="eyebrow">The 3-Step Flow</p>
          <h2>How HomeOps operates your house</h2>
          <p className="section-subtitle">
            From discovering appliances to receiving bids over the phone.
          </p>
        </div>

        <div className="workflow-grid">
          {steps.map((s, idx) => (
            <div
              key={s.id}
              className={`workflow-card ${activeTab === s.id ? "active" : ""}`}
              onClick={() => setActiveTab(s.id)}
            >
              <div className="workflow-img-box">
                <img src={s.image} alt={s.imageAlt} className="workflow-img" />
                <span className="workflow-number">{idx + 1}</span>
              </div>
              <span className="workflow-badge">{s.badge}</span>
              <h3>{s.title}</h3>
              <p>{s.desc}</p>
              <span className="workflow-tag">{s.tag}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Capabilities Grid */}
      <section id="features" className="features-section">
        <div className="section-header">
          <p className="eyebrow">Core Capabilities</p>
          <h2>Engineered for homeowner peace of mind</h2>
        </div>

        <div className="features-grid">
          {features.map((f, i) => (
            <div key={i} className="feature-card">
              <div className="feature-icon-box">
                <Icon name={f.icon} size={22} />
              </div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Architecture & Safety */}
      <section id="guardrails" className="guardrails-section">
        <div className="guardrails-card">
          <div className="guardrails-header">
            <span className="safety-badge">
              <Icon name="spark" size={18} />
              Safety & Ethics Standard
            </span>
            <h2>Budget-Capped Booking & Emergency Detection</h2>
          </div>
          <div className="guardrails-grid">
            <div className="guardrail-box">
              <h3>Budget Is a Hard Cap</h3>
              <p>
                HomeOps books only when the quote is at or under your stated budget and the time fits your availability.
                It never takes payment, never signs contracts, and over-budget quotes come back to you to decide.
              </p>
            </div>
            <div className="guardrail-box alert">
              <h3>Immediate Emergency Intervention</h3>
              <p>
                If danger keywords are detected (gas smell, open flame, uncontrolled flooding, carbon monoxide),
                HomeOps immediately halts vendor outreach and instructs the homeowner to contact 911 or local emergency services.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Architecture Tech Stack */}
      <section id="architecture" className="tech-section">
        <div className="section-header">
          <p className="eyebrow">Stack & Integrations</p>
          <h2>Powered by best-in-class APIs</h2>
        </div>
        <div className="tech-pills">
          <div className="tech-pill"><strong>FastAPI</strong> Python Backend</div>
          <div className="tech-pill"><strong>React 19 + Vite</strong> Frontend</div>
          <div className="tech-pill"><strong>Guava</strong> Voice AI · both legs</div>
          <div className="tech-pill"><strong>Exa</strong> Manuals & Specs Search</div>
          <div className="tech-pill"><strong>Apify</strong> Local Google Maps Pros</div>
          <div className="tech-pill"><strong>Client-First</strong> LocalStorage Memory</div>
        </div>
      </section>

      {/* Call to Action Banner */}
      <section className="cta-banner">
        <div className="cta-content">
          <h2>Ready to test your AI house super?</h2>
          <p>Launch the interactive iPhone demo and start exploring.</p>
          <button type="button" className="landing-btn hero-primary" onClick={onLaunchApp}>
            <span>Launch HomeOps App</span>
            <Icon name="chevron" size={18} />
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <strong>HomeOps</strong>
            <p>AI house super for one house. Visual inventory, triage, and real phone outreach.</p>
          </div>
          <div className="footer-links">
            <button type="button" className="footer-link-btn" onClick={onLaunchApp}>Interactive App</button>
            <a href="#workflow">Workflow</a>
            <a href="#features">Features</a>
            <a href="#guardrails">Guardrails</a>
          </div>
        </div>
        <div className="footer-bottom">
          <span>HomeOps · Local Demo Mode</span>
        </div>
      </footer>
    </div>
  );
}
