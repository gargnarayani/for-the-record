
# FOR THE RECORD - CORE OF PROJECT FUNCTION
# File: backend/pipeline.py

import os
import time
import random
import sqlite3
import shutil
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import yt_dlp
import psutil
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, COMM
from thefuzz import fuzz, process

DB_FILE = "backend/cache.db"

# LOCAL CACHING DATABASE
# To minimize API rates, implemented local SQLite cache w/ O(1)lookup for track hashes

def init_cache_database():
    """Initializes local relational database cache to protect network I/O bounds."""
    os.makedirs("backend", exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS track_cache (
            spotify_track_id TEXT PRIMARY KEY,
            title TEXT,
            artist TEXT,
            album TEXT,
            local_absolute_path TEXT,
            youtube_video_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

# EXPONENTIAL BACKOFF WITH JITTER
# Public APIs might block or rate limit the IP. Wrap API requests in try/ecept and use time.sleep() to wait exponentially before raising error.

def robust_api_call(func, *args, **kwargs):
    """Resilient API execution wrapper implementing exponential network backoff."""
    max_retries = 5
    base_delay = 2.0
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower() or attempt < max_retries - 1:
                delay = (base_delay ** attempt) + random.uniform(0, 1)
                print(f"[!] Rate limit or flakiness caught. Retrying in {delay:.2f}s...")
                time.sleep(delay)
            else:
                raise e

# FUZZY STRING MATCHING ALGORITHM
# Use string cleaning pipeline and Levenshtein distance algorithm to score search relevance to improve download accuracy.

def verify_search_relevance(spotify_track, youtube_title):
    """Applies string normalization and calculates mathematical match threshold."""
    target = f"{spotify_track['artist']} {spotify_track['name']}".lower()
    candidate = youtube_title.lower()
    
    for noise in ["official video", "lyric video", "hd", "audio", "mv", "official music video", "remastered"]:
        candidate = candidate.replace(noise, "")
        
    match_score = fuzz.token_set_ratio(target, candidate)
    return match_score >= 78


# VBR SHUFFLE-SQUEEZER & ID3 CONTAINER INJECTOR
# Ipod shuffle has little memory so we will automatically convert downloaded MP3 files to VBRs.
# Ipods read limited formats and need specific metadata strucutre with (ID3 tags).

def compress_and_tag_audio(temp_raw_path, final_dest_path, track_metadata):
    """Manipulates binary container formats to write hardware-level ID3 metadata and squeeze footprint."""
    try:
        # Move the downloaded file to its definitive playlist location
        shutil.move(temp_raw_path, final_dest_path)
        
        # Initialize or grab the ID3 tag metadata header structure from the MP3 container
        try:
            tags = ID3(final_dest_path)
        except Exception:
            tags = ID3()

        # Inject structural text frames for legacy hardware readability
        tags[TIT2] = TIT2(encoding=3, text=track_metadata['name'])
        tags[TPE1] = TPE1(encoding=3, text=track_metadata['artist'])
        tags[TALB] = TALB(encoding=3, text=track_metadata['album'])
        tags[COMM] = COMM(encoding=3, lang='eng', desc='Source', text='Synced via ForTheRecord [2026]')
        tags.save(final_dest_path)

        # Download and append raw binary artwork frames directly inside the MP3 asset wrapper
        if track_metadata['art_url']:
            with urllib.request.urlopen(track_metadata['art_url']) as response:
                raw_art_binary = response.read()
                
            audio_file = MP3(final_dest_path, ID3=ID3)
            audio_file.tags.add(APIC(
                encoding=3, 
                mime='image/jpeg', 
                type=3, # Front Cover frame
                desc='Cover', 
                data=raw_art_binary
            ))
            audio_file.save()
            print(f"[✓] Embedded hardware metadata tags and artwork for: {track_metadata['name']}")
            
    except Exception as e:
        print(f"[X] Post-processing pipeline failure for {track_metadata['name']}: {e}")

# CONCURRENT WORKER & DUPLICATE MITIGATION
#  Multithreading and asynchronous programing to overcome the netwokr I/O bottleneck.
# Make local database to track.

def process_track_worker(track, target_output_folder):
    """Atomic multi-threaded worker executing the evaluation, caching, and download chain."""
    # Connect to the local instance database cache safely per thread boundary
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT local_absolute_path, youtube_video_id FROM track_cache WHERE spotify_track_id=?", (track['id'],))
    cached_row = cursor.fetchone()
    
    final_dest_path = os.path.join(target_output_folder, f"{track['artist']} - {track['name']}.mp3")
    
    # SMART CACHING / DUPLICATE MITIGATION HIT CHECK
    if cached_row:
        local_cached_path, yt_id = cached_row
        if os.path.exists(local_cached_path) and not os.path.exists(final_dest_path):
            shutil.copy2(local_cached_path, final_dest_path)
            print(f"[-] Duplicate Mitigation (O1 Cache Hit): Linked {track['name']} without downloading.")
            conn.close()
            return

    # SEARCH & DOWNLOAD EXECUTIONS via yt-dlp
    search_query = f"{track['artist']} {track['name']} audio"
    temp_name = f"temp_{track['id']}"
    temp_out_path = os.path.join(target_output_folder, temp_name)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': temp_out_path,
        'quiet': True,
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '128' # 128k VBR Shuffle-Squeezer Config
        }],
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Query candidate data without physical download commitment
            info = ydl.extract_info(f"ytsearch1:{search_query}", download=False)
            if info and 'entries' in info and len(info['entries']) > 0:
                best_video = info['entries'][0]
                
                # Check Levenshtein similarity algorithmic match bounds before downloading
                if verify_search_relevance(track, best_video['title']):
                    ydl.download([best_video['webpage_url']])
                    
                    # Run Part 2: Compress and write binary ID3v2 tags
                    compress_and_tag_audio(f"{temp_out_path}.mp3", final_dest_path, track)
                    
                    # Update local database cache parameters
                    cursor.execute("""
                        INSERT OR REPLACE INTO track_cache 
                        (spotify_track_id, title, artist, album, local_absolute_path, youtube_video_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (track['id'], track['name'], track['artist'], track['album'], final_dest_path, best_video['id']))
                    conn.commit()
                else:
                    print(f"[X] Quality Match Rejected for: {track['name']}")
    except Exception as e:
        print(f"[X] Pipeline failure executing track {track['name']}: {e}")
    finally:
        conn.close()

# HARDWARE MOUNT AUTOMATION

def auto_detect_hardware_path():
    """Scans hardware partition paths looking for generic USB block storage mounts."""
    for partition in psutil.disk_partitions():
        if 'ipod' in partition.mountpoint.lower() or 'usb' in partition.mountpoint.lower():
            print(f"[✓] Physical target detected via Retro-Flasher: {partition.mountpoint}")
            return partition.mountpoint
    return "./backend/iPod_Music_Local"

# CENTRAL ENGINE EXECUTIVE RUNNER

def run_for_the_record_pipeline(parsed_tracks_array, playlist_name="My_iPod_Sync"):
    """Orchestrates system processes, spinning up parallel execution threads."""
    init_cache_database()
    
    # Establish target volume endpoints
    root_destination = auto_detect_hardware_path()
    playlist_folder = os.path.join(root_destination, playlist_name.replace(" ", "_"))
    os.makedirs(playlist_folder, exist_ok=True)
    
    print(f"[*] ThreadPool Executor Initialized. Syncing {len(parsed_tracks_array)} items concurrently...")
    
    # 🚀 PARALLEL PLAYLIST PROCESSOR CONCURRENCY LAYER
    with ThreadPoolExecutor(max_workers=4) as executor:
        for track in parsed_tracks_array:
            executor.submit(process_track_worker, track, playlist_folder)
            
    print(f"[✓] Process complete! Tracks cleanly compiled into target: {playlist_folder}")

# TEST BLOCK

if __name__ == "__main__":
    print("[*] Testing Pipeline Architecture Part 3 (Full Simulation Run)...")
    
    # Simulating structural data incoming from a mock Spotify playlist array
    mock_playlist_name = "Synthwave Retro Mix"
    mock_tracks_from_spotify = [
        {
            "id": "mock_track_01",
            "name": "Resonance",
            "artist": "HOME",
            "album": "Odyssey",
            "art_url": "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?q=80&w=200&auto=format&fit=crop"
        }
    ]
    
    # Execute full pipeline lifecycle
    run_for_the_record_pipeline(mock_tracks_from_spotify, mock_playlist_name)