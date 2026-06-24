const BASE = import.meta.env.BASE_URL + "demo";


async function fetchMock<T>(filename: string): Promise<T> {
  const res = await fetch(`${BASE}/${filename}`);
  if (!res.ok) {
    throw new Error(`Mock file ${filename} not found`);
  }
  return res.json();
}

export const USER_ID = "demo-user-1";

export const api = {
  health: () => fetchMock<{ status: string }>("health.json"),

  getDashboardStats: (userId: string) =>
    fetchMock<Record<string, number>>("dashboard.json"),

  getAnalytics: (userId: string) =>
    fetchMock<any>("dashboard.json"),

  uploadResume: async (userId: string, file: File) => {
    return { success: true };
  },

  parseResume: async (resumeId: string) =>
    ({ profile: { name: "Demo User", skills: ["React", "Python", "TypeScript"] } }),

  getProfile: async (userId: string) =>
    ({ name: "Demo User", preferred_roles: ["Frontend Developer"] }),

  getDrafts: (userId: string) => fetchMock<any[]>("drafts.json"),

  getDraft: async (draftId: string) => ({ id: draftId, subject: "Demo Draft", body: "Hello" }),

  generateDraft: async (userId: string, jobId: string) =>
    ({ id: "draft-demo", subject: "Generated Draft", body: "This is a demo generated draft." }),

  updateDraft: async (draftId: string, update: Record<string, unknown>) =>
    ({ id: draftId, ...update }),

  approveDraft: async (draftId: string) =>
    ({ id: draftId, status: "approved" }),

  sendDraft: async (draftId: string, recipient: string) =>
    ({ id: draftId, status: "sent", recipient }),

  getSentLog: async () => [],

  markApplied: async (payload: any) =>
    ({ success: true, ...payload }),

  getApplications: (userId: string) =>
    fetchMock<any[]>("applied.json"),

  updateApplication: async (applicationId: string, update: any) =>
    ({ id: applicationId, ...update }),

  unmarkApplied: async (applicationId: string) =>
    ({ success: true }),

  syncGmailApplications: async (userId: string) =>
    ({ synced: 0 }),

  
  githubConnect: async (token: string, userId = USER_ID) =>
    ({ success: true }),

  githubStatus: async (userId = USER_ID) =>
    ({ connected: true, github_username: "demo-user", last_synced: new Date().toISOString() }),

  githubSync: async (userId = USER_ID) =>
    ({ status: "success", repos_synced: 3 }),

  githubAnalyze: async (userId = USER_ID) =>
    ({ analyzed: 3 }),

  githubTop5: (role: string, userId = USER_ID) =>
    fetchMock<any>("repos.json"),

  githubRepoDetails: async (repoId: string, role: string) =>
    ({ repo_id: repoId, score: 95, feedback: "Great demo repo" }),

  githubRoles: async () =>
    ({ roles: [{ id: "frontend", label: "Frontend", description: "Frontend Developer" }, { id: "backend", label: "Backend", description: "Backend Developer" }] }),

  
  fetchInternships: async (userId: string, sources: string[]) =>
    ({ fetched: 3, new_matches: 3 }),

  getRankedInternships: (userId: string, limit = 30, sources: string[] = ['companycareers', 'govtportal']) =>
    fetchMock<any[]>("internships.json"),

  getNotice: async (noticeId: string) => ({ id: noticeId, title: "Demo Internship" }),

  projectMatch: async (noticeId: string, userId = USER_ID) =>
    ({ matches: [], notice_keywords: [] }),

  
  markAppliedNotice: async (payload: any) =>
    ({ success: true }),

  getAppliedNotices: async (userId: string) => [],

  updateAppliedNotice: async (appliedId: string, update: any) =>
    ({ success: true }),

  deleteAppliedNotice: async (appliedId: string) =>
    ({ success: true }),

  
  updateProfile: async (userId: string, update: any) =>
    ({ success: true }),

  
  sendToTelegram: async (userId: string, minScore = 4.0, limit = 20) =>
    ({ sent: 1, skipped: 0, chat_id: "demo-chat" }),

  
  gmailStatus: async () =>
    ({ connected: true, email: "demo@gmail.com", days_back: 30 }),

  gmailConnect: async () =>
    ({ success: true }),

  gmailSync: async (userId = USER_ID) =>
    ({ success: true, internship_matches: 0, notices: [] }),

  
  fetchFreelanceJobs: async (userId: string, sources: string[]) =>
    ({ fetched: 0, unique: 0, ranked: 0, saved: 0, top_5: [] }),

  getRankedFreelance: async (userId: string, limit = 30, sources: string[] = []) =>
    [],

  getFreelanceDetail: async (id: string) =>
    ({ id, title: "Demo Freelance Gig" }),

  updateFreelanceStatus: async (id: string, userId: string, status: string) =>
    ({ success: true }),

  getFreelanceStats: async (userId: string) =>
    ({ total_gigs: 0, saved: 0, applied: 0, in_progress: 0 }),

  
  getSources: async () =>
    [
      { name: "companycareers", category: "internship", enabled: true },
      { name: "govtportal", category: "internship", enabled: true }
    ],

  getSourcesByCategory: async (category: string) =>
    [],

  toggleSource: async (sourceName: string, enabled: boolean) =>
    ({ success: true }),
};
