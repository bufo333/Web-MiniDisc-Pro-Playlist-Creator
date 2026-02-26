import argparse
import sys

from playlist_sync import csv_utils, scraper


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync Apple Music playlist to MiniDisc CSV"
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Input CSV file path"
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output CSV file path"
    )
    parser.add_argument(
        "-u", "--url",
        required=True,
        help="Apple Music playlist URL"
    )

    args = parser.parse_args()

    try:
        original_rows = csv_utils.read_csv(args.input)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        return 1

    try:
        playlist_name, track_displays = scraper.fetch_playlist(args.url)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"Error fetching playlist: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1

    merged_rows, warnings = csv_utils.inject_names_by_index(
        original_rows,
        playlist_name,
        track_displays
    )

    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)

    try:
        csv_utils.write_csv(args.output, merged_rows)
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        return 1

    print(f"Successfully wrote {len(merged_rows)} rows to {args.output}")
    print(f"Playlist: {playlist_name}")
    print(f"Tracks: {len(track_displays)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
