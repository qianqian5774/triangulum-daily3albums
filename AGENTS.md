# Agent Instructions

## Validation Commands
Run these commands before committing changes when relevant:

- `daily3albums build --tag electronic --verbose`
- After the frontend is introduced, build the UI artifact into `_build/public` with:
  - `npm --prefix ui run build`

## Notes
- If the frontend build command changes, update this file to match the new source directory and output target.
