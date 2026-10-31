"""Unit + integration tests for the static site build."""
import json, pathlib, re, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = [p for p in ROOT.rglob('index.html') if '.git' not in p.parts and 'issues/' not in str(p.relative_to(ROOT)).replace('issues/index.html', '')]

def test_build_runs():
    r = subprocess.run([sys.executable, str(ROOT/'tools/build.py')], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

def test_nav_has_special_reports_on_all_layout_pages():
    for p in ROOT.rglob('index.html'):
        t = p.read_text()
        if '<ul id="nav">' in t:
            assert re.search(r'href="/special-reports/"[^>]*>Special Reports</a>', t), p

def test_reports_listed_and_cross_linked():
    reports = json.load(open(ROOT/'content/special-reports.json'))
    idx = (ROOT/'special-reports/index.html').read_text()
    assert len(reports) >= 4
    for r in reports:
        assert f'/special-reports/{r["slug"]}/' in idx
        page = (ROOT/f'special-reports/{r["slug"]}/index.html').read_text()
        for o in reports:
            if o is not r: assert f'/special-reports/{o["slug"]}/' in page

def test_only_special_reports_on_tab():
    idx = (ROOT/'special-reports/index.html').read_text()
    assert '/p/' not in re.sub(r'<header.*?</header>|<footer.*?</footer>', '', idx, flags=re.S)

def test_images_exist_and_are_credited():
    for f in (ROOT/'content/special-reports').glob('*.html'):
        h = f.read_text()
        imgs = re.findall(r'<img src="([^"]+)"', h)
        assert len(imgs) >= 3, f
        for src in imgs: assert (ROOT/src.lstrip('/')).exists(), src
        assert h.count('<figure>') == h.count('<figcaption>'), f
        for cap in re.findall(r'<figcaption>(.*?)</figcaption>', h, re.S):
            assert re.search(r'Photo:|Chart by|logo|AI-generated image', cap), cap

def test_sitemap_lists_reports():
    sm = (ROOT/'sitemap.xml').read_text()
    assert '/special-reports/' in sm
