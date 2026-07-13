
# FOR THE RECORD - WEB APPLICATION ROUTING 
# File: backend/app.py


import os
from flask import Flask, request, jsonify
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from pipeline import run_for_the_record_pipeline

# Configured to look backwards into the frontend folder for HTML/JS assets
app = Flask(__name__, static_folder='../frontend', static_url_path='')

def fetch_and_parse_spotify_playlist(playlist_url):
    """Initializes a temporary Spotify connection and parses raw track lists."""
    client_id = os.getenv("SPOTIFY_CLIENT_ID", "MOCK_ID_FOR_COMPILATION")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "MOCK_SECRET_FOR_COMPILATION")
    
    if client_id == "MOCK_ID_FOR_COMPILATION" or not playlist_url:
        return "Preview Playlist Mix", [
            {
                "id": "track_preview_01",
                "name": "Midnight City",
                "artist": "M83",
                "album": "Hurry Up, We're Dreaming",
                "art_url": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?q=80&w=200&auto=format&fit=crop"
            },
            {
                "id": "track_preview_02",
                "name": "Nightcall",
                "artist": "Kavinsky",
                "album": "Outrun",
                "art_url": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?q=80&w=200&auto=format&fit=crop"
            }
        ]

    sp = Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))
    playlist_id = playlist_url.split("/")[-1].split("?")[0]
    meta = sp.playlist(playlist_id)
    
    parsed_tracks = []
    for item in meta['tracks']['items']:
        if not item['track']: continue
        t = item['track']
        parsed_tracks.append({
            'id': t['id'],
            'name': t['name'],
            'artist': t['artists'][0]['name'],
            'album': t['album']['name'],
            'art_url': t['album']['images'][0]['url'] if t['album']['images'] else None
        })
        
    return meta['name'], parsed_tracks

# FLASK WEB ENDPOINT ROUTING

# NEW ROUTE: Mandates the server to deliver the HTML page layout automatically
@app.route('/')
def serve_frontend():
    return app.send_static_file('index.html')

@app.route('/api/sync', methods=['POST'])
def handle_playlist_sync_request():
    """Intercepts post strings sent from user interface to fire background workers."""
    try:
        data = request.get_json() or {}
        spotify_url = data.get("url", "")
        
        playlist_name, tracks_to_sync = fetch_and_parse_spotify_playlist(spotify_url)
        run_for_the_record_pipeline(tracks_to_sync, playlist_name)
        
        return jsonify({
            "status": "success",
            "message": f"Successfully synchronized {len(tracks_to_sync)} tracks to playlist directory: {playlist_name}!",
            "playlist_name": playlist_name,
            "track_count": len(tracks_to_sync)
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server integration error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)