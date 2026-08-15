# AGENTS.md

## Project Overview
Jamstack-based contest leaderboard using a **Git-as-a-Database** model. Contest standings and metadata are stored directly in Git as static JSON files.

## Architecture & Data Flow
- **Data Source**: Codeforces / HackerRank REST APIs.
- **Automated Ingestion**: Python script triggered via GitHub Actions on-demand post-contest to fetch standings, compile `contest_<id>.json`, and commit changes back to the repository.
- **Storage**: Flat JSON files (e.g., `contest_<id>.json`) committed directly to Git (no external database).
- **Frontend**: Single Page Application (HTML/CSS/JS or React) served via CDN (GitHub Pages / Vercel) consuming static JSON data.

## Implementation Guidelines & Constraints
- **No External Database**: Do not introduce dynamic database servers (Postgres, MongoDB, etc.); all contest data must remain versioned JSON in Git.
- **Static Ingestion Pipeline**: Keep data fetching logic in standalone Python scripts designed to run non-interactively in GitHub Actions.
- **Client Data Consumption**: The frontend should fetch and render pre-compiled `contest_<id>.json` files directly from the static host.
