# Prompt: make شاشة كاف work on any TV

Paste everything below the line into an agent that can read GitHub, browse the web and write code.

---

## Your task

You are extending **شاشة كاف**, an Arabic always-on TV screensaver/dashboard, so it runs on as many TV platforms as possible, choosing the best delivery method for each. Research first, then build, then document.

Repository: **https://github.com/DHME1/CAF-TV** (public). Work on a branch and open a pull request against `next`; do not push to `master` directly (changes reach `master` from `next` once tested).

## What already exists (read these first)

- `README.md` — overview, build, URL fragment parameters.
- `src/template.html` — the whole screen: one HTML/CSS/JS page, no framework, no build step. `src/build.py` makes `dist/caftv.html` (fonts and photos inlined, ~2.9 MB, works from `file://` and offline) and `dist/tv.html` (0.3 MB, for the Android app).
- `docs/RECREATE-PROMPT.md` — the full design and behaviour spec. Treat it as the source of truth for what the screen must show.
- `android/` — the current native Android app: a `DreamService` (system screensaver), a settings screen (city, up to 10 teams, the card beside the clock, show filters), and auto-update that downloads `dist/tv.html` from `master` every 6 hours. Built by `.github/workflows/android.yml` and published to the `apk-latest` release.
- `docs/TEST-PLAN.md` — how the Android build is tested; reuse its style.

Settings reach the page through the URL fragment, not a query string:
`caftv.html#city=..&lat=..&lon=..&tz=Asia/Riyadh&teams=<id>,<id>&panel=..&genres=..&langs=..&shows=..&minrating=..`

## Step 1 — research (report before building)

1. Search GitHub for open-source projects that put a clock, dashboard, photo frame or screensaver on TVs, to learn how they deliver to each platform. Starting points (verify, don't assume): screensaver/dream apps for Android TV and Google TV, Samsung Tizen web apps, LG webOS web apps, Fire TV apps, Roku channels, Apple TV/tvOS ambient apps, Chromecast custom receivers, kiosk/dashboard projects such as MagicMirror² and DAKboard-style setups, and "TV kiosk browser" apps.
2. For each platform below, find out from current official docs and those projects:
   - Can it run our HTML page as-is (web app, WebView, browser)? Which JS/CSS features does its engine support? Check `fetch`, CSS `backdrop-filter`, `Intl.DateTimeFormat` with `islamic-umalqura` and `timeZone`, woff2 fonts, and `localStorage`.
   - Can it act as the **system screensaver**, or only as an app the user opens?
   - How is it installed: store, sideload or developer mode? Does developer mode expire?
   - Can it fetch cross-origin APIs (CORS), or does it need a proxy?
3. Platforms to cover at minimum:
   - Android TV / Google TV (already done — note any gaps)
   - Amazon Fire TV
   - Samsung (Tizen)
   - LG (webOS)
   - Hisense/others (VIDAA)
   - Roku
   - Apple TV (tvOS)
   - Chromecast with built-in Cast
   - Any TV with only a web browser
   - A cheap HDMI stick or mini PC as a universal fallback
4. Deliver a short comparison table: platform → recommended method → screensaver possible? → effort → limits. Then **recommend the best overall strategy**, e.g. one hosted web page plus thin per-platform wrappers. List sources with links.

## Step 2 — build

Follow the recommended strategy. Expected shape (adjust if research shows better):

- **One shared page**: keep `src/template.html` as the single source. Any platform fix goes there behind feature detection, never a fork of the page.
- **Hosted version**: publish `dist/` with GitHub Pages so browser-only TVs and Cast receivers can load a URL. Add a lightweight variant that loads photos as separate files instead of inlined base64, for slow TVs.
- **Settings without the Android app**: a simple settings page, usable with a TV remote and also from a phone, that builds the fragment URL. City from the existing region list in `android/app/src/main/java/sa/urtv/screensaver/Cities.java` and the Open-Meteo search, plus two team fields and the show filters. Optionally show a QR code linking to it.
- **Per-platform wrappers** where they add real value (system screensaver, auto-start, offline). Examples: a Tizen `.wgt` and a webOS `.ipk` that bundle the page; a Fire TV build of the existing APK if its screensaver path differs; a Cast receiver; a tvOS or Roku native port **only if** research shows no web path. For those, document the cost instead of building it unless it is small.
- **CI**: extend GitHub Actions to build every package and attach it to a release, like `apk-latest`.

## Hard requirements (do not break)

- Everything in `docs/RECREATE-PROMPT.md`, especially: Arabic RTL, Arabic-Indic digits, Asia/Riyadh time zone handling, never inventing data (hide what failed), keep the last good data on failed refresh, offline fallback for clock, dates, prayer times and Ramadan.
- Team names Arabic (built-in table, then Wikidata, then transliteration); show titles and «S&P 500» stay English.
- No API keys; all data sources stay free.
- Burn-in protection and night dimming must work on every target.
- Do not commit credentials, the Android signing key included: it lives only in the repository's secrets
  (`ANDROID_KEYSTORE_B64`, `ANDROID_KEYSTORE_PASSWORD`; see `.github/tools/make_signing_key.py`).
- The existing Android app and its auto-update must keep working: test it, or at least don't change its files without reason.

## Step 3 — test and document

- Test the page in the oldest engine you target, e.g. an old Chromium via Playwright, or the Tizen/webOS simulators if available. Polyfill or degrade gracefully when a feature is missing; never show a blank screen.
- Add a section per platform to `docs/TEST-PLAN.md` in the same ID/action/expected format.
- Add `docs/INSTALL.md` in **simple Arabic with English commands**: per TV brand, step by step, written for a non-technical person.
- In the PR description: what was built, what was only documented, what you could not test and why.

## Deliverables checklist

- [ ] Research table + recommendation + sources (in the PR and in `docs/PLATFORMS.md`)
- [ ] GitHub Pages hosted screen + light variant
- [ ] Remote/phone-friendly settings page that produces the URL
- [ ] Wrappers/packages for the platforms where they are worth it, built in CI and attached to a release
- [ ] Updated `docs/TEST-PLAN.md`, new `docs/INSTALL.md`
- [ ] PR open against `next`, CI green
