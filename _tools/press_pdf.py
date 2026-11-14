"""Build press/walkers-press-kit.pdf from press/index.html.

Run from the repo root:  python3 _tools/press_pdf.py
Needs: pip install playwright && playwright install chromium
Optional: FONT_DIR=/path/to/node_modules/@fontsource  (serves the web fonts locally
when fonts.googleapis.com isn't reachable)
"""
import os, pathlib
from playwright.sync_api import sync_playwright

root = pathlib.Path(__file__).resolve().parent.parent
src = (root / 'press' / 'index.html').as_uri()
out = root / 'press' / 'walkers-press-kit.pdf'
font_dir = os.environ.get('FONT_DIR')

def local_font_css():
    faces = []
    for fam, pkg, weights in [('Big Shoulders Display', 'big-shoulders-display', [700, 800, 900]),
                              ('Figtree', 'figtree', [400, 500, 600, 700]),
                              ('JetBrains Mono', 'jetbrains-mono', [500])]:
        for w in weights:
            f = pathlib.Path(font_dir) / pkg / 'files' / f'{pkg}-latin-{w}-normal.woff2'
            faces.append(f"@font-face{{font-family:'{fam}';font-weight:{w};src:url({f.as_uri()}) format('woff2')}}")
    return '\n'.join(faces)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 816, 'height': 1056})
    if font_dir:
        css = local_font_css()
        pg.route('https://fonts.googleapis.com/**', lambda r: r.fulfill(status=200, content_type='text/css', body=css))
        pg.route('https://fonts.gstatic.com/**', lambda r: r.abort())
    pg.goto(src, wait_until='load')
    pg.emulate_media(media='print')
    # the teaser loop becomes its poster frame, still linked to YouTube; load every lazy image
    pg.evaluate("""() => {
      document.querySelectorAll('img[loading]').forEach(i => i.removeAttribute('loading'));
      document.querySelectorAll('.video video').forEach(v => {
        const img = document.createElement('img'); img.src = v.getAttribute('poster');
        img.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;object-fit:cover'; v.replaceWith(img);
      });
    }""")
    pg.wait_for_function("() => [...document.images].every(i => i.complete) && document.fonts.status === 'loaded'")
    pg.wait_for_timeout(300)
    pg.pdf(path=str(out), format='Letter', print_background=True, prefer_css_page_size=True,
           margin={'top': '0.5in', 'right': '0', 'bottom': '0.5in', 'left': '0'})
    b.close()
print('wrote', out, round(out.stat().st_size / 1e6, 1), 'MB')
