import { renderHome, renderDashboard, renderProfile, renderJobs, renderDrafts, renderSent, renderApplied, renderRepos, renderInternships, renderFreelancing, closeModal } from "./pages/pages";
import { initAnimation } from "./animation";
import { initLoadingAnimation, toggleLoadingAnimation } from "./loadingAnimation";

const PAGE_MAP: Record<string, { title: string; subtitle: string; render: () => Promise<void> }> = {
  dashboard: { title: "Dashboard", subtitle: "Overview of your job hunt", render: renderDashboard },
  profile:   { title: "My Profile", subtitle: "Resume, skills, and preferences", render: renderProfile },
  jobs:      { title: "Opportunity Engine", subtitle: "Autopilot semantic matching and ranking", render: renderJobs },
  internships: { title: "Internship Notices", subtitle: "Raw internship notices & alerts", render: renderInternships },
  drafts:    { title: "Autopilot Queue", subtitle: "Review generated drafts and queue applications", render: renderDrafts },
  applied:   { title: "Tracker", subtitle: "Track autopilot lifecycle and interview stages", render: renderApplied },
  repos:     { title: "Repo Intelligence", subtitle: "GitHub portfolio ranked for your target role", render: renderRepos },
  home:      { title: "Welcome", subtitle: "Get started with Job Hunter", render: renderHome },
};

async function navigate(page: string) {
  // Show Loading Animation
  toggleLoadingAnimation(true);

  document.querySelectorAll(".nav-item").forEach((el) => el.classList.remove("active"));
  document.querySelectorAll(".page").forEach((el) => el.classList.remove("active"));

  const navBtn = document.getElementById(`nav-${page}`);
  const pageEl = document.getElementById(`page-${page}`);
  if (!navBtn || !pageEl) {
    toggleLoadingAnimation(false);
    return;
  }

  navBtn.classList.add("active");
  pageEl.classList.add("active");

  const meta = PAGE_MAP[page];
  const titleEl = document.getElementById("page-title");
  if (titleEl) titleEl.textContent = meta.title;
  const subtitleEl = document.getElementById("page-subtitle");
  if (subtitleEl) subtitleEl.textContent = meta.subtitle;

  // Let loading screen show for a minimum duration to be visible
  await new Promise(r => setTimeout(r, 600));

  await meta.render();

  // Hide Loading Animation
  toggleLoadingAnimation(false);
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

initLoadingAnimation('loading-screen');
initAnimation();
navigate("home");
