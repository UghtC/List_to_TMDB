#!/usr/bin/env python3
"""
IMDb TV Show Data Scraper for TMDB Import
Uses Cinemagoer (formerly IMDbPY) to fetch TV show data from IMDb
"""

import csv
import time
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from imdb import Cinemagoer

# Suppress verbose imdbpy error traces and tracebacks
logging.getLogger('imdbpy').setLevel(logging.CRITICAL + 1)
logging.getLogger('imdbpy').addHandler(logging.NullHandler())
logging.getLogger('imdbpy').propagate = False

def get_progress_file(output_file: str) -> str:
    """Get progress file path."""
    return output_file.rsplit('.', 1)[0] + '_progress.txt'

def get_temp_csv(output_file: str) -> str:
    """Get temporary CSV file path."""
    return output_file.rsplit('.', 1)[0] + '_temp.csv'

def save_progress(output_file: str, position: int):
    """Save current position to progress file."""
    progress_file = get_progress_file(output_file)
    with open(progress_file, 'w') as f:
        f.write(str(position))

def load_progress(output_file: str) -> Optional[int]:
    """Load last processed position from progress file."""
    progress_file = get_progress_file(output_file)
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r') as f:
                return int(f.read().strip())
        except:
            return None
    return None

def append_to_csv(output_file: str, row: Dict, write_header: bool = False):
    """Append a row to CSV file."""
    fieldnames = [
        'Position', 'Const', 'Created', 'Modified', 'Description',
        'Title', 'URL', 'Title Type', 'IMDb Rating', 'Runtime (mins)',
        'Year', 'Genres', 'Num Votes', 'Release Date', 'Directors',
        'Your Rating', 'Date Rated'
    ]
    
    mode = 'w' if write_header else 'a'
    with open(output_file, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

def append_failure(output_file: str, position: int, title: str, error: str):
    """Immediately append failure to failed files."""
    failed_file = output_file.rsplit('.', 1)[0] + '_failed.txt'
    failed_list_file = output_file.rsplit('.', 1)[0] + '_failed_list.txt'
    
    # Write to detailed failed file
    mode = 'a' if os.path.exists(failed_file) else 'w'
    with open(failed_file, mode, encoding='utf-8') as f:
        if mode == 'w':
            f.write("FAILED TITLES\n")
            f.write("=" * 80 + "\n\n")
        f.write(f"Position: {position}\n")
        f.write(f"Title: {title}\n")
        f.write(f"Error: {error}\n")
        f.write("-" * 80 + "\n")
    
    # Write to simple failed list
    with open(failed_list_file, 'a', encoding='utf-8') as f:
        f.write(f"{title}\n")

def search_tv_show(ia: Cinemagoer, title: str, max_retries: int = 3) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Search for a TV show on IMDb and return the best match.
    Uses exponential backoff on rate limit errors.
    
    Args:
        ia: Cinemagoer instance
        title: TV show title to search for
        max_retries: Maximum number of retry attempts
        
    Returns:
        Tuple of (show_data, error_message)
        - show_data: Dictionary with show data or None if not found
        - error_message: Error string if failed, None if successful
    """
    print(f"Searching for: {title}")
    
    for attempt in range(max_retries):
        try:
            # Search for the title
            results = ia.search_movie(title)
            
            if not results:
                error_msg = "No results found"
                print(f"  ⚠️  {error_msg}")
                return None, error_msg
            
            # Find the first TV series in results
            for result in results:
                try:
                    # Get full details
                    ia.update(result, info=['main'])
                    
                    # Check if it's a TV series
                    if result.get('kind') in ['tv series', 'tv mini series']:
                        print(f"  ✓ Found: {result.get('title')} ({result.get('year', 'N/A')})")
                        return result, None
                except Exception as e:
                    # Skip this result and try next one
                    continue
            
            error_msg = "No TV series found in results"
            print(f"  ⚠️  {error_msg}")
            return None, error_msg
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Clean up verbose error messages
            if isinstance(e, dict) or error_msg.startswith('{'):
                # Extract just the important bits from IMDb error dict
                if '405' in error_msg:
                    error_msg = "HTTP 405: Not Allowed"
                elif '429' in error_msg:
                    error_msg = "HTTP 429: Too Many Requests"
                else:
                    error_msg = "HTTP error"
            
            # Check if it's an HTTP error that might benefit from retry
            if '405' in error_msg or '429' in error_msg or 'Too Many Requests' in error_msg:
                if attempt < max_retries - 1:
                    # Exponential backoff: 2, 4, 8 seconds
                    backoff_delay = 2 ** (attempt + 1)
                    print(f"  ⚠️  {error_msg}. Retrying in {backoff_delay}s... ({attempt + 2}/{max_retries})")
                    time.sleep(backoff_delay)
                    continue
                else:
                    print(f"  ❌ {error_msg} - max retries reached")
                    return None, f"{error_type}: {error_msg}"
            else:
                # Non-retryable error, don't retry
                print(f"  ❌ {error_msg}")
                return None, f"{error_type}: {error_msg}"
    
    return None, "Max retries exceeded"

def extract_show_data(show: Dict) -> Dict:
    """
    Extract relevant data from IMDb show object for CSV export.
    
    Args:
        show: IMDb show object
        
    Returns:
        Dictionary with formatted data for CSV
    """
    # Get basic info
    imdb_id = f"tt{show.movieID}"
    title = show.get('title', '')
    url = f"https://www.imdb.com/title/{imdb_id}/"
    
    # Rating and votes
    rating = show.get('rating', '')
    votes = show.get('votes', '')
    
    # Year and release date
    year = show.get('year', '')
    # For TV shows, use series start date if available
    release_date = show.get('original air date', '')
    if not release_date and year:
        release_date = f"{year}-01-01"
    
    # Runtime (episode length)
    runtime = ''
    if 'runtimes' in show and show['runtimes']:
        runtime = show['runtimes'][0]
    
    # Genres
    genres = ''
    if 'genres' in show:
        genres = ', '.join(show['genres'])
    
    # Creators/Directors (for TV shows, these are usually the creators)
    creators = ''
    if 'creator' in show:
        creators = ', '.join([str(c) for c in show['creator']])
    elif 'director' in show:
        creators = ', '.join([str(d) for d in show['director']])
    
    # Current timestamp for created/modified
    now = datetime.now().strftime('%Y-%m-%d')
    
    return {
        'Const': imdb_id,
        'Title': title,
        'URL': url,
        'Title Type': 'tvSeries',
        'IMDb Rating': rating,
        'Runtime (mins)': runtime,
        'Year': year,
        'Genres': genres,
        'Num Votes': votes,
        'Release Date': release_date,
        'Directors': creators,
        'Created': now,
        'Modified': now,
        'Description': '',
        'Your Rating': '',
        'Date Rated': ''
    }

def process_tv_list(input_file: str, output_file: str, delay: float = 0.0):
    """
    Process TV show list and create TMDB-compatible CSV.
    Supports resume from interruption.
    
    Args:
        input_file: Path to text file with TV show titles (one per line)
        output_file: Path to output CSV file
        delay: Delay in seconds between requests (0 = no delay)
    """
    # Initialize Cinemagoer
    ia = Cinemagoer()
    
    # Read TV show list
    print(f"\n📺 Reading TV shows from: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        tv_shows = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(tv_shows)} TV shows to process")
    if delay > 0:
        print(f"⏱️  Using {delay}s delay between requests")
    
    # Check for resume
    temp_csv = get_temp_csv(output_file)
    last_position = load_progress(output_file)
    start_position = 1
    
    if last_position and os.path.exists(temp_csv):
        print(f"\n⚠️  Found partial progress at position {last_position}")
        response = input(f"Resume from position {last_position + 1}? (y/n): ").strip().lower()
        if response == 'y':
            start_position = last_position + 1
            print(f"✓ Resuming from position {start_position}")
        else:
            print("✓ Starting from beginning")
            start_position = 1
            # Clean up old files
            if os.path.exists(temp_csv):
                os.remove(temp_csv)
            progress_file = get_progress_file(output_file)
            if os.path.exists(progress_file):
                os.remove(progress_file)
    
    # Initialize temp CSV if starting fresh
    if start_position == 1:
        append_to_csv(temp_csv, {}, write_header=True)
    
    print()
    
    # Process each show
    results = []
    failed_count = 0
    success_count = 0
    
    for position, title in enumerate(tv_shows, start=1):
        # Skip already processed
        if position < start_position:
            continue
        
        show, error = search_tv_show(ia, title)
        
        if show:
            try:
                show_data = extract_show_data(show)
                show_data['Position'] = position
                results.append(show_data)
                
                # Write successful result to temp CSV
                append_to_csv(temp_csv, show_data)
                success_count += 1
            except Exception as e:
                # Failed to extract data
                error_msg = f"Data extraction failed: {type(e).__name__}: {str(e)}"
                print(f"  ❌ {error_msg}")
                
                # Immediately write failure (NOT to CSV, only to failed files)
                append_failure(output_file, position, title, error_msg)
                failed_count += 1
        else:
            # Failed to find show
            error_msg = error if error else 'Not found'
            
            # Immediately write failure (NOT to CSV, only to failed files)
            append_failure(output_file, position, title, error_msg)
            failed_count += 1
        
        # Save progress every 10 titles
        if position % 10 == 0:
            save_progress(output_file, position)
            print(f"💾 Progress saved: {position}/{len(tv_shows)} ({success_count} successful, {failed_count} failed)")
        
        # Optional delay between requests
        if delay > 0 and position < len(tv_shows):
            print(f"⏳ Waiting {delay}s before next request...")
            time.sleep(delay)
        
        print()  # Empty line between results
    
    # Final write - copy temp to final
    print(f"\n📝 Writing final results to: {output_file}")
    
    fieldnames = [
        'Position', 'Const', 'Created', 'Modified', 'Description',
        'Title', 'URL', 'Title Type', 'IMDb Rating', 'Runtime (mins)',
        'Year', 'Genres', 'Num Votes', 'Release Date', 'Directors',
        'Your Rating', 'Date Rated'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    # Clean up temp and progress files
    if os.path.exists(temp_csv):
        os.remove(temp_csv)
    progress_file = get_progress_file(output_file)
    if os.path.exists(progress_file):
        os.remove(progress_file)
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"✓ Successfully processed: {success_count}/{len(tv_shows)} shows")
    print(f"❌ Failed to process: {failed_count}/{len(tv_shows)} shows")
    print(f"\nOutput files:")
    print(f"  - Main CSV: {output_file} (successful results only)")
    if failed_count > 0:
        print(f"  - Failed details: {output_file.rsplit('.', 1)[0]}_failed.txt")
        print(f"  - Failed list: {output_file.rsplit('.', 1)[0]}_failed_list.txt")
    print(f"{'='*80}\n")

def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python imdb_tv_scraper.py <input_file> [output_file] [--delay=N]")
        print("\nExample:")
        print("  python imdb_tv_scraper.py tv_list.txt tv_shows_imdb.csv")
        print("  python imdb_tv_scraper.py tv_list.txt tv_shows_imdb.csv --delay=2")
        print("\nOptions:")
        print("  --delay=N    Add N second delay between requests (default: 0)")
        print("\nFeatures:")
        print("  - Exponential backoff on errors (automatic)")
        print("  - Incremental progress saves every 10 titles")
        print("  - Resume capability if interrupted")
        print("  - Immediate failure logging")
        print("  - Only successful results in main CSV")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = 'tv_shows_imdb.csv'
    delay = 0.0
    
    # Parse arguments
    for arg in sys.argv[2:]:
        if arg.startswith('--delay='):
            try:
                delay = float(arg.split('=')[1])
            except ValueError:
                print(f"❌ Invalid delay value: {arg}")
                sys.exit(1)
        elif not arg.startswith('--'):
            output_file = arg
    
    try:
        process_tv_list(input_file, output_file, delay)
    except FileNotFoundError:
        print(f"❌ Error: Input file '{input_file}' not found")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Process interrupted by user")
        print(f"Progress saved. Run the same command to resume.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
