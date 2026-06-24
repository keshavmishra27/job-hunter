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

// Home / Landing page
export async function renderHome() {
  const el = document.getElementById("page-home")!;
  el.innerHTML = `
    <div class="hero-photo-band">
      <div style="max-width:800px;margin:0 auto">
        <h1 class="display-xl" style="margin:0">JOB HUNTER</h1>
        <p class="body-md" style="margin:24px 0;color:var(--colors-muted)">AI-assisted internship discovery, ranking and outreach — get started in seconds.</p>
        <div class="flex items-center justify-center gap-md" style="margin-top:40px">
          <button class="button-primary" id="home-open-app">Open App</button>
          <button class="button-primary" id="home-upload-resume">Upload Resume</button>
          <button class="button-primary" id="home-check-backend">Check Backend</button>
        </div>
        <div style="margin-top:40px;color:var(--colors-muted)" class="caption-uppercase">
          STATUS: <span id="home-backend-status">Checking...</span>
        </div>
      </div>
    </div>

    <div style="margin-top:var(--spacing-section)">
      <div class="title-md" style="margin-bottom:var(--spacing-lg)">QUICK TOUR</div>
      <div class="flex gap-lg">
        <div class="newsroom-article-card" style="flex:1">
          <div class="title-sm">Fetch & Rank</div>
          <div class="body-sm mt-sm" style="color:var(--colors-muted)">Pull opportunities from multiple sources and rank them for you.</div>
        </div>
        <div class="newsroom-article-card" style="flex:1">
          <div class="title-sm">Drafts</div>
          <div class="body-sm mt-sm" style="color:var(--colors-muted)">Generate outreach drafts tailored to each role and review them.</div>
        </div>
        <div class="newsroom-article-card" style="flex:1">
          <div class="title-sm">Repo Intelligence</div>
          <div class="body-sm mt-sm" style="color:var(--colors-muted)">Analyze your GitHub to surface matching projects for a role.</div>
        </div>
      </div>
    </div>`;

  document.getElementById("home-open-app")?.addEventListener("click", () => {
    (document.querySelector('[data-page="dashboard"]') as HTMLButtonElement)?.click();
  });

  document.getElementById("home-upload-resume")?.addEventListener("click", () => {
    (document.querySelector('[data-page="profile"]') as HTMLButtonElement)?.click();
  });

  document.getElementById("home-check-backend")?.addEventListener("click", async () => {
    const statusEl = document.getElementById("home-backend-status")!;
    statusEl.innerHTML = `<div class="spinner"></div> Checking…`;
    try {
      const data = await api.health();
      statusEl.innerHTML = `<span style="color:#10b981">Backend: ${data.status} • v${(data as any).version || 'unknown'}</span>`;
    } catch (e: any) {
      statusEl.innerHTML = `<span style="color:var(--danger)">Backend offline</span>`;
    }
  });

  // Auto-check backend once
  document.getElementById("home-check-backend")?.dispatchEvent(new Event('click'));
}

// dashboard page

export async function renderDashboard() {
  const el = document.getElementById("page-dashboard")!;
  el.innerHTML = `<div style="display:flex;align-items:center;gap:12px;margin-bottom:24px"><div class="spinner"></div>Loading stats…</div>`;

  try {
    const [stats, analytics] = await Promise.all([
      api.getDashboardStats(USER_ID),
      api.getAnalytics(USER_ID).catch(() => null)
    ]);

    let analyticsHtml = "";
    if (analytics) {
      analyticsHtml = `
      <div class="mt-xl">
        <div class="title-md mb-md">OUTCOME ANALYTICS</div>
        <div class="flex gap-md mb-md flex-wrap">
          <div class="career-callout-card flex-1" style="text-align:center"><div class="display-lg">${analytics.applications_sent}</div><div class="caption-uppercase mt-sm" style="color:var(--colors-muted)">Applications Sent</div></div>
          <div class="career-callout-card flex-1" style="text-align:center"><div class="display-lg">${analytics.interviews}</div><div class="caption-uppercase mt-sm" style="color:var(--colors-muted)">Interviews</div></div>
          <div class="career-callout-card flex-1" style="text-align:center"><div class="display-lg">${analytics.offers}</div><div class="caption-uppercase mt-sm" style="color:var(--colors-muted)">Offers</div></div>
          <div class="career-callout-card flex-1" style="text-align:center"><div class="display-lg">${analytics.response_rate_percent}%</div><div class="caption-uppercase mt-sm" style="color:var(--colors-muted)">Response Rate</div></div>
        </div>
        <div class="flex gap-md mb-md">
          <div class="newsroom-article-card flex-1">
             <div class="title-sm">RESUME PERFORMANCE</div>
             <div class="body-sm mt-sm" style="color:var(--colors-muted)"><strong>Best:</strong> ${analytics.best_resume}</div>
             <div class="body-sm mt-sm" style="color:var(--colors-muted)"><strong>Worst:</strong> ${analytics.worst_resume}</div>
          </div>
          <div class="newsroom-article-card flex-1">
             <div class="title-sm">SOURCE SUCCESS RATES</div>
             <div class="mt-sm">
               ${Object.entries(analytics.source_success_rates || {}).map(([src, rate]) => `<div class="body-sm flex justify-between" style="color:var(--colors-muted)"><span>${src}</span><span>${rate}%</span></div>`).join("")}
             </div>
          </div>
        </div>
      </div>`;
    }

    el.innerHTML = `
      <div class="hero-photo-band" style="padding-top:40px;padding-bottom:40px;text-align:left">
        <h1 class="display-lg" style="margin:0">DASHBOARD</h1>
      </div>
      <div>
        <div class="title-md mb-md">STATISTICS</div>
        <div class="flex gap-md mb-lg flex-wrap">
          <div class="career-callout-card flex-1" style="text-align:center"><div class="display-lg">${stats.total_jobs_fetched ?? 0}</div><div class="caption-uppercase mt-sm" style="color:var(--colors-muted)">Jobs Fetched</div></div>
          <div class="career-callout-card flex-1" style="text-align:center"><div class="display-lg">${stats.matched_for_user ?? 0}</div><div class="caption-uppercase mt-sm" style="color:var(--colors-muted)">Matched</div></div>
          <div class="career-callout-card flex-1" style="text-align:center"><div class="display-lg">${stats.drafts_pending_review ?? 0}</div><div class="caption-uppercase mt-sm" style="color:var(--colors-muted)">Drafts to Review</div></div>
          <div class="career-callout-card flex-1" style="text-align:center"><div class="display-lg">${stats.drafts_approved ?? 0}</div><div class="caption-uppercase mt-sm" style="color:var(--colors-muted)">Approved</div></div>
          <div class="career-callout-card flex-1" style="text-align:center"><div class="display-lg">${stats.emails_sent ?? 0}</div><div class="caption-uppercase mt-sm" style="color:var(--colors-muted)">Emails Sent</div></div>
        </div>
      </div>
      ${analyticsHtml}
      <div class="mt-xl">
        <div class="title-md mb-md">QUICK ACTIONS</div>
        <div class="newsroom-article-card flex gap-md">
          <button class="button-primary" id="dash-drafts-btn">REVIEW DRAFTS</button>
          <button class="button-primary" id="dash-freelance-btn">BROWSE FREELANCING</button>
        </div>
      </div>`;
    document.getElementById("dash-drafts-btn")?.addEventListener("click", () => {
      (document.querySelector('[data-page="drafts"]') as HTMLButtonElement)?.click();
    });
    document.getElementById("dash-freelance-btn")?.addEventListener("click", () => {
      (document.querySelector('[data-page="freelancing"]') as HTMLButtonElement)?.click();
    });
  } catch (e: any) {
    el.innerHTML = `<div class="empty-state"><div class="empty-icon"></div><div class="empty-title">Backend offline</div><div class="empty-sub">Start the FastAPI server first: <code>uvicorn backend.main:app --reload</code></div></div>`;
  }
}

// Profile page
export async function renderProfile() {
  const el = document.getElementById("page-profile")!;
  el.innerHTML = `
    <div>
      <div class="title-md" style="margin-bottom:var(--spacing-md)">CURRENT PROFILE</div>
      <div class="model-photo-card" id="profile-card">
        <div style="text-align:center;padding:32px">
          <div class="title-sm">NO PROFILE YET</div>
          <div class="body-sm" style="color:var(--colors-muted);margin-top:8px">Upload and parse your resume to build your profile.</div>
        </div>
      </div>
    </div>
    
    <div class="flex gap-lg" style="margin-top:var(--spacing-xl)">
      <div style="flex:1">
        <div class="title-md" style="margin-bottom:var(--spacing-md)">UPLOAD RESUME</div>
        <div class="model-photo-card">
          <div class="upload-zone" id="upload-zone" style="border:1px dashed var(--colors-hairline-strong);text-align:center;padding:32px;cursor:pointer">
            <div class="title-sm">DROP YOUR PDF RESUME HERE</div>
            <div class="body-sm" style="margin-top:8px;color:var(--colors-muted)">or click to browse</div>
            <input type="file" id="resume-file-input" accept=".pdf" style="display:none" />
          </div>
          <div style="margin-top:16px" id="upload-status"></div>
        </div>
      </div>
      
      <div style="flex:1">
        <div class="title-md" style="margin-bottom:var(--spacing-md)">PROFILE SETTINGS</div>
        <div class="model-photo-card" id="settings-card" style="padding:24px">
          <div style="margin-bottom:16px">
            <label class="title-sm" for="grad-year-input">GRADUATION YEAR</label>
            <div class="body-sm" style="color:var(--colors-muted);margin:4px 0">e.g. 2028 — used to detect internship batch eligibility</div>
            <input class="text-input" id="grad-year-input" type="number" min="2024" max="2032" placeholder="2028" style="width:160px" />
          </div>
          
          <div style="margin-bottom:24px">
            <label class="title-sm" for="tg-chat-id-input">TELEGRAM CHAT ID</label>
            <div class="body-sm" style="color:var(--colors-muted);margin:4px 0">Find via @BotFather.</div>
            <input class="text-input" id="tg-chat-id-input" type="text" placeholder="123456789" style="width:100%" />
          </div>
          
          <div style="display:flex;gap:12px;flex-wrap:wrap">
            <button class="button-primary" id="save-settings-btn">SAVE SETTINGS</button>
            <button class="button-primary" id="send-telegram-btn">TEST TELEGRAM</button>
          </div>
          <div id="settings-status" style="margin-top:10px;font-size:11px"></div>
        </div>
      </div>
    </div>`;

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
    statusEl.innerHTML = `<div style="display:flex;align-items:center;gap:8px"><div class="spinner"></div>Uploading…</div>`;
    try {
      const uploadRes = await api.uploadResume(USER_ID, file);
      statusEl.innerHTML = `<div style="display:flex;align-items:center;gap:8px"><div class="spinner"></div>Parsing…</div>`;
      await api.parseResume(uploadRes.resume_id);
      toast("Resume parsed successfully!", "success");
      statusEl.innerHTML = `<button class="btn btn-primary btn-sm" id="refresh-profile-btn">Refresh Profile</button>`;
      document.getElementById("refresh-profile-btn")?.addEventListener("click", loadProfile);
      loadProfile();
    } catch (e: any) {
      toast(e.message, "error");
      statusEl.innerHTML = `<span style="color:var(--danger);font-size:13px">${e.message}</span>`;
    }
  }

  async function loadProfile() {
    const card = document.getElementById("profile-card")!;
    const gradInput = document.getElementById("grad-year-input") as HTMLInputElement;
    const tgInput = document.getElementById("tg-chat-id-input") as HTMLInputElement;
    try {
      const profile = await api.getProfile(USER_ID) as any;

      // Populate settings inputs
      if (profile.graduation_year) gradInput.value = String(profile.graduation_year);
      if (profile.telegram_chat_id) tgInput.value = profile.telegram_chat_id;

      const gradYearDisplay = profile.graduation_year
        ? `<span style="color:var(--colors-ink);font-weight:600">${profile.graduation_year}</span>`
        : `<span style="color:var(--colors-muted);font-style:italic">Not set</span>`;

      const tgDisplay = profile.telegram_chat_id
        ? `<span style="color:var(--colors-ink);font-weight:600">${profile.telegram_chat_id}</span>`
        : `<span style="color:var(--colors-muted);font-style:italic">Not configured</span>`;

      card.innerHTML = `
        <div style="padding:24px;border-bottom:1px solid var(--colors-hairline)">
          <div class="title-sm">Graduation Year</div>
          <div class="body-sm mt-xs">${gradYearDisplay}</div>
        </div>
        <div style="padding:24px;border-bottom:1px solid var(--colors-hairline)">
          <div class="title-sm">Telegram Alerts</div>
          <div class="body-sm mt-xs">${tgDisplay}</div>
        </div>
        <div style="padding:24px;border-bottom:1px solid var(--colors-hairline)">
          <div class="title-sm">Skills</div>
          <div class="flex flex-wrap gap-xs mt-sm">${(profile.skills || []).map((s: string) => `<span class="category-tag">${s}</span>`).join("")}</div>
        </div>
        <div style="padding:24px;border-bottom:1px solid var(--colors-hairline)">
          <div class="title-sm">Research Areas</div>
          <div class="flex flex-wrap gap-xs mt-sm">${(profile.research_areas || []).map((s: string) => `<span class="category-tag">${s}</span>`).join("")}</div>
        </div>
        <div style="padding:24px;border-bottom:1px solid var(--colors-hairline)">
          <div class="title-sm">Preferred Roles</div>
          <div class="flex flex-wrap gap-xs mt-sm">${(profile.preferred_roles || []).map((s: string) => `<span class="category-tag">${s}</span>`).join("")}</div>
        </div>
        <div style="padding:24px;border-bottom:1px solid var(--colors-hairline)">
          <div class="title-sm">Location Rules</div>
          <div class="body-sm mt-xs" style="color:var(--colors-muted)">
            Remote: ${profile.location_rule?.remote_allowed ? "Allowed" : "Not allowed"}<br/>
            Offline cities: ${(profile.location_rule?.offline_allowed || []).join(", ")}
          </div>
        </div>
        <div style="padding:24px">
          <div class="title-sm">Projects (${(profile.projects || []).length})</div>
          <div class="mt-sm">
            ${(profile.projects || []).slice(0, 5).map((p: string) => `<div class="body-sm" style="color:var(--colors-muted);padding:4px 0;border-bottom:1px solid var(--colors-hairline)">• ${p}</div>`).join("")}
          </div>
        </div>`;
    } catch {
      // Profile not found yet — that's OK
    }
  }

  // Save settings button
  document.getElementById("save-settings-btn")?.addEventListener("click", async () => {
    const btn = document.getElementById("save-settings-btn") as HTMLButtonElement;
    const statusDiv = document.getElementById("settings-status")!;
    const gradYearRaw = (document.getElementById("grad-year-input") as HTMLInputElement).value.trim();
    const tgChatId = (document.getElementById("tg-chat-id-input") as HTMLInputElement).value.trim();

    const update: Record<string, any> = {};
    if (gradYearRaw) update.graduation_year = parseInt(gradYearRaw, 10);
    if (tgChatId) update.telegram_chat_id = tgChatId;

    if (Object.keys(update).length === 0) {
      toast("Nothing to save — fill in at least one field.", "info");
      return;
    }

    btn.disabled = true;
    btn.textContent = "Saving…";
    statusDiv.textContent = "";
    try {
      await api.updateProfile(USER_ID, update);
      toast("Settings saved!", "success");
      statusDiv.innerHTML = `<span style="color:#10b981">Saved successfully</span>`;
      loadProfile();
    } catch (e: any) {
      toast(e.message, "error");
      statusDiv.innerHTML = `<span style="color:var(--danger)">${e.message}</span>`;
    } finally {
      btn.disabled = false;
      btn.textContent = "💾 Save Settings";
    }
  });

  // Send to Telegram button
  document.getElementById("send-telegram-btn")?.addEventListener("click", async () => {
    const btn = document.getElementById("send-telegram-btn") as HTMLButtonElement;
    const statusDiv = document.getElementById("settings-status")!;
    btn.disabled = true;
    btn.textContent = "Sending…";
    statusDiv.textContent = "";
    try {
      const res = await api.sendToTelegram(USER_ID, 4.0, 20);
      toast(` Sent ${res.sent} notices to Telegram (${res.skipped} skipped)`, "success");
      statusDiv.innerHTML = `<span style="color:#10b981">Sent ${res.sent} eligible notices to Telegram • ${res.skipped} below threshold or not eligible</span>`;
    } catch (e: any) {
      toast(e.message, "error");
      statusDiv.innerHTML = `<span style="color:var(--danger)">${e.message}</span>`;
    } finally {
      btn.disabled = false;
      btn.textContent = "✈️ Send Eligible to Telegram";
    }
  });

  loadProfile();
}




// Internship News Scraper page
export async function renderInternships() {
  const el = document.getElementById("page-internships")!;

  // Source registry: website + Telegram + Gmail
  const WEB_SOURCES = [
    { id: "companycareers", label: "Company Careers", icon: "", type: "website" },
    { id: "govtportal", label: "Govt Portals", icon: "🏛️", type: "website" },
  ];
  const TG_SOURCES = [
    { id: "telegram", label: "Public Channels", icon: "✈️", type: "telegram" },
  ];
  const GMAIL_SOURCES = [
    { id: "gmail", label: "Gmail Inbox", icon: "📧", type: "gmail" },
  ];

  // Each tab has its own independent selection — no bleed-across
  let webSelected = new Set(["companycareers"]);
  let tgSelected = new Set(["telegram"]);
  let gmailSelected = new Set(["gmail"]);
  let activeTab: "all" | "eligible" | "saved" | "applied" = "all";
  let allNotices: any[] = [];
  let activeSrcTab: "website" | "telegram" | "gmail" = "website";

  // Returns only the sources for the currently visible tab
  function activeSources(): string[] {
    if (activeSrcTab === "telegram") return [...tgSelected];
    if (activeSrcTab === "gmail") return [...gmailSelected];
    return [...webSelected];
  }

  // ── Pipeline stage indicator ────────────────────────────────────────────────
  const PIPELINE = ["Fetch", "Normalize", "Detect", "Extract Links", "Eligibility", "Dedup", "Score", "Alert"];

  function pipelineHTML(active = -1) {
    return `<div class="intern-pipeline">${PIPELINE.map((s, i) => `
        <div class="pipe-step ${i < active ? "done" : i === active ? "running" : ""}"><div class="pipe-dot">${i < active ? "✓" : i === active ? "" : i + 1}</div><div class="pipe-label">${s}</div>${i < PIPELINE.length - 1 ? '<div class="pipe-line"></div>' : ""}
        </div>`).join("")}
    </div>`;
  }

  // ── Eligibility badge ───────────────────────────────────────────────────────
  function eligBadge(status: string) {
    const label: Record<string, string> = {
      eligible: "Eligible", maybe: "Maybe", not_eligible: "Not Eligible", unknown: "Unknown",
    };
    return `<span class="category-tag">${label[status] || status}</span>`;
  }

  // ── Deadline urgency chip ───────────────────────────────────────────────────
  function deadlineChip(deadline: string | null) {
    if (!deadline) return "";
    const d = new Date(deadline);
    const days = Math.ceil((d.getTime() - Date.now()) / 86400000);
    if (days < 0) return `<span class="date-pill">Expired</span>`;
    if (days <= 3) return `<span class="date-pill">${days}d left</span>`;
    if (days <= 7) return `<span class="date-pill">${days}d left</span>`;
    return `<span class="date-pill">${days}d left</span>`;
  }

  // ── Score ring (small) ──────────────────────────────────────────────────────
  function scoreRing(score: number) {
    const pct = Math.round(score * 10);
    const col = pct >= 7 ? "#10b981" : pct >= 4 ? "#f59e0b" : "#6366f1";
    const r = 18, c = 20, circ = 2 * Math.PI * r;
    const dash = (score / 10) * circ;
    return `<svg viewBox="0 0 40 40" class="score-ring-svg"><circle cx="${c}" cy="${c}" r="${r}" fill="none" stroke="rgba(255,255,255,0.07)" stroke-width="3"/><circle cx="${c}" cy="${c}" r="${r}" fill="none" stroke="${col}" stroke-width="3"
        stroke-dasharray="${dash} ${circ}" stroke-dashoffset="${circ / 4}" stroke-linecap="round"/><text x="${c}" y="${c}" text-anchor="middle" dominant-baseline="central"
        fill="${col}" font-size="9" font-weight="700">${pct}/10</text></svg>`;
  }

  // ── Render notices list ─────────────────────────────────────────────────────
  function renderList(notices: any[]) {
    const list = document.getElementById("intern-feed")!;
    if (!notices.length) {
      list.innerHTML = `<div class="empty-state"><div class="empty-icon">📭</div><div class="empty-title">No notices yet</div><div class="empty-sub">Select sources above and click Fetch to begin scraping.</div></div>`;
      return;
    }
    const filtered = notices.filter(n => {
      if (activeTab === "eligible") return n.status !== "saved" && n.status !== "applied" && (n.eligibility_status === "eligible" || n.eligibility_status === "maybe");
      if (activeTab === "saved") return n.status === "saved";
      if (activeTab === "applied") return n.status === "applied";
      return n.status !== "saved" && n.status !== "applied"; // For "all", hide items already processed
    });
    if (!filtered.length) {
      list.innerHTML = `<div class="empty-state"><div class="empty-icon">🔍</div><div class="empty-title">Nothing in this tab</div></div>`;
      return;
    }
    list.innerHTML = filtered.map((n: any) => `
      <div class="career-listing-row" data-id="${n.notice_id}">
        <div style="display:flex;gap:16px;align-items:center;flex:1">
          <div style="width:48px;height:48px;border-radius:var(--rounded-full);background:var(--colors-surface-card);display:flex;align-items:center;justify-content:center;font-family:var(--font-mono);border:1px solid var(--colors-hairline)">${(n.company || "?")[0].toUpperCase()}</div>
          <div>
            <div class="title-sm">${n.title || "Untitled"}</div>
            <div class="body-sm" style="color:var(--colors-muted);margin-top:4px">
              <span style="color:var(--colors-ink)">${n.company || "—"}</span> &bull; 
              <span>${n.source === "Gmail" ? "Gmail" : n.source || "—"}</span>
              ${n.location ? ` &bull; <span>${n.location}</span>` : ""}
            </div>
            <div class="flex gap-xs mt-xs">
              ${eligBadge(n.eligibility_status || "unknown")}
              ${deadlineChip(n.deadline || null)}
            </div>
          </div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px">
          ${scoreRing(n.score || 0)}
          <div class="flex gap-xs">
            <button class="button-primary view-notice-btn" style="height:32px;padding:0 16px;font-size:11px" data-id="${n.notice_id}">Intel</button>
            ${n.apply_link ? `<a class="button-primary" style="height:32px;padding:0 16px;font-size:11px;line-height:30px" href="${n.apply_link}" target="_blank">Apply</a>` : ""}
            <button class="button-primary save-notice-btn" style="height:32px;padding:0 16px;font-size:11px" data-id="${n.notice_id}">
              ${n.status === 'saved' ? 'Tracked' : 'Track'}
            </button>
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
            <div class="modal-title">${n.title}</div><div style="display:flex;gap:12px;align-items:center;margin-bottom:16px"><span style="color:var(--text-secondary)">${n.company} · ${n.source}</span>${eligBadge(n.eligibility_status || "unknown")}
              ${deadlineChip(n.deadline || null)}
            </div>${n.raw_text ? `<div class="intern-raw-text">${n.raw_text}</div>` : ""}
            ${n.eligibility_text ? `<div class="card-title" style="margin-top:16px">Eligibility Note</div><div style="font-size:13px;color:var(--text-secondary);margin-bottom:12px">${n.eligibility_text}</div>` : ""}
            ${Object.keys(bd).length ? `<div class="card-title" style="margin-top:16px">Score Breakdown</div><div class="score-breakdown">${Object.entries(bd).map(([k, v]) => `
                <div class="score-row"><span class="score-label">${k.replace(/_/g, " ")}</span><div class="progress-bar-outer" style="flex:1"><div class="progress-bar-inner" style="width:${Math.round((v as number) * 100)}%"></div></div><span class="score-value">${Math.round((v as number) * 100)}%</span></div>`).join("")}
              </div>` : ""}

            <div class="card-title" style="margin-top:20px">GitHub Project Match</div><div id="project-match-container" style="margin-top:8px"><div style="display:flex;gap:8px;align-items:center;color:var(--text-muted);font-size:13px"><div class="spinner" style="width:16px;height:16px;border-width:2px"></div>Matching your repos…
              </div></div>${n.links?.length ? `<div class="card-title" style="margin-top:16px">Extracted Links</div>${n.links.map((l: any) => `<div style="margin:4px 0"><a href="${l.url}" target="_blank" style="color:var(--accent-light);font-size:13px">${l.text || l.url}</a><span class="intern-link-kind">${l.kind || ""}</span></div>`).join("")}` : ""}
            ${n.portal_link ? `<a href="${n.portal_link}" target="_blank" class="btn btn-primary" style="margin-top:20px;display:inline-flex">Apply Now →</a>` : ""}
          `);

          // Async: load project matches
          try {
            const pm = await api.projectMatch(id);
            const container = document.getElementById("project-match-container");
            if (!container) return;

            if (!pm.matches.length) {
              container.innerHTML = `<div style="font-size:13px;color:var(--text-muted);padding:8px 0">No matching repos found.
                ${pm.notice_keywords.length ? `<br><span style="font-size:12px">Detected keywords: ${pm.notice_keywords.join(", ")}</span>` : ""}
              </div>`;
              return;
            }

            container.innerHTML = `
              ${pm.notice_keywords.length ? `<div style="margin-bottom:12px;display:flex;flex-wrap:wrap;gap:6px">${pm.notice_keywords.map((kw: string) => `<span style="
                  padding:2px 8px;border-radius:4px;font-size:11px;
                  background:rgba(99,102,241,0.15);color:#818cf8;
                  border:1px solid rgba(99,102,241,0.3)
                ">${kw}</span>`).join("")}
              </div>` : ""}
              ${pm.matches.map((m: any) => {
              const pctColor = m.match_pct >= 60 ? "#10b981" : m.match_pct >= 30 ? "#f59e0b" : "#6b7280";
              return `<div style="
                  display:flex;align-items:center;gap:12px;
                  padding:10px 12px;margin-bottom:8px;border-radius:8px;
                  background:rgba(255,255,255,0.03);
                  border:1px solid rgba(255,255,255,0.06);
                  transition:background 0.2s
                " onmouseover="this.style.background='rgba(255,255,255,0.06)'"
                   onmouseout="this.style.background='rgba(255,255,255,0.03)'"><div style="
                    width:44px;height:44px;border-radius:50%;
                    display:flex;align-items:center;justify-content:center;
                    background:conic-gradient(${pctColor} ${m.match_pct * 3.6}deg, rgba(255,255,255,0.08) 0);
                    font-size:12px;font-weight:700;color:${pctColor};flex-shrink:0;
                    position:relative
                  "><div style="
                      width:34px;height:34px;border-radius:50%;
                      background:var(--bg-card);display:flex;
                      align-items:center;justify-content:center
                    ">${m.match_pct}%</div></div><div style="flex:1;min-width:0"><a href="${m.repo_url}" target="_blank" style="
                      color:var(--accent-light);font-weight:600;font-size:14px;
                      text-decoration:none;display:flex;align-items:center;gap:6px
                    ">${m.repo_name}
                      <span style="
                        font-size:11px;padding:1px 6px;border-radius:4px;
                        background:rgba(255,255,255,0.08);color:var(--text-muted);
                        font-weight:400
                      ">${m.language}</span>${m.stars ? `<span style="font-size:11px;color:var(--text-muted)">⭐ ${m.stars}</span>` : ""}
                    </a>${m.description ? `<div style="font-size:12px;color:var(--text-muted);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${m.description}</div>` : ""}
                    <div style="font-size:11px;color:var(--text-secondary);margin-top:3px">${m.reasons.join(" · ")}</div></div></div>`;
            }).join("")}
            `;
          } catch { /* project match failed silently */ }

        } catch (e: any) { toast(e.message, "error"); }
      });
    });

    list.querySelectorAll(".save-notice-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = (btn as HTMLElement).dataset.id!;
        const n = allNotices.find(x => x.notice_id === id);
        if (!n) return;

        try {
          if (n.status === "saved" && n.applied_id) {
            await api.deleteAppliedNotice(n.applied_id);
            toast("Removed from Tracker", "success");
            n.status = null;
            n.applied_id = null;
          } else {
            const res = await api.markAppliedNotice({ user_id: USER_ID, notice_id: id, status: "saved" });
            toast("Notice added to Tracker!", "success");
            n.status = "saved";
            n.applied_id = res.applied_id;
          }
          updateTabCounts(allNotices);
          renderList(allNotices);
        } catch (e: any) { toast(e.message, "error"); }
      });
    });

    list.querySelectorAll(".autopilot-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        toast("Autopilot queued (Coming Soon) ⚡", "success");
      });
    });
  }

  // ── Load notices from backend ───────────────────────────────────────────────
  async function loadNotices() {
    const feed = document.getElementById("intern-feed")!;
    feed.innerHTML = `<div style="display:flex;gap:8px;align-items:center"><div class="spinner"></div>Loading notices…</div>`;
    try {
      // Load notices matching the active source tab only
      const notices = await api.getRankedInternships(USER_ID, 200, activeSources());
      allNotices = notices;
      updateTabCounts(notices);
      renderList(notices);
    } catch (e: any) {
      feed.innerHTML = `<div class="empty-state"><div class="empty-icon"></div><div class="empty-title">${e.message}</div></div>`;
    }
  }

  function updateTabCounts(notices: any[]) {
    const counts = { all: 0, eligible: 0, saved: 0, applied: 0 };
    for (const n of notices) {
      if (n.status === "saved") {
        counts.saved++;
      } else if (n.status === "applied") {
        counts.applied++;
      } else {
        counts.all++;
        if (n.eligibility_status === "eligible" || n.eligibility_status === "maybe") {
          counts.eligible++;
        }
      }
    }
    (["all", "eligible", "saved", "applied"] as const).forEach(t => {
      const el = document.getElementById(`intern-tab-${t}`);
      if (el) el.textContent = `${t.charAt(0).toUpperCase() + t.slice(1)} (${counts[t]})`;
    });
  }

  // ── Initial render ──────────────────────────────────────────────────────────
  el.innerHTML = `
    <div>
      <div class="title-md" style="margin-bottom:var(--spacing-md)">INTERNSHIP NEWS SCRAPER</div>
      <div class="model-photo-card" style="padding:24px;margin-bottom:24px">
        <div class="title-sm" style="margin-bottom:12px">SOURCE REGISTRY</div>
        <div class="intern-src-tabs" style="display:flex;gap:8px;margin-bottom:12px">
          <button class="intern-src-tab active" id="srctab-website" data-srctab="website">WEB</button>
          <button class="intern-src-tab" id="srctab-telegram" data-srctab="telegram">TELEGRAM</button>
          <button class="intern-src-tab" id="srctab-gmail" data-srctab="gmail">GMAIL</button>
        </div>
        <div id="src-website-chips" class="source-chips" style="margin-bottom:12px">${WEB_SOURCES.map(s => `<button class="source-chip ${webSelected.has(s.id) ? "selected" : ""}" data-source="${s.id}" data-group="web">${s.icon} ${s.label}</button>`).join("")}</div>
        <div id="src-telegram-chips" class="source-chips" style="margin-bottom:12px;display:none">${TG_SOURCES.map(s => `<button class="source-chip ${tgSelected.has(s.id) ? "selected" : ""}" data-source="${s.id}" data-group="tg">${s.icon} ${s.label}<span style="font-size:10px;color:var(--colors-muted);margin-left:4px">5 channels</span></button>`).join("")}<div class="body-sm" style="margin-top:8px;color:var(--colors-muted)">Scrapes: @JobsAndInternshipsIndia, @internshipsalert, @internship_update, @HiringIndia, @TechJobsIndia</div></div>
        <div id="src-gmail-chips" class="source-chips" style="margin-bottom:12px;display:none">${GMAIL_SOURCES.map(s => `<button class="source-chip ${gmailSelected.has(s.id) ? "selected" : ""}" data-source="${s.id}" data-group="gmail">${s.icon} ${s.label}</button>`).join("")}<div id="gmail-status-line" class="body-sm" style="margin-top:8px;color:var(--colors-muted)">Checking connection…</div></div>
        
        <div style="display:flex;align-items:center;gap:12px;margin-top:16px">
          <button class="button-primary" id="intern-fetch-btn">FETCH & PROCESS</button>
          <span id="intern-fetch-status" class="body-sm" style="color:var(--colors-muted)"></span>
        </div>
        <div id="intern-pipeline-wrap" style="display:none;margin-top:16px">${pipelineHTML(-1)}</div>
      </div>

      <div class="intern-tabs" style="display:flex;gap:8px;margin-bottom:12px">
        <button class="intern-tab active" id="intern-tab-all" data-tab="all">ALL (0)</button>
        <button class="intern-tab" id="intern-tab-eligible" data-tab="eligible">ELIGIBLE (0)</button>
        <button class="intern-tab" id="intern-tab-saved" data-tab="saved">SAVED (0)</button>
        <button class="intern-tab" id="intern-tab-applied" data-tab="applied">APPLIED (0)</button>
      </div>
      <div id="intern-feed" class="intern-feed"></div>
    </div>`;

  // Source type tab switching (website ↔ telegram)
  el.querySelectorAll(".intern-src-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      const which = (tab as HTMLElement).dataset.srctab as "website" | "telegram" | "gmail";
      activeSrcTab = which;
      el.querySelectorAll(".intern-src-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      (document.getElementById("src-website-chips") as HTMLElement).style.display =
        which === "website" ? "flex" : "none";
      (document.getElementById("src-telegram-chips") as HTMLElement).style.display =
        which === "telegram" ? "flex" : "none";
      (document.getElementById("src-gmail-chips") as HTMLElement).style.display =
        which === "gmail" ? "flex" : "none";
      // Reload feed to show only notices for the selected source tab
      loadNotices();
    });
  });

  // Source chip toggle — updates the correct tab's set based on data-group
  el.querySelectorAll(".source-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const src = (chip as HTMLElement).dataset.source!;
      const group = (chip as HTMLElement).dataset.group!;
      const set = group === "web" ? webSelected : group === "tg" ? tgSelected : gmailSelected;
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
    btn.innerHTML = `<div class="spinner"></div>Processing…`;
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

  // Fetch Gmail connection status on load
  (async () => {
    try {
      const status = await api.gmailStatus();
      const el = document.getElementById("gmail-status-line");
      if (el) {
        if (status.connected) {
          el.innerHTML = `<span style="color:#10b981">Connected: ${status.email}</span>· Scans last ${status.days_back} days`;
        } else {
          el.innerHTML = `<span style="color:var(--text-muted)">Not configured — add IMAP_USER and IMAP_PASSWORD to .env</span>`;
        }
      }
    } catch { /* backend offline */ }
  })();

  loadNotices();
}


// Drafts for the comapany/startup page
export async function renderDrafts() {
  const el = document.getElementById("page-drafts")!;
  el.innerHTML = `<div style="display:flex;align-items:center;gap:8px"><div class="spinner"></div>Loading drafts…</div>`;

  try {
    const drafts = await api.getDrafts(USER_ID) as any[];

    if (!drafts.length) {
      el.innerHTML = `<div class="empty-state"><div class="empty-icon"></div><div class="empty-title">No drafts yet</div><div class="empty-sub">Generate drafts from the Ranked Jobs page.</div></div>`;
      return;
    }

    el.innerHTML = `
      <div>
        <div class="title-md" style="margin-bottom:var(--spacing-md)">AUTOPILOT QUEUE</div>
        <div class="model-photo-card" style="padding:24px;margin-bottom:24px">
          <div class="body-sm" style="color:var(--colors-muted)">Manage AI-generated outreach drafts before they are sent.</div>
        </div>
        <div class="title-md" style="margin-bottom:var(--spacing-md)">DRAFTS (${drafts.length})</div>
        <div class="job-list" id="draft-list"></div>
      </div>`;

    const list = document.getElementById("draft-list")!;
    list.innerHTML = drafts.map((d: any) => `
      <div class="newsroom-article-card" id="draft-${d.draft_id}" style="margin-bottom:12px;padding:24px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
          <div>
            <div class="title-sm">${d.subject || "(no subject)"}</div>
            <div class="body-sm mt-xs" style="color:var(--colors-muted)">${d.company} &bull; ${d.job_title}</div>
          </div>
          <div style="display:flex;align-items:center;gap:16px">
            ${statusChip(d.status)}
            <div style="display:flex;gap:8px">
              <button class="button-primary view-draft-btn" style="height:36px;padding:0 24px" data-draft-id="${d.draft_id}">REVIEW</button>
              ${d.status !== "approved" && d.status !== "sent" ? `<button class="button-primary approve-btn" style="height:36px;padding:0 24px" data-draft-id="${d.draft_id}">APPROVE</button>` : ""}
              ${d.status === "approved" ? `<button class="button-primary send-btn" style="height:36px;padding:0 24px" data-draft-id="${d.draft_id}">SEND</button>` : ""}
            </div>
          </div>
        </div>
      </div>`).join("");

    list.querySelectorAll(".view-draft-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const draftId = (btn as HTMLElement).dataset.draftId!;
        try {
          const d = await api.getDraft(draftId);
          openModal(`
            <div class="modal-title">Draft Preview</div><div class="form-group"><div class="card-title">Subject</div><input class="form-input" id="edit-subject" value="${(d.subject || "").replace(/"/g, "&quot;")}" /></div><div class="form-group"><div class="card-title">Body</div><textarea class="form-textarea" id="edit-body" style="min-height:200px">${d.body || ""}</textarea></div>${d.linkedin_message ? `<div class="form-group"><div class="card-title">LinkedIn Message</div><p style="font-size:13px;color:var(--text-secondary)">${d.linkedin_message}</p></div>` : ""}
            <div style="display:flex;gap:8px;margin-top:8px"><button class="btn btn-primary" id="save-draft-btn" data-draft-id="${draftId}">Save Changes</button><button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button></div>`);
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
          <div class="modal-title">Send Email</div><div class="form-group"><label class="form-label">Recipient email address</label><input class="form-input" id="recipient-email" type="email" placeholder="hr@company.com" /></div><div style="display:flex;gap:8px"><button class="btn btn-primary" id="confirm-send-btn" data-draft-id="${draftId}">Send Now </button><button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button></div>`);
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

  el.innerHTML = `
    <div>
      <div class="title-md" style="margin-bottom:var(--spacing-md)">REPO INTELLIGENCE</div>
      <div class="model-photo-card" style="padding:24px">
        <div class="body-sm" style="color:var(--colors-muted);margin-bottom:16px">Sync your GitHub repos and use AI to rank them based on role fit.</div>
        <div class="repo-page-wrapper">
          <div class="repo-connect-panel" id="repo-connect-panel">
            <div class="spinner"></div><span style="margin-left:10px">Checking GitHub connection...</span>
          </div>
          <div id="repo-main-content" style="display:none">
            <div class="repo-toolbar" style="display:flex;justify-content:space-between;align-items:center;background:var(--colors-surface-card);padding:16px;border:1px solid var(--colors-hairline)">
              <div class="repo-toolbar-left" style="display:flex;gap:12px;align-items:center">
                <div class="repo-github-badge" id="repo-github-badge"></div>
                <div class="role-selector-wrap" style="display:flex;align-items:center;gap:8px">
                  <label class="title-sm">TARGET ROLE</label>
                  <select class="text-input" id="role-select" style="width:150px;height:36px"></select>
                </div>
              </div>
              <div class="repo-toolbar-right" style="display:flex;gap:8px">
                <button class="button-primary" id="repo-sync-btn">SYNC REPOS</button>
                <button class="button-primary" id="repo-analyze-btn">ANALYZE</button>
              </div>
            </div>
            <div id="repo-status-bar" class="repo-status-bar" style="display:none;margin-top:12px"></div>
            <div id="top5-section" style="display:none;margin-top:24px">
              <div class="title-md" style="margin-bottom:var(--spacing-sm)">TOP 5 REPOSITORIES <span id="active-role-pill" style="float:right"></span></div>
              <div class="repo-top5-grid" id="repo-top5-grid" style="margin-top:8px"></div>
            </div>
            <div id="all-repos-section" style="display:none;margin-top:24px">
              <div class="title-md" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:var(--spacing-sm)">
                <span id="all-repos-count-title">ALL REPOSITORIES</span>
                <button class="button-primary" id="toggle-all-repos" style="padding:0 12px;height:32px;font-size:11px">SHOW ALL</button>
              </div>
              <div class="job-list" id="all-repos-list" style="display:none;margin-top:8px"></div>
            </div>
          </div>
        </div>
      </div>
    </div>`;

  await checkConnectionAndRender(el);
}

async function checkConnectionAndRender(el: HTMLElement) {
  try {
    const status = await api.githubStatus();
    const panel = el.querySelector("#repo-connect-panel") as HTMLElement;
    const main = el.querySelector("#repo-main-content") as HTMLElement;

    if (!status.connected) {
      panel.innerHTML = renderConnectUI();
      wireConnectUI(el);
      return;
    }

    panel.style.display = "none";
    main.style.display = "block";

    const badge = el.querySelector("#repo-github-badge") as HTMLElement;
    badge.innerHTML = `<div style="display:flex;align-items:center;gap:12px"><span class="github-connected-badge"><span class="github-dot"></span><strong>${status.github_username}</strong><span style="color:var(--text-muted);font-size:11px">connected</span></span><button class="btn btn-secondary btn-sm" id="update-gh-token-btn" style="padding:4px 10px;font-size:11px">Update Token</button></div>`;

    badge.querySelector("#update-gh-token-btn")?.addEventListener("click", () => {
      openModal(`
        <div class="modal-title">Update GitHub Token</div><div class="form-group"><label class="form-label">Personal Access Token (repo scope)</label><input class="form-input" id="new-gh-token" type="password" placeholder="ghp_..." /></div><div style="display:flex;gap:8px"><button class="btn btn-primary" id="save-new-token-btn">Save Token</button><button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button></div>`);
      document.getElementById("save-new-token-btn")?.addEventListener("click", async () => {
        const token = (document.getElementById("new-gh-token") as HTMLInputElement).value.trim();
        if (!token) return toast("Enter a token", "error");

        const saveBtn = document.getElementById("save-new-token-btn") as HTMLButtonElement;
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<div class="spinner"></div>Saving...`;

        try {
          await api.githubConnect(token);
          toast("Token updated!", "success");
          closeModal();
          await renderRepos();
        } catch (e: any) {
          toast(e.message, "error");
          saveBtn.disabled = false;
          saveBtn.innerHTML = "Save Token";
        }
      });
    });

    await wireMainUI(el);
  } catch {
    const panel = el.querySelector("#repo-connect-panel") as HTMLElement;
    panel.innerHTML = `<div class="empty-state"><div class="empty-icon"></div><div class="empty-title">Backend offline</div><div class="empty-sub">Start uvicorn first.</div></div>`;
  }
}

function renderConnectUI(): string {
  return `
    <div class="github-connect-card"><div class="github-connect-icon"></div><div class="github-connect-title">Connect your GitHub account</div><div class="github-connect-sub">Enter a GitHub Personal Access Token (PAT) with <code>repo</code>scope to let
        Job Hunter analyse your repositories.
      </div><div style="margin:24px auto;max-width:480px"><input class="form-input" id="gh-token-input" type="password"
          placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" /><div style="display:flex;gap:10px;margin-top:12px;justify-content:center"><button class="btn btn-primary" id="gh-connect-btn">Connect GitHub</button><a class="btn btn-secondary"
            href="https://github.com/settings/tokens/new?scopes=repo,read:user"
            target="_blank">Create Token </a></div><div id="gh-connect-err" style="margin-top:12px;color:var(--danger);font-size:13px;text-align:center"></div></div></div>`;
}

function wireConnectUI(el: HTMLElement) {
  const btn = el.querySelector("#gh-connect-btn") as HTMLButtonElement;
  const inp = el.querySelector("#gh-token-input") as HTMLInputElement;
  const err = el.querySelector("#gh-connect-err") as HTMLElement;

  btn.addEventListener("click", async () => {
    const token = inp.value.trim();
    if (!token) { err.textContent = "Please enter a token."; return; }
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner"></div>Connecting…`;
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
    roleSelect.innerHTML = roles.map(r => `<option value="${r.id}" ${r.id === _currentRole ? "selected" : ""}>${r.label}</option>`
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
    btn.innerHTML = `<div class="spinner"></div>Syncing…`;
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
    btn.innerHTML = `<div class="spinner"></div>Analyzing…`;
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
  const top5Section = el.querySelector("#top5-section") as HTMLElement;
  const allSection = el.querySelector("#all-repos-section") as HTMLElement;
  const grid = el.querySelector("#repo-top5-grid") as HTMLElement;
  const allList = el.querySelector("#all-repos-list") as HTMLElement;
  const rolePill = el.querySelector("#active-role-pill") as HTMLElement;
  const allCountTitle = el.querySelector("#all-repos-count-title") as HTMLElement;
  const toggleBtn = el.querySelector("#toggle-all-repos") as HTMLButtonElement;

  grid.innerHTML = `<div class="repo-loading"><div class="spinner"></div><span>Loading ranked repos…</span></div>`;
  top5Section.style.display = "block";

  try {
    const data = await api.githubTop5(_currentRole);

    const roleLabel = (el.querySelector("#role-select") as HTMLSelectElement)?.selectedOptions?.[0]?.text ?? _currentRole;
    rolePill.textContent = roleLabel;

    if (!data.top5?.length) {
      grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon">📭</div><div class="empty-title">No analysed repos yet</div><div class="empty-sub">Click "⚡ Analyze &amp; Rank" to run the pipeline.</div></div>`;
      return;
    }

    grid.innerHTML = data.top5.map((repo: any, idx: number) => renderRepoCard(repo, idx + 1)
    ).join("");

    grid.querySelectorAll(".newsroom-article-card").forEach(card => {
      card.addEventListener("click", async () => {
        const repoId = (card as HTMLElement).dataset.repoId!;
        await openRepoExpansion(repoId, _currentRole);
      });
    });

    if (data.all_repos?.length > 5) {
      allSection.style.display = "block";
      allCountTitle.textContent = `All Repositories (${data.all_repos.length})`;

      allList.innerHTML = data.all_repos.slice(5).map((repo: any, i: number) => renderRepoListRow(repo, i + 6)
      ).join("");

      allList.querySelectorAll(".career-listing-row").forEach(row => {
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
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon"></div><div class="empty-title">${e.message}</div></div>`;
  }
}

function renderScoreRing(score: number, label: string, color: string): string {
  const pct = Math.round(score * 10);
  const circumference = 2 * Math.PI * 20;
  const dash = (pct / 100) * circumference;
  return `
    <div class="score-ring-wrap"><svg class="score-ring" viewBox="0 0 48 48"><circle cx="24" cy="24" r="20" fill="none" stroke="#262626" stroke-width="3"/><circle cx="24" cy="24" r="20" fill="none" stroke="${color}" stroke-width="3"
          stroke-dasharray="${dash.toFixed(1)} ${circumference.toFixed(1)}"
          stroke-linecap="round" transform="rotate(-90 24 24)"/><text x="24" y="28" text-anchor="middle" font-size="10" font-weight="700"
          fill="${color}">${score.toFixed(1)}</text></svg><div class="score-ring-label">${label}</div></div>`;
}

function renderRepoCard(repo: any, rank: number): string {
  const langColor: Record<string, string> = {
    Python: "#3572A5", TypeScript: "#3178c6", JavaScript: "#f1e05a",
    Rust: "#dea584", Go: "#00ADD8", Java: "#b07219", "C++": "#f34b7d",
    CSS: "#563d7c", HTML: "#e34c26", Swift: "#ffac45", Kotlin: "#A97BFF",
    Ruby: "#701516", PHP: "#4F5D95", "C#": "#178600",
  };
  const lc = langColor[repo.language] || "#ffffff";
  const rankColors = ["#fbbf24", "#94a3b8", "#b45309", "#64748b", "#64748b"];
  const rankColor = rankColors[rank - 1] || "#64748b";
  const finalPct = Math.round(repo.final_score * 10);

  const badges = [
    repo.has_readme ? `<span class="category-tag">README</span>` : "",
    repo.has_tests ? `<span class="category-tag">Tests</span>` : "",
    repo.has_ui ? `<span class="category-tag">UI</span>` : "",
    repo.has_deployment ? `<span class="category-tag">Deployed</span>` : "",
    repo.has_demo_link ? `<span class="category-tag">Demo</span>` : "",
  ].filter(Boolean).join("");

  return `
  <div class="newsroom-article-card" data-repo-id="${repo.repo_id}" title="Click to expand full analysis" style="cursor:pointer;padding:24px">
    <div style="display:flex;justify-content:space-between;align-items:flex-start">
      <div>
        <div class="title-sm" style="color:${rankColor}">#${rank} <span style="color:var(--colors-ink)">${repo.name}</span></div>
        <div class="body-sm mt-xs" style="color:var(--colors-muted)">${repo.description || "<em style='opacity:0.5'>No description</em>"}</div>
        <div style="display:flex;gap:12px;font-size:11px;color:var(--colors-ink);margin-bottom:8px;margin-top:8px">
          ${repo.language ? `<span style="font-weight:700;color:${lc}">${repo.language}</span>` : ""}
          ${repo.stars > 0 ? `<span>★ ${repo.stars}</span>` : ""}
          ${repo.forks > 0 ? `<span>⑂ ${repo.forks}</span>` : ""}
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">${badges}</div>
      </div>
      <div style="background:var(--colors-surface-card);border:1px solid var(--colors-hairline);padding:8px 16px;text-align:center">
        <div class="title-md" style="color:var(--colors-ink)">${repo.final_score.toFixed(1)}</div>
        <div class="body-sm" style="font-size:9px;color:var(--colors-muted);letter-spacing:1px;text-transform:uppercase">SCORE</div>
      </div>
    </div>
    
    <div style="display:flex;justify-content:space-between;background:transparent;border:1px solid var(--colors-hairline);padding:16px;margin-top:16px">
      ${renderScoreRing(repo.uniqueness_score, "Unique", "#a78bfa")}
      ${renderScoreRing(repo.code_quality_score, "Code", "#00f0ff")}
      ${renderScoreRing(repo.documentation_score, "Docs", "#10b981")}
      ${renderScoreRing(repo.uiux_score, "UI/UX", "#f59e0b")}
    </div>
    
    ${repo.selection_reason ? `<div class="body-sm mt-sm" style="color:var(--colors-muted);border-left:2px solid ${rankColor};padding-left:12px">${repo.selection_reason}</div>` : ""}
    <div style="margin-top:16px;display:flex;justify-content:space-between">
      <a href="${repo.html_url}" target="_blank" onclick="event.stopPropagation()" style="color:var(--colors-ink);font-weight:700;font-size:11px;text-decoration:underline">VIEW ON GITHUB ↗</a>
      <span style="color:var(--colors-muted);font-size:11px">CLICK TO EXPAND</span>
    </div>
  </div>`;
}

function renderRepoListRow(repo: any, rank: number): string {
  return `
  <div class="career-listing-row" data-repo-id="${repo.repo_id}" style="cursor:pointer">
    <div style="display:flex;align-items:center;gap:16px">
      <div style="background:var(--colors-surface-card);color:var(--colors-ink);width:32px;height:32px;text-align:center;line-height:32px;border:1px solid var(--colors-hairline);font-weight:700">${repo.name[0].toUpperCase()}</div>
      <div>
        <div class="title-sm" style="color:var(--colors-ink)">#${rank} ${repo.name}</div>
        <div class="body-sm mt-xs" style="color:var(--colors-muted);display:flex;gap:8px">
          <span>${repo.language || "—"}</span><span>★ ${repo.stars}</span>
          ${repo.description ? `<span style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${repo.description}</span>` : ""}
        </div>
      </div>
    </div>
    <div style="text-align:right">
      <div class="title-sm" style="color:var(--colors-ink)">${repo.final_score.toFixed(1)} / 10</div>
      <div class="body-sm" style="font-size:10px;text-transform:uppercase;color:var(--colors-muted)">${repo.analyzed ? "ANALYZED" : "UNANALYZED"}</div>
    </div>
  </div>`;
}

async function openRepoExpansion(repoId: string, role: string) {
  openModal(`<div style="display:flex;align-items:center;gap:8px"><div class="spinner"></div>Loading full analysis…</div>`);
  try {
    const d = await api.githubRepoDetails(repoId, role);
    const a = d.analysis || {};
    const s = d.scores || {};
    const breakdown = s.breakdown || {};
    const signalReasons: Record<string, { why: string; fix: string }> = d.signal_reasons || {};
    const improvementTips: Array<{ icon: string; title: string; tip: string }> = d.improvement_tips || [];

    const metricRows = Object.entries(breakdown).map(([key, val]: any) => {
      const colors: Record<string, string> = {
        uniqueness: "#a78bfa",
        code_quality: "#22d3ee",
        documentation: "#10b981",
        uiux: "#f59e0b",
      };
      const c = colors[key] || "var(--accent-light)";
      const pct = Math.round((val.score / 10) * 100);
      const labels: Record<string, string> = {
        uniqueness: "Uniqueness", code_quality: "Code Quality",
        documentation: "Documentation", uiux: "UI / UX",
      };
      return `
      <div class="expansion-metric"><div class="expansion-metric-header"><span class="expansion-metric-label" style="color:${c}">${labels[key] || key}</span><span class="expansion-metric-score" style="color:${c}">${val.score.toFixed(1)} / 10</span><span class="expansion-metric-weight">weight: ${Math.round(val.weight * 100)}%</span></div><div class="progress-bar-outer"><div class="progress-bar-inner" style="width:${pct}%;background:${c}"></div></div></div>`;
    }).join("");

    const signal = (flag: boolean, label: string, signalKey: string) => {
      const reason = signalReasons[signalKey];
      if (flag) {
        if (reason) {
          const safeWhy = reason.why.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
          const safeFix = reason.fix.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
          return `
            <div class="signal-chip signal-yes signal-expandable" data-why="${safeWhy}" data-fix="${safeFix}"><span>✓ ${label}</span><span class="signal-why-icon" title="Why?">?</span></div>`;
        }
        return `<div class="signal-chip signal-yes">✓ ${label}</div>`;
      }
      if (reason) {
        const safeWhy = reason.why.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
        const safeFix = reason.fix.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
        return `
          <div class="signal-chip signal-no signal-expandable" data-why="${safeWhy}" data-fix="${safeFix}"><span>✗ ${label}</span><span class="signal-why-icon" title="Why?">?</span></div>`;
      }
      return `<div class="signal-chip signal-no">✗ ${label}</div>`;
    };

    const finalPct = Math.round(s.final_score * 10);

    const tipsHtml = improvementTips.length ? `
    <div class="expansion-section-title" style="margin-top:28px">Improvement Tips for ${role.replace(/_/g, " ")}</div><div class="improvement-tips-grid">${improvementTips.map(t => `
        <div class="improvement-tip-card"><div class="tip-icon">${t.icon}</div><div class="tip-body"><div class="tip-title">${t.title}</div><div class="tip-text">${t.tip}</div></div></div>`).join("")}
    </div>` : "";

    const html = `
    <div class="expansion-header"><div><div class="expansion-repo-name">${d.name}</div><div style="font-size:13px;color:var(--text-muted);margin-top:4px">${d.full_name}</div><div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">${d.language ? `<span class="badge badge-new">${d.language}</span>` : ""}
          ${(d.topics || []).map((t: string) => `<span class="badge badge-new">${t}</span>`).join("")}
        </div></div><div class="expansion-score-ring"><svg viewBox="0 0 80 80"><circle cx="40" cy="40" r="34" fill="none" stroke="#262626" stroke-width="4"/><circle cx="40" cy="40" r="34" fill="none" stroke="#ffffff" stroke-width="4"
            stroke-dasharray="${((finalPct / 100) * 213.63).toFixed(1)} 213.63"
            stroke-linecap="round" transform="rotate(-90 40 40)"/><text x="40" y="45" text-anchor="middle" font-size="18" font-weight="800" fill="#ffffff">${s.final_score?.toFixed(1)}</text></svg><div style="font-size:12px;color:var(--text-muted);margin-top:4px;text-align:center">Final Score</div></div></div>${d.description ? `<div class="expansion-description">${d.description}</div>` : ""}

    <div class="expansion-section-title">Score Breakdown</div><div class="expansion-metrics">${metricRows}</div><div class="expansion-section-title">Repository Signals</div><div style="font-size:12px;color:var(--text-muted);margin-bottom:10px">Click any <span style="color:#10b981;font-weight:600">✓</span>or <span style="color:#f87171;font-weight:600">✗</span>signal to see details.</div><div class="signals-grid" id="signals-grid-${repoId}">${signal(a.has_readme, "README", "has_readme")}
      ${signal(a.has_problem_statement, "Problem Statement", "has_problem_statement")}
      ${signal(a.has_features_section, "Features Section", "has_features_section")}
      ${signal(a.has_setup_instructions, "Setup Guide", "has_setup_instructions")}
      ${signal(a.has_architecture_info, "Architecture Docs", "has_architecture_info")}
      ${signal(a.has_screenshots, "Screenshots", "has_screenshots")}
      ${signal(a.has_api_docs, "API Docs", "has_api_docs")}
      ${signal(a.has_future_scope, "Roadmap / Future", "has_future_scope")}
      ${signal(a.has_tests, "Test Suite", "has_tests")}
      ${signal(a.has_ci_cd, "CI / CD Pipeline", "has_ci_cd")}
      ${signal(a.has_docker, "Docker", "has_docker")}
      ${signal(a.has_ui, "Frontend / UI", "has_ui")}
      ${signal(a.has_deployment, "Deployment Config", "has_deployment")}
      ${signal(a.has_demo_link, "Live Demo", "has_demo_link")}
      ${signal(a.has_license, "License", "has_license")}
      ${signal(a.has_contributing, "Contributing Guide", "has_contributing")}
    </div><div class="signal-reason-panel" id="signal-reason-panel" style="display:none"><div class="srp-header"><span class="srp-title" id="srp-title"></span><button class="srp-close" id="srp-close"></button></div><div class="srp-section-label">Why this matters</div><div class="srp-why" id="srp-why"></div><div class="srp-section-label" style="margin-top:10px" id="srp-fix-label">How to fix it</div><div class="srp-fix" id="srp-fix"></div></div><div class="expansion-stats-row"><div class="expansion-stat"><div class="expansion-stat-val">${a.file_count ?? "—"}</div><div class="expansion-stat-lbl">Files</div></div><div class="expansion-stat"><div class="expansion-stat-val">${a.directory_count ?? "—"}</div><div class="expansion-stat-lbl">Dirs</div></div><div class="expansion-stat"><div class="expansion-stat-val">${d.stars ?? 0}</div><div class="expansion-stat-lbl">Stars</div></div><div class="expansion-stat"><div class="expansion-stat-val">${d.forks ?? 0}</div><div class="expansion-stat-lbl">Forks</div></div><div class="expansion-stat"><div class="expansion-stat-val">${a.readme_length ? Math.round(a.readme_length / 100) + "00" : "0"}</div><div class="expansion-stat-lbl">README chars</div></div></div>${(a.folder_structure || []).length ? `
    <div class="expansion-section-title">Top-Level Structure</div><div class="repo-folder-tree">${(a.folder_structure || []).map((f: string) => `<span class="folder-chip">${f}</span>`).join("")}
    </div>` : ""}

    ${tipsHtml}

    <div class="expansion-actions"><a class="btn btn-primary" href="${d.html_url}" target="_blank">View on GitHub </a>${d.analysis?.has_demo_link ? `<a class="btn btn-secondary" href="#" target="_blank">Live Demo </a>` : ""}
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
  el.innerHTML = `<div style="display:flex;gap:8px;align-items:center"><div class="spinner"></div>Loading…</div>`;

  try {
    const log = await api.getSentLog() as any[];

    if (!log.length) {
      el.innerHTML = `<div class="empty-state"><div class="empty-icon"></div><div class="empty-title">Nothing sent yet</div><div class="empty-sub">Approve and send drafts from the Review Queue.</div></div>`;
      return;
    }

    el.innerHTML = `
      <div>
        <div class="title-md" style="margin-bottom:var(--spacing-md)">SENT LOG</div>
        <div class="model-photo-card" style="padding:24px;margin-bottom:24px">
          <div class="body-sm" style="color:var(--colors-muted)">Record of all outgoing messages and pitches.</div>
        </div>
        <div class="title-md" style="margin-bottom:var(--spacing-md)">SENT MESSAGES (${log.length})</div>
        <div class="job-list">${log.map((s: any) => `
          <div class="newsroom-article-card" style="margin-bottom:12px;padding:24px">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <div>
                <div class="title-sm" style="color:var(--colors-ink)">${s.subject || "—"}</div>
                <div class="body-sm mt-xs" style="color:var(--colors-muted)">${s.recipient} &bull; ${s.sent_at ? new Date(s.sent_at).toLocaleString() : "—"}</div>
              </div>
              ${statusChip(s.status)}
            </div>
          </div>`).join("")}
        </div>
      </div>`;
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
  el.innerHTML = `<div style="display:flex;gap:8px;align-items:center"><div class="spinner"></div>Loading applications\u2026</div>`;
  try {
    const apps = await api.getAppliedNotices(USER_ID) as any[];
    const syncBtnHtml = ``;
    if (!apps.length) {
      el.innerHTML = `<div class="empty-state"><div class="empty-title">No tracked notices yet</div><div class="empty-sub" style="margin-top: 16px;">Track internships from the Discovery feed.</div>${syncBtnHtml}</div>`;
    } else {
      el.innerHTML = `
        <div>
          <div class="title-md" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:var(--spacing-md)">
            TRACKER
          </div>
          <div class="model-photo-card" style="padding:24px;margin-bottom:24px">
            <div class="body-sm" style="color:var(--colors-muted)">Track your sent applications and follow-ups.</div>
          </div>
          <div class="title-md" style="margin-bottom:var(--spacing-md)">APPLICATIONS (${apps.length})</div>
          <div class="job-list" id="applied-list"></div>
        </div>`;
      const list = document.getElementById("applied-list")!;
      list.innerHTML = apps.map((a: any) => `
      <div class="career-listing-row" id="app-${a.applied_id}">
        <div style="display:flex;align-items:center;gap:16px;flex:1">
          <div style="background:var(--colors-surface-card);color:var(--colors-ink);width:48px;height:48px;border-radius:var(--rounded-full);text-align:center;line-height:48px;border:1px solid var(--colors-hairline);font-family:var(--font-mono)">${(a.company || "?")[0].toUpperCase()}</div>
          <div>
            <div class="title-sm" style="color:var(--colors-ink)">${a.title || "—"}</div>
            <div class="body-sm mt-xs" style="color:var(--colors-muted)">
              <span style="font-weight:700;color:var(--colors-ink)">${a.company || "—"}</span> &bull; <span>${a.source || "—"}</span> &bull; <span>Tracked: ${a.updated_at ? new Date(a.updated_at).toLocaleDateString() : "—"}</span>
            </div>
            ${a.notes ? `<div class="body-sm mt-xs" style="color:var(--colors-muted)">📝 NOTES: ${a.notes}</div>` : ""}
          </div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:12px">
          <span class="category-tag">${a.status}</span>
          <div style="display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end"><button class="button-primary unmark-btn" style="height:32px;padding:0 16px;font-size:11px" data-app-id="${a.applied_id}">Remove</button></div>
        </div>
      </div>`).join("");

      list.querySelectorAll(".unmark-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const appId = (btn as HTMLElement).dataset.appId!;
          if (!confirm("Remove from Tracker? The notice will reappear in your feed.")) return;
          try {
            await api.deleteAppliedNotice(appId);
            toast("Removed from Tracker.", "success");
            renderApplied();
          } catch (e: any) { toast(e.message, "error"); }
        });
      });
    } // End of else block

    document.getElementById("btn-sync-gmail")?.addEventListener("click", async (e) => {
      const btn = e.target as HTMLButtonElement;
      const ogText = btn.innerHTML;
      btn.innerHTML = `<div class="spinner"></div> Syncing…`;
      btn.disabled = true;
      try {
        await api.syncGmailApplications(USER_ID);
        renderApplied();
      } catch (err: any) {
        alert(err.message || "Failed to sync Gmail applications");
        btn.innerHTML = ogText;
        btn.disabled = false;
      }
    });
  } catch (e: any) {
    el.innerHTML = `<div class="empty-state"><div class="empty-icon">\u26a0\ufe0f</div><div class="empty-title">${e.message}</div></div>`;
  }
}


// ─── Freelancing Page (Lane 3) ───────────────────────────────────────────────

const FREELANCE_SOURCES = [
  { id: "upwork", label: "Upwork", icon: "" },
  { id: "fiverr", label: "Fiverr", icon: "" },
  { id: "freelancer", label: "Freelancer", icon: "" },
  { id: "guru", label: "Guru", icon: "" },
  { id: "toptal", label: "Toptal", icon: "🟣" },
  { id: "contra", label: "Contra", icon: "🟡" },
  { id: "peopleperhour", label: "PeoplePerHour", icon: "" },
  { id: "arc", label: "Arc.dev", icon: "⚡" },
  { id: "turing", label: "Turing", icon: "🔮" },
  { id: "lemonio", label: "Lemon.io", icon: "🍋" },
  { id: "gunio", label: "Gun.io", icon: "🔫" },
  { id: "99designs", label: "99Designs", icon: "🎨" },
  { id: "dribbble", label: "Dribbble", icon: "🏀" },
  { id: "behance", label: "Behance", icon: "🅱️" },
];

const FL_PIPELINE = [
  { label: "Fetching gigs", icon: "📡" },
  { label: "Normalizing", icon: "🔄" },
  { label: "Deduplicating", icon: "🧹" },
  { label: "Classifying", icon: "🏷️" },
  { label: "Scoring", icon: "" },
  { label: "Storing", icon: "💾" },
];

export async function renderFreelancing() {
  const el = document.getElementById("page-freelancing")!;
  let flSelected = new Set(["upwork", "freelancer"]);
  let activeFlTab: "all" | "saved" | "applied" | "in_progress" = "all";
  let allGigs: any[] = [];

  function flPipelineHTML(step: number): string {
    return `<div class="pipeline" style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">${FL_PIPELINE.map((s, i) => {
      const cls = i < step ? "done" : i === step ? "active" : "";
      return `<div class="pipeline-stage ${cls}">${s.icon} ${s.label}</div>`;
    }).join('<div class="pipeline-arrow">→</div>')}
    </div>`;
  }

  function flScoreRing(score: number): string {
    const pct = Math.round(score * 100);
    return `<div style="background:var(--colors-surface-card);border:1px solid var(--colors-hairline);padding:8px 16px;text-align:center"><div class="title-md" style="color:var(--colors-ink)">${pct}</div><div class="body-sm" style="font-size:9px;color:var(--colors-muted);letter-spacing:1px;text-transform:uppercase">SCORE</div></div>`;
  }

  function budgetBadge(gig: any): string {
    const bd = gig.budget_display || "Budget TBD";
    const verified = gig.payment_verified ? `<span style="color:var(--success);font-size:11px;margin-left:4px" title="Payment Verified"></span>` : "";
    return `<div class="freelance-budget"><span class="budget-tag">${bd}</span>${verified}</div>`;
  }

  function skillTags(skills: string[]): string {
    if (!skills || !skills.length) return "";
    return `<div class="freelance-skills">${skills.slice(0, 5).map(s => `<span class="skill-tag">${s}</span>`
    ).join("")}${skills.length > 5 ? `<span class="skill-tag muted">+${skills.length - 5}</span>` : ""}</div>`;
  }

  function gigCard(gig: any): string {
    const statusLabel = gig.status && gig.status !== "new" ? `<span class="category-tag">${gig.status.replace("_", " ")}</span>` : "";
    const clientInfo = gig.client_rating ? `<span class="client-rating">⭐ ${gig.client_rating.toFixed(1)}</span>` : "";
    const timeline = gig.delivery_time_days ? `<span class="date-pill">${gig.delivery_time_days}d</span>` : "";

    return `<div class="newsroom-article-card" data-gig-id="${gig.id}" style="padding:24px;margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div style="flex:1">
          <div class="title-sm" style="color:var(--colors-ink)">${gig.title || "Untitled Gig"}</div>
          <div class="body-sm mt-xs" style="color:var(--colors-muted)">
            <span style="font-weight:700;color:var(--colors-ink)">${gig.source || "Unknown"}</span>${clientInfo}${timeline}
          </div>
          ${budgetBadge(gig)}
          ${skillTags(gig.required_skills)}
          ${gig.matched_skills?.length ? `<div class="body-sm mt-xs" style="color:var(--colors-ink)">✓ Matched: ${gig.matched_skills.join(", ")}</div>` : ""}
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:12px">
          <div style="display:flex;gap:12px;align-items:center">
            ${statusLabel}
            ${flScoreRing(gig.score || 0)}
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end">
            ${gig.apply_link ? `<a href="${gig.apply_link}" target="_blank" class="button-primary" style="height:32px;padding:0 16px;font-size:11px;line-height:30px">Apply</a>` : ""}
            <button class="button-primary fl-save-btn" style="height:32px;padding:0 16px;font-size:11px" data-id="${gig.id}" data-status="${gig.status}">${gig.status === "saved" ? "Saved" : "Save"}</button>
            <button class="button-primary fl-progress-btn" style="height:32px;padding:0 16px;font-size:11px" data-id="${gig.id}">${gig.status === "in_progress" ? "In Progress" : "Start"}</button>
            <button class="button-primary fl-detail-btn" style="height:32px;padding:0 16px;font-size:11px" data-id="${gig.id}">Score</button>
          </div>
        </div>
      </div>
    </div>`;
  }

  function renderGigList(gigs: any[]) {
    const feed = document.getElementById("fl-feed")!;
    let filtered = gigs;
    if (activeFlTab === "saved") filtered = gigs.filter(g => g.status === "saved");
    else if (activeFlTab === "applied") filtered = gigs.filter(g => g.status === "applied");
    else if (activeFlTab === "in_progress") filtered = gigs.filter(g => g.status === "in_progress");

    if (!filtered.length) {
      feed.innerHTML = `<div class="empty-state"><div class="empty-icon"></div><div class="empty-title">${activeFlTab === "all" ? "No freelance gigs yet" : `No ${activeFlTab.replace("_", " ")} gigs`}</div><div class="empty-sub">${activeFlTab === "all" ? "Select sources and click Fetch to discover freelance opportunities." : "Gigs you track will appear here."}</div></div>`;
      return;
    }

    feed.innerHTML = filtered.map(gigCard).join("");

    // Wire action buttons
    feed.querySelectorAll(".fl-save-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = (btn as HTMLElement).dataset.id!;
        const current = (btn as HTMLElement).dataset.status;
        const newStatus = current === "saved" ? "new" : "saved";
        try {
          await api.updateFreelanceStatus(id, USER_ID, newStatus === "new" ? "dismissed" : "saved");
          toast(newStatus === "saved" ? "Gig saved!" : "Removed from saved", "success");
          await loadGigs();
        } catch (e: any) { toast(e.message, "error"); }
      });
    });

    feed.querySelectorAll(".fl-progress-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = (btn as HTMLElement).dataset.id!;
        try {
          await api.updateFreelanceStatus(id, USER_ID, "in_progress");
          toast("Marked as in progress!", "success");
          await loadGigs();
        } catch (e: any) { toast(e.message, "error"); }
      });
    });

    feed.querySelectorAll(".fl-detail-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = (btn as HTMLElement).dataset.id!;
        try {
          const detail = await api.getFreelanceDetail(id);
          const bd = detail.score_breakdown || {};
          const LABELS: Record<string, string> = {
            skill_match: " Skill Match",
            budget_fit: "💰 Budget Fit",
            task_clarity: " Task Clarity",
            client_quality: "👤 Client Quality",
            deadline_fit: " Deadline Fit",
            project_relevance: "📂 Project Relevance",
          };
          const WEIGHTS: Record<string, number> = {
            skill_match: 30, budget_fit: 20, task_clarity: 15,
            client_quality: 15, deadline_fit: 10, project_relevance: 10,
          };
          const rows = Object.entries(bd).map(([k, v]) => {
            const pct = Math.round((v as number) * 100);
            const label = LABELS[k] || k;
            const w = WEIGHTS[k] || 0;
            return `<tr><td style="padding:6px 12px">${label}</td><td style="padding:6px 12px;text-align:center;font-size:11px;color:var(--text-muted)">${w}%</td><td style="padding:6px 12px;width:140px"><div style="background:var(--bg-tertiary);border-radius:4px;height:8px;overflow:hidden"><div style="width:${pct}%;height:100%;border-radius:4px;background:${pct >= 70 ? 'var(--success)' : pct >= 40 ? 'var(--warning)' : 'var(--danger)'};transition:width .3s ease"></div></div></td><td style="padding:6px 12px;text-align:right;font-weight:600">${pct}%</td></tr>`;
          }).join("");

          openModal(`
            <div class="modal-title">${detail.title}</div><div style="font-size:13px;color:var(--text-secondary);margin-bottom:16px">${detail.organization} · ${detail.source}</div>${detail.freelance_details ? `<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px">${detail.freelance_details.budget_max ? `<span class="budget-tag">💵 $${detail.freelance_details.budget_min || 0}–$${detail.freelance_details.budget_max} ${detail.freelance_details.budget_type || 'fixed'}</span>` : ""}
              ${detail.freelance_details.payment_verified ? '<span class="budget-tag" style="background:rgba(16,185,129,.15);color:#10b981">Payment Verified</span>' : ""}
              ${detail.freelance_details.delivery_time_days ? `<span class="budget-tag">${detail.freelance_details.delivery_time_days} days</span>` : ""}
              ${detail.freelance_details.remote_only ? '<span class="budget-tag">🌍 Remote</span>' : ""}
            </div>` : ""}
            <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:16px"><thead><tr style="border-bottom:1px solid var(--border)"><th style="text-align:left;padding:6px 12px">Factor</th><th style="text-align:center;padding:6px 12px">Weight</th><th style="padding:6px 12px">Bar</th><th style="text-align:right;padding:6px 12px">Score</th></tr></thead><tbody>${rows}</tbody></table><div style="text-align:center;font-size:18px;font-weight:700;margin-bottom:8px">Overall: ${Math.round((detail.score || 0) * 100)}%
            </div>${detail.description ? `<div style="max-height:200px;overflow-y:auto;font-size:12px;color:var(--text-muted);padding:12px;background:var(--bg-tertiary);border-radius:8px;margin-top:12px">${detail.description}</div>` : ""}
          `);
        } catch (e: any) { toast(e.message, "error"); }
      });
    });

    // Update tab counts
    const counts = {
      all: gigs.length,
      saved: gigs.filter(g => g.status === "saved").length,
      applied: gigs.filter(g => g.status === "applied").length,
      in_progress: gigs.filter(g => g.status === "in_progress").length,
    };
    const tabAll = document.getElementById("fl-tab-all");
    const tabSaved = document.getElementById("fl-tab-saved");
    const tabApplied = document.getElementById("fl-tab-applied");
    const tabProgress = document.getElementById("fl-tab-progress");
    if (tabAll) tabAll.textContent = `All (${counts.all})`;
    if (tabSaved) tabSaved.textContent = `Saved (${counts.saved})`;
    if (tabApplied) tabApplied.textContent = `Applied (${counts.applied})`;
    if (tabProgress) tabProgress.textContent = `In Progress (${counts.in_progress})`;
  }

  async function loadGigs() {
    try {
      const gigs = await api.getRankedFreelance(USER_ID, 50);
      allGigs = gigs;
      renderGigList(allGigs);
    } catch (e: any) {
      toast(`Failed to load gigs: ${e.message}`, "error");
    }
  }

  // ── Render the page ────────────────────────────────────────────────────
  // ── Render the page ────────────────────────────────────────────────────
  el.innerHTML = `
    <div>
      <div class="title-md" style="margin-bottom:var(--spacing-md)">FREELANCE HUB</div>
      <div class="model-photo-card" style="padding:24px;margin-bottom:24px">
        <div class="title-sm" style="margin-bottom:12px">FREELANCE SOURCES</div>
        <div class="source-chips" id="fl-source-chips" style="margin-bottom:12px">${FREELANCE_SOURCES.map(s => `<button class="source-chip ${flSelected.has(s.id) ? "selected" : ""}" data-source="${s.id}">${s.icon} ${s.label}</button>`).join("")}</div>
        <div style="display:flex;align-items:center;gap:12px;margin-top:16px">
          <button class="button-primary" id="fl-fetch-btn">FETCH GIGS</button>
          <span id="fl-fetch-status" class="body-sm" style="color:var(--colors-muted)"></span>
        </div>
        <div id="fl-pipeline-wrap" style="display:none;margin-top:16px">${flPipelineHTML(-1)}</div>
      </div>
      <div class="fl-tabs" style="display:flex;gap:8px;margin-bottom:12px">
        <button class="fl-tab active" id="fl-tab-all" data-tab="all">ALL (0)</button>
        <button class="fl-tab" id="fl-tab-saved" data-tab="saved">SAVED (0)</button>
        <button class="fl-tab" id="fl-tab-applied" data-tab="applied">APPLIED (0)</button>
        <button class="fl-tab" id="fl-tab-progress" data-tab="in_progress">IN PROGRESS (0)</button>
      </div>
      <div id="fl-feed"></div>
    </div>`;

  // Wire source chip toggles
  el.querySelectorAll("#fl-source-chips .source-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const src = (chip as HTMLElement).dataset.source!;
      if (flSelected.has(src)) flSelected.delete(src);
      else flSelected.add(src);
      chip.classList.toggle("selected", flSelected.has(src));
    });
  });

  // Wire tab switching
  el.querySelectorAll(".fl-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      el.querySelectorAll(".fl-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      activeFlTab = (tab as HTMLElement).dataset.tab as any;
      renderGigList(allGigs);
    });
  });

  // Wire fetch button
  document.getElementById("fl-fetch-btn")?.addEventListener("click", async () => {
    const btn = document.getElementById("fl-fetch-btn") as HTMLButtonElement;
    const status = document.getElementById("fl-fetch-status")!;
    const pipeWrap = document.getElementById("fl-pipeline-wrap")!;

    if (!flSelected.size) { toast("Select at least one source", "error"); return; }

    btn.disabled = true;
    btn.innerHTML = `<div class="spinner"></div>Fetching…`;
    pipeWrap.style.display = "block";
    status.textContent = "";

    // Animate pipeline
    for (let i = 0; i < FL_PIPELINE.length; i++) {
      pipeWrap.innerHTML = flPipelineHTML(i);
      await new Promise(r => setTimeout(r, 400));
    }

    try {
      const res = await api.fetchFreelanceJobs(USER_ID, Array.from(flSelected));
      pipeWrap.innerHTML = flPipelineHTML(FL_PIPELINE.length);
      toast(`Fetched ${res.fetched} gigs → ${res.ranked} ranked → ${res.saved} saved`, "success");
      status.textContent = `${res.saved} new gigs`;
      await loadGigs();
    } catch (e: any) {
      toast(e.message, "error");
      pipeWrap.style.display = "none";
    } finally {
      btn.disabled = false;
      btn.innerHTML = "⚡ Fetch Gigs";
    }
  });

  // Load existing gigs
  loadGigs();
}
