#!/usr/bin/env python3
"""
Fetch contest standings from Codeforces API and generate JSON files.
"""

import json
import os
import sys
import requests
from typing import Dict, List, Optional

CONTESTS_INDEX_PATH = 'data/contests/index.json'
CONTESTS_DIR = 'data/contests'

def fetch_contest_list() -> List[Dict]:
    """Fetch list of contests from Codeforces API."""
    url = 'https://codeforces.com/api/contest.list'
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    if data['status'] != 'OK':
        raise Exception(f"API error: {data.get('comment', 'Unknown error')}")
    return data['result']

def fetch_contest_standings(contest_id: int) -> List[Dict]:
    """Fetch standings for a specific contest."""
    url = f'https://codeforces.com/api/contest.standings?contestId={contest_id}'
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    if data['status'] != 'OK':
        raise Exception(f"API error: {data.get('comment', 'Unknown error')}")
    return data['result']['rows']

def generate_standings_json(contest_id: int, contest_name: str, rows: List[Dict]) -> Dict:
    """Generate standings JSON structure."""
    standings = []
    for i, row in enumerate(rows):
        party = row['party']
        members = party.get('members', [])
        handle = members[0]['handle'] if members else f"team_{party.get('teamId', '')}"
        
        problems_solved = sum(1 for p in row['problemResults'] if p['points'] > 0)
        
        standings.append({
            'rank': row['rank'],
            'handle': handle,
            'score': row['points'],
            'problemsSolved': problems_solved
        })
    
    return {
        'contestId': contest_id,
        'contestName': contest_name,
        'standings': standings
    }

def load_contests_index() -> Dict:
    """Load existing contests index."""
    if os.path.exists(CONTESTS_INDEX_PATH):
        with open(CONTESTS_INDEX_PATH, 'r') as f:
            return json.load(f)
    return {'contests': []}

def save_contests_index(index: Dict):
    """Save contests index."""
    os.makedirs(CONTESTS_DIR, exist_ok=True)
    with open(CONTESTS_INDEX_PATH, 'w') as f:
        json.dump(index, f, indent=2)

def save_contest_standings(contest_id: int, data: Dict):
    """Save contest standings to JSON file."""
    os.makedirs(CONTESTS_DIR, exist_ok=True)
    filepath = os.path.join(CONTESTS_DIR, f'contest_{contest_id}.json')
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def update_contest_index(index: Dict, contest_id: int, contest_name: str, date: str):
    """Update contest in index."""
    contests = index.get('contests', [])
    existing = next((c for c in contests if c['id'] == contest_id), None)
    
    contest_data = {
        'id': contest_id,
        'name': contest_name,
        'date': date
    }
    
    if existing:
        idx = contests.index(existing)
        contests[idx] = contest_data
    else:
        contests.append(contest_data)
    
    contests.sort(key=lambda x: x['id'], reverse=True)
    index['contests'] = contests

def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_standings.py <contest_id> [contest_name]")
        print("       python fetch_standings.py --list")
        sys.exit(1)
    
    if sys.argv[1] == '--list':
        try:
            contests = fetch_contest_list()
            for c in contests[:20]:
                print(f"ID: {c['id']}, Name: {c['name']}, Phase: {c['phase']}, Type: {c['type']}")
        except Exception as e:
            print(f"Error fetching contest list: {e}")
            sys.exit(1)
        return
    
    contest_id = int(sys.argv[1])
    contest_name = sys.argv[2] if len(sys.argv) > 2 else f"Contest {contest_id}"
    
    print(f"Fetching standings for contest {contest_id}...")
    
    try:
        rows = fetch_contest_standings(contest_id)
        print(f"Fetched {len(rows)} participants")
        
        standings_data = generate_standings_json(contest_id, contest_name, rows)
        save_contest_standings(contest_id, standings_data)
        print(f"Saved standings to data/contests/contest_{contest_id}.json")
        
        index = load_contests_index()
        update_contest_index(index, contest_id, contest_name, "")
        save_contests_index(index)
        print("Updated contests index")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()