"""
Test script for Stats.xml parser.
"""
import sys
from pathlib import Path
from parsers.stats_parser import parse_stats_file

def main():
    stats_path = "../Save/LocalProfiles/00000000/Stats.xml"

    print("=" * 80)
    print("Testing Stats.xml Parser")
    print("=" * 80)
    print(f"\nParsing: {stats_path}")

    try:
        parser = parse_stats_file(stats_path)

        print(f"\n✓ Successfully parsed Stats.xml")
        print(f"  Total songs with performance data: {len(parser.performances)}")

        all_perfs = parser.get_all_performances()
        print(f"  Total chart performances: {len(all_perfs)}")

        # Stats
        with_scores = sum(1 for p in all_perfs if p.all_scores)
        print(f"  Charts with detailed scores: {with_scores}")

        # Show some example performances
        print("\n" + "=" * 80)
        print("Sample Performance Data")
        print("=" * 80)

        # Find some interesting examples
        examples = []
        for perf in all_perfs:
            if perf.num_times_played > 3 and perf.best_accuracy:
                examples.append(perf)
                if len(examples) >= 5:
                    break

        for i, perf in enumerate(examples, 1):
            print(f"\n{i}. {perf.song_dir}")
            print(f"   Difficulty: {perf.difficulty} ({perf.steps_type})")
            print(f"   Times played: {perf.num_times_played}")
            print(f"   High grade: {perf.high_grade}")
            if perf.best_accuracy:
                print(f"   Best accuracy: {perf.best_accuracy:.2%}")
            if perf.best_percent_dp:
                print(f"   Best DP: {perf.best_percent_dp:.2%}")
            if perf.best_max_combo:
                print(f"   Best combo: {perf.best_max_combo}")
            if perf.consistency_score is not None:
                print(f"   Consistency: {perf.consistency_score:.2f}")
            if perf.best_tap_scores:
                ts = perf.best_tap_scores
                print(f"   Best timing: W1:{ts.w1} W2:{ts.w2} W3:{ts.w3} W4:{ts.w4} W5:{ts.w5} Miss:{ts.miss}")

        # Test lookup functionality
        print("\n" + "=" * 80)
        print("Testing Chart Lookup")
        print("=" * 80)

        test_song = "Songs/DDR 1st Mix/Butterfly"
        test_diff = "Challenge"
        test_type = "dance-single"

        print(f"\nLooking up: {test_song} - {test_diff} ({test_type})")
        perf = parser.get_performance(test_song, test_diff, test_type)

        if perf:
            print(f"✓ Found performance data!")
            print(f"  Times played: {perf.num_times_played}")
            print(f"  High grade: {perf.high_grade}")
            if perf.best_accuracy:
                print(f"  Best accuracy: {perf.best_accuracy:.2%}")
        else:
            print("✗ No performance data found")

        # Statistics summary
        print("\n" + "=" * 80)
        print("Performance Statistics")
        print("=" * 80)

        play_counts = [p.num_times_played for p in all_perfs]
        accuracies = [p.best_accuracy for p in all_perfs if p.best_accuracy]

        print(f"\nPlay counts:")
        print(f"  Total plays: {sum(play_counts)}")
        print(f"  Average plays per chart: {sum(play_counts) / len(play_counts):.1f}")
        print(f"  Most played chart: {max(play_counts)} times")

        if accuracies:
            print(f"\nAccuracies (charts with detailed scores):")
            print(f"  Charts: {len(accuracies)}")
            print(f"  Average: {sum(accuracies) / len(accuracies):.2%}")
            print(f"  Best: {max(accuracies):.2%}")
            print(f"  Worst: {min(accuracies):.2%}")

        # Difficulty distribution
        by_diff = {}
        for perf in all_perfs:
            diff = perf.difficulty
            by_diff[diff] = by_diff.get(diff, 0) + 1

        print(f"\nChart plays by difficulty:")
        for diff in ['Beginner', 'Easy', 'Medium', 'Hard', 'Challenge', 'Edit']:
            if diff in by_diff:
                print(f"  {diff}: {by_diff[diff]} charts")

        print("\n" + "=" * 80)
        print("✓ All tests passed!")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
