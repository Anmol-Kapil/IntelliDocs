# IntelliDocs verification — 17 November 2026

This report covers the fixes, dependency updates, and checks prepared for the GitHub repository.

## Verified

- Frontend production build passes with Vite 8.3.8 and the matching React plugin.
- npm audit reports zero known vulnerabilities after dependency updates.
- The Vite development server returns HTTP 200.
- Python dependency consistency check passes (`pip check`).
- All 20 backend regression tests pass with offline model substitutes.
- All 19 tests also pass with the actual `all-MiniLM-L6-v2` embedding model.
- Tests exercise real TXT, Markdown, and PDF ingestion, Chroma retrieval and persistence,
  restart recovery, deletion, validation, oversized/empty uploads, chat reset,
  missing configuration, and provider failure responses.
- Groq completion responses are simulated in the regression suite.
- Follow-up verification with the locally configured key confirmed live chat, summary,
  and comparison all return HTTP 200 with nonempty responses using synthetic documents.
- Fixed a local certificate verification failure using the system trust store and
  changed the unavailable Llama model to `openai/gpt-oss-20b`.

## Fixed

- Invalid JSON, question types, document IDs, and retrieval depth now return JSON errors.
- Missing documents return 404; invalid comparisons return 400.
- Empty and scanned documents are rejected with a useful message.
- Uploads have a 25 MB request limit and file-save failures are handled.
- Retrieval respects the available chunk count and handles an empty index.
- Restart recovery restores the upload path so deleting a recovered document removes its file.
- Database/file deletion errors propagate instead of reporting success.
- Missing Groq configuration returns 503; generation failures return 502.
- Frontend messages are stored per document scope; older summary requests cannot overwrite newer ones.
- Document-list connection failures are visible with a Retry action.
- Frontend API requests use a development proxy and a configurable deployment URL.
- Patched frontend dependencies, declared the Node version requirement, and corrected setup instructions.

## Remaining limits and suggested improvements

- Live AI behavior was checked with small synthetic documents; quality across real documents still needs evaluation.
- Browser visual and interaction checks remain incomplete because the available browser could not reach the local server.
- Shared backend chat histories are not isolated by user/session. Add session isolation and authentication before multi-user hosting.
- Add automated browser tests and CI for uploads, scope changes, chat, summaries, and comparisons.
- Citation cards represent retrieved chunks; generated citation correctness and relevance percentages need better validation.
- Replace deprecated LangChain community loaders with maintained alternatives.
- The README now includes the application screenshot and consolidates the duplicated sections.
  The application's DocMind AI branding can be aligned with IntelliDocs in a future UI update.

## Repeat checks

From the root using the backend virtual environment:

```powershell
backend/.venv/Scripts/python -m unittest discover -s backend/tests -v
backend/.venv/Scripts/python -m pip check
```

To test real embeddings in PowerShell (downloads model files on the first run):

```powershell
$env:INTELLIDOCS_LIVE_EMBEDDINGS = '1'
$env:HF_HOME = Join-Path (Get-Location) 'backend/.cache/huggingface'
backend/.venv/Scripts/python -m unittest discover -s backend/tests -v
```

From `frontend`:

```powershell
npm ci
npm run build
npm audit
```
