# Daily3Albums Runbook

## Where to find logs

- GitHub Actions runs: **Actions → Build and Deploy Pages**
- Click the latest run to inspect the build job logs and artifact steps.

## Re-run the workflow

1. Open **Actions → Build and Deploy Pages**.
2. Select a failed run.
3. Click **Re-run jobs → Re-run all jobs**.

## Clear / refresh cache

The pipeline caches `.state/` for dedupe and rate limits.

To refresh it:

1. Go to **Actions → Caches** in the repository.
2. Delete the cache keys starting with `state-`.
3. Re-run the workflow to rebuild a clean cache.

## Roll back to last known-good deployment

1. Identify the last successful commit in **Actions** or **Pages → Deployments**.
2. Reset `main` (or create a revert commit) to that SHA.
3. Re-run **Build and Deploy Pages** to publish the known-good build.
