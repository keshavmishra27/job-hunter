import pathlib
import importlib.util


def load_module_from_path(path):
    spec = importlib.util.spec_from_file_location('portal_link_extractor', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_strip_tracking_params_and_classify():
    mod = load_module_from_path(pathlib.Path(__file__).parent.parent / 'backend' / 'modules' / 'portal_link_extractor.py')

    raw_links = [
        {'url': 'https://careers.example.com/apply?utm_source=newsletter&utm_medium=email&ref=abc'},
        {'url': 'https://forms.gle/example?usp=sharing'},
        {'url': 'https://example.com/redirect?target=https%3A%2F%2Fcareers.example.com%2Fjob%2F123'},
    ]

                                                            
    import asyncio

    cleaned = asyncio.run(mod.clean_and_resolve_links(raw_links, base_url=None, follow=False))

    urls = [c['url'] for c in cleaned]
    assert any('careers.example.com/apply' in u for u in urls)
    assert any('forms.gle' in u for u in urls)
