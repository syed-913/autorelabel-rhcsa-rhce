# autorelabel website

The static project website for autorelabel. It runs on Astro 7 and TypeScript, with local fonts, handwritten CSS, and browser interactions. The deployment target is GitHub Pages at `/autorelabel-rhcsa-rhce/`.

## Run locally

Use Node 22.23.4 or a newer Node 22 patch release, plus npm. The version in `.nvmrc` is used by the Pages workflow. With nvm installed, run `nvm install` and `nvm use` from `site/` before the commands below:

```sh
cd site
npm ci
npm run dev
```

Open the printed Local URL, including the project base. The default is `http://localhost:4321/autorelabel-rhcsa-rhce/`.

The complete search index is created by the production build. To test Docs and FAQ search:

```sh
npm run build
npm run preview
```

The preview also uses the project base. Commands disable Astro build telemetry. Dev and preview stay in the foreground with normal terminal output and Ctrl+C shutdown. The website uses no analytics, cookies, external fonts, embedded services, or runtime CDN requests. Browser preferences are stored locally.

## Checks

```sh
npm run check:deps
npm run check
npm run build
npm run verify
npm run check:html
```

`verify` checks every local resource and anchor, unique IDs, one H1 per page, current source counts and objective coverage, the exact getting-started command sequence, the README disclaimer, visible copy style, the metadata-only task boundary, and the initial script budget. The counts are read from the current banks, so adding a task does not require editing website numbers.

HTML validation uses HTML5 IDs, including the source objective IDs and the guide’s numbered heading anchors.

With a built preview running and Google Chrome available, `npm run review:browser` records (in `qa/`, which git ignores) the desktop/mobile browser matrix, accessibility results and interaction evidence. `npm run review:interactions` adds native keyboard navigation, FAQ disclosures, console success and failure, clipboard fallback and pointer recovery. Set `CHROME_PATH` to use another Chrome executable or `SITE_PREVIEW_URL` to change the preview address. `npm run review:states` refreshes the close component captures. These commands use an isolated browser profile and do not control a personal browser session.

## Content and routes

The source boundary is intentionally small:

- `../pyproject.toml`: the version displayed beside the release-notes link.
- `../README.md`: Requirements, Getting started, Supported platforms, the dated comparison, and the affiliation disclaimer.
- `../banks/{rhcsa,rhce}/`: task metadata, objective lines and blueprints. Prompts and solutions are not exported.
- `../docs/guide/README.md`: guide order and titles.
- `../docs/guide/*.md`: guide content; `11-faq.md` renders only at `/faq/`.
- `../docs/guide/04-the-lab.md`: the lab reference tables.
- `../docs/ARCHITECTURE.md`: the documented exam pipeline.
- `../docs/media/` and `../docs/social-preview.png`: genuine product imagery.

The Markdown pipeline parses source structure with remark, sanitizes HTML, rewrites links and media, adds command-copy controls, collects heading outlines, and styles anchored question callouts. Presentation normalization keeps visible status marks and prose consistent without changing objective wording or commands. Removed README anchors map to the matching site or guide page.

The main routes are `/`, `/start/`, `/rhcsa/`, `/rhce/`, `/tasks/`, `/how-it-works/`, `/faq/`, and `/docs/`. Numbered guide filenames become `/docs/<page>/`; the guide FAQ links to the single FAQ route. The build also includes `404.html`, a sitemap, robots file, manifest, favicons, canonical metadata, social cards, and the requested structured data.

The task bank filters titles and metadata. It does not change a timed exam’s draw. Search, domain, exam, difficulty, eligibility and sort state are shareable in the URL. Practice mode in autorelabel lets the user choose tasks.

Pagefind indexes only Docs and FAQ, after the Astro build. Its script, index and search resources are served from the same project base and load when search is used.

## Interaction and accessibility

The native cursor remains. The follower is for a mouse on a fine-pointer device, and hides during dragging, selection, input, scrolling, window blur and reduced motion. The red score annotation has a pause control and pauses offscreen or in hidden pages. Reduced motion keeps the complete static circle and final counter values.

FAQ panels use an interruptible height transition with native disclosure semantics. Their plus marks rotate with expanded state. Search inputs use a quiet boundary and a one-pixel keyboard focus line. Other controls keep visible keyboard focus. The full-screen navigation and search dialogs contain focus, close with Escape, and return it to their opener.

The default theme follows the system. A selected theme and install tab persist locally. Single-key shortcuts can be disabled in the shortcut sheet. `/` focuses the task filter on the bank and opens Docs/FAQ search elsewhere. `t` changes theme, `g h`, `g s`, and `g t` navigate, and `?` opens help. Text fields and dialogs retain their own keys.

## Media

The source is `demo.mp4`, rendered by `scripts/dev/demo/render.sh` and never committed. The local distribution files are `public/media/demo-720.mp4`, `demo-720.webm`, and `demo-poster.avif`. The player attaches video sources on user interaction. It does not fetch the video during initial page load.

From the repository root, reproduce the transcodes with:

```sh
ffmpeg -i demo.mp4 -map 0:v:0 -map '0:a?' -vf scale=1280:720 \
  -c:v libx264 -preset slow -crf 26 -threads 2 -c:a aac -b:a 96k \
  -movflags +faststart site/public/media/demo-720.mp4

ffmpeg -i demo.mp4 -map 0:v:0 -map '0:a?' -vf scale=1280:720 \
  -c:v libvpx-vp9 -crf 34 -b:v 0 -row-mt 1 -cpu-used 3 -threads 2 \
  -c:a libopus site/public/media/demo-720.webm

ffmpeg -ss 12 -i demo.mp4 -frames:v 1 -vf scale=1280:720 \
  -c:v libaom-av1 -crf 28 -still-picture 1 -cpu-used 6 \
  site/public/media/demo-poster.avif
```

Product screenshots use `astro:assets` WebP output with explicit dimensions. The silent demo has a visible text alternative, associated with the player. The supplied social card stays PNG. Font licences and asset origins are included; see [ASSETS.md](ASSETS.md).

## Deployment

`.github/workflows/pages.yml` builds on relevant pushes to `main` and through manual dispatch. It uses the Node 22 patch pinned in `.nvmrc`, the pinned npm lockfile, type and static checks, a static Pages artifact, and the Pages deployment action. The triggers include website code, banks, README, pyproject version changes, guide pages and media. The workflow uses checkout v7, setup-node v7, upload-pages-artifact v5 and deploy-pages v5.

In the repository’s Pages settings, the build source must be GitHub Actions. The workflow publishes `site/dist` under the configured base. Building this checkout does not commit, push, or deploy it.

## Display font preparation

The checked-in font files are ready for production. To reproduce the smaller display faces after a font-source update, install Python FontTools with its WOFF2 dependency and run `python3 scripts/prepare-display-fonts.py` from `site/`. The script retains the original files and writes the exact headline settings already used in CSS. No font tools run during the website build.

## Dependency maintenance

Astro 7.4.2 replaces the original Astro 5 dependency to include the current security fixes. Node 22.23.4 is the minimum runtime for this release. `npm run check:deps` audits the complete dependency tree, including development tools. Run it before updating packages; the Pages build leaves it out, so a new advisory in a build tool never blocks a docs fix (Dependabot alerts cover that). Update the pinned packages and lockfile together, then run the content, HTML and browser checks.

Funding notices are informational. Deprecation notices identify packages whose maintainers recommend a replacement; they do not by themselves report a vulnerability. Lighthouse currently includes a deprecated OpenTelemetry tracing package through its upstream dependency tree. It has no advisory in the checked audit. No install scripts require approval in the current tree. If a later update adds an installer, review its source and approve only the required package and version. Avoid a blanket forced audit update.
