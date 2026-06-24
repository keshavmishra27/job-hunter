content = r'''

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
'''

with open(r"d:\kfiles\job-hunter\frontend\src\pages\pages.ts", "a", encoding="utf-8") as f:
    f.write(content)

                                                                             
with open(r"d:\kfiles\job-hunter\frontend\src\pages\pages.ts", "r", encoding="utf-8") as f:
    src = f.read()

                                                                              
src = src.replace(
    'let selected = new Set(["internshala"]);\n\n  el.innerHTML',
    'let selected = new Set(["internshala"]);\n  let showApplied = false;\n\n  el.innerHTML'
)

                                                           
old_btn_block = '<button class="btn btn-primary" id="fetch-btn">\u26a1 Fetch &amp; Rank</button>\n      <span id="fetch-status" style="font-size:13px;color:var(--text-secondary);margin-left:12px"></span>'
new_btn_block = '''<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
        <button class="btn btn-primary" id="fetch-btn">\u26a1 Fetch &amp; Rank</button>
        <label style="display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text-secondary);cursor:pointer">
          <input type="checkbox" id="show-applied-toggle" style="accent-color:var(--accent);width:15px;height:15px" />
          Show already applied
        </label>
        <span id="fetch-status" style="font-size:13px;color:var(--text-secondary)"></span>
      </div>'''
src = src.replace(old_btn_block, new_btn_block)

                                                            
old_chip_end = '    });\n  });\n\n  document.getElementById("fetch-btn")'
new_chip_end = '''    });
  });

  document.getElementById("show-applied-toggle")?.addEventListener("change", (e) => {
    showApplied = (e.target as HTMLInputElement).checked;
    loadJobs();
  });

  document.getElementById("fetch-btn")'''
src = src.replace(old_chip_end, new_chip_end)

                                        
src = src.replace(
    'const jobs = await api.getRankedJobs(USER_ID);',
    'const jobs = await api.getRankedJobs(USER_ID, 30, showApplied);'
)

                                                           
old_job_title = '<div class="job-title">${j.title}</div>'
new_job_title = '<div class="job-title">${j.title} ${j.is_applied ? \'<span class="badge badge-applied">\u2713 Applied</span>\' : \'\'}</div>'
src = src.replace(old_job_title, new_job_title)

old_draft_btn = '<button class="btn btn-primary btn-sm gen-draft-btn" data-job-id="${j.job_id}">Draft \u2709\ufe0f</button>\n            </div>'
new_draft_btn = '''<button class="btn btn-primary btn-sm gen-draft-btn" data-job-id="${j.job_id}">Draft \u2709\ufe0f</button>
              ${!j.is_applied ? `<button class="btn btn-success btn-sm mark-applied-btn" data-job-id="${j.job_id}">\u2713 Applied</button>` : \'\'}
            </div>'''
src = src.replace(old_draft_btn, new_draft_btn)

                                                                
old_gen_end = '''      });
    } catch (e: any) {
      list.innerHTML = `<div class="empty-state"><div class="empty-icon">\u26a0\ufe0f</div><div class="empty-title">${e.message}</div></div>`;
    }
  }

  function showJobModal'''
new_gen_end = '''      });

      list.querySelectorAll(".mark-applied-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const jobId = (btn as HTMLElement).dataset.jobId!;
          btn.textContent = "\u2026";
          (btn as HTMLButtonElement).disabled = true;
          try {
            await api.markApplied({ user_id: USER_ID, job_id: jobId, status: "applied" });
            toast("Marked as applied! Job removed from feed.", "success");
            loadJobs();
          } catch (e: any) {
            toast(e.message, "error");
            btn.textContent = "\u2713 Applied";
            (btn as HTMLButtonElement).disabled = false;
          }
        });
      });
    } catch (e: any) {
      list.innerHTML = `<div class="empty-state"><div class="empty-icon">\u26a0\ufe0f</div><div class="empty-title">${e.message}</div></div>`;
    }
  }

  function showJobModal'''
src = src.replace(old_gen_end, new_gen_end)

with open(r"d:\kfiles\job-hunter\frontend\src\pages\pages.ts", "w", encoding="utf-8") as f:
    f.write(src)

print("Done patching pages.ts")
