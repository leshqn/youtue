# Deploy — run VIRALWORKS in the cloud (free)

`weekly-content.yml` is a GitHub Actions workflow that runs the engine on a
schedule (Mondays 06:00 UTC / 09:00 EAT) and on demand, generates a film-ready
content plan into `content_plans/`, and commits the engine's learnings back so
the playbook keeps improving.

## Install it (one of two ways)

**A. Paste it in (no extra token permissions needed)**
1. GitHub repo → **Actions** tab → *set up a workflow yourself*
2. Replace the editor contents with `deploy/weekly-content.yml`
3. Name the file `weekly-content.yml` → **Commit changes**

**B. Push it from a clone**
Requires a token with the **Workflows** permission, then:

```bash
mkdir -p .github/workflows
cp deploy/weekly-content.yml .github/workflows/
git add .github/workflows/weekly-content.yml && git commit -m "Add weekly workflow" && git push
```

Once installed, use **Actions → Weekly content plan → Run workflow** to trigger
it immediately instead of waiting for Monday.
