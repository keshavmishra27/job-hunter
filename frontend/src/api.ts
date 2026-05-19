const BASE = "/api";

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export const USER_ID = "demo-user-1";

export const api = {
  health: () => req<{ status: string }>("/health"),

  getDashboardStats: (userId: string) =>
    req<Record<string, number>>(`/dashboard/stats/${userId}`),

  uploadResume: (userId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return fetch(`${BASE}/profile/upload-resume?user_id=${userId}`, {
      method: "POST",
      body: form,
    }).then((r) => r.json());
  },

  parseResume: (resumeId: string) =>
    req<{ profile: Record<string, unknown> }>(`/profile/parse/${resumeId}`, { method: "POST" }),

  getProfile: (userId: string) =>
    req<Record<string, unknown>>(`/profile/${userId}`),

  fetchJobs: (userId: string, sources: string[]) =>
    req<{ fetched: number; new_unique: number; ranked: number }>(`/jobs/fetch?user_id=${userId}&${sources.map((s) => `sources=${s}`).join("&")}`, { method: "POST" }),

  getRankedJobs: (userId: string, limit = 30, includeApplied = false, sources: string[] = ["internshala", "indeed", "naukri"]) =>
    req<any[]>(`/jobs/ranked/${userId}?limit=${limit}&include_applied=${includeApplied}&${sources.map((s) => `sources=${s}`).join("&")}`),

  getDrafts: (userId: string) => req<any[]>(`/drafts/${userId}`),

  getDraft: (draftId: string) => req<any>(`/drafts/detail/${draftId}`),

  generateDraft: (userId: string, jobId: string) =>
    req<any>(`/drafts/generate/${userId}/${jobId}`, { method: "POST" }),

  updateDraft: (draftId: string, update: Record<string, unknown>) =>
    req<any>(`/drafts/${draftId}`, {
      method: "PATCH",
      body: JSON.stringify(update),
    }),

  approveDraft: (draftId: string) =>
    req<any>(`/drafts/approve/${draftId}`, { method: "POST" }),

  sendDraft: (draftId: string, recipient: string) =>
    req<any>("/send/", {
      method: "POST",
      body: JSON.stringify({ draft_id: draftId, recipient_email: recipient }),
    }),

  getSentLog: () => req<any[]>("/send/log"),

  markApplied: (payload: {
    user_id: string;
    job_id: string;
    draft_id?: string;
    status?: string;
    source?: string;
    follow_up_date?: string;
    notes?: string;
  }) =>
    req<any>("/applications/mark", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getApplications: (userId: string) =>
    req<any[]>(`/applications/${userId}`),

  updateApplication: (applicationId: string, update: { status?: string; follow_up_date?: string; notes?: string }) =>
    req<any>(`/applications/${applicationId}`, {
      method: "PATCH",
      body: JSON.stringify(update),
    }),

  unmarkApplied: (applicationId: string) =>
    req<any>(`/applications/${applicationId}`, { method: "DELETE" }),

  // --- GitHub Intelligence ---
  githubConnect: (token: string, userId = USER_ID) =>
    req<any>("/github/connect", {
      method: "POST",
      body: JSON.stringify({ token, user_id: userId }),
    }),

  githubStatus: (userId = USER_ID) =>
    req<{ connected: boolean; github_username?: string; last_synced?: string }>(
      `/github/status?user_id=${userId}`
    ),

  githubSync: (userId = USER_ID) =>
    req<{ status: string; repos_synced: number }>(
      `/github/sync?user_id=${userId}`, { method: "POST" }
    ),

  githubAnalyze: (userId = USER_ID) =>
    req<{ analyzed: number }>(`/github/analyze?user_id=${userId}`, { method: "POST" }),

  githubTop5: (role: string, userId = USER_ID) =>
    req<any>(`/github/top5?role=${role}&user_id=${userId}`),

  githubRepoDetails: (repoId: string, role: string) =>
    req<any>(`/github/repos/${repoId}/details?role=${role}`),

  githubRoles: () =>
    req<{ roles: Array<{ id: string; label: string; description: string }> }>("/github/roles"),
  // --- Internships endpoints
  fetchInternships: (userId: string, sources: string[]) =>
    req<any>(`/internships/fetch?user_id=${userId}&${sources.map((s) => `sources=${s}`).join("&")}`, { method: "POST" }),

  getRankedInternships: (userId: string, limit = 30, sources: string[] = ['companycareers', 'govtportal']) =>
    req<any[]>(`/internships/ranked/${userId}?limit=${limit}&${sources.map((s) => `sources=${s}`).join("&")}`),

  getNotice: (noticeId: string) => req<any>(`/internships/${noticeId}`),

  // applied notices (save/view/dismiss)
  markAppliedNotice: (payload: { user_id: string; notice_id: string; status?: string; notes?: string }) =>
    req<any>(`/applied/mark`, { method: "POST", body: JSON.stringify(payload) }),

  getAppliedNotices: (userId: string) => req<any[]>(`/applied/${userId}`),

  updateAppliedNotice: (appliedId: string, update: { status?: string; notes?: string }) =>
    req<any>(`/applied/${appliedId}`, { method: "PATCH", body: JSON.stringify(update) }),

  deleteAppliedNotice: (appliedId: string) => req<any>(`/applied/${appliedId}`, { method: "DELETE" }),
};
