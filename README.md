# IMDb TV Show Scraper

Python script to fetch TV show data from IMDb and generate TMDB-compatible CSV files.

## Features

- ✅ No API key required
- ✅ Resume capability if interrupted
- ✅ Progress saves every 10 titles
- ✅ Clean CSV with successful results only
- ✅ Automatic retry on HTTP errors
- ✅ Optional rate limiting

## Installation

```bash
pip install cinemagoer
```

## Usage

**Basic:**
```bash
python imdb_tv_scraper.py tv_list.txt
```

**With rate limiting:**
```bash
python imdb_tv_scraper.py tv_list.txt --delay=2
```

**Custom output:**
```bash
python imdb_tv_scraper.py tv_list.txt output.csv --delay=1.5
```

## Input Format

Text file with one TV show per line:
```
Breaking Bad
The Office
Stranger Things
```

## Output Files

- `tv_shows_imdb.csv` - Successful results (TMDB-ready)
- `tv_shows_imdb_failed.txt` - Failure details
- `tv_shows_imdb_failed_list.txt` - Failed titles list

## Resume After Interruption

If interrupted (Ctrl+C), just run the same command again:
```bash
python imdb_tv_scraper.py tv_list.txt

⚠️ Found partial progress at position 245
Resume from position 246? (y/n): y
```

## Rate Limiting

**Default:** No delays (fastest)

**Add delays if getting HTTP errors:**
- `--delay=1` - 1 second between requests
- `--delay=2` - 2 seconds between requests

## CSV Format

Compatible with TMDB import. Columns include:
- Position, IMDb ID, Title, URL
- Rating, Votes, Year, Genres
- Runtime, Release Date, Directors

## Troubleshooting

**Titles with years causing HTTP 405:**
- Use plain titles: "Lost in Space" instead of "Lost in Space (2018)"

**Many HTTP errors:**
- Add `--delay=2` to slow down requests

**Import error:**
```bash
pip install cinemagoer
```

Note: Package is `cinemagoer` but imports as `imdb`

## Performance

- 100 titles: ~2-5 minutes (no delay)
- 400 titles: ~8-20 minutes (no delay)
- With `--delay=2`: roughly double the time

## License

For personal use. IMDb data belongs to IMDb.com.
