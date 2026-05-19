import { api, USER_ID } from "../api";

export function toast(msg: string, type: "success" | "error" | "info" = "info") {
  const container = document.getElementById("toast-container")!;
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

export function openModal(html: string) {
  document.getElementById("modal-content")!.innerHTML = html;
  document.getElementById("modal-overlay")!.classList.remove("hidden");
}

export function closeModal() {
  document.getElementById("modal-overlay")!.classList.add("hidden");
}

function scorePct(s: number) { return `${Math.round(s * 100)}%`; }

function modeChip(mode: string) {
  const cls = mode === "remote" ? "badge-remote" : "badge-offline";
  return `<span class="badge ${cls}">${mode}</span>`;
}

function statusChip(status: string) {
  const map: Record<string, string> = {
    new: "badge-new",
    approved: "badge-approved",
    sent: "badge-sent",
    failed: "badge-failed",
  };
  return `<span class="badge ${map[status] || "badge-new"}">${status}</span>`;
}

// dashboard page

export async function renderDashboard() {
  const el = document.getElementById("page-dashboard")!;
  el.innerHTML = `<div style="display:flex;align-items:center;gap:12px;margin-bottom:24px"><div class="spinner"></div> Loading stats…</div>`;

  try {
    const stats = await api.getDashboardStats(USER_ID);
    el.innerHTML = `
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-number">${stats.total_jobs_fetched ?? 0}</div>
          <div class="stat-label">Jobs Fetched</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">${stats.matched_for_user ?? 0}</div>
          <div class="stat-label">Matched & Ranked</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">${stats.drafts_pending_review ?? 0}</div>
          <div class="stat-label">Drafts to Review</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">${stats.drafts_approved ?? 0}</div>
          <div class="stat-label">Approved Drafts</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">${stats.emails_sent ?? 0}</div>
          <div class="stat-label">Emails Sent</div>
        </div>
      </div>

      <div class="section-header">
        <span class="section-title">Quick Actions</span>
      </div>
      <div style="display:flex;gap:12px;flex-wrap:wrap">
        <button class="btn btn-primary" id="dash-fetch-btn"> Fetch & Rank Jobs</button>
        <button class="btn btn-secondary" id="dash-drafts-btn"> Review Drafts</button>
      </div>
    `;

    document.getElementById("dash-fetch-btn")?.addEventListener("click", () => {
      (document.querySelector('[data-page="jobs"]') as HTMLButtonElement)?.click();
    });
    document.getElementById("dash-drafts-btn")?.addEventListener("click", () => {
      (document.querySelector('[data-page="drafts"]') as HTMLButtonElement)?.click();
    });
  } catch (e: any) {
    el.innerHTML = `<div class="empty-state"><div class="empty-icon"></div><div class="empty-title">Backend offline</div><div class="empty-sub">Start the FastAPI server first: <code>uvicorn backend.main:app --reload</code></div></div>`;
  }
}

// Profile page 
export async function renderProfile() {
  const el = document.getElementById("page-profile")!;
  el.innerHTML = `
    <div class="two-col">
      <div>
        <div class="section-header"><span class="section-title">Upload Resume</span></div>
        <div class="card">
          <div class="upload-zone" id="upload-zone">
            <div class="upload-icon"></div>
            <div class="upload-text">Drop your PDF resume here</div>
            <div class="upload-sub">or click to browse</div>
            <input type="file" id="resume-file-input" accept=".pdf" style="display:none" />
          </div>
          <div style="margin-top:16px" id="upload-status"></div>
        </div>
      </div>
      <div>
        <div class="section-header"><span class="section-title">Current Profile</span></div>
        <div class="card" id="profile-card">
          <div class="empty-state" style="padding:32px">
            <div class="empty-icon"></div>
            <div class="empty-title">No profile yet</div>
            <div class="empty-sub">Upload and parse your resume to build your profile.</div>
          </div>
        </div>
      </div>
    </div>
  `;

  const zone = document.getElementById("upload-zone")!;
  const fileInput = document.getElementById("resume-file-input") as HTMLInputElement;
  const statusEl = document.getElementById("upload-status")!;

  zone.addEventListener("click", () => fileInput.click());
  zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("drag-over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    const files = e.dataTransfer?.files;
    if (files?.[0]) handleUpload(files[0]);
  });
  fileInput.addEventListener("change", () => {
    if (fileInput.files?.[0]) handleUpload(fileInput.files[0]);
  });

  async function handleUpload(file: File) {
    statusEl.innerHTML = `<div style="display:flex;align-items:center;gap:8px"><div class="spinner"></div> Uploading…</div>`;
    try {
      const uploadRes = await api.uploadResume(USER_ID, file);
      statusEl.innerHTML = `<div style="display:flex;align-items:center;gap:8px"><div class="spinner"></div> Parsing…</div>`;
      const parseRes = await api.parseResume(uploadRes.resume_id);
      toast("Resume parsed successfully!", "success");
      statusEl.innerHTML = `<button class="btn btn-primary btn-sm" id="refresh-profile-btn"> Refresh Profile</button>`;
      document.getElementById("refresh-profile-btn")?.addEventListener("click", loadProfile);
      loadProfile();
    } catch (e: any) {
      toast(e.message, "error");
      statusEl.innerHTML = `<span style="color:var(--danger);font-size:13px">${e.message}</span>`;
    }
  }

  async function loadProfile() {
    const card = document.getElementById("profile-card")!;
    try {
      const profile = await api.getProfile(USER_ID) as any;
      card.innerHTML = `
        <div class="form-group">
          <div class="card-title">Skills</div>
          <div class="tag-list">${(profile.skills || []).map((s: string) => `<span class="tag">${s}</span>`).join("")}</div>
        </div>
        <div class="form-group">
          <div class="card-title">Research Areas</div>
          <div class="tag-list">${(profile.research_areas || []).map((s: string) => `<span class="tag">${s}</span>`).join("")}</div>
        </div>
        <div class="form-group">
          <div class="card-title">Preferred Roles</div>
          <div class="tag-list">${(profile.preferred_roles || []).map((s: string) => `<span class="tag">${s}</span>`).join("")}</div>
        </div>
        <div class="form-group">
          <div class="card-title">Location Rules</div>
          <div style="font-size:13px;color:var(--text-secondary)">
            Remote: ${profile.location_rule?.remote_allowed ? "Allowed" : "Not allowed"}<br/>
            Offline cities: ${(profile.location_rule?.offline_allowed || []).join(", ")}
          </div>
        </div>
        <div>
          <div class="card-title">Projects (${(profile.projects || []).length})</div>
          ${(profile.projects || []).slice(0, 5).map((p: string) => `<div style="font-size:13px;color:var(--text-secondary);padding:4px 0;border-bottom:1px solid var(--border-subtle)">• ${p}</div>`).join("")}
        </div>
      `;
    } catch {
      
    }
  }

  loadProfile();
}

// Job list page
export async function renderJobs() {
  const el = document.getElementById("page-jobs")!;
  const sources = [
    { id: "internshala", label: "Internshala" },
    { id: "indeed", label: "Indeed" },
    { id: "naukri", label: "LinkedIn" },
  ];
  let selected = new Set(["internshala", "indeed", "naukri"]);
  let showApplied = false;

  el.innerHTML = `
    <div class="section-header"><span class="section-title">Fetch & Rank Internships</span></div>
    <div class="card" style="margin-bottom:24px">
      <div class="card-title" style="margin-bottom:10px">Select Sources</div>
      <div class="source-chips">
        ${sources.map((source) => `<button class="source-chip ${selected.has(source.id) ? "selected" : ""}" data-source="${source.id}">${source.label}</button>`).join("")}
      </div>
      <button class="btn btn-primary" id="fetch-btn"> Fetch & Rank</button>
      <span id="fetch-status" style="font-size:13px;color:var(--text-secondary);margin-left:12px"></span>
    </div>
    <div id="jobs-list" class="job-list"></div>
  `;

  el.querySelectorAll(".source-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const src = (chip as HTMLElement).dataset.source!;
      if (selected.has(src)) selected.delete(src);
      else selected.add(src);
      chip.classList.toggle("selected", selected.has(src));
      loadJobs();  // Reload list with new source filter
    });
  });

  document.getElementById("show-applied-toggle")?.addEventListener("change", (e) => {
    showApplied = (e.target as HTMLInputElement).checked;
    loadJobs();
  });

  document.getElementById("fetch-btn")?.addEventListener("click", async () => {
    const btn = document.getElementById("fetch-btn") as HTMLButtonElement;
    const status = document.getElementById("fetch-status")!;
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner"></div> Fetching…`;
    status.textContent = "";

    try {
      const res = await api.fetchJobs(USER_ID, [...selected]);
      toast(`Fetched ${res.fetched} jobs, ${res.new_unique} new, ${res.ranked} ranked`, "success");
      status.textContent = ` ${res.ranked} ranked`;
      loadJobs();
    } catch (e: any) {
      toast(e.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = " Fetch & Rank";
    }
  });

  async function loadJobs() {
    const list = document.getElementById("jobs-list")!;
    list.innerHTML = `<div style="display:flex;gap:8px;align-items:center"><div class="spinner"></div> Loading ranked jobs…</div>`;
    try {
      const jobs = await api.getRankedJobs(USER_ID, 30, showApplied, [...selected]);
      if (!jobs.length) {
        list.innerHTML = `<div class="empty-state"><div class="empty-icon"></div><div class="empty-title">No jobs yet</div><div class="empty-sub">Click "Fetch & Rank" to pull internships.</div></div>`;
        return;
      }
      list.innerHTML = jobs.map((j: any) => `
        <div class="job-card" data-job-id="${j.job_id}">
          <div class="job-company-logo">${j.company[0].toUpperCase()}</div>
          <div class="job-info">
            <div class="job-title">${j.title} ${j.is_applied ? '<span class="badge badge-applied">✓ Applied</span>' : ''}</div>
            <div class="job-meta">
              <span> ${j.company}</span>
              <span>${j.location || "—"}</span>
              <span>${modeChip(j.mode || "offline")}</span>
              <span style="color:var(--text-muted);font-size:11px">${j.source}</span>
            </div>
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px">
            <div class="job-score"> ${scorePct(j.score)}</div>
            <div style="display:flex;gap:6px">
              <button class="btn btn-secondary btn-sm view-job-btn" data-job-id="${j.job_id}" data-job='${JSON.stringify(j).replace(/'/g, "&#39;")}'>Details</button>
              <button class="btn btn-primary btn-sm gen-draft-btn" data-job-id="${j.job_id}">Draft </button>
              ${!j.is_applied ? `<button class="btn btn-success btn-sm mark-applied-btn" data-job-id="${j.job_id}">✓ Applied</button>` : ''}
            </div>
          </div>
        </div>
      `).join("");

      list.querySelectorAll(".view-job-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const j = JSON.parse((btn as HTMLElement).dataset.job!.replace(/&#39;/g, "'"));
          showJobModal(j);
        });
      });

      list.querySelectorAll(".gen-draft-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const jobId = (btn as HTMLElement).dataset.jobId!;
          btn.textContent = "…";
          (btn as HTMLButtonElement).disabled = true;
          try {
            await api.generateDraft(USER_ID, jobId);
            toast("Draft generated! Check Review Queue.", "success");
          } catch (e: any) {
            toast(e.message, "error");
          } finally {
            btn.textContent = "Draft ";
            (btn as HTMLButtonElement).disabled = false;
          }
        });
      });

      list.querySelectorAll(".mark-applied-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const jobId = (btn as HTMLElement).dataset.jobId!;
          btn.textContent = "…";
          (btn as HTMLButtonElement).disabled = true;
          try {
            await api.markApplied({ user_id: USER_ID, job_id: jobId, status: "applied" });
            toast("Marked as applied! Job removed from feed.", "success");
            loadJobs();
          } catch (e: any) {
            toast(e.message, "error");
            btn.textContent = "✓ Applied";
            (btn as HTMLButtonElement).disabled = false;
          }
        });
      });
    } catch (e: any) {
      list.innerHTML = `<div class="empty-state"><div class="empty-icon"></div><div class="empty-title">${e.message}</div></div>`;
    }
  }

  function showJobModal(j: any) {
    const breakdown = j.score_breakdown || {};
    const matchedSkills: string[] = j.matched_skills || [];
    const matchedProjects: string[] = j.matched_projects || [];

    const skillTags = matchedSkills.length
      ? `<div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:6px">
          ${matchedSkills.map((s: string) => `<span class="tag" style="background:rgba(99,102,241,0.18);color:#a5b4fc">${s}</span>`).join("")}
        </div>`
      : `<span style="font-size:12px;color:var(--text-muted)">No skills matched in job description</span>`;

    const projectTags = matchedProjects.length
      ? `<div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:6px">
          ${matchedProjects.map((p: string) => `<span class="tag" style="background:rgba(16,185,129,0.15);color:#6ee7b7;font-size:11px">${p}</span>`).join("")}
        </div>`
      : `<span style="font-size:12px;color:var(--text-muted)">No project keywords matched</span>`;

    openModal(`
      <div class="modal-title">${j.title}</div>
      <div style="margin-bottom:16px">
        <span style="font-size:15px;color:var(--text-secondary)"> ${j.company}</span>
        <span style="margin-left:12px">${modeChip(j.mode || "offline")}</span>
      </div>
      <div class="card-title">Score Breakdown</div>
      <div class="score-breakdown" style="margin-bottom:16px">
        ${Object.entries(breakdown).map(([k, v]) => `
          <div class="score-row">
            <span class="score-label">${k.replace(/_/g, " ")}</span>
            <div class="progress-bar-outer" style="flex:1"><div class="progress-bar-inner" style="width:${Math.round((v as number) * 100)}%"></div></div>
            <span class="score-value">${Math.round((v as number) * 100)}%</span>
          </div>
        `).join("")}
      </div>
      <div style="margin-bottom:12px">
        <div class="card-title" style="margin-bottom:4px">Matched Skills (${matchedSkills.length})</div>
        ${skillTags}
      </div>
      <div style="margin-bottom:20px">
        <div class="card-title" style="margin-bottom:4px">Matched Projects (${matchedProjects.length})</div>
        ${projectTags}
      </div>
      ${j.apply_link ? `<a href="${j.apply_link}" target="_blank" class="btn btn-primary">Apply →</a>` : ""}
    `);
  }

  loadJobs();
}

// Internship News Scraper page
export async function renderInternships() {
  const el = document.getElementById("page-internships")!;

  // Source registry: website + Telegram
  const WEB_SOURCES = [
    { id: "companycareers", label: "Company Careers", icon: "🏢", type: "website" },
    { id: "govtportal",     label: "Govt Portals",   icon: "🏛️", type: "website" },
  ];
  const TG_SOURCES = [
    { id: "telegram", label: "Public Channels", icon: "✈️", type: "telegram" },
  ];

  // Each tab has its own independent selection — no bleed-across
  let webSelected = new Set(["companycareers"]);
  let tgSelected  = new Set(["telegram"]);
  let activeTab: "all" | "eligible" | "saved" | "applied" = "all";
  let allNotices: any[] = [];
  let activeSrcTab: "website" | "telegram" = "website";

  // Returns only the sources for the currently visible tab
  function activeSources(): string[] {
    return activeSrcTab === "website" ? [...webSelected] : [...tgSelected];
  }

  // ── Pipeline stage indicator ────────────────────────────────────────────────
  const PIPELINE = ["Fetch", "Normalize", "Detect", "Extract Links", "Eligibility", "Dedup", "Score", "Alert"];

  function pipelineHTML(active = -1) {
    return `<div class="intern-pipeline">
      ${PIPELINE.map((s, i) => `
        <div class="pipe-step ${i < active ? "done" : i === active ? "running" : ""}">
          <div class="pipe-dot">${i < active ? "✓" : i === active ? "" : i + 1}</div>
          <div class="pipe-label">${s}</div>
          ${i < PIPELINE.length - 1 ? '<div class="pipe-line"></div>' : ""}
        </div>`).join("")}
    </div>`;
  }

  // ── Eligibility badge ───────────────────────────────────────────────────────
  function eligBadge(status: string) {
    const map: Record<string, string> = {
      eligible: "elig-yes", maybe: "elig-maybe", not_eligible: "elig-no", unknown: "elig-unknown",
    };
    const label: Record<string, string> = {
      eligible: "✓ Eligible", maybe: "~ Maybe", not_eligible: "✗ Not Eligible", unknown: "? Unknown",
    };
    return `<span class="elig-badge ${map[status] || "elig-unknown"}">${label[status] || status}</span>`;
  }

  // ── Deadline urgency chip ───────────────────────────────────────────────────
  function deadlineChip(deadline: string | null) {
    if (!deadline) return "";
    const d = new Date(deadline);
    const days = Math.ceil((d.getTime() - Date.now()) / 86400000);
    if (days < 0) return `<span class="deadline-chip expired">Expired</span>`;
    if (days <= 3) return `<span class="deadline-chip urgent">🔥 ${days}d left</span>`;
    if (days <= 7) return `<span class="deadline-chip soon">⚡ ${days}d left</span>`;
    return `<span class="deadline-chip ok">📅 ${days}d left</span>`;
  }

  // ── Score ring (small) ──────────────────────────────────────────────────────
  function scoreRing(score: number) {
    const pct = Math.round(score * 10);
    const col = pct >= 7 ? "#10b981" : pct >= 4 ? "#f59e0b" : "#6366f1";
    const r = 18, c = 20, circ = 2 * Math.PI * r;
    const dash = (score / 10) * circ;
    return `<svg viewBox="0 0 40 40" class="score-ring-svg">
      <circle cx="${c}" cy="${c}" r="${r}" fill="none" stroke="rgba(255,255,255,0.07)" stroke-width="3"/>
      <circle cx="${c}" cy="${c}" r="${r}" fill="none" stroke="${col}" stroke-width="3"
        stroke-dasharray="${dash} ${circ}" stroke-dashoffset="${circ / 4}" stroke-linecap="round"/>
      <text x="${c}" y="${c}" text-anchor="middle" dominant-baseline="central"
        fill="${col}" font-size="9" font-weight="700">${pct}/10</text>
    </svg>`;
  }

  // ── Render notices list ─────────────────────────────────────────────────────
  function renderList(notices: any[]) {
    const list = document.getElementById("intern-feed")!;
    if (!notices.length) {
      list.innerHTML = `<div class="empty-state"><div class="empty-icon">📭</div>
        <div class="empty-title">No notices yet</div>
        <div class="empty-sub">Select sources above and click Fetch to begin scraping.</div></div>`;
      return;
    }
    const filtered = notices.filter(n => {
      if (activeTab === "eligible") return n.eligibility_status === "eligible" || n.eligibility_status === "maybe";
      if (activeTab === "saved")    return n.status === "saved";
      if (activeTab === "applied")  return n.status === "applied";
      return true;
    });
    if (!filtered.length) {
      list.innerHTML = `<div class="empty-state"><div class="empty-icon">🔍</div>
        <div class="empty-title">Nothing in this tab</div></div>`;
      return;
    }
    list.innerHTML = filtered.map((n: any) => `
      <div class="intern-card" data-id="${n.notice_id}">
        <div class="intern-card-left">
          <div class="intern-logo">${(n.company || "?")[0].toUpperCase()}</div>
        </div>
        <div class="intern-card-body">
          <div class="intern-card-top">
            <span class="intern-title">${n.title || "Untitled"}</span>
            ${eligBadge(n.eligibility_status || "unknown")}
            ${deadlineChip(n.deadline || null)}
          </div>
          <div class="intern-meta">
            <span>🏢 ${n.company || "—"}</span>
            <span>📡 ${n.source || "—"}</span>
            ${n.location ? `<span>📍 ${n.location}</span>` : ""}
          </div>
        </div>
        <div class="intern-card-right">
          ${scoreRing(n.score || 0)}
          <div class="intern-actions">
            <button class="btn btn-secondary btn-sm view-notice-btn" data-id="${n.notice_id}">Details</button>
            ${n.apply_link ? `<a class="btn btn-success btn-sm" href="${n.apply_link}" target="_blank">Apply →</a>` : ""}
            <button class="btn btn-sm save-notice-btn ${n.status === "saved" ? "btn-success" : "btn-secondary"}"
              data-id="${n.notice_id}">${n.status === "saved" ? "✓ Saved" : "Save"}</button>
          </div>
        </div>
      </div>`).join("");

    // Wire buttons
    list.querySelectorAll(".view-notice-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = (btn as HTMLElement).dataset.id!;
        try {
          const n = await api.getNotice(id);
          const bd = n.score_breakdown || {};
          openModal(`
            <div class="modal-title">${n.title}</div>
            <div style="display:flex;gap:12px;align-items:center;margin-bottom:16px">
              <span style="color:var(--text-secondary)">${n.company} · ${n.source}</span>
              ${eligBadge(n.eligibility_status || "unknown")}
              ${deadlineChip(n.deadline || null)}
            </div>
            ${n.raw_text ? `<div class="intern-raw-text">${n.raw_text}</div>` : ""}
            ${n.eligibility_text ? `<div class="card-title" style="margin-top:16px">Eligibility Note</div>
              <div style="font-size:13px;color:var(--text-secondary);margin-bottom:12px">${n.eligibility_text}</div>` : ""}
            ${Object.keys(bd).length ? `<div class="card-title" style="margin-top:16px">Score Breakdown</div>
              <div class="score-breakdown">
              ${Object.entries(bd).map(([k, v]) => `
                <div class="score-row">
                  <span class="score-label">${k.replace(/_/g, " ")}</span>
                  <div class="progress-bar-outer" style="flex:1">
                    <div class="progress-bar-inner" style="width:${Math.round((v as number)*100)}%"></div>
                  </div>
                  <span class="score-value">${Math.round((v as number)*100)}%</span>
                </div>`).join("")}
              </div>` : ""}
            ${n.links?.length ? `<div class="card-title" style="margin-top:16px">Extracted Links</div>
              ${n.links.map((l: any) => `<div style="margin:4px 0">
                <a href="${l.url}" target="_blank" style="color:var(--accent-light);font-size:13px">${l.text || l.url}</a>
                <span class="intern-link-kind">${l.kind || ""}</span>
              </div>`).join("")}` : ""}
            ${n.portal_link ? `<a href="${n.portal_link}" target="_blank" class="btn btn-primary" style="margin-top:20px;display:inline-flex">Apply Now →</a>` : ""}
          `);
        } catch (e: any) { toast(e.message, "error"); }
      });
    });

    list.querySelectorAll(".save-notice-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = (btn as HTMLElement).dataset.id!;
        try {
          await api.markAppliedNotice({ user_id: USER_ID, notice_id: id, status: "saved" });
          toast("Notice saved!", "success");
          const n = allNotices.find(x => x.notice_id === id);
          if (n) n.status = "saved";
          renderList(allNotices);
        } catch (e: any) { toast(e.message, "error"); }
      });
    });
  }

  // ── Load notices from backend ───────────────────────────────────────────────
  async function loadNotices() {
    const feed = document.getElementById("intern-feed")!;
    feed.innerHTML = `<div style="display:flex;gap:8px;align-items:center"><div class="spinner"></div> Loading notices…</div>`;
    try {
      // Show all stored notices regardless of active tab — fetch is tab-scoped, view is global
      const allSources = [...WEB_SOURCES.map(s => s.id), ...TG_SOURCES.map(s => s.id)];
      const notices = await api.getRankedInternships(USER_ID, 60, allSources);
      allNotices = notices;
      updateTabCounts(notices);
      renderList(notices);
    } catch (e: any) {
      feed.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-title">${e.message}</div></div>`;
    }
  }

  function updateTabCounts(notices: any[]) {
    const counts = { all: notices.length, eligible: 0, saved: 0, applied: 0 };
    for (const n of notices) {
      if (n.eligibility_status === "eligible" || n.eligibility_status === "maybe") counts.eligible++;
      if (n.status === "saved") counts.saved++;
      if (n.status === "applied") counts.applied++;
    }
    (["all", "eligible", "saved", "applied"] as const).forEach(t => {
      const el = document.getElementById(`intern-tab-${t}`);
      if (el) el.textContent = `${t.charAt(0).toUpperCase() + t.slice(1)} (${counts[t]})`;
    });
  }

  // ── Initial render ──────────────────────────────────────────────────────────
  el.innerHTML = `
    <div class="section-header">
      <span class="section-title">📡 Internship News Scraper</span>
      <span style="font-size:12px;color:var(--text-muted)">Detect · Score · Track</span>
    </div>

    <!-- Source Registry -->
    <div class="card" style="margin-bottom:20px">
      <div class="intern-src-header">
        <div class="card-title" style="margin:0">Source Registry</div>
        <div class="intern-src-tabs">
          <button class="intern-src-tab active" id="srctab-website" data-srctab="website">🌐 Website</button>
          <button class="intern-src-tab" id="srctab-telegram" data-srctab="telegram">✈️ Telegram</button>
        </div>
      </div>
      <div id="src-website-chips" class="source-chips" style="margin-top:12px">
        ${WEB_SOURCES.map(s => `
          <button class="source-chip ${webSelected.has(s.id) ? "selected" : ""}" data-source="${s.id}" data-group="web">
            ${s.icon} ${s.label}
          </button>`).join("")}
      </div>
      <div id="src-telegram-chips" class="source-chips" style="margin-top:12px;display:none">
        ${TG_SOURCES.map(s => `
          <button class="source-chip ${tgSelected.has(s.id) ? "selected" : ""}" data-source="${s.id}" data-group="tg">
            ${s.icon} ${s.label}
            <span style="font-size:10px;color:var(--text-muted);margin-left:4px">5 channels</span>
          </button>`).join("")}
        <div style="margin-top:8px;font-size:12px;color:var(--text-muted)">
          Scrapes: @JobsAndInternshipsIndia · @internshipsalert · @internship_update · @HiringIndia · @TechJobsIndia
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:12px;margin-top:16px">
        <button class="btn btn-primary" id="intern-fetch-btn">⚡ Fetch &amp; Process</button>
        <span id="intern-fetch-status" style="font-size:13px;color:var(--text-secondary)"></span>
      </div>
    </div>

    <!-- Pipeline status (hidden until fetch) -->
    <div id="intern-pipeline-wrap" style="display:none;margin-bottom:20px">
      ${pipelineHTML(-1)}
    </div>

    <!-- Filter tabs -->
    <div class="intern-tabs">
      <button class="intern-tab active" id="intern-tab-all" data-tab="all">All (0)</button>
      <button class="intern-tab" id="intern-tab-eligible" data-tab="eligible">Eligible (0)</button>
      <button class="intern-tab" id="intern-tab-saved" data-tab="saved">Saved (0)</button>
      <button class="intern-tab" id="intern-tab-applied" data-tab="applied">Applied (0)</button>
    </div>

    <!-- Feed -->
    <div id="intern-feed" class="intern-feed"></div>
  `;

  // Source type tab switching (website ↔ telegram)
  el.querySelectorAll(".intern-src-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      const which = (tab as HTMLElement).dataset.srctab as "website" | "telegram";
      activeSrcTab = which;
      el.querySelectorAll(".intern-src-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      (document.getElementById("src-website-chips") as HTMLElement).style.display =
        which === "website" ? "flex" : "none";
      (document.getElementById("src-telegram-chips") as HTMLElement).style.display =
        which === "telegram" ? "flex" : "none";
    });
  });

  // Source chip toggle — updates the correct tab's set based on data-group
  el.querySelectorAll(".source-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const src   = (chip as HTMLElement).dataset.source!;
      const group = (chip as HTMLElement).dataset.group!;
      const set   = group === "web" ? webSelected : tgSelected;
      if (set.has(src)) set.delete(src);
      else set.add(src);
      chip.classList.toggle("selected", set.has(src));
    });
  });

  // Tab switching
  el.querySelectorAll(".intern-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      el.querySelectorAll(".intern-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      activeTab = (tab as HTMLElement).dataset.tab as any;
      renderList(allNotices);
    });
  });

  // Fetch button
  document.getElementById("intern-fetch-btn")?.addEventListener("click", async () => {
    const btn = document.getElementById("intern-fetch-btn") as HTMLButtonElement;
    const status = document.getElementById("intern-fetch-status")!;
    const pipeWrap = document.getElementById("intern-pipeline-wrap")!;
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner"></div> Processing…`;
    pipeWrap.style.display = "block";
    status.textContent = "";

    // Animate pipeline stages
    for (let i = 0; i < PIPELINE.length; i++) {
      pipeWrap.innerHTML = pipelineHTML(i);
      await new Promise(r => setTimeout(r, 320));
    }

    try {
      const res = await api.fetchInternships(USER_ID, activeSources());
      if (Array.isArray(res.warnings)) res.warnings.forEach((w: string) => toast(w, "error"));
      toast(`Fetched ${res.fetched} notices, saved ${res.saved}`, "success");
      status.textContent = `${res.saved} new notices`;
      pipeWrap.innerHTML = pipelineHTML(PIPELINE.length); // all done
      await loadNotices();
    } catch (e: any) {
      toast(e.message, "error");
      pipeWrap.style.display = "none";
    } finally {
      btn.disabled = false;
      btn.innerHTML = "⚡ Fetch &amp; Process";
    }
  });

  loadNotices();
}


// Drafts for the comapany/startup page
export async function renderDrafts() {
  const el = document.getElementById("page-drafts")!;
  el.innerHTML = `<div style="display:flex;align-items:center;gap:8px"><div class="spinner"></div> Loading drafts…</div>`;

  try {
    const drafts = await api.getDrafts(USER_ID) as any[];

    if (!drafts.length) {
      el.innerHTML = `<div class="empty-state"><div class="empty-icon"></div><div class="empty-title">No drafts yet</div><div class="empty-sub">Generate drafts from the Ranked Jobs page.</div></div>`;
      return;
    }

    el.innerHTML = `
      <div class="section-header"><span class="section-title">Review Queue (${drafts.length})</span></div>
      <div class="job-list" id="draft-list"></div>
    `;

    const list = document.getElementById("draft-list")!;
    list.innerHTML = drafts.map((d: any) => `
      <div class="draft-card" id="draft-${d.draft_id}">
        <div class="draft-header">
          <div>
            <div class="draft-subject">${d.subject || "(no subject)"}</div>
            <div style="font-size:13px;color:var(--text-secondary);margin-top:4px">${d.company} · ${d.job_title}</div>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            ${statusChip(d.status)}
            <div class="draft-actions">
              <button class="btn btn-secondary btn-sm view-draft-btn" data-draft-id="${d.draft_id}">View</button>
              ${d.status !== "approved" && d.status !== "sent" ? `<button class="btn btn-success btn-sm approve-btn" data-draft-id="${d.draft_id}">Approve</button>` : ""}
              ${d.status === "approved" ? `<button class="btn btn-primary btn-sm send-btn" data-draft-id="${d.draft_id}">Send</button>` : ""}
            </div>
          </div>
        </div>
      </div>
    `).join("");

    list.querySelectorAll(".view-draft-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const draftId = (btn as HTMLElement).dataset.draftId!;
        try {
          const d = await api.getDraft(draftId);
          openModal(`
            <div class="modal-title">Draft Preview</div>
            <div class="form-group">
              <div class="card-title">Subject</div>
              <input class="form-input" id="edit-subject" value="${(d.subject || "").replace(/"/g, "&quot;")}" />
            </div>
            <div class="form-group">
              <div class="card-title">Body</div>
              <textarea class="form-textarea" id="edit-body" style="min-height:200px">${d.body || ""}</textarea>
            </div>
            ${d.linkedin_message ? `<div class="form-group"><div class="card-title">LinkedIn Message</div><p style="font-size:13px;color:var(--text-secondary)">${d.linkedin_message}</p></div>` : ""}
            <div style="display:flex;gap:8px;margin-top:8px">
              <button class="btn btn-primary" id="save-draft-btn" data-draft-id="${draftId}">Save Changes</button>
              <button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button>
            </div>
          `);
          document.getElementById("save-draft-btn")?.addEventListener("click", async () => {
            const subject = (document.getElementById("edit-subject") as HTMLInputElement).value;
            const body = (document.getElementById("edit-body") as HTMLTextAreaElement).value;
            try {
              await api.updateDraft(draftId, { subject, body });
              toast("Draft saved", "success");
              closeModal();
            } catch (e: any) {
              toast(e.message, "error");
            }
          });
        } catch (e: any) {
          toast(e.message, "error");
        }
      });
    });

    list.querySelectorAll(".approve-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const draftId = (btn as HTMLElement).dataset.draftId!;
        try {
          await api.approveDraft(draftId);
          toast("Draft approved!", "success");
          renderDrafts();
        } catch (e: any) {
          toast(e.message, "error");
        }
      });
    });

    list.querySelectorAll(".send-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const draftId = (btn as HTMLElement).dataset.draftId!;
        openModal(`
          <div class="modal-title">Send Email</div>
          <div class="form-group">
            <label class="form-label">Recipient email address</label>
            <input class="form-input" id="recipient-email" type="email" placeholder="hr@company.com" />
          </div>
          <div style="display:flex;gap:8px">
            <button class="btn btn-primary" id="confirm-send-btn" data-draft-id="${draftId}">Send Now </button>
            <button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button>
          </div>
        `);
        document.getElementById("confirm-send-btn")?.addEventListener("click", async () => {
          const recipient = (document.getElementById("recipient-email") as HTMLInputElement).value;
          if (!recipient) { toast("Enter recipient email", "error"); return; }
          try {
            const res = await api.sendDraft(draftId, recipient);
            toast(`Email ${res.status}!`, res.status === "sent" ? "success" : "error");
            closeModal();
            renderDrafts();
          } catch (e: any) {
            toast(e.message, "error");
          }
        });
      });
    });
  } catch (e: any) {
    el.innerHTML = `<div class="empty-state"><div class="empty-icon"></div><div class="empty-title">${e.message}</div></div>`;
  }
}

// ─── Repo Intelligence Page ──────────────────────────────────────────────────

let _currentRole = "fullstack";

export async function renderRepos() {
  const el = document.getElementById("page-repos")!;

  el.innerHTML = `<div class="repo-page-wrapper">
    <div class="repo-connect-panel" id="repo-connect-panel">
      <div class="spinner"></div><span style="margin-left:10px">Checking GitHub connection…</span>
    </div>
    <div id="repo-main-content" style="display:none">
      <div class="repo-toolbar">
        <div class="repo-toolbar-left">
          <div class="repo-github-badge" id="repo-github-badge"></div>
          <div class="role-selector-wrap">
            <label class="role-selector-label">Target Role</label>
            <select class="role-select" id="role-select"></select>
          </div>
        </div>
        <div class="repo-toolbar-right">
          <button class="btn btn-secondary btn-sm" id="repo-sync-btn">⟳ Sync Repos</button>
          <button class="btn btn-primary" id="repo-analyze-btn">⚡ Analyze &amp; Rank</button>
        </div>
      </div>

      <div id="repo-status-bar" class="repo-status-bar" style="display:none"></div>

      <div id="top5-section" style="display:none">
        <div class="section-header" style="margin-bottom:20px">
          <span class="section-title">Top 5 Repositories</span>
          <span class="repo-role-pill" id="active-role-pill"></span>
        </div>
        <div class="repo-top5-grid" id="repo-top5-grid"></div>
      </div>

      <div id="all-repos-section" style="display:none">
        <div class="section-header" style="margin-top:40px;margin-bottom:16px">
          <span class="section-title" id="all-repos-count-title">All Repositories</span>
          <button class="btn btn-secondary btn-sm" id="toggle-all-repos">Show All</button>
        </div>
        <div class="job-list" id="all-repos-list" style="display:none"></div>
      </div>
    </div>
  </div>`;

  await checkConnectionAndRender(el);
}

async function checkConnectionAndRender(el: HTMLElement) {
  try {
    const status = await api.githubStatus();
    const panel = el.querySelector("#repo-connect-panel") as HTMLElement;
    const main  = el.querySelector("#repo-main-content") as HTMLElement;

    if (!status.connected) {
      panel.innerHTML = renderConnectUI();
      wireConnectUI(el);
      return;
    }

    panel.style.display = "none";
    main.style.display  = "block";

    const badge = el.querySelector("#repo-github-badge") as HTMLElement;
    badge.innerHTML = `<span class="github-connected-badge">
      <span class="github-dot"></span>
      <strong>${status.github_username}</strong>
      <span style="color:var(--text-muted);font-size:11px">connected</span>
    </span>`;

    await wireMainUI(el);
  } catch {
    const panel = el.querySelector("#repo-connect-panel") as HTMLElement;
    panel.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div>
      <div class="empty-title">Backend offline</div>
      <div class="empty-sub">Start uvicorn first.</div></div>`;
  }
}

function renderConnectUI(): string {
  return `
    <div class="github-connect-card">
      <div class="github-connect-icon">🔗</div>
      <div class="github-connect-title">Connect your GitHub account</div>
      <div class="github-connect-sub">
        Enter a GitHub Personal Access Token (PAT) with <code>repo</code> scope to let
        Job Hunter analyse your repositories.
      </div>
      <div style="margin:24px auto;max-width:480px">
        <input class="form-input" id="gh-token-input" type="password"
          placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" />
        <div style="display:flex;gap:10px;margin-top:12px;justify-content:center">
          <button class="btn btn-primary" id="gh-connect-btn">Connect GitHub</button>
          <a class="btn btn-secondary"
            href="https://github.com/settings/tokens/new?scopes=repo,read:user"
            target="_blank">Create Token ↗</a>
        </div>
        <div id="gh-connect-err" style="margin-top:12px;color:var(--danger);font-size:13px;text-align:center"></div>
      </div>
    </div>`;
}

function wireConnectUI(el: HTMLElement) {
  const btn = el.querySelector("#gh-connect-btn") as HTMLButtonElement;
  const inp = el.querySelector("#gh-token-input") as HTMLInputElement;
  const err = el.querySelector("#gh-connect-err") as HTMLElement;

  btn.addEventListener("click", async () => {
    const token = inp.value.trim();
    if (!token) { err.textContent = "Please enter a token."; return; }
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner"></div> Connecting…`;
    err.textContent = "";
    try {
      await api.githubConnect(token);
      toast("GitHub connected! Syncing repos…", "success");
      await renderRepos();
    } catch (e: any) {
      err.textContent = e.message;
      btn.disabled = false;
      btn.innerHTML = "Connect GitHub";
    }
  });
}

async function wireMainUI(el: HTMLElement) {
  const roleSelect = el.querySelector("#role-select") as HTMLSelectElement;
  try {
    const { roles } = await api.githubRoles();
    roleSelect.innerHTML = roles.map(r =>
      `<option value="${r.id}" ${r.id === _currentRole ? "selected" : ""}>${r.label}</option>`
    ).join("");
  } catch {
    roleSelect.innerHTML = `<option value="fullstack">Full-Stack</option>`;
  }

  roleSelect.addEventListener("change", async () => {
    _currentRole = roleSelect.value;
    await loadTop5(el);
  });

  el.querySelector("#repo-sync-btn")?.addEventListener("click", async () => {
    const btn = el.querySelector("#repo-sync-btn") as HTMLButtonElement;
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner"></div> Syncing…`;
    try {
      const res = await api.githubSync();
      toast(`Synced ${res.repos_synced} repos`, "success");
    } catch (e: any) {
      toast(e.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = "⟳ Sync Repos";
    }
  });

  el.querySelector("#repo-analyze-btn")?.addEventListener("click", async () => {
    const btn = el.querySelector("#repo-analyze-btn") as HTMLButtonElement;
    const bar = el.querySelector("#repo-status-bar") as HTMLElement;
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner"></div> Analyzing…`;
    bar.style.display = "flex";
    bar.innerHTML = `<div class="spinner"></div><span>Syncing repos from GitHub…</span>`;

    try {
      const syncRes = await api.githubSync();
      bar.innerHTML = `<div class="spinner"></div><span>Analysing ${syncRes.repos_synced} repos (fetching READMEs + file trees)…</span>`;

      const analyzeRes = await api.githubAnalyze();
      bar.innerHTML = `<div class="spinner"></div><span>Scoring &amp; ranking…</span>`;

      await loadTop5(el);
      bar.style.display = "none";
      toast(`Analysis complete — ${analyzeRes.analyzed} repos ranked for ${_currentRole}`, "success");
    } catch (e: any) {
      toast(e.message, "error");
      bar.style.display = "none";
    } finally {
      btn.disabled = false;
      btn.innerHTML = "⚡ Analyze &amp; Rank";
    }
  });

  await loadTop5(el);
}

async function loadTop5(el: HTMLElement) {
  const top5Section    = el.querySelector("#top5-section") as HTMLElement;
  const allSection     = el.querySelector("#all-repos-section") as HTMLElement;
  const grid           = el.querySelector("#repo-top5-grid") as HTMLElement;
  const allList        = el.querySelector("#all-repos-list") as HTMLElement;
  const rolePill       = el.querySelector("#active-role-pill") as HTMLElement;
  const allCountTitle  = el.querySelector("#all-repos-count-title") as HTMLElement;
  const toggleBtn      = el.querySelector("#toggle-all-repos") as HTMLButtonElement;

  grid.innerHTML = `<div class="repo-loading"><div class="spinner"></div><span>Loading ranked repos…</span></div>`;
  top5Section.style.display = "block";

  try {
    const data = await api.githubTop5(_currentRole);

    const roleLabel = (el.querySelector("#role-select") as HTMLSelectElement)?.selectedOptions?.[0]?.text ?? _currentRole;
    rolePill.textContent = roleLabel;

    if (!data.top5?.length) {
      grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
        <div class="empty-icon">📭</div>
        <div class="empty-title">No analysed repos yet</div>
        <div class="empty-sub">Click "⚡ Analyze &amp; Rank" to run the pipeline.</div>
      </div>`;
      return;
    }

    grid.innerHTML = data.top5.map((repo: any, idx: number) =>
      renderRepoCard(repo, idx + 1)
    ).join("");

    grid.querySelectorAll(".repo-card").forEach(card => {
      card.addEventListener("click", async () => {
        const repoId = (card as HTMLElement).dataset.repoId!;
        await openRepoExpansion(repoId, _currentRole);
      });
    });

    if (data.all_repos?.length > 5) {
      allSection.style.display = "block";
      allCountTitle.textContent = `All Repositories (${data.all_repos.length})`;

      allList.innerHTML = data.all_repos.slice(5).map((repo: any, i: number) =>
        renderRepoListRow(repo, i + 6)
      ).join("");

      allList.querySelectorAll(".repo-list-row").forEach(row => {
        row.addEventListener("click", async () => {
          const repoId = (row as HTMLElement).dataset.repoId!;
          await openRepoExpansion(repoId, _currentRole);
        });
      });

      let expanded = false;
      toggleBtn.addEventListener("click", () => {
        expanded = !expanded;
        allList.style.display = expanded ? "flex" : "none";
        toggleBtn.textContent = expanded ? "Hide" : "Show All";
      });
    }
  } catch (e: any) {
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
      <div class="empty-icon">⚠️</div>
      <div class="empty-title">${e.message}</div>
    </div>`;
  }
}

function renderScoreRing(score: number, label: string, color: string): string {
  const pct = Math.round(score * 10);
  const circumference = 2 * Math.PI * 20;
  const dash = (pct / 100) * circumference;
  return `
    <div class="score-ring-wrap">
      <svg class="score-ring" viewBox="0 0 48 48">
        <circle cx="24" cy="24" r="20" fill="none" stroke="rgba(255,255,255,0.07)" stroke-width="4"/>
        <circle cx="24" cy="24" r="20" fill="none" stroke="${color}" stroke-width="4"
          stroke-dasharray="${dash.toFixed(1)} ${circumference.toFixed(1)}"
          stroke-linecap="round" transform="rotate(-90 24 24)"/>
        <text x="24" y="28" text-anchor="middle" font-size="10" font-weight="700"
          fill="${color}">${score.toFixed(1)}</text>
      </svg>
      <div class="score-ring-label">${label}</div>
    </div>`;
}

function renderRepoCard(repo: any, rank: number): string {
  const langColor: Record<string, string> = {
    Python: "#3572A5", TypeScript: "#3178c6", JavaScript: "#f1e05a",
    Rust: "#dea584", Go: "#00ADD8", Java: "#b07219", "C++": "#f34b7d",
    CSS: "#563d7c", HTML: "#e34c26", Swift: "#ffac45", Kotlin: "#A97BFF",
    Ruby: "#701516", PHP: "#4F5D95", "C#": "#178600",
  };
  const lc = langColor[repo.language] || "var(--accent-light)";
  const rankColors = ["#FFD700","#C0C0C0","#CD7F32","var(--accent-light)","var(--accent-light)"];
  const rankColor  = rankColors[rank - 1] || "var(--accent-light)";
  const finalPct   = Math.round(repo.final_score * 10);

  const badges = [
    repo.has_readme     ? `<span class="repo-badge badge-readme">README</span>`     : "",
    repo.has_tests      ? `<span class="repo-badge badge-tests">Tests</span>`       : "",
    repo.has_ui         ? `<span class="repo-badge badge-ui">UI</span>`             : "",
    repo.has_deployment ? `<span class="repo-badge badge-deploy">Deployed</span>`   : "",
    repo.has_demo_link  ? `<span class="repo-badge badge-demo">Demo</span>`         : "",
  ].filter(Boolean).join("");

  return `
  <div class="repo-card" data-repo-id="${repo.repo_id}" title="Click to expand full analysis">
    <div class="repo-card-rank" style="color:${rankColor}">#${rank}</div>

    <div class="repo-card-header">
      <div class="repo-card-name">${repo.name}</div>
      <div class="repo-card-score-circle" style="--score-color:${rankColor}">
        <svg viewBox="0 0 48 48">
          <circle cx="24" cy="24" r="20" fill="none" stroke="rgba(255,255,255,0.07)" stroke-width="4"/>
          <circle cx="24" cy="24" r="20" fill="none" stroke="${rankColor}" stroke-width="4"
            stroke-dasharray="${((finalPct/100)*125.66).toFixed(1)} 125.66"
            stroke-linecap="round" transform="rotate(-90 24 24)"/>
          <text x="24" y="28" text-anchor="middle" font-size="9" font-weight="800" fill="${rankColor}">${repo.final_score.toFixed(1)}</text>
        </svg>
        <span class="repo-card-score-label">/ 10</span>
      </div>
    </div>

    <div class="repo-card-desc">${repo.description || "<em style='opacity:0.5'>No description</em>"}</div>

    <div class="repo-card-meta">
      ${repo.language ? `<span class="repo-lang-dot" style="background:${lc}"></span><span>${repo.language}</span>` : ""}
      ${repo.stars > 0 ? `<span>★ ${repo.stars}</span>` : ""}
      ${repo.forks > 0 ? `<span>⑂ ${repo.forks}</span>` : ""}
    </div>

    <div class="repo-badges-row">${badges}</div>

    <div class="repo-card-scores">
      ${renderScoreRing(repo.uniqueness_score,     "Unique",  "#a78bfa")}
      ${renderScoreRing(repo.code_quality_score,   "Code",    "#22d3ee")}
      ${renderScoreRing(repo.documentation_score,  "Docs",    "#10b981")}
      ${renderScoreRing(repo.uiux_score,            "UI/UX",   "#f59e0b")}
    </div>

    ${repo.selection_reason ? `<div class="repo-card-reason">${repo.selection_reason}</div>` : ""}

    <div class="repo-card-footer">
      <a class="repo-card-link" href="${repo.html_url}" target="_blank" onclick="event.stopPropagation()">View on GitHub ↗</a>
      <span class="repo-expand-hint">Click to expand →</span>
    </div>
  </div>`;
}

function renderRepoListRow(repo: any, rank: number): string {
  return `
  <div class="job-card repo-list-row" data-repo-id="${repo.repo_id}" style="cursor:pointer">
    <div class="job-company-logo" style="background:linear-gradient(135deg,#4f46e5,#7c3aed);font-size:14px">
      ${repo.name[0].toUpperCase()}
    </div>
    <div class="job-info">
      <div class="job-title">#${rank} ${repo.name}</div>
      <div class="job-meta">
        <span>${repo.language || "—"}</span>
        <span>★ ${repo.stars}</span>
        ${repo.description ? `<span style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${repo.description}</span>` : ""}
      </div>
    </div>
    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px">
      <div class="job-score">${repo.final_score.toFixed(1)} / 10</div>
      <div style="font-size:11px;color:var(--text-muted)">${repo.analyzed ? "analysed" : "not analysed"}</div>
    </div>
  </div>`;
}

async function openRepoExpansion(repoId: string, role: string) {
  openModal(`<div style="display:flex;align-items:center;gap:8px"><div class="spinner"></div> Loading full analysis…</div>`);
  try {
    const d = await api.githubRepoDetails(repoId, role);
    const a = d.analysis || {};
    const s = d.scores || {};
    const breakdown = s.breakdown || {};
    const signalReasons: Record<string, { why: string; fix: string }> = d.signal_reasons || {};
    const improvementTips: Array<{ icon: string; title: string; tip: string }> = d.improvement_tips || [];

    const metricRows = Object.entries(breakdown).map(([key, val]: any) => {
      const colors: Record<string, string> = {
        uniqueness:    "#a78bfa",
        code_quality:  "#22d3ee",
        documentation: "#10b981",
        uiux:          "#f59e0b",
      };
      const c = colors[key] || "var(--accent-light)";
      const pct = Math.round((val.score / 10) * 100);
      const labels: Record<string, string> = {
        uniqueness: "Uniqueness", code_quality: "Code Quality",
        documentation: "Documentation", uiux: "UI / UX",
      };
      return `
      <div class="expansion-metric">
        <div class="expansion-metric-header">
          <span class="expansion-metric-label" style="color:${c}">${labels[key] || key}</span>
          <span class="expansion-metric-score" style="color:${c}">${val.score.toFixed(1)} / 10</span>
          <span class="expansion-metric-weight">weight: ${Math.round(val.weight * 100)}%</span>
        </div>
        <div class="progress-bar-outer">
          <div class="progress-bar-inner" style="width:${pct}%;background:${c}"></div>
        </div>
      </div>`;
    }).join("");

    const signal = (flag: boolean, label: string, signalKey: string) => {
      const reason = signalReasons[signalKey];
      if (flag) {
        if (reason) {
          const safeWhy = reason.why.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
          const safeFix = reason.fix.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
          return `
            <div class="signal-chip signal-yes signal-expandable" data-why="${safeWhy}" data-fix="${safeFix}">
              <span>✓ ${label}</span>
              <span class="signal-why-icon" title="Why?">?</span>
            </div>`;
        }
        return `<div class="signal-chip signal-yes">✓ ${label}</div>`;
      }
      if (reason) {
        const safeWhy = reason.why.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
        const safeFix = reason.fix.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
        return `
          <div class="signal-chip signal-no signal-expandable" data-why="${safeWhy}" data-fix="${safeFix}">
            <span>✗ ${label}</span>
            <span class="signal-why-icon" title="Why?">?</span>
          </div>`;
      }
      return `<div class="signal-chip signal-no">✗ ${label}</div>`;
    };

    const finalPct = Math.round(s.final_score * 10);

    const tipsHtml = improvementTips.length ? `
    <div class="expansion-section-title" style="margin-top:28px">💡 Improvement Tips for ${role.replace(/_/g, " ")}</div>
    <div class="improvement-tips-grid">
      ${improvementTips.map(t => `
        <div class="improvement-tip-card">
          <div class="tip-icon">${t.icon}</div>
          <div class="tip-body">
            <div class="tip-title">${t.title}</div>
            <div class="tip-text">${t.tip}</div>
          </div>
        </div>
      `).join("")}
    </div>` : "";

    const html = `
    <div class="expansion-header">
      <div>
        <div class="expansion-repo-name">${d.name}</div>
        <div style="font-size:13px;color:var(--text-muted);margin-top:4px">${d.full_name}</div>
        <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
          ${d.language ? `<span class="badge badge-new">${d.language}</span>` : ""}
          ${(d.topics || []).map((t: string) => `<span class="badge badge-new">${t}</span>`).join("")}
        </div>
      </div>
      <div class="expansion-score-ring">
        <svg viewBox="0 0 80 80">
          <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(255,255,255,0.07)" stroke-width="6"/>
          <circle cx="40" cy="40" r="34" fill="none" stroke="var(--accent-light)" stroke-width="6"
            stroke-dasharray="${((finalPct/100)*213.63).toFixed(1)} 213.63"
            stroke-linecap="round" transform="rotate(-90 40 40)"/>
          <text x="40" y="45" text-anchor="middle" font-size="18" font-weight="800" fill="var(--accent-light)">${s.final_score?.toFixed(1)}</text>
        </svg>
        <div style="font-size:12px;color:var(--text-muted);margin-top:4px;text-align:center">Final Score</div>
      </div>
    </div>

    ${d.description ? `<div class="expansion-description">${d.description}</div>` : ""}

    <div class="expansion-section-title">Score Breakdown</div>
    <div class="expansion-metrics">${metricRows}</div>

    <div class="expansion-section-title">Repository Signals</div>
    <div style="font-size:12px;color:var(--text-muted);margin-bottom:10px">Click any <span style="color:#10b981;font-weight:600">✓</span> or <span style="color:#f87171;font-weight:600">✗</span> signal to see details.</div>
    <div class="signals-grid" id="signals-grid-${repoId}">
      ${signal(a.has_readme,             "README",            "has_readme")}
      ${signal(a.has_problem_statement,  "Problem Statement", "has_problem_statement")}
      ${signal(a.has_features_section,   "Features Section",  "has_features_section")}
      ${signal(a.has_setup_instructions, "Setup Guide",       "has_setup_instructions")}
      ${signal(a.has_architecture_info,  "Architecture Docs", "has_architecture_info")}
      ${signal(a.has_screenshots,        "Screenshots",       "has_screenshots")}
      ${signal(a.has_api_docs,           "API Docs",          "has_api_docs")}
      ${signal(a.has_future_scope,       "Roadmap / Future",  "has_future_scope")}
      ${signal(a.has_tests,              "Test Suite",        "has_tests")}
      ${signal(a.has_ci_cd,             "CI / CD Pipeline",  "has_ci_cd")}
      ${signal(a.has_docker,             "Docker",            "has_docker")}
      ${signal(a.has_ui,                 "Frontend / UI",     "has_ui")}
      ${signal(a.has_deployment,         "Deployment Config", "has_deployment")}
      ${signal(a.has_demo_link,          "Live Demo",         "has_demo_link")}
      ${signal(a.has_license,            "License",           "has_license")}
      ${signal(a.has_contributing,       "Contributing Guide","has_contributing")}
    </div>

    <div class="signal-reason-panel" id="signal-reason-panel" style="display:none">
      <div class="srp-header">
        <span class="srp-title" id="srp-title"></span>
        <button class="srp-close" id="srp-close">✕</button>
      </div>
      <div class="srp-section-label">Why this matters</div>
      <div class="srp-why" id="srp-why"></div>
      <div class="srp-section-label" style="margin-top:10px" id="srp-fix-label">How to fix it</div>
      <div class="srp-fix" id="srp-fix"></div>
    </div>

    <div class="expansion-stats-row">
      <div class="expansion-stat"><div class="expansion-stat-val">${a.file_count ?? "—"}</div><div class="expansion-stat-lbl">Files</div></div>
      <div class="expansion-stat"><div class="expansion-stat-val">${a.directory_count ?? "—"}</div><div class="expansion-stat-lbl">Dirs</div></div>
      <div class="expansion-stat"><div class="expansion-stat-val">${d.stars ?? 0}</div><div class="expansion-stat-lbl">Stars</div></div>
      <div class="expansion-stat"><div class="expansion-stat-val">${d.forks ?? 0}</div><div class="expansion-stat-lbl">Forks</div></div>
      <div class="expansion-stat"><div class="expansion-stat-val">${a.readme_length ? Math.round(a.readme_length/100)+"00" : "0"}</div><div class="expansion-stat-lbl">README chars</div></div>
    </div>

    ${(a.folder_structure || []).length ? `
    <div class="expansion-section-title">Top-Level Structure</div>
    <div class="repo-folder-tree">
      ${(a.folder_structure || []).map((f: string) => `<span class="folder-chip">📁 ${f}</span>`).join("")}
    </div>` : ""}

    ${tipsHtml}

    <div class="expansion-actions">
      <a class="btn btn-primary" href="${d.html_url}" target="_blank">View on GitHub ↗</a>
      ${d.analysis?.has_demo_link ? `<a class="btn btn-secondary" href="#" target="_blank">Live Demo ↗</a>` : ""}
    </div>`;

    document.getElementById("modal-content")!.innerHTML = html;
    const overlay = document.getElementById("modal-overlay")!;
    overlay.classList.remove("hidden");
    const modal = document.getElementById("modal")!;
    modal.style.maxWidth = "720px";
    modal.style.maxHeight = "90vh";

    // Wire up signal reason panel
    document.querySelectorAll(".signal-expandable").forEach(chip => {
      chip.addEventListener("click", () => {
        const el = chip as HTMLElement;
        const panel = document.getElementById("signal-reason-panel")!;
        const textContent = el.querySelector("span")?.textContent || "";
        const isPositive = textContent.includes("✓");
        const symbol = isPositive ? "✓" : "✗";
        const label = textContent.replace("✓ ", "").replace("✗ ", "");
        document.getElementById("srp-title")!.textContent = `${symbol} ${label}`;
        document.getElementById("srp-why")!.textContent = el.dataset.why || "";
        
        // Parse the fix text for positive/negative signals
        const fixText = el.dataset.fix || "";
        const fixLabel = document.getElementById("srp-fix-label")!;
        let displayFix = fixText;
        
        if (isPositive && fixText.includes("|")) {
          const parts = fixText.split("|");
          displayFix = parts[0].replace("✓", "").trim();
          fixLabel.textContent = "What you're doing right";
        } else if (!isPositive && fixText.includes("|")) {
          const parts = fixText.split("|");
          displayFix = parts[1].replace("✗", "").trim();
          fixLabel.textContent = "How to fix it";
        } else {
          fixLabel.textContent = isPositive ? "Best practice" : "How to fix it";
        }
        
        document.getElementById("srp-fix")!.textContent = displayFix;
        panel.style.display = "block";
        panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
    });

    document.getElementById("srp-close")?.addEventListener("click", () => {
      document.getElementById("signal-reason-panel")!.style.display = "none";
    });

  } catch (e: any) {
    toast(e.message, "error");
    closeModal();
  }
}

export async function renderSent() {
  const el = document.getElementById("page-sent")!;
  el.innerHTML = `<div style="display:flex;gap:8px;align-items:center"><div class="spinner"></div> Loading…</div>`;

  try {
    const log = await api.getSentLog() as any[];

    if (!log.length) {
      el.innerHTML = `<div class="empty-state"><div class="empty-icon">📬</div><div class="empty-title">Nothing sent yet</div><div class="empty-sub">Approve and send drafts from the Review Queue.</div></div>`;
      return;
    }

    el.innerHTML = `
      <div class="section-header"><span class="section-title">Sent Log (${log.length})</span></div>
      <div class="job-list">
        ${log.map((s: any) => `
          <div class="draft-card">
            <div class="draft-header">
              <div>
                <div class="draft-subject">${s.subject || "—"}</div>
                <div style="font-size:13px;color:var(--text-secondary);margin-top:4px">
                   ${s.recipient} · ${s.sent_at ? new Date(s.sent_at).toLocaleString() : "—"}
                </div>
              </div>
              ${statusChip(s.status)}
            </div>
          </div>
        `).join("")}
      </div>
    `;
  } catch (e: any) {
    el.innerHTML = `<div class="empty-state"><div class="empty-icon"></div><div class="empty-title">${e.message}</div></div>`;
  }
}


//  Applied Jobs page
const STATUS_COLORS: Record<string, string> = {
  saved: "badge-new", drafted: "badge-new", approved: "badge-approved",
  sent: "badge-sent", applied: "badge-applied", failed: "badge-failed",
};

export async function renderApplied() {
  const el = document.getElementById("page-applied")!;
  el.innerHTML = `<div style="display:flex;gap:8px;align-items:center"><div class="spinner"></div> Loading applications\u2026</div>`;
  try {
    const apps = await api.getApplications(USER_ID) as any[];
    if (!apps.length) {
      el.innerHTML = `<div class="empty-state"><div class="empty-icon">\ud83d\udccb</div><div class="empty-title">No applications yet</div><div class="empty-sub">Mark jobs as applied from the Ranked Jobs page.</div></div>`;
      return;
    }
    el.innerHTML = `
      <div class="section-header"><span class="section-title">Applied Jobs (${apps.length})</span></div>
      <div class="job-list" id="applied-list"></div>
    `;
    const list = document.getElementById("applied-list")!;
    list.innerHTML = apps.map((a: any) => `
      <div class="job-card applied-row" id="app-${a.application_id}">
        <div class="job-company-logo">${(a.company_name || "?")[0].toUpperCase()}</div>
        <div class="job-info">
          <div class="job-title">${a.role_title || "\u2014"}</div>
          <div class="job-meta">
            <span>\ud83c\udfe2 ${a.company_name || "\u2014"}</span>
            <span>\ud83d\udccc ${a.source || "\u2014"}</span>
            <span>\ud83d\udccd ${a.location || "\u2014"}</span>
            <span style="color:var(--text-muted);font-size:11px">${a.applied_at ? new Date(a.applied_at).toLocaleDateString() : "\u2014"}</span>
          </div>
          ${a.follow_up_date ? `<div style="font-size:12px;color:var(--accent);margin-top:4px">\u23f0 Follow-up: ${new Date(a.follow_up_date).toLocaleDateString()}</div>` : ""}
          ${a.draft_subject ? `<div style="font-size:12px;color:var(--text-muted);margin-top:2px">\u2709\ufe0f Draft: ${a.draft_subject}</div>` : ""}
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px">
          <span class="badge ${STATUS_COLORS[a.status] || "badge-new"}">${a.status}</span>
          <div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end">
            <button class="btn btn-secondary btn-sm set-followup-btn" data-app-id="${a.application_id}" data-follow-up="${a.follow_up_date || ""}">\u23f0 Follow-up</button>
            <button class="btn btn-danger btn-sm unmark-btn" data-app-id="${a.application_id}">\u2715 Unmark</button>
          </div>
        </div>
      </div>
    `).join("");

    list.querySelectorAll(".set-followup-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const appId = (btn as HTMLElement).dataset.appId!;
        const existing = (btn as HTMLElement).dataset.followUp || "";
        openModal(`
          <div class="modal-title">Set Follow-up Date</div>
          <div class="form-group">
            <label class="form-label">Date</label>
            <input class="form-input" type="date" id="followup-date" value="${existing ? existing.split("T")[0] : ""}" />
          </div>
          <div style="display:flex;gap:8px;margin-top:8px">
            <button class="btn btn-primary" id="save-followup-btn" data-app-id="${appId}">Save</button>
            <button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button>
          </div>
        `);
        document.getElementById("save-followup-btn")?.addEventListener("click", async () => {
          const date = (document.getElementById("followup-date") as HTMLInputElement).value;
          try {
            await api.updateApplication(appId, { follow_up_date: date });
            toast("Follow-up date saved!", "success");
            closeModal();
            renderApplied();
          } catch (e: any) { toast(e.message, "error"); }
        });
      });
    });

    list.querySelectorAll(".unmark-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const appId = (btn as HTMLElement).dataset.appId!;
        if (!confirm("Remove this application? The job will reappear in your feed.")) return;
        try {
          await api.unmarkApplied(appId);
          toast("Application removed. Job restored to feed.", "success");
          renderApplied();
        } catch (e: any) { toast(e.message, "error"); }
      });
    });
  } catch (e: any) {
    el.innerHTML = `<div class="empty-state"><div class="empty-icon">\u26a0\ufe0f</div><div class="empty-title">${e.message}</div></div>`;
  }
}
