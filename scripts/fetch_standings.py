#!/usr/bin/env python3
"""
Fetch contest standings from the Codeforces API into lean JSON files.

Produces data/contests/contest_<id>.json containing only what
compute_scores.py needs: per-participant rank, score, solved count and
per-problem results with best submission times (for First-AC detection).

Group contests
use the authenticated group.contest.standings endpoint and require API
credentials generated at https://codeforces.com/settings/api:

    export CODEFORCES_API_KEY=...
    export CODEFORCES_API_SECRET=...

Usage:
    python fetch_standings.py <contest_id> [contest_name]
    python fetch_standings.py <contest_id> [contest_name] --group GROUP_ID
    python fetch_standings.py --contest-id ID [--contest-name NAME] --group GROUP_ID
    python fetch_standings.py --list

Note: prefer flag form (--contest-id/--contest-name) in scripts; combining
--group between the two positional arguments trips an argparse limitation.
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

STANDINGS_API = 'https://codeforces.com/api/contest.standings'
GROUP_STANDINGS_API = 'contest.standings'
LIST_API = 'https://codeforces.com/api/contest.list'

CONTESTS_DIR = os.path.join('data', 'contests')
CONTESTS_INDEX_PATH = os.path.join(CONTESTS_DIR, 'index.json')


def make_api_sig(method, params, api_secret):
    rand = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(6))
    query = urlencode(sorted(params.items()))
    sig_source = f'{rand}/{method}?{query}{api_secret}'
    return rand + hashlib.sha512(sig_source.encode()).hexdigest()


def api_get(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload['status'] != 'OK':
        raise Exception(f"API error: {payload.get('comment', 'Unknown error')}")
    return payload['result']


def fetch_contest_list():
    return api_get(LIST_API)


def fetch_contest(contest_id):
    return api_get(f'{STANDINGS_API}?contestId={contest_id}')


def load_group_credentials():
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


def fetch_group_contest(group_id, contest_id):
    api_key, api_secret = load_group_credentials()
    params = {'groupId': group_id, 'contestId': str(contest_id)}
    signed = {
        **params,
        'apiKey': api_key,
        'apiSig': make_api_sig(GROUP_STANDINGS_API, params, api_secret),
    }
    response = requests.get(
        f'https://codeforces.com/api/{GROUP_STANDINGS_API}', params=signed, timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload['status'] != 'OK':
        comment = payload.get('comment', 'Unknown error')
        if 'authorization' in comment.lower() or 'apikey' in comment.lower():
            comment += (
                ' (check that CODEFORCES_API_KEY/CODEFORCES_API_SECRET are valid '
                f'and your account administers group {group_id})'
            )
        raise Exception(f'API error: {comment}')
    return payload['result']


def to_iso_time(epoch_seconds):
    if not epoch_seconds:
        return None
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


def build_contest_json(contest_id, contest_name, result):
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
        'startTime': to_iso_time(contest_info.get('startTimeSeconds')),
        'durationSeconds': contest_info.get('durationSeconds'),
        'problems': [{'index': p['index'], 'name': p['name']} for p in problems],
        'standings': standings,
    }


def load_index():
    if os.path.exists(CONTESTS_INDEX_PATH):
        with open(CONTESTS_INDEX_PATH, 'r') as f:
            return json.load(f)
    return {'contests': []}


def update_index(index, contest_id, contest_name, date):
    contests = [c for c in index.get('contests', []) if c['id'] != contest_id]
    contests.append({
        'id': contest_id,
        'name': contest_name,
        'date': date or '',
    })
    index['contests'] = contests


def save_index(index):
    contests = sorted(
        index['contests'],
        key=lambda c: (c.get('date') or '9999-12-31', c['id']),
    )
    index['contests'] = contests
    os.makedirs(CONTESTS_DIR, exist_ok=True)
    with open(CONTESTS_INDEX_PATH, 'w') as f:
        json.dump(index, f, indent=2)


def clean_name(name):
    if name is None:
        return None
    return name.strip().strip('"').strip("'").strip()


def main():
    parser = argparse.ArgumentParser(description='Fetch Codemon contest standings.')
    parser.add_argument('contest_id_pos', type=int, nargs='?', metavar='contest_id',
                        help='Codeforces contest ID (positional form)')
    parser.add_argument('contest_name_pos', nargs='?', metavar='contest_name',
                        help='Display name for the contest (positional form)')
    parser.add_argument('--contest-id', dest='contest_id_opt', type=int,
                        help='Codeforces contest ID (flag form, preferred in scripts)')
    parser.add_argument('--contest-name', dest='contest_name_opt',
                        help='Display name for the contest (flag form)')
    parser.add_argument('--group', dest='group_id', help='Codeforces group ID for mashup contests')
    parser.add_argument('--list', action='store_true', help='List recent public contests')
    args = parser.parse_args()

    if args.list:
        try:
            contests = fetch_contest_list()
            for c in contests[:20]:
                print(f"ID: {c['id']}, Name: {c['name']}, Phase: {c['phase']}")
        except Exception as e:
            print(f"Error fetching contest list: {e}")
            sys.exit(1)
        return

    contest_id = args.contest_id_pos if args.contest_id_pos is not None else args.contest_id_opt
    raw_name = args.contest_name_pos if args.contest_name_pos is not None else args.contest_name_opt
    if contest_id is None:
        parser.print_usage()
        sys.exit(1)

    group_id = args.group_id.strip() if args.group_id else None
    contest_name = clean_name(raw_name)

    print(f"Invocation: contest_id={contest_id} "
          f"group={group_id or '-'} name='{contest_name or '-'}'")

    print(f"Fetching standings for contest {contest_id}"
          + (f" (group {group_id})" if group_id else "") + "...")
    try:
        if group_id:
            result = fetch_group_contest(group_id, contest_id)
        else:
            result = fetch_contest(contest_id)

        contest_json = build_contest_json(contest_id, contest_name, result)
        print(f"Fetched {len(contest_json['standings'])} participants")

        os.makedirs(CONTESTS_DIR, exist_ok=True)
        out_path = os.path.join(CONTESTS_DIR, f'contest_{contest_id}.json')
        with open(out_path, 'w') as f:
            json.dump(contest_json, f, indent=2)
        print(f"Saved standings to {out_path}")

        index = load_index()
        update_index(index, contest_id, contest_json['contestName'], contest_json['startTime'])
        save_index(index)
        print("Updated contests index")
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
