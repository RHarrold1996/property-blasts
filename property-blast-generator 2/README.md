# Robert Buys Houses — Property Blast Generator

Fill in a short property file → get a branded, ready-to-paste GHL email.

```
properties/123-main-st.yml   ──►  GitHub builds it  ──►  docs/emails/123-main-st-decatur.html
                                                         + dashboard with Copy buttons
```

## Folder map

| Folder / file | What it's for |
|---|---|
| `properties/` | **One file per deal.** This is the only place you work day to day. |
| `properties/_TEMPLATE.yml` | Blank form. Copy it for each new property. |
| `photos/` | Optional: upload property photos here and reference them by filename. |
| `config.yml` | Brand settings shared by every email (markets and phone numbers, logo, disclosure). |
| `templates/investor-blast.html` | Email design used by the property files. |
| `builder/index.html` | The live Deal Blast Builder page (embedded in GHL). Uses the same design. |
| `docs/` | Generated output. Don't edit by hand — it's rebuilt automatically. |
| `build.py` | The generator script. |

---

## One-time setup (about 10 minutes)

### 1. Create the repository
1. Go to [github.com/new](https://github.com/new).
2. Name it `property-blasts`. Choose **Public** (needed for free GitHub Pages; see note below).
3. Click **Create repository**.

### 2. Upload the files
1. On the new repo page, click **uploading an existing file**.
2. Unzip `property-blast-generator.zip` on your computer, open the folder, select **everything inside it**, and drag it into the browser. Click **Commit changes**.
3. **Check the `.github` folder made it.** Mac and Windows hide folders that start with a dot, so it often gets left behind. If you don't see `.github/workflows/build.yml` in the repo:
   - Click **Add file → Create new file**
   - Type the name `.github/workflows/build.yml` (the slashes create the folders)
   - Paste in the contents of that file from the zip (open it in a text editor) and commit.

### 3. Add your markets
Open `config.yml` → pencil icon → under `markets:` add one entry per market with its phone number → **Commit changes**. Each property file picks its market with `market: atlanta` (the key, lowercase).

### 4. Turn on the dashboard (GitHub Pages)
1. Repo **Settings → Pages**.
2. Under **Build and deployment**: Source = **Deploy from a branch**, Branch = **main**, Folder = **/docs** → **Save**.
3. After a minute your dashboard is live at `https://<your-username>.github.io/property-blasts/`. Bookmark it.

### 5. Let the robot commit
Repo **Settings → Actions → General → Workflow permissions** → select **Read and write permissions** → **Save**.

### 6. Add the Deal Blast Builder to GHL (iframe)
The live builder is published with your site at
`https://<your-username>.github.io/property-blasts/builder/`. Open that link once to check it loads.

1. In GHL, switch to **Agency view** (only agency admins with "Manage Custom Menu Links" can do this).
2. **Settings → Custom Menu Links → Create New**.
3. Icon: pick one (e.g. envelope). Title: `Deal Blast Builder`.
4. URL: `https://<your-username>.github.io/property-blasts/builder/`
   - Per-market sub-accounts: add `?market=houston` (the key from `config.yml`) so the right phone number is preselected. Make one link per market and show each only in that market's sub-account.
5. Open as: **Embedded Page (iFrame)**.
6. Visibility: Sub-Account sidebar → choose your sub-account(s). Roles: All (or Admin only).
7. Save, open the sub-account, click **Deal Blast Builder** in the left sidebar.

**Using it inside GHL:** fill in the deal → **Copy email HTML** → Marketing → Emails → New → Code editor → paste. If the browser blocks the copy inside the iframe, a box opens with the HTML already selected; press Ctrl+C (⌘C on Mac).

**Adding a market:** edit `markets:` in `config.yml` and commit. The builder picks it up after the build finishes (~1 minute; refresh the page).

---

## Everyday use: new property blast

1. In `properties/`, open `_TEMPLATE.yml` → click **⋯ → Copy raw contents** (or just select all and copy).
2. Go back to `properties/` → **Add file → Create new file**.
3. Name it after the property, e.g. `4521-oak-dr-stone-mountain.yml`. Paste, fill in the fields, **Commit changes**.
4. Wait ~1 minute (watch the **Actions** tab turn green).
5. Open your dashboard → find the property → **Copy email HTML**.
6. In GHL: **Marketing → Emails → New → Code editor** → paste. Grab a subject line and preheader from the dashboard too.

**Editing a deal** (price drop, new photos): edit its `.yml` file and commit. The email rebuilds.
**Removing a deal**: delete its `.yml` file. It disappears from the dashboard on the next build.

### Tips for the property file
- Money can be written any way: `185000`, `"185,000"`, `$185k`.
- **Spread** is calculated for you (ARV − price − repairs) unless you type your own.
- Leave an optional field blank or delete the line, and that row disappears from the email.
- `main_photo` is the big image up top; add as many extra `photos` and `highlights` bullets as you want.
- Use `badge: PRICE DROP` or `badge: BACK ON MARKET` to change the orange tag.

### Logo
Emails load the logo from `logo_url` in `config.yml` (currently your site's `BIMI.png`). Your logo file is also in `photos/logo.png`; to use that copy instead, set `logo_url` to `https://<your-username>.github.io/property-blasts/photos/logo.png`, or upload the logo to GHL Media Library and paste its link.

### Photos
Email images must live at a public web address. Two options:
- **Easiest:** upload to GHL's Media Library, copy the image URL, paste it in `photos:`.
- **In this repo:** upload images to the `photos/` folder, then list just the filename (e.g. `- 4521-oak-front.jpg`). They're served from your GitHub Pages site automatically. Keep photos under ~500 KB each so emails load fast.

> **Private repo?** GitHub Pages on private repos needs a paid plan. Everything else still works: open `docs/emails/<property>.html` in the repo, click **Raw**, select all, copy. Use GHL Media Library URLs for photos.

---

## If something goes wrong

- **Actions tab shows a red ✗:** click it and open "Build emails". The log says which property file has a problem, e.g. `missing required field(s): arv`. Fix the file and commit again.
- **Required fields:** `address`, `city`, `state`, `price`, `arv`, `repairs`.
- **YAML gotchas:** keep the two-space indent under `highlights:` and `photos:`, and wrap text containing a colon in quotes (e.g. `showing: "Sat 10:00–12:00"`).
- **Warnings** like `Placeholder text still in: ...` mean a `[BRACKETED]` placeholder is still there.

## Running it on your own computer (optional)

```bash
pip install -r requirements.txt
python build.py                              # build everything
python build.py 4521-oak-dr-stone-mountain.yml   # build one
```
Then open `docs/index.html` or `docs/emails/*.html` in your browser.
