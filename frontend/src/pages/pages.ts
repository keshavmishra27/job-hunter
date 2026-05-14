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

// ─── Dashboard ─────────────────────────────────────────────────────────────

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
        <button class="btn btn-primary" id="dash-fetch-btn">⚡ Fetch & Rank Jobs</button>
        <button class="btn btn-secondary" id="dash-drafts-btn">✉️ Review Drafts</button>
      </div>
    `;

    document.getElementById("dash-fetch-btn")?.addEventListener("click", () => {
      (document.querySelector('[data-page="jobs"]') as HTMLButtonElement)?.click();
    });
    document.getElementById("dash-drafts-btn")?.addEventListener("click", () => {
      (document.querySelector('[data-page="drafts"]') as HTMLButtonElement)?.click();
    });
  } catch (e: any) {
    el.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-title">Backend offline</div><div class="empty-sub">Start the FastAPI server first: <code>uvicorn backend.main:app --reload</code></div></div>`;
  }
}

// ─── Profile ────────────────────────────────────────────────────────────────

export async function renderProfile() {
  const el = document.getElementById("page-profile")!;
  el.innerHTML = `
    <div class="two-col">
      <div>
        <div class="section-header"><span class="section-title">Upload Resume</span></div>
        <div class="card">
          <div class="upload-zone" id="upload-zone">
            <div class="upload-icon">📄</div>
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
            <div class="empty-icon">👤</div>
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
      statusEl.innerHTML = `<button class="btn btn-primary btn-sm" id="refresh-profile-btn">🔄 Refresh Profile</button>`;
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
            Remote: ${profile.location_rule?.remote_allowed ? "✅ Allowed" : "❌ Not allowed"}<br/>
            Offline cities: ${(profile.location_rule?.offline_allowed || []).join(", ")}
          </div>
        </div>
        <div>
          <div class="card-title">Projects (${(profile.projects || []).length})</div>
          ${(profile.projects || []).slice(0, 5).map((p: string) => `<div style="font-size:13px;color:var(--text-secondary);padding:4px 0;border-bottom:1px solid var(--border-subtle)">• ${p}</div>`).join("")}
        </div>
      `;
    } catch {
      // no profile yet, keep placeholder
    }
  }

  loadProfile();
}

// ─── Jobs ────────────────────────────────────────────────────────────────────

export async function renderJobs() {
  const el = document.getElementById("page-jobs")!;
  const sources = ["internshala", "indeed", "linkedin"];
  let selected = new Set(["internshala"]);
  let showApplied = false;

  el.innerHTML = `
    <div class="section-header"><span class="section-title">Fetch & Rank Internships</span></div>
    <div class="card" style="margin-bottom:24px">
      <div class="card-title" style="margin-bottom:10px">Select Sources</div>
      <div class="source-chips">
        ${sources.map((s) => `<button class="source-chip ${selected.has(s) ? "selected" : ""}" data-source="${s}">${s.charAt(0).toUpperCase() + s.slice(1)}</button>`).join("")}
      </div>
      <button class="btn btn-primary" id="fetch-btn">⚡ Fetch & Rank</button>
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
      status.textContent = `✅ ${res.ranked} ranked`;
      loadJobs();
    } catch (e: any) {
      toast(e.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = "⚡ Fetch & Rank";
    }
  });

  async function loadJobs() {
    const list = document.getElementById("jobs-list")!;
    list.innerHTML = `<div style="display:flex;gap:8px;align-items:center"><div class="spinner"></div> Loading ranked jobs…</div>`;
    try {
      const jobs = await api.getRankedJobs(USER_ID, 30, showApplied);
      if (!jobs.length) {
        list.innerHTML = `<div class="empty-state"><div class="empty-icon">🔍</div><div class="empty-title">No jobs yet</div><div class="empty-sub">Click "Fetch & Rank" to pull internships.</div></div>`;
        return;
      }
      list.innerHTML = jobs.map((j: any) => `
        <div class="job-card" data-job-id="${j.job_id}">
          <div class="job-company-logo">${j.company[0].toUpperCase()}</div>
          <div class="job-info">
            <div class="job-title">${j.title} ${j.is_applied ? '<span class="badge badge-applied">✓ Applied</span>' : ''}</div>
            <div class="job-meta">
              <span>🏢 ${j.company}</span>
              <span>📍 ${j.location || "—"}</span>
              <span>${modeChip(j.mode || "offline")}</span>
              <span style="color:var(--text-muted);font-size:11px">${j.source}</span>
            </div>
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px">
            <div class="job-score">⭐ ${scorePct(j.score)}</div>
            <div style="display:flex;gap:6px">
              <button class="btn btn-secondary btn-sm view-job-btn" data-job-id="${j.job_id}" data-job='${JSON.stringify(j).replace(/'/g, "&#39;")}'>Details</button>
              <button class="btn btn-primary btn-sm gen-draft-btn" data-job-id="${j.job_id}">Draft ✉️</button>
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
            btn.textContent = "Draft ✉️";
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
      list.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-title">${e.message}</div></div>`;
    }
  }

  function showJobModal(j: any) {
    const breakdown = j.score_breakdown || {};
    openModal(`
      <div class="modal-title">${j.title}</div>
      <div style="margin-bottom:16px">
        <span style="font-size:15px;color:var(--text-secondary)">🏢 ${j.company}</span>
        <span style="margin-left:12px">${modeChip(j.mode || "offline")}</span>
      </div>
      <div class="card-title">Score Breakdown</div>
      <div class="score-breakdown" style="margin-bottom:20px">
        ${Object.entries(breakdown).map(([k, v]) => `
          <div class="score-row">
            <span class="score-label">${k.replace(/_/g, " ")}</span>
            <div class="progress-bar-outer" style="flex:1"><div class="progress-bar-inner" style="width:${Math.round((v as number) * 100)}%"></div></div>
            <span class="score-value">${Math.round((v as number) * 100)}%</span>
          </div>
        `).join("")}
      </div>
      ${j.apply_link ? `<a href="${j.apply_link}" target="_blank" class="btn btn-primary">Apply →</a>` : ""}
    `);
  }

  loadJobs();
}

// ─── Drafts ──────────────────────────────────────────────────────────────────

export async function renderDrafts() {
  const el = document.getElementById("page-drafts")!;
  el.innerHTML = `<div style="display:flex;align-items:center;gap:8px"><div class="spinner"></div> Loading drafts…</div>`;

  try {
    const drafts = await api.getDrafts(USER_ID) as any[];

    if (!drafts.length) {
      el.innerHTML = `<div class="empty-state"><div class="empty-icon">✉️</div><div class="empty-title">No drafts yet</div><div class="empty-sub">Generate drafts from the Ranked Jobs page.</div></div>`;
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
            <div style="font-size:13px;color:var(--text-secondary);margin-top:4px">🏢 ${d.company} · ${d.job_title}</div>
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
            <button class="btn btn-primary" id="confirm-send-btn" data-draft-id="${draftId}">Send Now 🚀</button>
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
    el.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-title">${e.message}</div></div>`;
  }
}

// ─── Sent Log ────────────────────────────────────────────────────────────────

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
                  📧 ${s.recipient} · ${s.sent_at ? new Date(s.sent_at).toLocaleString() : "—"}
                </div>
              </div>
              ${statusChip(s.status)}
            </div>
          </div>
        `).join("")}
      </div>
    `;
  } catch (e: any) {
    el.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-title">${e.message}</div></div>`;
  }
}


// \u2500\u2500\u2500 Applied Jobs \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

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
