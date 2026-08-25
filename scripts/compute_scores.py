#!/usr/bin/env python3
"""
Compute Codemon scores from fetched contest JSONs.

Applies the Codemon Series scoring rules:
  1. Base points by rank: 1st -> 30 pts, 2nd -> 29 pts, ..., 30th -> 1 pt,
     beyond 30th or zero score -> 0.
  2. First-AC bonus: +2 per problem for the fastest accepted submission.
  3. Streak multiplier on (base + bonus): 2 consecutive scoring contests
     x1.05, 3 x1.10, 4+ x1.15 (capped). A zero-score contest resets it.
  4. Season total = sum of final contest points.

Ranks resolve ties by: most wins, longest streak, best single rank,
earliest reaching their final total.

Outputs:
  - Enriches each data/contests/contest_<id>.json in place with scored fields.
  - Writes data/leaderboard.json with full season details per participant.

Usage:
    python compute_scores.py [repo_root]
"""

import json
import os
import sys
from datetime import datetime, timezone

# Calulcations constants: 
BASE_POINTS_DEPTH = 30
FIRST_AC_BONUS = 2
MULTIPLIERS = {0: 1.00, 1: 1.00, 2: 1.05, 3: 1.10}
MULTIPLIER_CAP = 1.15

# Returns the correspoding multiplier of each participants, based on their current active streak
def multiplier_for(streak):
    if streak <= 3:
        return MULTIPLIERS[streak]
    return MULTIPLIER_CAP

# Constructs the path to index.json
def load_contests(contests_dir):
    index_path = os.path.join(contests_dir, 'index.json')
    if not os.path.exists(index_path):
        raise SystemExit(f"Missing {index_path}. Run fetch_standings.py first.")

    with open(index_path, 'r') as f:
        index = json.load(f)

    contests = []
    for entry in index.get('contests', []):
        path = os.path.join(contests_dir, f"contest_{entry['id']}.json")
        if not os.path.exists(path):
            print(f"Warning: missing {path}, skipping contest {entry['id']}")
            continue
        with open(path, 'r') as f:
            contest = json.load(f)
        contests.append((entry, contest))

    contests.sort(key=lambda item: (
        item[0].get('date')
        or item[1].get('startTime')
        or '9999-12-31',
        item[0]['id'],
    ))
    return contests


def compute_first_ac(standings):
    """Return {problem_index: min_best_submission_time} across solvers."""
    first_ac_times = {}
    for entry in standings:
        for pr in entry.get('problemResults', []):
            if pr['solved'] and pr.get('bestSubmissionTimeSeconds') is not None:
                idx = pr['index']
                t = pr['bestSubmissionTimeSeconds']
                if idx not in first_ac_times or t < first_ac_times[idx]:
                    first_ac_times[idx] = t
    return first_ac_times


def score_base_and_first_ac(contest):
    """Annotate standings with basePoints / firstAC fields; return entries."""
    first_ac_times = compute_first_ac(contest['standings'])

    for entry in contest['standings']:
        rank = entry['rank']
        base_points = 31 - rank if rank and 1 <= rank <= BASE_POINTS_DEPTH else 0
        if entry['problemsSolved'] == 0:
            base_points = 0

        first_ac_problems = [
            pr['index']
            for pr in entry.get('problemResults', [])
            if pr['solved']
            and pr.get('bestSubmissionTimeSeconds') is not None
            and pr['bestSubmissionTimeSeconds'] == first_ac_times.get(pr['index'])
        ]
        first_ac_bonus = FIRST_AC_BONUS * len(first_ac_problems)

        entry['basePoints'] = base_points
        entry['firstACProblems'] = first_ac_problems
        entry['firstACBonus'] = first_ac_bonus
        entry['preStreakTotal'] = base_points + first_ac_bonus
    return contest['standings']


def new_participant(handle):
    return {
        'handle': handle,
        'seasonTotal': 0.0,
        'wins': 0,
        'longestStreak': 0,
        'currentStreak': 0,
        'bestSingleRank': None,
        'contestsParticipated': 0,
        'lastScoredContestIndex': -1,
        'perContest': {},
    }


def apply_streaks_and_totals(contests):
    """Chronological pass assigning streak multipliers and season totals."""
    participants = {}

    for order, (index_entry, contest) in enumerate(contests):
        present = {}
        for entry in contest['standings']:
            present[entry['handle']] = entry

        for handle in sorted(set(present) | set(participants)):
            person = participants.setdefault(handle, new_participant(handle))
            entry = present.get(handle)

            if entry is not None:
                person['contestsParticipated'] += 1
                person['bestSingleRank'] = min(
                    person['bestSingleRank'] if person['bestSingleRank'] is not None else entry['rank'],
                    entry['rank'],
                )
                if entry['rank'] == 1:
                    person['wins'] += 1

            if entry is None or entry['preStreakTotal'] <= 0:
                final_points = 0.0
                multiplier = None
                active_streak = 0
                person['currentStreak'] = 0
            else:
                person['currentStreak'] += 1
                active_streak = person['currentStreak']
                multiplier = multiplier_for(active_streak)
                final_points = round(entry['preStreakTotal'] * multiplier, 2)
                person['lastScoredContestIndex'] = order

            person['longestStreak'] = max(person['longestStreak'], active_streak)
            person['seasonTotal'] = round(person['seasonTotal'] + final_points, 2)

            breakdown = {
                'rank': entry['rank'] if entry else None,
                'problemsSolved': entry['problemsSolved'] if entry else 0,
                'basePoints': entry['basePoints'] if entry else 0,
                'firstACProblems': entry['firstACProblems'] if entry else [],
                'firstACBonus': entry['firstACBonus'] if entry else 0,
                'preStreakTotal': entry['preStreakTotal'] if entry else 0,
                'activeStreak': active_streak,
                'multiplier': multiplier,
                'finalPoints': final_points,
            }
            person['perContest'][str(index_entry['id'])] = breakdown

            if entry is not None:
                entry['activeStreak'] = active_streak
                entry['multiplier'] = multiplier
                entry['finalPoints'] = final_points

    return participants


def build_leaderboard(index_entries, participants):
    ranked = sorted(
        participants.values(),
        key=lambda p: (
            -p['seasonTotal'],
            -p['wins'],
            -p['longestStreak'],
            p['bestSingleRank'] if p['bestSingleRank'] is not None else float('inf'),
            p['lastScoredContestIndex'],
            p['handle'].lower(),
        ),
    )

    result = []
    previous_key = None
    current_rank = 0
    for position, person in enumerate(ranked, start=1):
        key = (
            person['seasonTotal'],
            person['wins'],
            person['longestStreak'],
            person['bestSingleRank'],
            person['lastScoredContestIndex'],
        )
        if key != previous_key:
            current_rank = position
            previous_key = key
        result.append({
            'rank': current_rank,
            'handle': person['handle'],
            'seasonTotal': person['seasonTotal'],
            'wins': person['wins'],
            'longestStreak': person['longestStreak'],
            'currentStreak': person['currentStreak'],
            'bestSingleRank': person['bestSingleRank'],
            'contestsParticipated': person['contestsParticipated'],
            'perContest': person['perContest'],
        })
    return result


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    contests_dir = os.path.join(root, 'data', 'contests')

    contests = load_contests(contests_dir)
    if not contests:
        raise SystemExit('No contest data found.')

    print(f"Processing {len(contests)} contest(s):")
    for index_entry, contest in contests:
        print(f"  - [{index_entry['id']}] {contest.get('contestName')}")
        score_base_and_first_ac(contest)

    participants = apply_streaks_and_totals(contests)
    leaderboard = build_leaderboard([e for e, _ in contests], participants)

    for _, contest in contests:
        out_path = os.path.join(contests_dir, f"contest_{contest['contestId']}.json")
        save_json(out_path, contest)

    leaderboard_data = {
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'totalContests': len(contests),
        'contests': [
            {
                'id': index_entry['id'],
                'name': contest.get('contestName'),
                'date': index_entry.get('date') or contest.get('startTime'),
            }
            for index_entry, contest in contests
        ],
        'participants': leaderboard,
    }
    leaderboard_path = os.path.join(root, 'data', 'leaderboard.json')
    save_json(leaderboard_path, leaderboard_data)

    print(f"Ranked {len(leaderboard)} participants")
    top = leaderboard[:5]
    for person in top:
        print(f"  #{person['rank']} {person['handle']}: {person['seasonTotal']} pts "
              f"(wins={person['wins']}, streak={person['longestStreak']})")
    print(f"Saved leaderboard to {leaderboard_path}")


if __name__ == '__main__':
    main()
