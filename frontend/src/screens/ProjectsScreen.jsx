import { Icon, StatusChip } from "../components/Icons.jsx";
import { roomLabel } from "../house.js";

export default function ProjectsScreen({ house, openJob, startJob }) {
  const jobs = house.projects || [];
  return (
    <div className="page">
      <header className="title-block">
        <h1>Projects</h1>
        <p className="quiet">Repairs and renovations, bids side by side</p>
      </header>
      <button type="button" className="btn wide" onClick={startJob}>
        <Icon name="plus" size={18} /> New project
      </button>
      {jobs.length ? (
        <div className="list-stack">
          {jobs.map((job) => (
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
                <span className="work-bids">{job.bids?.length || 0} bids</span>
              </div>
              <Icon name="chevron" size={18} />
            </button>
          ))}
        </div>
      ) : (
        <div className="empty-card">
          <Icon name="folder" size={28} />
          <p>No projects yet. Start one here, or tell Ops what broke.</p>
        </div>
      )}
    </div>
  );
}
