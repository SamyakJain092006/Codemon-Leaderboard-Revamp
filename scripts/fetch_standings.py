#!/usr/bin/env python3
"""
Fetch contest standings from Codeforces API with authenticated requests.

Produces data/contests/contest_<id>.json containing per-participant
rank, score, solved count and per-problem results with best submission
times (for First-AC detection).

Usage:
    python fetch_standings.py <contest_id> [contest_name]
    python fetch_standings.py --contest-id ID [--contest-name NAME]

Note: API credentials must be set via environment variables:
    export CODEFORCES_API_KEY=...
    export CODEFORCES_API_SECRET=...
    (Generate them at https://codeforces.com/settings/api)
"""

import argparse
import hashlib
import json
import os
import secrets
import string
import sys
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests

# API endpoints
STANDINGS_API = 'https://codeforces.com/api/contest.standings'
LIST_API = 'https://codeforces.com/api/contest.list'

# Output directories
CONTESTS_DIR = os.path.join('data', 'contests')
CONTESTS_INDEX_PATH = os.path.join(CONTESTS_DIR, 'index.json')


def load_credentials():
    """Load API credentials from environment variables."""
    api_key = os.environ.get('CODEFORCES_API_KEY')
    api_secret = os.environ.get('CODEFORCES_API_SECRET')
    return api_key, api_secret


def make_api_sig(method, params, api_secret):
    """Generate Codeforces API v2 signature."""
    rand = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(6))
    query = urlencode(sorted(params.items()))
    sig_source = f'{rand}/{method}?{query}{api_secret}'
    return rand + hashlib.sha512(sig_source.encode()).hexdigest()


def api_get(url, api_key, api_secret, contest_id):
    """Make authenticated API request to Codeforces.

    Signs the request with apiKey and apiSig using the Codeforces
    authentication protocol. Properly handles URLs that already contain
    query parameters (e.g. ?contestId=XXX).
    """
    rand = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(6))

    # Parse existing URL to merge params correctly (avoids double ?)
    from urllib.parse import urlparse, parse_qs, urlunparse
    parsed = urlparse(url)
    existing_params = parse_qs(parsed.query, keep_blank_values=True)

    # Build params: existing params + apiKey + contestId
    all_params = dict(existing_params)
    all_params['apiKey'] = api_key
    all_params['contestId'] = str(contest_id)

    # Compute apiSig using the full parameter set
    sig_query = urlencode(sorted(all_params.items()))
    sig_source = f'{rand}/contest.standings?{sig_query}{api_secret}'
    api_sig = rand + hashlib.sha512(sig_source.encode()).hexdigest()

    # Final params for the request
    final_params = {'apiKey': api_key, 'apiSig': api_sig, 'contestId': str(contest_id)}

    response = requests.get(url, params=final_params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload['status'] != 'OK':
        raise Exception(f"API error: {payload.get('comment', 'Unknown error')}")
    return payload['result']


def build_contest_json(contest_id, contest_name, result):
    """Build the lean JSON structure from API result.

    Extracts only what compute_scores.py needs:
    - per-participant rank, score, solved count
    - per-problem results with best submission times
    """
    contest_info = result['contest']
    problems = result.get('problems', [])
    problem_indices = [p['index'] for p in problems]

    standings = []
    for row in result.get('rows', []):
        party = row['party']
        if party.get('participantType') != 'CONTESTANT' or party.get('ghost'):
            continue

        members = party.get('members', [])
        if not members:
            continue

        problem_results = []
        solved_count = 0
        for index, pr in zip(problem_indices, row.get('problemResults', [])):
            solved = pr['points'] > 0
            if solved:
                solved_count += 1
            problem_results.append({
                'index': index,
                'solved': solved,
                'bestSubmissionTimeSeconds': pr.get('bestSubmissionTimeSeconds'),
            })

        standings.append({
            'rank': row['rank'],
            'handle': members[0]['handle'],
            'score': row['points'],
            'problemsSolved': solved_count,
            'problemResults': problem_results,
        })

    standings.sort(key=lambda x: x['rank'])

    return {
        'contestId': contest_id,
        'contestName': contest_name or contest_info.get('name', f'Contest {contest_id}'),
        'startTime': contest_info.get('startTimeSeconds'),
        'durationSeconds': contest_info.get('durationSeconds'),
        'problems': [{'index': p['index'], 'name': p['name']} for p in problems],
        'standings': standings,
    }


def load_index():
    """Load the contests index file, or return empty index."""
    if os.path.exists(CONTESTS_INDEX_PATH):
        with open(CONTESTS_INDEX_PATH, 'r') as f:
            return json.load(f)
    return {'contests': []}


def update_index(index, contest_id, contest_name, date):
    """Add or update a contest entry in the index."""
    contests = [c for c in index.get('contests', []) if c['id'] != contest_id]
    contests.append({
        'id': contest_id,
        'name': contest_name,
        'date': date or '',
    })
    index['contests'] = contests


def save_index(index):
    """Save the contests index, sorted by date then ID."""
    contests = sorted(
        index['contests'],
        key=lambda c: (c.get('date') or '9999-12-31', c['id']),
    )
    index['contests'] = contests
    os.makedirs(CONTESTS_DIR, exist_ok=True)
    with open(CONTESTS_INDEX_PATH, 'w') as f:
        json.dump(index, f, indent=2)


def save_standings(contest_json, contest_id):
    """Save the contest JSON to data/contests/contest_<id>.json."""
    os.makedirs(CONTESTS_DIR, exist_ok=True)
    out_path = os.path.join(CONTESTS_DIR, f'contest_{contest_id}.json')
    with open(out_path, 'w') as f:
        json.dump(contest_json, f, indent=2)
    print(f"Saved standings to {out_path}")


def main():
    parser = argparse.ArgumentParser(description='Fetch Codemon contest standings.')
    parser.add_argument('contest_id', type=int,
                        help='Codeforces contest ID')
    parser.add_argument('contest_name', nargs='?', default=None,
                        help='Display name for the contest (optional)')
    args = parser.parse_args()

    # Load credentials - will raise SystemExit if not set
    api_key, api_secret = load_credentials()
    if not api_key or not api_secret:
        raise SystemExit(
            'API credentials required. Set CODEFORCES_API_KEY and '
            'CODEFORCES_API_SECRET environment variables, or provide '
            'them via the environment.'
        )

    # Fetch contest standings via authenticated API call
    print(f"Fetching standings for contest {args.contest_id}"
          + (f" ('{args.contest_name}')" if args.contest_name else "") + "...")
    try:
        result = api_get(STANDINGS_API, api_key, api_secret, args.contest_id)
    except Exception as e:
        print(f"Error fetching contest: {e}")
        sys.exit(1)

    # Build the lean JSON and save
    contest_json = build_contest_json(args.contest_id, args.contest_name, result)
    print(f"Fetched {len(contest_json['standings'])} participants")

    save_standings(contest_json, args.contest_id)

    # Update the contests index
    index = load_index()
    update_index(index, args.contest_id, contest_json['contestName'],
                 contest_json.get('startTime'))
    save_index(index)
    print("Updated contests index")

    print("Done.")


if __name__ == '__main__':
    main()