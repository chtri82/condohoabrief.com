#!/usr/bin/env python3
"""Build the static Florida Condo & HOA Brief site from content/ + config.json.
Usage: python3 tools/build.py   (add an issue: drop its HTML in content/issues/<slug>.html and an entry in content/issues.json)"""
import json, re, html, os, pathlib, datetime, urllib.request, hashlib
from email.utils import format_datetime
ROOT = pathlib.Path(__file__).resolve().parent.parent
C = json.load(open(ROOT/'config.json'))
ISSUES = sorted(json.load(open(ROOT/'content/issues.json')), key=lambda i: i['date'], reverse=True)
TOPICS = json.load(open(ROOT/'content/topics.json'))
E = html.escape
def dt(i): return datetime.datetime.fromisoformat(i['date'].replace('Z', '+00:00'))
def nice(i): return dt(i).astimezone(datetime.timezone(datetime.timedelta(hours=-4))).strftime('%B %-d, %Y')
def slugify(s): return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', re.sub(r'^\d+\.\s*', '', s.lower()))).strip('-')

def localize_images(h, slug):
    """Download any remote images into assets/img/issues/<slug>/ so we never hotlink beehiiv."""
    d = ROOT/'assets/img/issues'/slug
    def rep(m):
        url = m.group(1)
        if not url.startswith('http'): return m.group(0)
        ext = os.path.splitext(url.split('?')[0])[1][:5] or '.jpg'
        name = hashlib.sha1(url.encode()).hexdigest()[:12] + ext
        d.mkdir(parents=True, exist_ok=True)
        if not (d/name).exists():
            urllib.request.urlretrieve(url, d/name)
        return f'src="/assets/img/issues/{slug}/{name}"'
    return re.sub(r'src="([^"]+)"', rep, h)

def clean(h, slug):
    h = re.sub(r'\s(data-[\w-]+|class|target)="[^"]*"', '', h)
    h = h.replace('rel="noopener noreferrer nofollow"', 'rel="noopener"')
    h = re.sub(r'<figcaption>\s*</figcaption>', '', h)
    h = re.sub(r'<figure>\s*(<blockquote>.*?</blockquote>)\s*</figure>', r'\1', h, flags=re.S)
    h = re.sub(r'<p><strong>[^<]*</strong> <em>By [^<]*</em></p>', '', h, count=1)  # byline shown in page header
    h = re.sub(r'<h2>(.*?)</h2>', lambda m: f'<h2 id="{slugify(html.unescape(re.sub("<[^>]+>","",m.group(1))))}">{m.group(1)}</h2>', h)
    h = localize_images(h, slug)
    return h.replace('<blockquote>', '<blockquote class="note">').replace('<hr>', '<hr class="rule">')

def headings(h): return [(m.group(1), html.unescape(re.sub('<[^>]+>', '', m.group(2)))) for m in re.finditer(r'<h2 id="([^"]+)">(.*?)</h2>', h)]
def excerpts(h):
    out = []
    for m in re.finditer(r'<h2 id="([^"]+)">(.*?)</h2>\s*<p>(.*?)</p>', h, re.S):
        t = html.unescape(re.sub('<[^>]+>', '', m.group(3))).strip()
        out.append((m.group(1), html.unescape(re.sub(r'<[^>]+>|^\d+\.\s*', '', m.group(2))), (t[:180].rsplit(' ', 1)[0] + '…') if len(t) > 180 else t))
    return out

NAV = [('Home', '/'), ('Issues', '/issues/'), ('About', '/about/'), ('Sponsor', '/sponsor/')]
def layout(title, body, desc, path, canonical=None, extra_head=''):
    nav = ''.join(f'<li><a href="{u}"{" aria-current=page" if (u == path or (u != "/" and path.startswith(u))) else ""}>{n}</a></li>' for n, u in NAV)
    canon = canonical or C['site_url'] + path
    today = datetime.date.today().strftime('%A, %B %-d, %Y')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{canon}">
<meta property="og:site_name" content="{E(C['site_name'])}"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canon}">
<link rel="alternate" type="application/rss+xml" title="{E(C['site_name'])}" href="/feed.xml">
<link rel="icon" href="/assets/img/mark.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/style.css">{extra_head}</head>
<body><a class="skip" href="#main">Skip to content</a>
<div class="topbar"><div class="wrap"><span>Florida condo &amp; HOA law, from the source</span><span>Facts first · Every claim cited · Free</span></div></div>
<header class="masthead"><div class="wrap mast-inner">
<a class="brand" href="/"><img src="/assets/img/mark.svg" width="46" height="46" alt=""><span><b>Florida Condo &amp; HOA</b><em>Brief</em></span></a>
<button class="menu" aria-expanded="false" aria-controls="nav" onclick="var n=document.getElementById('nav');this.setAttribute('aria-expanded',n.classList.toggle('open'))">Menu</button>
<nav aria-label="Primary"><ul id="nav">{nav}<li><a class="btn" href="/subscribe/">Subscribe</a></li></ul></nav></div></header>
<main id="main">{body}</main>
<footer class="foot"><div class="wrap foot-grid">
<div><a class="brand brand-foot" href="/"><img src="/assets/img/mark.svg" width="38" height="38" alt=""><span><b>Florida Condo &amp; HOA</b><em>Brief</em></span></a>
<p>Published by <a href="{C['publisher_url']}">{E(C['publisher'])}</a>. Informational, not legal advice.</p></div>
<div><h4>Read</h4><ul><li><a href="/issues/">All issues</a></li><li><a href="/feed.xml">RSS feed</a></li><li><a href="/subscribe/">Subscribe free</a></li></ul></div>
<div><h4>About</h4><ul><li><a href="/about/">About &amp; standards</a></li><li><a href="/sponsor/">Sponsor ({E(C['sponsor_price'])})</a></li></ul></div>
<div><h4>Contact</h4><ul><li>Editor: <a href="mailto:{C['editor_email']}">{C['editor_email']}</a></li><li>Advertising: <a href="mailto:{C['advertise_email']}">{C['advertise_email']}</a></li><li><a href="{C['linkedin_url']}" target="_blank" rel="noopener">LinkedIn</a></li></ul></div>
</div><div class="wrap copy">© {datetime.date.today().year} {E(C['publisher'])}</div></footer></body></html>'''

def cover(i, size='lg'):
    if i.get('thumbnail'): return f'<img class="cover-img" src="{i["thumbnail"]}" alt="">'
    return f'<div class="cover cover-{size}" aria-hidden="true"><span class="cover-no">Issue #{i["number"]}</span><span class="cover-fl"></span><span class="cover-date">{nice(i)}</span></div>'

def subscribe_block(head='Get the Brief free in your inbox', text='Plain-English Florida condo and HOA law, with a link to the source for every fact.'):
    return f'<aside class="sub"><div><h3>{head}</h3><p>{text}</p></div><a class="btn btn-lg" href="/subscribe/">Subscribe free →</a></aside>'

def write(path, s):
    p = ROOT/path.lstrip('/'); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(s)

bodies = {}
for i in ISSUES:
    raw = (ROOT/'content/issues'/f"{i['slug']}.html").read_text()
    bodies[i['slug']] = clean(raw, i['slug'])
    i['heads'] = headings(bodies[i['slug']])
    i['url'] = f"/issues/{i['slug']}/"

# Issue pages
for n, i in enumerate(ISSUES):
    toc = ''.join(f'<li><a href="#{a}">{E(t)}</a></li>' for a, t in i['heads'])
    newer = ISSUES[n-1] if n > 0 else None; older = ISSUES[n+1] if n + 1 < len(ISSUES) else None
    pn = ''.join([f'<a href="{older["url"]}">← {E(older["title"])}</a>' if older else '<span></span>', f'<a href="{newer["url"]}">{E(newer["title"])} →</a>' if newer else ''])
    body = f'''<article class="issue wrap">
<header class="issue-head"><p class="kicker"><a href="/issues/">Issues</a> · Issue #{i["number"]}</p><h1>{E(i["title"])}</h1><p class="dek">{E(i["subtitle"])}</p>
<p class="byline">By {E(i["author"])}, Editor · <time datetime="{i["date"]}">{nice(i)}</time></p></header>
<div class="issue-grid"><div class="prose">{bodies[i["slug"]]}</div>
<aside class="issue-side"><div class="toc"><h4>In this issue</h4><ol>{toc}</ol></div>{subscribe_block("Get the next issue", "Free. Unsubscribe anytime.")}</aside></div>
<nav class="prevnext">{pn}</nav></article>'''
    write(f"issues/{i['slug']}/index.html", layout(f"{i['title']} | {C['site_name']}", body, i['subtitle'], i['url']))

# Archive
cards = ''.join(f'''<article class="arch-item"><a href="{i["url"]}">{cover(i,"sm")}</a><div><p class="kicker">Issue #{i["number"]} · <time datetime="{i["date"]}">{nice(i)}</time></p>
<h2><a href="{i["url"]}">{E(i["title"])}</a></h2><p class="dek">{E(i["subtitle"])}</p><ul class="heads">{"".join(f'<li><a href="{i["url"]}#{a}">{E(t)}</a></li>' for a,t in i["heads"])}</ul></div></article>''' for i in ISSUES)
write('issues/index.html', layout(f"All issues | {C['site_name']}", f'''<section class="page-head"><div class="wrap"><p class="kicker">Archive</p><h1>All issues</h1><p class="dek">Every issue of the Brief, newest first. {len(ISSUES)} published so far.</p></div></section>
<section class="wrap arch">{cards}</section><section class="wrap">{subscribe_block()}</section>''', 'Every issue of the Florida Condo & HOA Brief.', '/issues/'))

# Home
L = ISSUES[0]
lead_heads = ''.join(f'<li><a href="{L["url"]}#{a}">{E(t)}</a></li>' for a, t in L["heads"] if "sponsor" not in a)
more = ''.join(f'''<article class="card-story"><p class="kicker">From Issue #{L["number"]}</p><h3><a href="{L["url"]}#{a}">{E(t)}</a></h3><p>{E(x)}</p><a class="more" href="{L["url"]}#{a}">Read more →</a></article>''' for a, t, x in excerpts(bodies[L["slug"]]) if 'sponsor' not in a)
recent = ''.join(f'''<article class="card-issue"><a href="{i["url"]}">{cover(i,"sm")}</a><p class="kicker">Issue #{i["number"]} · {nice(i)}</p><h3><a href="{i["url"]}">{E(i["title"])}</a></h3><p>{E(i["subtitle"])}</p></article>''' for i in ISSUES[1:7])
by_topic = lambda k: [i for i in ISSUES if k in i.get('topics', [])]
topics = ''.join(f'''<article class="topic"><h3>{E(t["label"])}</h3><p>{E(t["summary"])}</p><ul>{"".join(f'<li><a href="{i["url"]}#{t["anchor"]}">{E(i["title"])}</a> <span>{nice(i)}</span></li>' for i in by_topic(t["key"])[:3])}</ul></article>''' for t in TOPICS)
deadlines = '''<li><b>Dec 31, 2026</b> SIRS due "in no event" later than this date if the building's milestone inspection is due on or before it</li>
<li><b>Nov 3, 2026</b> General election; committee assignments for condo and HOA bills may change after it</li>
<li><b>Mar 2, 2027</b> 2027 regular session of the Florida Legislature starts</li>'''
home = f'''<section class="lead wrap">
<article class="lead-story"><a class="lead-art" href="{L["url"]}">{cover(L)}</a>
<div class="lead-text"><p class="kicker">Latest issue · Issue #{L["number"]} · {nice(L)}</p><h1><a href="{L["url"]}">{E(L["title"])}</a></h1><p class="dek">{E(L["subtitle"])}</p>
<p class="byline">By {E(L["author"])}, Editor</p><a class="btn btn-lg" href="{L["url"]}">Read the issue →</a></div></article>
<aside class="lead-side"><h2 class="sec-label">In this issue</h2><ol class="heads-big">{lead_heads}</ol>
<h2 class="sec-label">Dates to know</h2><ul class="dates">{deadlines}</ul><p class="src-note">From Issue #{L["number"]}, with statute citations in the issue.</p></aside></section>
<section class="wrap"><div class="sec-head"><h2 class="sec-label">Top stories</h2><a href="{L["url"]}">Full issue →</a></div><div class="recent">{more}</div></section>
<section class="wrap"><div class="sec-head"><h2 class="sec-label">Topics we cover</h2><a href="/issues/">All issues →</a></div><div class="topics">{topics}</div></section>
<section class="wrap">{subscribe_block()}</section>
<section class="wrap"><div class="sec-head"><h2 class="sec-label">Recent issues</h2><a href="/issues/">Archive →</a></div>{f'<div class="recent">{recent}</div>' if recent else f'<p class="src-note">Issue #{L["number"]} is our first. New issues will be listed here and in the <a href="/issues/">archive</a>.</p>'}</section>'''
write('index.html', layout(f"{C['site_name']}: {C['tagline']}", home, 'A free newsletter explaining Florida condo and HOA laws, rules and deadlines in plain English, with links to the original sources.', '/'))

# About / standards
write('about/index.html', layout(f"About | {C['site_name']}", f'''<section class="page-head"><div class="wrap"><p class="kicker">About</p><h1>About the Brief</h1><p class="dek">What changed, what's due, and how owners, board members and managers can take part in their communities, for condos (Chapter 718) and HOAs (Chapter 720) alike.</p></div></section>
<section class="wrap prose narrow"><h2>Our standards</h2><ul>
<li>Facts first. We report what the law, the records and officials say, and we cite them.</li>
<li>Objective. We present the facts and the authorities' statements and let readers draw their own conclusions.</li>
<li>We are nonpartisan, take no position on legislation, and endorse no candidates.</li>
<li>No invented numbers. If we can't source it, we don't print it.</li>
<li>We use video only when we can confirm it is authentic and not AI-generated or manipulated.</li>
<li>Sponsor messages are clearly labeled and kept separate from coverage.</li></ul>
<h2>Informational, not legal advice</h2><p>This newsletter summarizes Florida statutes and official sources in plain English. It is not legal advice and does not create an attorney-client relationship. Your declaration, bylaws and specific facts matter. For decisions affecting your association, consult a Florida-licensed attorney or the <a href="https://www2.myfloridalicense.com/condos-timeshares-mobile-homes/">DBPR Division of Condominiums, Timeshares and Mobile Homes</a>.</p>
<h2>Who we are</h2><p>The Brief is published by <a href="{C['publisher_url']}">{E(C['publisher'])}</a>. Editor: {E(ISSUES[-1]["author"])}.</p>
<h2>Contact</h2><p>Tips, questions and corrections: <a href="mailto:{C['editor_email']}">{C['editor_email']}</a>. Please include a link to the source.</p>
{subscribe_block()}</section>''', 'About the Florida Condo & HOA Brief and its editorial standards.', '/about/'))

# Sponsor
write('sponsor/index.html', layout(f"Sponsor | {C['site_name']}", f'''<section class="page-head"><div class="wrap"><p class="kicker">Sponsor</p><h1>Sponsor the Brief</h1><p class="dek">Reach Florida condo and HOA owners, board members and managers.</p></div></section>
<section class="wrap prose narrow"><p class="price"><b>{E(C['sponsor_price'])}</b></p><p>Each issue carries one clearly labeled "Florida sponsor" message, kept separate from our coverage. Sponsors have no say over what we report.</p>
<p><a class="btn btn-lg" href="mailto:{C['advertise_email']}?subject=Sponsoring%20the%20Florida%20Condo%20%26%20HOA%20Brief">Email {C['advertise_email']}</a></p></section>''', 'Sponsor the Florida Condo & HOA Brief.', '/sponsor/'))

# Subscribe: the ONE place the signup URL is used (config.json -> subscribe_url)
write('subscribe/index.html', layout(f"Subscribe | {C['site_name']}", f'''<section class="page-head"><div class="wrap"><p class="kicker">Subscribe</p><h1>Get the Brief free</h1><p class="dek">Plain-English Florida condo and HOA law, with a link to the source for every fact. Unsubscribe anytime.</p>
<p><a class="btn btn-lg" href="{C['subscribe_url']}" rel="noopener">Continue to signup →</a></p><p class="src-note">You'll be taken to our signup form.</p></div></section>''', 'Subscribe free to the Florida Condo & HOA Brief.', '/subscribe/',
    extra_head=f'<meta http-equiv="refresh" content="2;url={C["subscribe_url"]}">'))

# RSS
items = ''.join(f'''<item><title>{E(i["title"])}</title><link>{C["site_url"]}{i["url"]}</link><guid isPermaLink="true">{C["site_url"]}{i["url"]}</guid><pubDate>{format_datetime(dt(i))}</pubDate><description>{E(i["subtitle"])}</description><content:encoded><![CDATA[{bodies[i["slug"]].replace('href="/', f'href="{C["site_url"]}/').replace('src="/', f'src="{C["site_url"]}/')}]]></content:encoded></item>''' for i in ISSUES)
write('feed.xml', f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>{E(C["site_name"])}</title><link>{C["site_url"]}/</link><atom:link href="{C["site_url"]}/feed.xml" rel="self" type="application/rss+xml"/><description>{E(C["tagline"])}</description><language>en-us</language>{items}</channel></rss>
''')
urls = ['/', '/issues/', '/about/', '/sponsor/', '/subscribe/'] + [i['url'] for i in ISSUES]
write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{C["site_url"]}{u}</loc></url>' for u in urls) + '</urlset>\n')
print(f'built {len(ISSUES)} issue(s)')
