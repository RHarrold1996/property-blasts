#!/usr/bin/env python3
"""
Build property blast emails.

Reads every properties/*.yml (except files starting with "_"),
fills templates/investor-blast.html, and writes:
  docs/emails/<slug>.html   -> paste into GHL's code editor
  docs/index.html           -> dashboard with previews, subject lines, copy buttons

Usage:
  pip install -r requirements.txt
  python build.py                 # build all properties
  python build.py 123-main.yml    # build just one
"""
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
PROPS = ROOT / "properties"
DOCS = ROOT / "docs"
OUT = DOCS / "emails"
PHOTOS = ROOT / "photos"

REQUIRED = ["address", "city", "state", "price", "arv", "repairs"]


# ---------- helpers ----------
def parse_money(v):
    """185000 | '185,000' | '$185k' | '1.2m' -> int (or None)."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return int(round(v))
    s = str(v).strip().lower().replace("$", "").replace(",", "").replace(" ", "")
    mult = 1
    if s.endswith("k"):
        mult, s = 1_000, s[:-1]
    elif s.endswith("m"):
        mult, s = 1_000_000, s[:-1]
    try:
        return int(round(float(s) * mult))
    except ValueError:
        raise ValueError(f"Can't read money value: {v!r}")


def fmt_money(n):
    return "" if n is None else f"${n:,.0f}"


def short_money(n):
    if n is None:
        return ""
    if n >= 1_000_000:
        return f"${n/1_000_000:.2f}".rstrip("0").rstrip(".") + "M"
    if n >= 1_000:
        return f"${n/1_000:.0f}K"
    return f"${n}"


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def resolve_photo(src, base):
    src = str(src).strip()
    if re.match(r"^https?://", src):
        return src
    if not base:
        print(f"  ! Photo '{src}' is a filename but no photo_base_url is set — it won't load in email.")
    return base.rstrip("/") + "/" + src.lstrip("/") if base else src


def default_photo_base():
    repo = os.environ.get("GITHUB_REPOSITORY")  # set automatically inside GitHub Actions
    if repo and "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner.lower()}.github.io/{name}/photos/"
    return ""


def find_placeholders(obj, path=""):
    """Flag leftover [BRACKETED] placeholders."""
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            hits += find_placeholders(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits += find_placeholders(v, f"{path}[{i}]")
    elif isinstance(obj, str) and re.search(r"\[[A-Z][A-Z _/]+\]", obj):
        hits.append(path)
    return hits


# ---------- build ----------
def build_one(path, cfg, tmpl):
    p = yaml.safe_load(path.read_text()) or {}
    missing = [k for k in REQUIRED if p.get(k) in (None, "")]
    if missing:
        raise ValueError(f"missing required field(s): {', '.join(missing)}")

    nums = {k: parse_money(p.get(k)) for k in ["price", "arv", "repairs", "spread", "rent", "emd"]}
    if nums["spread"] is None:
        nums["spread"] = nums["arv"] - nums["price"] - nums["repairs"]
    if nums["spread"] <= 0:
        print(f"  ! Spread is {fmt_money(nums['spread'])} — double-check the numbers.")
    money = {k: fmt_money(v) for k, v in nums.items()}

    base = cfg.get("photo_base_url") or default_photo_base()
    photos = [resolve_photo(x, base) for x in (p.get("photos") or []) if x]
    if p.get("main_photo"):
        hero, gallery = resolve_photo(p["main_photo"], base), photos
    else:  # older files: first photo is the hero
        hero, gallery = (photos[0], photos[1:]) if photos else (None, [])

    markets = cfg.get("markets") or {}
    mkey = str(p.get("market") or "").strip().lower()
    if mkey and mkey not in markets:
        raise ValueError(f"market '{mkey}' isn't in config.yml (have: {', '.join(markets) or 'none'})")
    market = markets.get(mkey) or (next(iter(markets.values())) if markets else {})
    phone = str(market.get("phone") or cfg["phone"])
    market_name = market.get("name", "")

    beds_baths = " / ".join(str(p[k]) for k in ("beds", "baths") if p.get(k) not in (None, ""))
    sqft = f"{int(p['sqft']):,}" if str(p.get("sqft", "")).isdigit() else p.get("sqft")
    details = [(label, val) for label, val in [
        ("Beds / Baths", beds_baths),
        ("Sq Ft", sqft),
        ("Year Built", p.get("year_built")),
        ("Lot Size", p.get("lot_size")),
        ("Occupancy", p.get("occupancy")),
        ("Exit", p.get("exit_strategy")),
        ("Est. Rent", f"{money['rent']}/mo" if nums["rent"] else None),
        ("Condition", p.get("condition")),
    ] if val not in (None, "")]

    bb = f"{p.get('beds', '?')}/{p.get('baths', '?')}"
    subjects = p.get("subject_lines") or [
        f"Off-market: {p['city']} {bb} | {short_money(nums['spread'])} spread",
        f"{cfg['first_name_merge_field']}, {short_money(nums['spread'])} spread in {p['city']}",
        f"New {p['city']} deal: {short_money(nums['price'])} | ARV {short_money(nums['arv'])}",
        f"First look: {p.get('neighborhood') or p['city']} deal before it's gone",
    ]
    preheader = " | ".join(x for x in [
        f"{p.get('beds')}bd/{p.get('baths')}ba" if p.get("beds") else "",
        f"ARV {money['arv']}",
        f"Repairs ~{money['repairs']}",
        f"Closes {p['close_by']}" if p.get("close_by") else "",
    ] if x)

    website_display = re.sub(r"^https?://(www\.)?", "", cfg["website"]).rstrip("/")
    phone_digits = re.sub(r"\D", "", phone)

    html_out = tmpl.render(
        p=p, cfg=cfg, c=cfg["brand_colors"], money=money, hero=hero, gallery=gallery,
        details=details, preheader=preheader, website_display=website_display,
        phone_digits=phone_digits, phone=phone, market_name=market_name,
    )

    slug = slugify(f"{p['address']} {p['city']}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{slug}.html").write_text(html_out)

    warn = find_placeholders(p) + [f"config.{x}" for x in find_placeholders(cfg)]
    if warn:
        print(f"  ! Placeholder text still in: {', '.join(warn)}")

    return {
        "slug": slug, "address": p["address"], "city": p["city"], "state": p["state"],
        "price": money["price"], "arv": money["arv"], "spread": money["spread"],
        "subjects": subjects, "preheader": preheader, "hero": hero, "source": path.name,
        "market": market_name,
    }


def build_index(items):
    cards = []
    for it in items:
        subj = "".join(
            f'<li><span>{html.escape(s)}</span><button class="mini" data-copy="{html.escape(s)}">Copy</button></li>'
            for s in it["subjects"]
        )
        thumb = f'<img src="{html.escape(it["hero"])}" alt="">' if it["hero"] else '<div class="noimg">No photo</div>'
        cards.append(f"""
<article class="card">
  {thumb}
  <div class="body">
    <h2>{html.escape(it['address'])}</h2>
    <p class="loc">{html.escape(it['market'] + ' market · ' if it['market'] else '')}{html.escape(it['city'])}, {html.escape(it['state'])} · from <code>{html.escape(it['source'])}</code></p>
    <p class="nums"><b>{it['price']}</b> ask · ARV {it['arv']} · <span class="spread">{it['spread']} spread</span></p>
    <div class="actions">
      <button class="primary" data-html="emails/{it['slug']}.html">Copy email HTML</button>
      <a class="secondary" href="emails/{it['slug']}.html" target="_blank">Preview</a>
    </div>
    <h3>Subject lines</h3><ul class="subj">{subj}</ul>
    <h3>Preheader</h3><ul class="subj"><li><span>{html.escape(it['preheader'])}</span><button class="mini" data-copy="{html.escape(it['preheader'])}">Copy</button></li></ul>
  </div>
</article>""")

    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Property Blasts</title>
<style>
:root{{--navy:#224066;--blue:#006EC1;--orange:#FF6F00;--gray:#BDC3CA;--bg:#EEF1F4;--card:#fff;--text:#224066;--muted:#5A6B80}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0f1a2a;--card:#17263b;--text:#e8eef5;--muted:#9fb0c3}}}}
*{{box-sizing:border-box}} body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:var(--bg);color:var(--text)}}
header{{background:var(--navy);color:#fff;padding:18px 16px;border-bottom:4px solid var(--orange)}}
header h1{{margin:0;font-size:20px}} header p{{margin:4px 0 0;color:var(--gray);font-size:13px}}
main{{max-width:1100px;margin:0 auto;padding:20px 16px;display:grid;gap:18px;grid-template-columns:repeat(auto-fill,minmax(320px,1fr))}}
.card{{background:var(--card);border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.card img,.noimg{{width:100%;height:180px;object-fit:cover;display:block;background:var(--gray)}}
.noimg{{display:flex;align-items:center;justify-content:center;color:var(--navy)}}
.body{{padding:16px}} h2{{margin:0;font-size:18px}} .loc{{margin:4px 0;color:var(--muted);font-size:13px}}
.nums{{margin:8px 0 14px;font-size:14px}} .spread{{color:var(--orange);font-weight:bold}}
.actions{{display:flex;gap:8px;flex-wrap:wrap}}
button,.secondary{{font:inherit;cursor:pointer;border-radius:6px;padding:10px 14px;font-weight:bold;font-size:14px;text-decoration:none}}
.primary{{background:var(--orange);color:#fff;border:0}} .secondary{{border:2px solid var(--blue);color:var(--blue);background:transparent}}
h3{{font-size:12px;letter-spacing:1px;text-transform:uppercase;color:var(--muted);margin:16px 0 6px}}
.subj{{list-style:none;margin:0;padding:0;font-size:13px}} .subj li{{display:flex;gap:8px;align-items:center;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(127,127,127,.15)}}
.mini{{padding:4px 8px;font-size:11px;background:transparent;border:1px solid var(--gray);color:var(--text)}}
.empty{{grid-column:1/-1;text-align:center;color:var(--muted)}}
#toast{{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--navy);color:#fff;padding:10px 16px;border-radius:6px;opacity:0;transition:.2s}}
</style></head><body>
<header><h1>Robert Buys Houses · Property Blasts</h1><p>Click "Copy email HTML", then paste into GHL → Emails → Code editor. Or build one live in the <a href="builder/" style="color:#FF6F00;font-weight:bold">Deal Blast Builder</a>.</p></header>
<main>{''.join(cards) or '<p class="empty">No properties yet — add a file to /properties.</p>'}</main>
<div id="toast"></div>
<script>
const toast=m=>{{const t=document.getElementById('toast');t.textContent=m;t.style.opacity=1;setTimeout(()=>t.style.opacity=0,1600)}};
document.addEventListener('click',async e=>{{
  const b=e.target.closest('button'); if(!b) return;
  try{{
    if(b.dataset.html){{const r=await fetch(b.dataset.html);await navigator.clipboard.writeText(await r.text());toast('Email HTML copied');}}
    else if(b.dataset.copy){{await navigator.clipboard.writeText(b.dataset.copy);toast('Copied');}}
  }}catch(err){{toast('Copy failed — open Preview and use View Source');}}
}});
</script></body></html>"""
    (DOCS / "index.html").write_text(page)


def build_builder(cfg):
    """Publish the live Deal Blast Builder at docs/builder/ plus its settings file."""
    src = ROOT / "builder" / "index.html"
    if not src.exists():
        return
    (DOCS / "builder").mkdir(parents=True, exist_ok=True)
    shutil.copy(src, DOCS / "builder" / "index.html")
    markets = [
        {"id": k, "name": str(v.get("name") or k), "phone": str(v.get("phone") or cfg["phone"])}
        for k, v in (cfg.get("markets") or {}).items()
    ]
    settings = {
        "company": cfg["company_name"], "website": cfg["website"], "buyers": cfg["buyers_page"],
        "logo": cfg["logo_url"], "phone": str(cfg["phone"]),
        "firstName": cfg["first_name_merge_field"], "unsub": cfg["unsubscribe_merge_field"],
        "disclosure": " ".join(str(cfg["disclosure"]).split()),
        "c": cfg.get("brand_colors") or {}, "markets": markets,
    }
    (DOCS / "builder-config.json").write_text(json.dumps(settings, indent=2))


def main():
    cfg = yaml.safe_load((ROOT / "config.yml").read_text())
    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"), autoescape=True,
        variable_start_string="[[", variable_end_string="]]",
        block_start_string="[%", block_end_string="%]",
        comment_start_string="[#", comment_end_string="#]",
        trim_blocks=True, lstrip_blocks=True,
    )
    tmpl = env.get_template("investor-blast.html")

    only = set(sys.argv[1:])
    files = sorted(f for f in PROPS.glob("*.y*ml") if not f.name.startswith("_"))
    if only:
        files = [f for f in files if f.name in only]

    # Fresh output so deleted property files disappear from the dashboard
    if not only and OUT.exists():
        shutil.rmtree(OUT)

    # Publish /photos alongside the site so filename-only photos work via GitHub Pages
    if PHOTOS.exists():
        shutil.copytree(PHOTOS, DOCS / "photos", dirs_exist_ok=True)

    items, errors = [], 0
    for f in files:
        print(f"• {f.name}")
        try:
            items.append(build_one(f, cfg, tmpl))
            print(f"  ✓ docs/emails/{items[-1]['slug']}.html")
        except Exception as e:  # keep building the rest
            errors += 1
            print(f"  ✗ {e}")

    if not only:
        build_index(items)
        build_builder(cfg)
        (DOCS / ".nojekyll").write_text("")
    print(f"\nBuilt {len(items)} email(s), {errors} error(s).")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
