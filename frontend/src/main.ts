import { renderDashboard, renderProfile, renderJobs, renderDrafts, renderSent, renderApplied, closeModal } from "./pages/pages";

const PAGE_MAP: Record<string, { title: string; subtitle: string; render: () => Promise<void> }> = {
  dashboard: { title: "Dashboard", subtitle: "Overview of your job hunt", render: renderDashboard },
  profile:   { title: "My Profile", subtitle: "Resume, skills, and preferences", render: renderProfile },
  jobs:      { title: "Ranked Jobs", subtitle: "Best-matched internships for you", render: renderJobs },
  drafts:    { title: "Review Queue", subtitle: "Edit, approve, and send outreach drafts", render: renderDrafts },
  sent:      { title: "Sent Log", subtitle: "Track what you've sent", render: renderSent },
  applied:   { title: "Applied Jobs", subtitle: "Track every application you've sent", render: renderApplied },
};

function navigate(page: string) {
  document.querySelectorAll(".nav-item").forEach((el) => el.classList.remove("active"));
  document.querySelectorAll(".page").forEach((el) => el.classList.remove("active"));

  const navBtn = document.getElementById(`nav-${page}`);
  const pageEl = document.getElementById(`page-${page}`);
  if (!navBtn || !pageEl) return;

  navBtn.classList.add("active");
  pageEl.classList.add("active");

  const meta = PAGE_MAP[page];
  document.getElementById("page-title")!.textContent = meta.title;
  document.getElementById("page-subtitle")!.textContent = meta.subtitle;

  meta.render();
}

document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => {
    const page = (btn as HTMLElement).dataset.page;
    if (page) navigate(page);
  });
});

document.getElementById("modal-close")?.addEventListener("click", closeModal);
document.getElementById("modal-overlay")?.addEventListener("click", (e) => {
  if ((e.target as HTMLElement).id === "modal-overlay") closeModal();
});

navigate("dashboard");
