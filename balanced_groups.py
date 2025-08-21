#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "numpy",
# ]
# ///

#!/usr/bin/env python3
"""
Group Balancer CLI - Create balanced groups with minimal overlap
Usage: python group_balancer.py participants.txt [options]
"""

import argparse
import itertools
import random
import sys
from collections import defaultdict, Counter
from pathlib import Path
import json
import numpy as np


class GroupBalancer:
    def __init__(self, people, group_size=4):
        self.people = list(people)
        self.group_size = group_size
        self.pair_counts = defaultdict(int)
        self.session_history = []

    def generate_session(self, num_groups=None):
        """Generate one session of balanced groups"""
        if num_groups is None:
            num_groups = len(self.people) // self.group_size

        available_count = num_groups * self.group_size
        if len(self.people) < available_count:
            raise ValueError(f"Not enough people ({len(self.people)}) for {num_groups} groups of {self.group_size}")

        # Select people for this session (rotate if more people than needed)
        if len(self.people) > available_count:
            # Rotate starting position to give everyone chances
            start_idx = len(self.session_history) % len(self.people)
            selected_people = (self.people[start_idx:] + self.people[:start_idx])[:available_count]
        else:
            selected_people = self.people[:available_count]

        best_groups = None
        best_score = float('inf')

        # Try multiple random arrangements and pick the best one
        for _ in range(min(1000, len(selected_people) * 50)):
            shuffled = selected_people.copy()
            random.shuffle(shuffled)

            groups = [shuffled[i:i+self.group_size]
                     for i in range(0, len(shuffled), self.group_size)]

            score = self._calculate_overlap_score(groups)

            if score < best_score:
                best_score = score
                best_groups = groups

        # Update pair counts
        for group in best_groups:
            for pair in itertools.combinations(group, 2):
                self.pair_counts[tuple(sorted(pair))] += 1

        self.session_history.append({
            'groups': best_groups,
            'score': best_score,
            'participants': selected_people
        })
        return best_groups

    def _calculate_overlap_score(self, groups):
        """Calculate penalty score based on existing pair frequencies"""
        score = 0
        for group in groups:
            for pair in itertools.combinations(group, 2):
                pair_key = tuple(sorted(pair))
                score += self.pair_counts[pair_key] ** 2  # Quadratic penalty
        return score

    def get_pair_statistics(self):
        """Get statistics about pair frequencies"""
        if not self.pair_counts:
            return None

        frequencies = list(self.pair_counts.values())
        return {
            'total_pairs': len(self.pair_counts),
            'min_frequency': min(frequencies),
            'max_frequency': max(frequencies),
            'mean_frequency': round(np.mean(frequencies), 2),
            'std_frequency': round(np.std(frequencies), 2),
            'distribution': dict(Counter(frequencies))
        }

    def save_state(self, filename):
        """Save session history to JSON file"""
        state = {
            'people': self.people,
            'group_size': self.group_size,
            'pair_counts': dict(self.pair_counts),
            'session_history': self.session_history
        }
        with open(filename, 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self, filename):
        """Load session history from JSON file"""
        with open(filename, 'r') as f:
            state = json.load(f)

        self.people = state['people']
        self.group_size = state['group_size']
        self.pair_counts = defaultdict(int, state['pair_counts'])
        self.session_history = state['session_history']


def load_participants(filename):
    """Load participant names from text file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            participants = [line.strip() for line in f if line.strip()]

        if not participants:
            raise ValueError("No participants found in file")

        return participants
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file '{filename}': {e}")
        sys.exit(1)


def print_session(session_num, groups, show_indices=False):
    """Print a formatted session"""
    print(f"\n{'='*20} SESSION {session_num} {'='*20}")
    for i, group in enumerate(groups, 1):
        group_str = ", ".join(group)
        if show_indices:
            print(f"Group {i:2d}: [{len(group)} people] {group_str}")
        else:
            print(f"Group {i:2d}: {group_str}")


def print_statistics(balancer):
    """Print overlap statistics"""
    stats = balancer.get_pair_statistics()
    if not stats:
        print("\nNo statistics available yet.")
        return

    print(f"\n{'='*20} STATISTICS {'='*20}")
    print(f"Total unique pairs: {stats['total_pairs']}")
    print(f"Pair frequency range: {stats['min_frequency']} - {stats['max_frequency']}")
    print(f"Mean pair frequency: {stats['mean_frequency']} ± {stats['std_frequency']}")

    print(f"\nFrequency distribution:")
    for freq, count in sorted(stats['distribution'].items()):
        print(f"  {freq} meetings: {count} pairs")


def print_overlap_matrix(balancer, max_display=20):
    """Print overlap matrix (limited for readability)"""
    if not balancer.pair_counts:
        print("\nNo overlap data available yet.")
        return

    people_list = sorted(balancer.people)[:max_display]
    if len(balancer.people) > max_display:
        print(f"\nOverlap Matrix (showing first {max_display} people):")
    else:
        print(f"\nOverlap Matrix:")

    print("=" * (len(people_list) * 4 + 10))

    # Print header
    print(f"{'':>10}", end="")
    for person in people_list:
        print(f"{person[:3]:>4}", end="")
    print()

    # Print matrix
    for i, person1 in enumerate(people_list):
        print(f"{person1[:9]:>10}", end="")
        for j, person2 in enumerate(people_list):
            if i == j:
                print(f"{'—':>4}", end="")
            elif i < j:
                pair_key = tuple(sorted([person1, person2]))
                count = balancer.pair_counts.get(pair_key, 0)
                print(f"{count:>4}", end="")
            else:
                print(f"{'':>4}", end="")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Generate balanced groups with minimal overlap",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python group_balancer.py participants.txt
  python group_balancer.py participants.txt --sessions 3 --group-size 5
  python group_balancer.py participants.txt --load-state history.json --sessions 2
  python group_balancer.py participants.txt --stats-only --load-state history.json
        """
    )

    parser.add_argument('participants_file',
                       help='Text file with participant names (one per line)')
    parser.add_argument('--sessions', '-s', type=int, default=1,
                       help='Number of sessions to generate (default: 1)')
    parser.add_argument('--group-size', '-g', type=int, default=4,
                       help='Size of each group (default: 4)')
    parser.add_argument('--num-groups', '-n', type=int,
                       help='Number of groups per session (default: all participants)')
    parser.add_argument('--save-state', metavar='FILE',
                       help='Save session history to JSON file')
    parser.add_argument('--load-state', metavar='FILE',
                       help='Load previous session history from JSON file')
    parser.add_argument('--show-stats', action='store_true',
                       help='Show overlap statistics after generation')
    parser.add_argument('--show-matrix', action='store_true',
                       help='Show overlap matrix after generation')
    parser.add_argument('--stats-only', action='store_true',
                       help='Only show statistics, don\'t generate new sessions')
    parser.add_argument('--seed', type=int,
                       help='Random seed for reproducible results')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Only output the groups, no headers or stats')

    args = parser.parse_args()

    # Set random seed if provided
    if args.seed:
        random.seed(args.seed)

    # Load participants
    participants = load_participants(args.participants_file)

    if not args.quiet:
        print(f"Loaded {len(participants)} participants from '{args.participants_file}'")
        if len(participants) <= 20:
            print(f"Participants: {', '.join(participants)}")

    # Initialize balancer
    balancer = GroupBalancer(participants, args.group_size)

    # Load previous state if requested
    if args.load_state:
        if Path(args.load_state).exists():
            balancer.load_state(args.load_state)
            if not args.quiet:
                print(f"Loaded previous state from '{args.load_state}'")
                print(f"Previous sessions: {len(balancer.session_history)}")
        else:
            print(f"Warning: State file '{args.load_state}' not found, starting fresh")

    # Show stats only mode
    if args.stats_only:
        print_statistics(balancer)
        if args.show_matrix:
            print_overlap_matrix(balancer)
        return

    # Validate parameters
    total_needed = args.group_size * (args.num_groups or (len(participants) // args.group_size))
    if total_needed > len(participants):
        print(f"Error: Need {total_needed} participants but only have {len(participants)}")
        sys.exit(1)

    # Generate sessions
    try:
        for session_num in range(1, args.sessions + 1):
            groups = balancer.generate_session(args.num_groups)

            if args.quiet:
                for i, group in enumerate(groups, 1):
                    print(f"Group {i}: {', '.join(group)}")
                if session_num < args.sessions:
                    print()  # Blank line between sessions
            else:
                print_session(session_num, groups)

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Show statistics if requested
    if args.show_stats and not args.quiet:
        print_statistics(balancer)

    if args.show_matrix and not args.quiet:
        print_overlap_matrix(balancer)

    # Save state if requested
    if args.save_state:
        balancer.save_state(args.save_state)
        if not args.quiet:
            print(f"\nSaved session history to '{args.save_state}'")


if __name__ == "__main__":
    main()
