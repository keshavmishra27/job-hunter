import pathlib
import importlib.util


def load_module_from_path(path):
    spec = importlib.util.spec_from_file_location('internship_scorer', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_score_notice_basic_range():
    mod = load_module_from_path(pathlib.Path(__file__).parent.parent / 'backend' / 'modules' / 'internship_scorer.py')

    # minimal notice + profile to assert scoring runs and returns numeric score
    notice = {
        'title': 'Backend Intern',
        'company': 'Acme',
        'location': 'Bengaluru',
        'eligibility': ['pre-final year', '3rd year'],
        'skills': ['python', 'rest'],
        'deadline': None,
    }

    profile = {'skills': ['python', 'sql'], 'location': 'Bengaluru'}

    res = mod.score_notice_detailed(notice, profile)
    # API returns a dict with numeric 'score'
    assert isinstance(res, dict)
    score = res.get('score')
    assert isinstance(score, (int, float))
    assert 0.0 <= score <= 10.0
