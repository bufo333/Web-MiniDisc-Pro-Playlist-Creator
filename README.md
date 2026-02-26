# Playlist Sync

A tool to sync Apple Music playlists to MiniDisc CSV format.

## Overview

This tool fetches track information from an Apple Music shared playlist URL and fills in the NAME column of a MiniDisc CSV file with "Title - Artist" format.

## Installation

```bash
pip install -r requirements.txt
```

Or with a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

## Usage

### Command Line

```bash
python -m playlist_sync -i input.csv -o output.csv -u "https://music.apple.com/us/playlist/name/pl.u-xxxxx"
```

Arguments:
- `-i, --input`: Input CSV file path (required)
- `-o, --output`: Output CSV file path (required)
- `-u, --url`: Apple Music playlist URL (required)

### Jupyter Notebook

Open `sample.ipynb` and edit the configuration variables:

```python
playlist_csv_path = "metal.csv"   # your original CSV
output_csv_path = "output.csv"    # output CSV
url = "https://music.apple.com/..."  # Apple Music playlist URL
```

Then run the cell.

## CSV Format

The tool expects a CSV with these columns (index 0-10):
- INDEX, GROUP RANGE, GROUP NAME, GROUP FULL WIDTH NAME, NAME, FULL WIDTH NAME, HIMD ALBUM, HIMD ARTIST, DURATION, ENCODING, BITRATE

The NAME column (index 4) is populated with track names from Apple Music.

### Escaped Commas

The tool handles commas in track names by escaping them as `\,`. This preserves fields when the CSV is re-parsed.

## Project Structure

```
playlist/
├── src/playlist_sync/
│   ├── __init__.py       # Package init
│   ├── csv_utils.py      # CSV handling
│   ├── scraper.py        # Apple Music scraping
│   └── __main__.py       # CLI entry point
├── sample.ipynb          # Jupyter notebook interface
├── metal.csv             # Sample input
└── requirements.txt     # Python dependencies
```

## Features

- Fetches playlist name and track info from Apple Music
- Handles escaped commas in CSV fields
- Preserves original NAME when Apple playlist has fewer tracks
- Retry logic with exponential backoff for network requests
- URL validation (must be apple.com)
- Proper error handling

## License

MIT
