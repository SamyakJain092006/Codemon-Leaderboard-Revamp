#!/usr/bin/env python3
"""
Fetch contest standings from Codeforces API with authenticated requests.

Produces data/contests/contest_<id>.json containing per-participant
rank, score, solved count and per-problem results with best submission
times (for First-AC detection).

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

# Output directories
CONTESTS_DIR = os.path.join('data', 'contests')
CONTESTS_INDEX_PATH = os.path.join(CONTESTS_DIR, 'index.json')

# Safely loads the CODEFORCES_API_KEY and CODEFORCES_API_SECRET
def load_credentials():
    """Load API credentials from environment variables OF Github."""
    api_key = os.environ.get('CODEFORCES_API_KEY')
    api_secret = os.environ.get('CODEFORCES_API_SECRET')
    return api_key, api_secret

# Safely loads the CODEFORCES_API_KEY and CODEFORCES_API_SECRET for Private Groups in Codeforces and terminates if the key or secret is not available
def load_group_credentials():
    """Load group contest API credentials from environment variables."""
    api_key = os.environ.get('CODEFORCES_API_KEY')
    api_secret = os.environ.get('CODEFORCES_API_SECRET')
    if not api_key or not api_secret:
        raise SystemExit(
            'Group contests require Codeforces API credentials.\n'
            'Generate them at https://codeforces.com/settings/api (you must '
            'be an admin of the group), then export:\n'
            '  export CODEFORCES_API_KEY=...\n'
            '  export CODEFORCES_API_SECRET=...'
        )
    return api_key, api_secret


def api_get(url, api_key, api_secret, contest_id, is_group=False, group_id=None):
    """Make API request to Codeforces.

    Signs the request with apiKey, time, and apiSig using the Codeforces
    authentication protocol when credentials are provided.
    Falls back to unauthenticated request if api_key/api_secret are None.
    """
    # If no credentials, make unauthenticated request (add contestId to URL)
    if not api_key and not api_secret:
        url = f'{url}?contestId={contest_id}'
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if payload['status'] != 'OK':
            raise Exception(f"API error: {payload.get('comment', 'Unknown error')}")
        return payload['result']

    rand = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(6))

    # Creating the current UNIX timestamp for authentication
    current_time = str(int(datetime.now(timezone.utc).timestamp()))

    # Building params
    all_params = {
        'apiKey': api_key,
        'contestId': str(contest_id),
        'time': current_time
    }

    # Use the groupCode for private mashups
    if is_group and group_id:
        all_params['groupCode'] = group_id

    # Compute apiSig using the sorted parameter set
    sig_query = urlencode(sorted(all_params.items()))
    sig_source = f'{rand}/contest.standings?{sig_query}#{api_secret}'
    api_sig = rand + hashlib.sha512(sig_source.encode()).hexdigest()

    # Final params for the request including the signature
    all_params['apiSig'] = api_sig

    response = requests.get(url, params=all_params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload['status'] != 'OK':
        raise Exception(f"API error: {payload.get('comment', 'Unknown error')}")
    return payload['result']

# Wrapper function for private group contests mashup, ensuring api_key and api_secret are present before calling the api_get
def fetch_group_contest(group_id, contest_id):
    """Fetch standings for a group (mashup) contest.

    Uses the standard contest.standings endpoint with API v2 authentication
    and the groupCode parameter workaround to access private mashups.
    """
    api_key, api_secret = load_group_credentials()

    try:
        # Pass both is_group=True and the group_id to api_get
        return api_get(STANDINGS_API, api_key, api_secret, contest_id, is_group=True, group_id=group_id)
    except Exception as e:
        raise Exception(f"API error: {e} (Check that your API keys are valid and your account administers group {group_id})")

# Extracts details such as contest, problems, and problem labels from raw Codeforces responses.
def build_contest_json(contest_id, contest_name, result, is_group=False):
    """Build the lean JSON structure from API result.

    Extracts only what compute_scores.py needs:
    - per-participant rank, score, solved count
    - per-problem results with best submission times
    """
    contest_info = result['contest']
    problems = result.get('problems', [])
    problem_indices = [p['index'] for p in problems]

    # Filtering out non-official participants (ignoring practice attempts, manager tests, out-of-competition submissions, and ghost users)
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

    # Sorting the standings by overall rank and building the final JSON file directory
    standings.sort(key=lambda x: x['rank'])

    return {
        'contestId': contest_id,
        'contestName': contest_name or contest_info.get('name', f'Contest {contest_id}'),
        'startTime': contest_info.get('startTimeSeconds'),
        'durationSeconds': contest_info.get('durationSeconds'),
        'problems': [{'index': p['index'], 'name': p['name']} for p in problems],
        'standings': standings,
    }

# Reads the master contest catalog file if present; else defaults to an empty list
def load_index():
    """Load the contests index file, or return empty index."""
    if os.path.exists(CONTESTS_INDEX_PATH):
        with open(CONTESTS_INDEX_PATH, 'r') as f:
            return json.load(f)
    return {'contests': []}

# Add or update a contest entry in the index.
def update_index(index, contest_id, contest_name, date):
    
    contests = [c for c in index.get('contests', []) if c['id'] != contest_id]
    contests.append({
        'id': contest_id,
        'name': contest_name,
        'date': date or '',
    })
    index['contests'] = contests

# Save the contests index, sorted by date then ID.
def save_index(index):
    
    contests = sorted(
        index['contests'],
        key=lambda c: (c.get('date') or '9999-12-31', c['id']),
    )
    index['contests'] = contests
    os.makedirs(CONTESTS_DIR, exist_ok=True)
    with open(CONTESTS_INDEX_PATH, 'w') as f:
        json.dump(index, f, indent=2)

# Save the contest JSON to data/contests/contest_<id>.json.
def save_standings(contest_json, contest_id):
    
    os.makedirs(CONTESTS_DIR, exist_ok=True)
    out_path = os.path.join(CONTESTS_DIR, f'contest_{contest_id}.json')
    with open(out_path, 'w') as f:
        json.dump(contest_json, f, indent=2)
    print(f"Saved standings to {out_path}")


def main():
    parser = argparse.ArgumentParser(description='Fetch Codemon contest standings.')
    parser.add_argument('contest_id', type=int, nargs='?', default=None, metavar='contest_id',
                        help='Codeforces contest ID (positional or --contest-id)')
    parser.add_argument('--contest-id', dest='contest_id_opt', type=int,
                        help='Codeforces contest ID (flag form, preferred in scripts)')
    parser.add_argument('contest_name', nargs='?', default=None, metavar='contest_name',
                        help='Display name for the contest (positional or --contest-name)')
    parser.add_argument('--contest-name', dest='contest_name_opt',
                        help='Display name for the contest (flag form)')
    parser.add_argument('--group', dest='group_id', help='Codeforces group ID for mashup contests')
    parser.add_argument('--list', action='store_true', help='List recent public contests')
    args = parser.parse_args()

    # Resolve contest_id from positional or flag form
    contest_id = args.contest_id if args.contest_id is not None else args.contest_id_opt
    # Resolve contest_name from positional or flag form
    contest_name = args.contest_name if args.contest_name is not None else args.contest_name_opt

    if contest_id is None:
        parser.print_usage()
        sys.exit(1)

    # Handle group contests
    is_group = args.group_id is not None
    group_id = args.group_id

    if is_group:
        # Group contest mode
        if not group_id:
            parser.print_usage()
            sys.exit(1)
        print(f"Fetching group contest standings for group {group_id}, contest {contest_id}...")
        try:
            result = fetch_group_contest(group_id, contest_id)
            used_auth = True
        except Exception as e:
            print(f"Error fetching group contest: {e}")
            sys.exit(1)
    else:
        # Individual contest mode
        # Try authenticated request first, fall back to unauthenticated
        api_key, api_secret = load_credentials()
        result = None
        used_auth = False

        if api_key and api_secret:
            try:
                result = api_get(STANDINGS_API, api_key, api_secret, contest_id)
                used_auth = True
            except Exception as e:
                # Auth failed (e.g., invalid credentials, or endpoint doesn't accept auth)
                # Fall back to unauthenticated request
                print(f"Warning: Authenticated request failed ({type(e).__name__}), "
                      "falling back to unauthenticated request")
                api_key, api_secret = None, None

        if result is None:
            # Unauthenticated request
            result = api_get(STANDINGS_API, None, None, contest_id)
            used_auth = False

    # Build the lean JSON and save
    contest_json = build_contest_json(contest_id, contest_name, result, is_group=is_group)
    print(f"Fetched {len(contest_json['standings'])} participants")

    save_standings(contest_json, contest_id)

    # Update the contests index
    index = load_index()
    update_index(index, contest_id, contest_json['contestName'],
                 contest_json.get('startTime'))
    save_index(index)

    auth_msg = " (using API authentication)" if used_auth else ""
    print(f"Updated contests index{auth_msg}")
    print("Done.")


if __name__ == '__main__':
    main()