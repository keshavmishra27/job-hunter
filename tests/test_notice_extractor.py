import pathlib
import importlib.util
from types import ModuleType


def load_fixture(name: str) -> str:
    p = pathlib.Path(__file__).parent / 'fixtures' / name
    return p.read_text(encoding='utf-8')


def load_module_from_path(path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location('notice_extractor', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_extract_from_html_basic_fields():
    html = load_fixture('sample_notice.html')
    mod = load_module_from_path(pathlib.Path(__file__).parent.parent / 'backend' / 'modules' / 'notice_extractor.py')
    notice = mod.extract_from_html(html)

    assert 'Software Engineering Intern' in notice.get('title', '')
    # company may not be a first-class field; ensure raw_text contains company name
    assert 'Acme' in notice.get('raw_text', '')
    assert 'Bengaluru' in (notice.get('location') or '')
    assert '30,000' in (notice.get('stipend') or '') or '30000' in (notice.get('stipend') or '')
    assert any('3rd' in s or 'pre-final' in s.lower() for s in [notice.get('eligibility_text') or ''])
    assert isinstance(notice.get('links'), list)
    # ensure we captured the official portal link
    links = [l.get('url', '') for l in notice.get('links', [])]
    assert any('careers.example.com' in u for u in links)
