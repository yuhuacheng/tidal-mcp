import os
import tempfile
import functools

from flask import Flask, request, jsonify
from pathlib import Path

from browser_session import BrowserSession
from utils import format_track_data, bound_limit

app = Flask(__name__)
token_path = os.path.join(tempfile.gettempdir(), 'tidal-session-oauth.json')
SESSION_FILE = Path(token_path)

def requires_tidal_auth(f):
    """
    Decorator to ensure routes have an authenticated TIDAL session.
    Returns 401 if not authenticated.
    Passes the authenticated session to the decorated function.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not SESSION_FILE.exists():
            return jsonify({"error": "Not authenticated"}), 401
        
        # Create session and load from file
        session = BrowserSession()
        login_success = session.login_session_file_auto(SESSION_FILE)
        
        if not login_success:
            return jsonify({"error": "Authentication failed"}), 401
            
        # Add the authenticated session to kwargs
        kwargs['session'] = session
        return f(*args, **kwargs)
    return decorated_function


@app.route('/api/auth/login', methods=['GET'])
def login():
    """
    Initiates the TIDAL authentication process.
    Automatically opens a browser for the user to login to their TIDAL account.
    """
    # Create our custom session object
    session = BrowserSession()
    
    def log_message(msg):
        print(f"TIDAL AUTH: {msg}")
    
    # Try to authenticate (will open browser if needed)
    try:
        login_success = session.login_session_file_auto(SESSION_FILE, fn_print=log_message)
        
        if login_success:
            return jsonify({
                "status": "success", 
                "message": "Successfully authenticated with TIDAL",
                "user_id": session.user.id
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Authentication failed"
            }), 401
    
    except TimeoutError:
        return jsonify({
            "status": "error",
            "message": "Authentication timed out"
        }), 408
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    """
    Check if there's an active authenticated session.
    """
    if not SESSION_FILE.exists():
        return jsonify({
            "authenticated": False,
            "message": "No session file found"
        })
    
    # Create session and try to load from file
    session = BrowserSession()
    login_success = session.login_session_file_auto(SESSION_FILE)
    
    if login_success:
        # Get basic user info
        user_info = {
            "id": session.user.id,
            "username": session.user.username if hasattr(session.user, 'username') else "N/A",
            "email": session.user.email if hasattr(session.user, 'email') else "N/A"            
        }
        
        return jsonify({
            "authenticated": True,
            "message": "Valid TIDAL session",
            "user": user_info
        })
    else:
        return jsonify({
            "authenticated": False,
            "message": "Invalid or expired session"
        })

@app.route('/api/tracks', methods=['GET'])
@requires_tidal_auth
def get_tracks(session: BrowserSession):
    """
    Get tracks from the user's history.
    """
    try:        
        # TODO: Add streaminig history support if TIDAL API allows it
        # Get user favorites or history (for now limiting to user favorites only)
        favorites = session.user.favorites
        
        # Get limit from query parameter, default to 10 if not specified
        limit = bound_limit(request.args.get('limit', default=10, type=int))
        
        tracks = favorites.tracks(limit=limit, order="DATE", order_direction="DESC")        
        track_list = [format_track_data(track) for track in tracks]

        return jsonify({"tracks": track_list})
    except Exception as e:
        return jsonify({"error": f"Error fetching tracks: {str(e)}"}), 500
    
    
@app.route('/api/recommendations/track/<track_id>', methods=['GET'])
@requires_tidal_auth
def get_track_recommendations(track_id: str, session: BrowserSession):
    """
    Get recommended tracks based on a specific track using TIDAL's track radio feature.
    """
    try:
        # Get limit from query parameter, default to 10 if not specified
        limit = bound_limit(request.args.get('limit', default=10, type=int))
                
        # Get recommendations using track radio
        track = session.track(track_id)
        if not track:
            return jsonify({"error": f"Track with ID {track_id} not found"}), 404
            
        recommendations = track.get_track_radio(limit=limit)
        
        # Format track data
        track_list = [format_track_data(track) for track in recommendations]        
        return jsonify({"recommendations": track_list})
    except Exception as e:
        return jsonify({"error": f"Error fetching recommendations: {str(e)}"}), 500    


@app.route('/api/recommendations/batch', methods=['POST'])
@requires_tidal_auth
def get_batch_recommendations(session: BrowserSession):
    """
    Get recommended tracks based on a list of track IDs using concurrent requests.
    """
    import concurrent.futures
    
    try:
        # Get request data
        request_data = request.get_json()
        if not request_data or 'track_ids' not in request_data:
            return jsonify({"error": "Missing track_ids in request body"}), 400
            
        track_ids = request_data['track_ids']
        if not isinstance(track_ids, list):
            return jsonify({"error": "track_ids must be a list"}), 400
            
        # Get limit per track from query parameter
        limit_per_track = bound_limit(request_data.get('limit_per_track', 20))
                    
        # Optional parameter to remove duplicates across recommendations
        remove_duplicates = request_data.get('remove_duplicates', True)
        
        def get_track_recommendations(track_id):
            """Function to get recommendations for a single track"""
            try:
                track = session.track(track_id)
                recommendations = track.get_track_radio(limit=limit_per_track)
                # Format track data immediately
                formatted_recommendations = [
                    format_track_data(rec, source_track_id=track_id) 
                    for rec in recommendations
                ]
                return formatted_recommendations
            except Exception as e:
                print(f"Error getting recommendations for track {track_id}: {str(e)}")
                return []
        
        all_recommendations = []
        seen_track_ids = set()
        
        # Use ThreadPoolExecutor to process tracks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(track_ids)) as executor:
            # Submit all tasks and map them to their track_ids
            future_to_track_id = {
                executor.submit(get_track_recommendations, track_id): track_id 
                for track_id in track_ids
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_track_id):
                track_recommendations = future.result()
                
                # Add recommendations to the result list
                for track_data in track_recommendations:
                    track_id = track_data.get('id')
                    
                    # Skip if we've already seen this track and want to remove duplicates
                    if remove_duplicates and track_id in seen_track_ids:
                        continue
                        
                    all_recommendations.append(track_data)
                    seen_track_ids.add(track_id)
        
        return jsonify({"recommendations": all_recommendations})
    except Exception as e:
        return jsonify({"error": f"Error fetching batch recommendations: {str(e)}"}), 500


@app.route('/api/playlists', methods=['POST'])
@requires_tidal_auth
def create_playlist(session: BrowserSession):
    """
    Creates a new TIDAL playlist and adds tracks to it.
    
    Expected JSON payload:
    {
        "title": "Playlist title",
        "description": "Playlist description",
        "track_ids": [123456789, 987654321, ...]
    }
    
    Returns the created playlist information.
    """
    try:
        # Get request data
        request_data = request.get_json()
        if not request_data:
            return jsonify({"error": "Missing request body"}), 400
            
        # Validate required fields
        if 'title' not in request_data:
            return jsonify({"error": "Missing 'title' in request body"}), 400
            
        if 'track_ids' not in request_data or not request_data['track_ids']:
            return jsonify({"error": "Missing 'track_ids' in request body or empty track list"}), 400
            
        # Get parameters from request
        title = request_data['title']
        description = request_data.get('description', '')  # Optional
        track_ids = request_data['track_ids']
        
        # Validate track_ids is a list
        if not isinstance(track_ids, list):
            return jsonify({"error": "'track_ids' must be a list"}), 400
        
        # Create the playlist
        playlist = session.user.create_playlist(title, description)
        
        # Add tracks to the playlist
        playlist.add(track_ids)
        
        # Return playlist information
        playlist_info = {
            "id": playlist.id,
            "title": playlist.name,
            "description": playlist.description,
            "created": playlist.created,
            "last_updated": playlist.last_updated,
            "track_count": playlist.num_tracks,
            "duration": playlist.duration,
        }
        
        return jsonify({
            "status": "success",
            "message": f"Playlist '{title}' created successfully with {len(track_ids)} tracks",
            "playlist": playlist_info
        })
        
    except Exception as e:
        return jsonify({"error": f"Error creating playlist: {str(e)}"}), 500


@app.route('/api/playlists', methods=['GET'])
@requires_tidal_auth
def get_user_playlists(session: BrowserSession):
    """
    Get the user's playlists from TIDAL.
    """
    try:        
        # Get user playlists
        playlists = session.user.playlists()
        
        # Format playlist data
        playlist_list = []
        for playlist in playlists:
            playlist_info = {
                "id": playlist.id,
                "title": playlist.name,
                "description": playlist.description if hasattr(playlist, 'description') else "",
                "created": playlist.created if hasattr(playlist, 'created') else None,
                "last_updated": playlist.last_updated if hasattr(playlist, 'last_updated') else None,
                "track_count": playlist.num_tracks if hasattr(playlist, 'num_tracks') else 0,
                "duration": playlist.duration if hasattr(playlist, 'duration') else 0,
                "url": f"https://tidal.com/playlist/{playlist.id}"
            }
            playlist_list.append(playlist_info)
        
        # Sort playlists by last_updated in descending order
        sorted_playlists = sorted(
            playlist_list, 
            key=lambda x: x.get('last_updated', ''), 
            reverse=True
        )

        return jsonify({"playlists": sorted_playlists})
    except Exception as e:
        return jsonify({"error": f"Error fetching playlists: {str(e)}"}), 500
    

@app.route('/api/playlists/<playlist_id>/tracks', methods=['GET'])
@requires_tidal_auth
def get_playlist_tracks(playlist_id: str, session: BrowserSession):
    """
    Get tracks from a specific TIDAL playlist.
    """
    try:
        # Get limit from query parameter, default to 100 if not specified
        limit = bound_limit(request.args.get('limit', default=100, type=int))
        
        # Get the playlist object
        playlist = session.playlist(playlist_id)
        if not playlist:
            return jsonify({"error": f"Playlist with ID {playlist_id} not found"}), 404
            
        # Get tracks from the playlist with pagination if needed
        tracks = playlist.items(limit=limit)
        
        # Format track data
        track_list = [format_track_data(track) for track in tracks]
        
        return jsonify({
            "playlist_id": playlist.id,
            "tracks": track_list,
            "total_tracks": len(track_list)
        })
        
    except Exception as e:
        return jsonify({"error": f"Error fetching playlist tracks: {str(e)}"}), 500
    

@app.route('/api/playlists/<playlist_id>', methods=['DELETE'])
@requires_tidal_auth
def delete_playlist(playlist_id: str, session: BrowserSession):
    """
    Delete a TIDAL playlist by its ID.
    """
    try:
        # Get the playlist object
        playlist = session.playlist(playlist_id)
        if not playlist:
            return jsonify({"error": f"Playlist with ID {playlist_id} not found"}), 404
            
        # Delete the playlist
        playlist.delete()
        
        return jsonify({
            "status": "success",
            "message": f"Playlist with ID {playlist_id} was successfully deleted"
        })
        
    except Exception as e:
        return jsonify({"error": f"Error deleting playlist: {str(e)}"}), 500
    
    
if __name__ == '__main__':
    import os
    
    # Get port from environment variable or use default
    port = int(os.environ.get("TIDAL_MCP_PORT", 5050))
    
    print(f"Starting Flask app on port {port}")
    app.run(debug=True, port=port)