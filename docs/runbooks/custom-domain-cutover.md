# Custom Domain Cutover Runbook

Target canonical public URL:

```text
https://triangulumdaily.space/
```

Compatible `www` URL after GitHub Pages and DNS finish:

```text
https://www.triangulumdaily.space/
```

The site is static. Do not add a backend, database, login, comments, player service, visitor-side writes, runtime external music API calls, GeoDNS, CDN routing, R2, S3, server functions, or any new hosting provider integration for this cutover.

## Codex-Completed Repository Readiness

- UI data and asset paths are built from Vite `BASE_URL`/`resolvePublicPath()` and are compatible with deployment from `/`.
- HashRouter keeps public routes at `#/` and `#/archive`, so direct static hosting from the root does not need server-side route rewrites.
- `scripts/self_check.py` rejects public artifacts that reintroduce the old production project-site paths:
  - `qianqian5774.github.io/triangulum-daily3albums`
  - `/triangulum-daily3albums/`
- The Pages workflow reads optional repository variable `DAILY3ALBUMS_PAGES_BASE_URL` for archive seed restore.
- No repository root `CNAME` file is required for the current GitHub Actions Pages deployment model.

## Human Manual Operations

Do these from GitHub and Porkbun manually. Do not commit account pages, DNS challenge values, contact information, tokens, or screenshots with private data.

1. In GitHub account settings, start domain verification for:

```text
triangulumdaily.space
```

2. Add GitHub's TXT verification record in Porkbun, then complete verification in GitHub.
3. In this repository's GitHub Pages settings, set the custom domain to:

```text
triangulumdaily.space
```

4. In Porkbun DNS, remove parking/default records such as records pointing to:

```text
pixie.porkbun.com
```

5. Add apex A records:

```text
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153
```

6. Optionally add apex AAAA records:

```text
2606:50c0:8000::153
2606:50c0:8001::153
2606:50c0:8002::153
2606:50c0:8003::153
```

7. Add the `www` CNAME:

```text
Host: www
Answer: qianqian5774.github.io
```

Do not point `www` to `qianqian5774.github.io/triangulum-daily3albums/`.
Do not point `www` to `triangulumdaily.space`.
Do not add wildcard DNS records such as `*.triangulumdaily.space`.

8. Wait for DNS propagation and for GitHub Pages DNS checks to pass.
9. Enable GitHub Pages `Enforce HTTPS` only after GitHub allows it.
10. After `https://triangulumdaily.space/data/index.json` is reachable, set repository variable:

```text
DAILY3ALBUMS_PAGES_BASE_URL=https://triangulumdaily.space/
```

11. Trigger the Pages workflow manually:

```text
Build and Deploy Pages (Daily)
```

12. Verify the live site.

## Post-Cutover Verification

Run these from Windows PowerShell:

```powershell
Resolve-DnsName triangulumdaily.space -Type A
Resolve-DnsName triangulumdaily.space -Type AAAA
Resolve-DnsName www.triangulumdaily.space -Type CNAME

curl.exe -I http://triangulumdaily.space/
curl.exe -I https://triangulumdaily.space/
curl.exe -I https://www.triangulumdaily.space/
```

Open these browser checks:

```text
https://triangulumdaily.space/
https://triangulumdaily.space/#/archive
https://triangulumdaily.space/#/?debug_time=2026-06-27T05:59:50
https://triangulumdaily.space/#/?debug_time=2026-06-27T06:00:10
https://triangulumdaily.space/#/?debug_time=2026-06-27T12:00:10
https://triangulumdaily.space/#/?debug_time=2026-06-27T18:00:10
```

Check the standard UI surfaces and terms:

- Today Page loads from the root URL.
- Archive Page loads from `#/archive`.
- HUD, BJT Clock, Status Badge, Today Timeline, Slot, Album Card, Treatment Viewer, Share Card Dialog, Ambient Overlay, and Mobile Layout render normally.
- Status Badge is not stuck in `ERROR`.
- Offline State before 06:00 BJT is normal; do not call normal Offline State a BSOD.
- `debug_time` shows correct Slot unlock behavior at 06:00, 12:00, and 18:00 BJT.
- `data/today.json`, `data/index.json`, and archive JSON load from the root deployment.
- Album Card covers load, or use a valid fallback.
- Share Card Dialog opens.
- Browser console has no root-domain public-path 404s.
- There is no full-page Horizontal Overflow in Mobile Layout.

## Rollback

If DNS or Pages custom-domain setup fails:

1. Remove or unset repository variable `DAILY3ALBUMS_PAGES_BASE_URL` so archive seed restore falls back to the existing GitHub Pages project URL.
2. Revert the GitHub Pages custom domain setting if needed.
3. Restore the previous DNS records only if they were known-good and do not include parking records that conflict with GitHub Pages.
4. Trigger `Build and Deploy Pages (Daily)` again and verify the default GitHub Pages deployment.

If a repository change breaks the site, revert the commit or merge a fix, then trigger the Pages workflow again.

## Mirror-Site Notes

Main site remains canonical:

```text
https://triangulumdaily.space/
```

Future mirror candidates may be:

```text
https://hk.triangulumdaily.space/
https://sg.triangulumdaily.space/
```

Mirror candidates should reuse the same `_build/public` static artifact. Mirrors must not introduce backend behavior, visitor-side writes, runtime external music API calls, login, comments, database, player service, marketplace, or dynamic personalization.

Do not add GeoDNS, CDN routing, DNS records, deployment secrets, or provider-specific mirror workflow in this task.
