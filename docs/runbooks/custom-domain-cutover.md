# Custom-domain maintenance runbook

## Status and boundary

The canonical production URL is https://triangulumdaily.space/. GitHub Pages serves the static artifact from the normal Build and Deploy Pages (Daily) workflow.

This is a maintenance and incident reference, not a routine deployment instruction. Do not add a backend, database, login, comments, player service, visitor-side writes, runtime music APIs, a new hosting provider, or DNS-based dynamic application behavior while maintaining the domain.

## Deployment invariants

- Vite uses a relative base path and the UI resolves static data/assets through resolvePublicPath().
- Hash routes keep the current Record Shop at #/, with supporting #/today and #/archive surfaces.
- The daily workflow can use DAILY3ALBUMS_PAGES_BASE_URL to restore the published archive seed.
- The public site reads data/today.json, data/index.json, archive JSON, assets/cover-manifest.js, and same-origin cover assets from the canonical deployment.

## Verify after a Pages or DNS change

1. Confirm the Pages workflow deployed successfully.
2. Request the canonical root, data/index.json, data/today.json, and assets/cover-manifest.js over HTTPS.
3. Open the root in a real browser and check the Record Shop exterior, door transition, current Today inventory, one History date, and Treatment Viewer.
4. Use debug_time only as a deterministic inspection aid. Check 07:59, 08:00, 12:30, and 16:00 BJT to confirm the expected 0 / 3 / 6 / 9 visibility.
5. Check browser errors and console output. Verify covers resolve from same-origin assets when materialized and fall back locally without blocking the scene.

## DNS or domain incident

Keep the existing GitHub Pages custom-domain configuration and repository variable unless an inspected failure proves they are the cause. If a domain setting must be changed, record the prior known-good value in the change review, let GitHub Pages complete DNS/HTTPS validation, then rerun the normal Pages workflow and perform the verification above.

For a product-code regression, use a reviewed revert or focused fix; do not compensate by creating a separate mirror, manually publishing JSON, or bypassing the archive and contract checks.
