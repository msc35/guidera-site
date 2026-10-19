#!/usr/bin/env python3
"""Publish a Markdown blog post into the static site, using an existing post as the HTML template.

Usage:
  python3 scripts/new_post.py SOURCE.md --slug my-post --title "SEO title (<=60)" \
      --desc "Meta description (<=155)" --summary "One line for the blog list" \
      --cover path/to/cover.png --date 2026-10-19 [--crumb "Short name"]

What it does:
  - converts the Markdown (headings, paragraphs, lists, tables, **bold**, *italic*, [links](url))
  - writes blog/<slug>.html with the site header/footer, byline, dates, JSON-LD (BlogPosting + BreadcrumbList)
  - saves the cover as assets/blog/<slug>.jpg and a 1200x630 share image as assets/og/<slug>.png
  - adds the post to blog/index.html (first card), blog/feed.xml, sitemap.xml and llms.txt
"""
import argparse, datetime, email.utils, html, json, os, re, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://guidera.live'
TEMPLATE = os.path.join(ROOT, 'blog/how-guidera-keeps-ai-tour-guide-accurate.html')
e = lambda s: html.escape(s, quote=True)


def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:60]


def inline(s):
    s = e(s).replace('&#x27;', "'")
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: f'<a href="{m.group(2).replace("https://guidera.live", "")}">{m.group(1)}</a>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<![*\w])\*([^*]+)\*(?!\*)', r'<i>\1</i>', s)
    return s


def md_to_html(md):
    lines = md.strip().split('\n')
    title = lines[0].lstrip('# ').strip()
    out, i, first_p = [], 1, True
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1; continue
        m = re.match(r'^(#{2,3}) (.+)', ln)
        if m:
            lvl = len(m.group(1)); t = m.group(2).strip()
            out.append(f'<h{lvl} id="{slugify(t)}">{inline(t)}</h{lvl}>'); i += 1; continue
        if ln.startswith('* ') or ln.startswith('- '):
            items = []
            while i < len(lines) and (lines[i].startswith('* ') or lines[i].startswith('- ')):
                items.append(f'<li>{inline(lines[i][2:].strip())}</li>'); i += 1
            out.append('<ul>' + ''.join(items) + '</ul>'); continue
        if ln.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')]); i += 1
            head, body = rows[0], [r for r in rows[1:] if not set(''.join(r)) <= set(':- ')]
            th = ''.join(f'<th>{inline(c)}</th>' for c in head)
            tb = ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>' for r in body)
            out.append(f'<div class="table-wrap"><table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>'); continue
        para = [ln.strip()]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#|\* |- |\|)', lines[i]):
            para.append(lines[i].strip()); i += 1
        cls = ' class="lead"' if first_p else ''
        out.append(f'<p{cls}>{inline(" ".join(para))}</p>'); first_p = False
    return title, '\n'.join(out)


def human(d):
    return f'{d.day} {d.strftime("%B %Y")}'


def main():
    ap = argparse.ArgumentParser()
    for a in ['source', '--slug', '--title', '--desc', '--summary', '--cover', '--date']:
        ap.add_argument(a, required=a != 'source' or None) if a.startswith('--') else ap.add_argument(a)
    ap.add_argument('--crumb')
    a = ap.parse_args()
    assert len(a.title) <= 60, f'title {len(a.title)} > 60'
    assert len(a.desc) <= 155, f'desc {len(a.desc)} > 155'
    d = datetime.date.fromisoformat(a.date)
    h1, body = md_to_html(open(a.source).read())
    words = len(re.sub(r'<[^>]+>', ' ', body).split())
    reading = max(3, round(words / 220))
    path = f'/blog/{a.slug}.html'; url = BASE + path
    cover_rel = f'/assets/blog/{a.slug}.jpg'; og_rel = f'/assets/og/{a.slug}.jpg'

    # images
    os.makedirs(os.path.join(ROOT, 'assets/blog'), exist_ok=True)
    im = Image.open(a.cover).convert('RGB')
    im.save(os.path.join(ROOT, cover_rel.lstrip('/')), quality=82, optimize=True, progressive=True)
    tw, th = 1200, 630
    sc = max(tw / im.width, th / im.height)
    og = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
    l = (og.width - tw) // 2; t = (og.height - th) // 2
    og.crop((l, t, l + tw, t + th)).save(os.path.join(ROOT, og_rel.lstrip('/')), quality=85, optimize=True, progressive=True)

    s = open(TEMPLATE).read()
    old_title = re.search(r'<title>(.*?)</title>', s).group(1)
    old_desc = re.search(r'<meta name="description" content="(.*?)"', s).group(1)
    old_url = re.search(r'<link rel="canonical" href="(.*?)"', s).group(1)
    s = s.replace(old_title, e(a.title)).replace(old_desc, e(a.desc)).replace(old_url, url)
    s = re.sub(r'content="https://guidera.live/assets/og/[^"]+"', f'content="{BASE}{og_rel}"', s)
    s = re.sub(r'(article:(published|modified)_time" content=")[^"]+', rf'\g<1>{a.date}', s)
    # hero
    crumb = a.crumb or a.title
    s = re.sub(r'(<nav class="breadcrumb".*?<span aria-hidden="true">›</span><a href="/blog/">Blog</a><span aria-hidden="true">›</span><span>)[^<]*', lambda m: m.group(1) + e(crumb), s, count=1, flags=re.S)
    s = re.sub(r'(<section class="page-hero article-hero">.*?<h1>).*?(</h1>)', lambda m: m.group(1) + e(h1) + m.group(2), s, count=1, flags=re.S)
    s = re.sub(r'Published <time datetime="[^"]+">[^<]+</time> · Last updated <time datetime="[^"]+">[^<]+</time> · \d+ min read',
               f'Published <time datetime="{a.date}">{human(d)}</time> · Last updated <time datetime="{a.date}">{human(d)}</time> · {reading} min read', s, count=1)
    # article body (keep the CTA box)
    cover = f'<figure class="figure" style="padding:0;overflow:hidden"><img src="{cover_rel}" alt="{e(h1)}" width="{im.width}" height="{im.height}" style="width:100%;height:auto;display:block"/></figure>'
    s = re.sub(r'(<article class="article">\n).*?(<aside class="cta-box")', lambda m: m.group(1) + cover + '\n' + body + '\n' + m.group(2), s, count=1, flags=re.S)
    # related posts: the 3 newest existing posts
    rel = [('/blog/how-guidera-keeps-ai-tour-guide-accurate.html', 'How We Stop an AI Tour Guide From Making Up History', 'How Guidera checks every story against sources before telling it.'),
           ('/blog/best-audio-tour-apps-which-one-for-which-trip.html', 'Audio Tour Apps Compared: Which One Fits Your Trip? (2026)', 'Six apps, what each is best for, and their honest limits.'),
           ('/blog/munich-old-town-self-guided-walking-tour.html', "Free Self-Guided Walking Tour of Munich's Old Town", '11 stops from Marienplatz to the Asamkirche, with a map and sources.')]
    rel_html = '\n'.join(f'<li><a href="{p}">{e(t)}</a><p>{e(x)}</p></li>' for p, t, x in rel)
    s = re.sub(r'(<section class="related" aria-label="Related posts">\s*<h2>Related posts</h2>\s*<ul>).*?(</ul>)', lambda m: m.group(1) + rel_html + m.group(2), s, count=1, flags=re.S)
    # JSON-LD
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', s, re.S)
    g = json.loads(m.group(1))
    nodes = []
    for n in g['@graph']:
        if n['@type'] == 'FAQPage':
            continue
        if n['@type'] == 'BlogPosting':
            n.update({'@id': url + '#post', 'headline': h1, 'description': a.desc, 'image': BASE + og_rel,
                      'datePublished': a.date, 'dateModified': a.date, 'mainEntityOfPage': url})
        if n['@type'] == 'BreadcrumbList':
            n['itemListElement'][2].update({'name': crumb, 'item': url})
        nodes.append(n)
    g['@graph'] = nodes
    s = s[:m.start(1)] + json.dumps(g, ensure_ascii=False, indent=1) + s[m.end(1):]
    open(os.path.join(ROOT, path.lstrip('/')), 'w').write(s)

    # blog index: new first card + JSON-LD
    bi = os.path.join(ROOT, 'blog/index.html'); b = open(bi).read()
    if path not in b:
        card = f'''<article class="post-card">
  <a href="{path}" tabindex="-1" aria-hidden="true"><img src="{og_rel}" alt="" width="1200" height="630" loading="lazy"/></a>
  <div class="post-body">
    <p class="post-meta"><time datetime="{a.date}">{human(d)}</time> · {reading} min read</p>
    <h2><a href="{path}">{e(h1)}</a></h2>
    <p class="summary">{e(a.summary)}</p>
    <a href="{path}" class="read story-link">Read the post →</a>
  </div>
</article>
'''
        b = b.replace('  <div class="post-list">\n', '  <div class="post-list">\n' + card, 1)
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>', b, re.S)
        g = json.loads(m.group(1))
        for n in g['@graph']:
            if n['@type'] == 'Blog':
                n['blogPost'].insert(0, {'@id': url + '#post'})
            if n['@type'] == 'ItemList':
                n['itemListElement'].insert(0, {'@type': 'ListItem', 'position': 1, 'url': url, 'name': h1})
                for k, it in enumerate(n['itemListElement'], 1):
                    it['position'] = k
        b = b[:m.start(1)] + json.dumps(g, ensure_ascii=False, indent=1) + b[m.end(1):]
        open(bi, 'w').write(b)

    # RSS
    fp = os.path.join(ROOT, 'blog/feed.xml'); f = open(fp).read()
    if url not in f:
        pub = email.utils.format_datetime(datetime.datetime.fromisoformat(a.date + 'T09:00:00+02:00'))
        item = f'''  <item>
    <title>{e(h1)}</title>
    <link>{url}</link>
    <guid isPermaLink="true">{url}</guid>
    <pubDate>{pub}</pubDate>
    <dc:creator>Mehmet Selim Çetin</dc:creator>
    <description>{e(a.desc)}</description>
  </item>
'''
        f = f.replace('  <item>', item + '  <item>', 1)
        f = re.sub(r'<lastBuildDate>[^<]+</lastBuildDate>', f'<lastBuildDate>{pub}</lastBuildDate>', f)
        open(fp, 'w').write(f)

    # sitemap
    sp = os.path.join(ROOT, 'sitemap.xml'); sm = open(sp).read()
    if url not in sm:
        sm = sm.replace('</urlset>', f'  <url><loc>{url}</loc><lastmod>{a.date}</lastmod></url>\n</urlset>')
        sm = re.sub(r'(<loc>https://guidera.live/blog/</loc><lastmod>)[^<]+', rf'\g<1>{a.date}', sm)
        open(sp, 'w').write(sm)

    # llms.txt
    lp = os.path.join(ROOT, 'llms.txt'); ll = open(lp).read()
    if url not in ll:
        ll = ll.replace('## Blog\n', f'## Blog\n- [{h1}]({url}): {a.summary}\n', 1)
        open(lp, 'w').write(ll)

    print(f'wrote {path} ({words} words, {reading} min) + cover {cover_rel} + share image {og_rel}')


if __name__ == '__main__':
    main()
