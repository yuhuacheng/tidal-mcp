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
        # Get user favorites or history
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


if __name__ == '__main__':
    app.run(debug=True, port=5000)