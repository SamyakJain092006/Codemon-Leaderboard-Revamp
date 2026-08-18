# Codemon Leaderboard

A Jamstack-based contest leaderboard system for Codeforces/HackerRank competitions. Built with React, Python, and GitHub Actions.

## Architecture

- **Frontend**: React SPA hosted on GitHub Pages
- **Backend**: Python script fetches data from Codeforces API
- **Database**: Git-as-a-Database (JSON files versioned in Git)
- **CI/CD**: GitHub Actions for automated updates

## Project Structure

```
├── frontend/           # React application
│   ├── src/
│   │   ├── main.jsx    # Entry point
│   │   ├── App.jsx     # Main component
│   │   ├── App.css     # Styles
│   │   └── index.css   # Global styles
│   └── public/         # Static assets
├── scripts/            # Python automation scripts
│   └── fetch_standings.py  # Fetches standings from Codeforces API
├── data/
│   └── contests/       # Contest data (JSON files)
│       ├── index.json  # Contest list index
│       └── contest_<id>.json  # Individual contest standings
├── .github/workflows/  # GitHub Actions
│   └── update-leaderboard.yml
├── package.json        # Frontend dependencies
├── vite.config.js      # Vite configuration
└── index.html          # HTML entry point
```

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- npm

### Installation

```bash
# Install frontend dependencies
npm install

# Install Python dependencies
pip install requests
```

### Development

```bash
# Start development server
npm run dev
```

### Building for Production

```bash
npm run build
```

## Usage

### Fetching Contest Standings

```bash
# Fetch standings for a specific contest
python scripts/fetch_standings.py <contest_id> "<contest_name>"

# List recent contests
python scripts/fetch_standings.py --list
```

### Automated Updates

1. Go to GitHub Actions tab
2. Run "Update Leaderboard" workflow
3. Enter Contest ID and Contest Name
4. Workflow will:
   - Fetch standings from Codeforces API
   - Generate JSON files
   - Commit to repository
   - Build and deploy to GitHub Pages

## Deployment

The site is automatically deployed to GitHub Pages when the workflow runs. Configure in repository settings:

1. Go to Settings > Pages
2. Source: GitHub Actions
3. The workflow handles the rest

## Data Format

### Contest Index (`data/contests/index.json`)

```json
{
  "contests": [
    {
      "id": 123456,
      "name": "Codeforces Round #123",
      "date": "2024-01-15"
    }
  ]
}
```

### Contest Standings (`data/contests/contest_<id>.json`)

```json
{
  "contestId": 123456,
  "contestName": "Codeforces Round #123",
  "standings": [
    {
      "rank": 1,
      "handle": "tourist",
      "score": 1000,
      "problemsSolved": 5
    }
  ]
}
```
