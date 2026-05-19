"""Quick test of the graduation year fix."""
from backend.modules.internship_scorer import _year_fit_score, score_notice_detailed

notice = {
    "title": "Amazon is hiring SDE I",
    "description": "For 2024, 2025 gards Location: Bangalore Apply Now",
    "eligibility_text": None,
}

profile_2028 = {"graduation_year": 2028, "preferred_roles": ["SDE", "Software Engineer"], "skills": [], "location_rule": {}, "preferred_companies": []}
profile_2024 = {"graduation_year": 2024, "preferred_roles": ["SDE"], "skills": [], "location_rule": {}, "preferred_companies": []}
profile_none = {"graduation_year": None, "preferred_roles": ["SDE"], "skills": [], "location_rule": {}, "preferred_companies": []}

print("=== Year Fit Scores ===")
print(f"2028 grad (should be 0.0): {_year_fit_score(notice, profile_2028)}")
print(f"2024 grad (should be 1.0): {_year_fit_score(notice, profile_2024)}")
print(f"No grad year (should be 1.0): {_year_fit_score(notice, profile_none)}")
print()

print("=== Full Score for 2028 grad ===")
result = score_notice_detailed(notice, profile_2028)
score = result["score"]
breakdown = result["breakdown"]
print(f"Total score: {score}/10")
for k, v in breakdown.items():
    print(f"  {k}: {round(v * 100)}%")
print()

print("=== Full Score for 2024 grad ===")
result2 = score_notice_detailed(notice, profile_2024)
score2 = result2["score"]
print(f"Total score: {score2}/10")
for k, v in result2["breakdown"].items():
    print(f"  {k}: {round(v * 100)}%")
