#!/usr/bin/env python3
"""Create a Brevo email campaign DRAFT from content/issues/<slug>.html.

    BREVO_API_KEY=... python3 tools/send_issue.py <slug>            # create the draft in Brevo
    python3 tools/send_issue.py <slug> --preview out.html           # just write the rendered email (no API calls)
    BREVO_API_KEY=... python3 tools/send_issue.py --sync-template   # (re)create the "Brief - issue layout" template in Brevo

This script can only create DRAFTS. It never sends or schedules: a human reviews the draft in Brevo
(Campaigns > Drafts), sends a test to themselves, and clicks Send. There is deliberately no send code here.
The list, sender and reply-to come from config.json ("email"). Uses only the standard library.

Email goes through Brevo only (list from config.json, list 3), never beehiiv.
Logging: each Brevo call is logged with method, path and status to
/workspace/logs/send_issue.log. The API key is never logged.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from lp_logging import get_logger
log = get_logger('send_issue')  # trace file: /workspace/logs/send_issue.log
import json, re, os, sys, html, pathlib, datetime, urllib.request, urllib.error
ROOT = pathlib.Path(__file__).resolve().parent.parent
C = json.load(open(ROOT/'config.json')); EM = C['email']
API = 'https://api.brevo.com/v3'

def brevo(method, path, data=None):
    """Call the Brevo v3 API and return parsed JSON; exit with the error text on HTTP failure."""
    log.info('Brevo %s %s', method, path)
    key = os.environ.get('BREVO_API_KEY')
    if not key: sys.exit('BREVO_API_KEY is not set')
    req = urllib.request.Request(API+path, method=method, data=json.dumps(data).encode() if data is not None else None,
        headers={'api-key': key, 'content-type': 'application/json', 'accept': 'application/json', 'user-agent': 'condohoabrief-tools/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            t = r.read().decode(); return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        log.error('Brevo %s %s failed: HTTP %s', method, path, e.code)
        sys.exit(f'Brevo {method} {path} -> {e.code}: {e.read().decode()[:400]}')

STYLES = {  # inline styles: most email clients ignore <style> blocks
 'p': 'margin:0 0 14px 0;', 'h2': "font:700 21px/1.3 Georgia,'Times New Roman',serif;color:#0B2540;margin:26px 0 10px 0;",
 'h3': "font:700 18px/1.3 Georgia,'Times New Roman',serif;color:#0B2540;margin:20px 0 8px 0;",
 'ul': 'margin:0 0 14px 0;padding-left:22px;', 'ol': 'margin:0 0 14px 0;padding-left:22px;', 'li': 'margin:0 0 8px 0;',
 'blockquote': 'margin:16px 0;padding:10px 16px;border-left:4px solid #F2B544;background:#FBF6EA;',
 'hr': 'border:0;border-top:1px solid #E2DDD3;margin:22px 0;', 'a': 'color:#1F7A6D;',
 'img': 'max-width:100%;height:auto;border-radius:6px;', 'figure': 'margin:16px 0;'}

def absolute(u):
    return C['site_url'] + u if u.startswith('/') and not u.startswith('//') else u

def email_body(raw, slug):
    h = re.sub(r'\s(data-[\w-]+|class|target)="[^"]*"', '', raw)
    h = re.sub(r'<figcaption>\s*</figcaption>', '', h)
    h = re.sub(r'<figure>\s*(<blockquote>.*?</blockquote>)\s*</figure>', r'\1', h, flags=re.S)
    h = re.sub(r'<p><strong>[^<]*</strong> <em>By [^<]*</em></p>', '', h, count=1)  # byline is in the header
    h = re.sub(r'(href|src)="([^"]+)"', lambda m: f'{m.group(1)}="{absolute(m.group(2))}"', h)
    def style(m):
        tag, attrs = m.group(1), m.group(2)
        s = STYLES.get(tag)
        if not s or 'style=' in attrs: return m.group(0)
        return f'<{tag}{attrs} style="{s}"' + ('/>' if m.group(0).endswith('/>') else '>')
    h = re.sub(r'<(p|h2|h3|ul|ol|li|blockquote|hr|a|img|figure)((?:\s[^>]*?)?)\s*/?>', style, h)
    return h

def render(issue):
    raw = (ROOT/'content/issues'/f"{issue['slug']}.html").read_text()
    d = datetime.datetime.fromisoformat(issue['date'].replace('Z', '+00:00')).astimezone(datetime.timezone(datetime.timedelta(hours=-4)))
    E = html.escape
    sub = {'TITLE': E(issue['title']), 'PREHEADER': E(issue['subtitle']), 'NUMBER': str(issue['number']),
           'DATE': d.strftime('%B %-d, %Y'), 'AUTHOR': E(issue['author']), 'WEB_URL': f"{C['site_url']}{issue.get('url') or '/p/'+issue['slug']+'/'}",
           'SITE_URL': C['site_url'], 'POSTAL_ADDRESS': E(EM['postal_address']), 'EDITOR_EMAIL': E(C['editor_email']),
           'BODY': email_body(raw, issue['slug'])}
    out = (ROOT/'tools/email/brief_issue.html').read_text()
    for k, v in sub.items(): out = out.replace(f'%%{k}%%', v)
    left = re.findall(r'%%[A-Z_]+%%', out)
    if left: sys.exit(f'unfilled placeholders: {left}')
    if '{{ unsubscribe }}' not in out: sys.exit('template lost its unsubscribe link')
    return out

def pick_sender():
    want = EM['sender_email'].lower()
    if os.environ.get('BREVO_API_KEY'):
        senders = brevo('GET', '/senders').get('senders', [])
        if any(s['email'].lower() == want and s.get('active') for s in senders): return EM['sender_name'], EM['sender_email']
        print(f"NOTE: {EM['sender_email']} is not an active Brevo sender yet; using {EM['fallback_sender_email']}", file=sys.stderr)
    return EM['sender_name'], EM['fallback_sender_email']

def issue_by_slug(slug):
    for i in json.load(open(ROOT/'content/issues.json')):
        if i['slug'] == slug: return i
    sys.exit(f'no issue with slug {slug!r} in content/issues.json')

def main(a):
    """Command-line entry point; see the module docstring for usage."""
    log.info('main args=%s', a)
    if '--sync-template' in a:
        issues = sorted(json.load(open(ROOT/'content/issues.json')), key=lambda i: i['date'])
        name, email = pick_sender()
        r = brevo('POST', '/smtp/templates', {'templateName': 'Brief - issue layout', 'subject': 'Florida Condo & HOA Brief',
            'sender': {'name': name, 'email': email}, 'htmlContent': render(issues[-1]), 'isActive': True})
        return print('created Brevo template id', r.get('id'))
    slugs = [x for x in a if not x.startswith('--') and not x.endswith('.html')]
    if len(slugs) != 1: sys.exit(__doc__)
    issue = issue_by_slug(slugs[0]); body = render(issue)
    if '--preview' in a:
        out = a[a.index('--preview')+1]; pathlib.Path(out).write_text(body); return print('wrote', out, len(body), 'bytes')
    name = f"Brief #{issue['number']}: {issue['title']}"
    existing = [c for c in brevo('GET', '/emailCampaigns?limit=100&sort=desc').get('campaigns', []) if c['name'] == name]
    if existing: sys.exit(f"a campaign named {name!r} already exists (id {existing[0]['id']}, {existing[0]['status']}); not creating another")
    sname, semail = pick_sender()
    payload = {'name': name, 'subject': issue['title'], 'previewText': issue['subtitle'][:150], 
        'sender': {'name': sname, 'email': semail}, 'replyTo': EM['reply_to'], 'htmlContent': body,
        'recipients': {'listIds': [EM['brevo_list_id']]}, 'utmCampaignValue': issue['slug'][:50]}
    assert 'scheduledAt' not in payload  # drafts only, never scheduled
    r = brevo('POST', '/emailCampaigns', payload)
    print(f"DRAFT created: campaign id {r.get('id')} (list {EM['brevo_list_id']}, sender {semail}). Review and send it yourself in Brevo > Campaigns.")

if __name__ == '__main__': main(sys.argv[1:])
