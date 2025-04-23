from mcp.server.fastmcp import FastMCP
import requests
import atexit

from typing import Optional

from utils import start_flask_app, shutdown_flask_app, FLASK_APP_URL

# Create an MCP server
mcp = FastMCP("TIDAL Integration")

# Start the Flask app when this script is loaded
print("MCP server module is being loaded. Starting Flask app...")
start_flask_app()

# Register the shutdown function to be called when the MCP server exits
atexit.register(shutdown_flask_app)

@mcp.tool()
def tidal_login() -> dict:
    """
    Authenticate with TIDAL through browser login flow.
    This will open a browser window for the user to log in to their TIDAL account.
    
    Returns:
        A dictionary containing authentication status and user information if successful
    """
    try:
        # Call your Flask endpoint for TIDAL authentication
        response = requests.get(f"{FLASK_APP_URL}/api/auth/login")
        
        # Check if the request was successful
        if response.status_code == 200:
            return response.json()
        else:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Authentication failed: {error_data.get('message', 'Unknown error')}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to TIDAL authentication service: {str(e)}"
        }
    
def _get_tidal_tracks(limit: int = 10) -> dict:
    """
    [INTERNAL USE] Retrieves tracks from the user's TIDAL account history or favorites.
    This is a lower-level function primarily used by higher-level recommendation functions.
    
    Args:
        limit: Maximum number of tracks to retrieve (default: 10).
               ONLY specify this parameter if the user explicitly requests 
               a different number of tracks.    
    Returns:
        A dictionary containing track information including track ID, title, artist, album, and duration.
        Returns an error message if not authenticated or if retrieval fails.
    """
    try:
        # Call your Flask endpoint to retrieve tracks with the specified limit
        response = requests.get(f"{FLASK_APP_URL}/api/tracks", params={"limit": limit})
        
        # Check if the request was successful
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {
                "status": "error",
                "message": "Not authenticated with TIDAL. Please login first using tidal_login()."
            }
        else:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Failed to retrieve tracks: {error_data.get('error', 'Unknown error')}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to TIDAL tracks service: {str(e)}"
        }
    
@mcp.tool()
def summarize_music_preferences(limit: int = 10) -> dict:
    """
    Analyzes the user's recent favorite tracks from TIDAL and provides a summary of their music preferences.
    
    USE THIS TOOL WHENEVER A USER ASKS FOR:
    - "What's my music taste?"
    - "Analyze my music preferences"
    - "What kind of music do I like?"
    - "Tell me about my music taste"
    - "What genres do I listen to?"
    - "Summarize my TIDAL favorites"
    - Any request to analyze or understand their music preferences
    
    This function retrieves the user's favorite tracks from TIDAL and analyzes patterns
    in artists, genres, and musical style to generate insights about their music taste.
    
    When processing the results of this tool:
    1. Analyze patterns in artists, genres, potential mood preferences, and other insights
    2. Provide a thoughtful summary of their overall music taste
    3. Identify key artists they seem to enjoy
    4. Note genres or styles that appear frequently
    5. Mention any mood patterns or themes you notice
    6. If you're not familiar with any artists, note this and use your general knowledge
    
    Args:
        limit: Number of recent favorite tracks to analyze (default: 10, max: 50)
        
    Returns:
        A dictionary containing the summary of music preferences and track data
    """
    # First, check if the user is authenticated
    auth_check = requests.get(f"{FLASK_APP_URL}/api/auth/status")
    auth_data = auth_check.json()
    
    if not auth_data.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first before I can analyze your music preferences. Please use the tidal_login() function."
        }
    
    # Retrieve the user's favorite tracks
    tracks_response = _get_tidal_tracks(limit=limit)
    
    # Check if we successfully retrieved tracks
    if "status" in tracks_response and tracks_response["status"] == "error":
        return {
            "status": "error", 
            "message": f"Unable to analyze your music preferences: {tracks_response['message']}"
        }
    
    # Extract the track data
    tracks = tracks_response.get("tracks", [])
    
    if not tracks:
        return {
            "status": "error",
            "message": "I couldn't find any favorite tracks in your TIDAL account. Please make sure you have saved some tracks as favorites."
        }
    
    # Return the track data for MCP client to analyze
    return {
        "status": "success",
        "favorite_tracks": tracks,
        "track_count": len(tracks)
    }
    
# @mcp.prompt("summarize_music_preferences")
# def summarize_music_preferences(limit: int = 10) -> str:
#     """
#     Analyzes the user's recent favorite tracks from TIDAL and provides a summary of their music preferences.

#     USE THIS FUNCTION WHENEVER A USER ASKS FOR:
#     - "What's my music taste?"
#     - "Analyze my music preferences"
#     - "What kind of music do I like?"
#     - "Tell me about my music taste"
#     - "What genres do I listen to?"
#     - "Summarize my TIDAL favorites"
#     - Any request to analyze or understand their music preferences
    
#     This function:
#     1. Retrieves the user's recent favorite tracks
#     2. Analyzes patterns in artists, genres, and musical style
#     3. Generates a natural language summary of the user's musical taste
    
#     Args:
#         limit: Number of recent favorite tracks to analyze (default: 10, max: 50)
        
#     Returns:
#         A detailed summary of the user's music preferences based on their recent TIDAL favorites
#     """
#     # First, check if the user is authenticated
#     auth_check = requests.get(f"{FLASK_APP_URL}/api/auth/status")
#     auth_data = auth_check.json()
    
#     if not auth_data.get("authenticated", False):
#         return "You need to login to TIDAL first before I can analyze your music preferences. Please use the tidal_login() function."
    
#     # Retrieve the user's favorite tracks
#     tracks_response = _get_tidal_tracks(limit=limit)
    
#     # Check if we successfully retrieved tracks
#     if "status" in tracks_response and tracks_response["status"] == "error":
#         return f"Unable to analyze your music preferences: {tracks_response['message']}"
    
#     # Extract the track data
#     tracks = tracks_response.get("tracks", [])
    
#     if not tracks:
#         return "I couldn't find any favorite tracks in your TIDAL account. Please make sure you have saved some tracks as favorites."
    
#     # Create a prompt for the LLM to analyze
#     tracks_info = "\n".join([
#         f"- [ID: {track['id']}] \"{track['title']}\" by {track['artist']} from the album \"{track['album']}\""
#         for track in tracks
#     ])
    
#     # This is the actual prompt that will be sent to the LLM (Claude in this case)
#     prompt = f"""
#     Based on the following list of a user's recent favorite tracks from TIDAL, please provide a thoughtful summary of their music preferences. 
#     Analyze patterns in artists, genres, potential mood preferences, and any other insights you can draw (note that the track id is not relevant for this analysis and we don't need to show it to the users unless they ask for it).:

#     {tracks_info}

#     If you're not familiar with any of these artists, albums, or songs, please use internet search if that capability is available to you. This will help you provide more accurate information about genres, music styles, and artist backgrounds.

#     Please provide:
#     1. A summary of their overall music taste
#     2. Key artists they seem to enjoy
#     3. Genres or styles that appear frequently
#     4. Any mood patterns or themes you notice    
    
#     If you use internet search to help with your analysis, please mention this briefly so the user understands your information is up-to-date.
#     """
    
#     # The MCP prompt decorator handles sending this to the LLM and returning the response
#     return prompt

def _get_tidal_recommendations(track_ids: list = None, limit_seed_tracks: int = 10, limit_per_track: int = 10, filter_criteria: str = None) -> dict:
    """
    [INTERNAL USE] Gets raw recommendation data from TIDAL API.
    This is a lower-level function primarily used by higher-level recommendation functions.
    For end-user recommendations, use recommend_tracks instead.
    
    Args:
        track_ids: List of TIDAL track IDs to use as seeds for recommendations. 
                  If not provided, will use the user's favorite tracks.
        limit_seed_tracks: Maximum number of seed tracks to use (default: 10)
        limit_per_track: Maximum number of recommendations to get per track (default: 10)
        filter_criteria: Optional string describing criteria to filter recommendations
                         (e.g., "relaxing", "new releases", "upbeat")
    
    Returns:
        A dictionary containing recommended tracks based on seed tracks and filtering criteria.
    """
    try:
        # First, check if the user is authenticated
        auth_check = requests.get(f"{FLASK_APP_URL}/api/auth/status")
        auth_data = auth_check.json()
        
        if not auth_data.get("authenticated", False):
            return {
                "status": "error",
                "message": "You need to login to TIDAL first. Please use the tidal_login() function."
            }
        
        # If track_ids not provided, get them from user favorites
        if not track_ids:
            # Retrieve favorite tracks to use as seeds
            tracks_response = _get_tidal_tracks(limit=limit_seed_tracks)
            
            if "status" in tracks_response and tracks_response["status"] == "error":
                return {
                    "status": "error",
                    "message": f"Unable to get recommendations: {tracks_response['message']}"
                }
            
            # Extract track IDs from favorites
            tracks = tracks_response.get("tracks", [])
            if not tracks:
                return {
                    "status": "error",
                    "message": "No favorite tracks found to use as seeds for recommendations."
                }
            
            track_ids = [track["id"] for track in tracks]
                
        # Call the batch recommendations endpoint
        payload = {
            "track_ids": track_ids,
            "limit_per_track": limit_per_track,
            "remove_duplicates": True
        }
        
        response = requests.post(f"{FLASK_APP_URL}/api/recommendations/batch", json=payload)
        
        if response.status_code != 200:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Failed to get recommendations: {error_data.get('error', 'Unknown error')}"
            }
        
        recommendations = response.json().get("recommendations", [])
        
        # If filter criteria is provided, include it in the response for LLM processing
        result = {
            "recommendations": recommendations,
            "total_count": len(recommendations)
        }
        
        if filter_criteria:
            result["filter_criteria"] = filter_criteria
            
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get recommendations: {str(e)}"
        }
    
# @mcp.prompt("recommend_tracks")
# def recommend_tracks(filter_criteria: str = None, seed_count: int = 10, limit_per_track: int = 10, max_recommendations: int = 30) -> str:
#     """
#     Recommends music tracks based on the user's TIDAL listening history.
    
#     USE THIS FUNCTION WHENEVER A USER ASKS FOR:
#     - Music recommendations
#     - Track suggestions
#     - Music similar to their TIDAL favorites
#     - "What should I listen to?"
#     - Any request to recommend songs/tracks/music based on their TIDAL history
        
#     This function:
#     1. Retrieves the user's most recent favorite tracks
#     2. Gets recommendations based on these tracks from TIDAL
#     3. Filters and ranks recommendations based on the user's specified criteria
#     4. Provides context and explanation for each recommendation
    
#     Args:
#         filter_criteria: Specific preferences for filtering recommendations (e.g., "relaxing music," 
#                          "recent releases," "upbeat," "jazz influences")
#         seed_count: Number of tracks from user's history to use as seeds
#         limit_per_track: Maximum number of recommendations to get per track
#         max_recommendations: Maximum number of tracks to recommend
        
#     Returns:
#         A thoughtfully curated list of music recommendations with explanations
#     """
#     # First, check if the user is authenticated
#     auth_check = requests.get(f"{FLASK_APP_URL}/api/auth/status")
#     auth_data = auth_check.json()
    
#     if not auth_data.get("authenticated", False):
#         return "You need to login to TIDAL first before I can recommend music. Please use the tidal_login() function."
    
#     # Get the user's favorite tracks
#     tracks_response = _get_tidal_tracks(limit=seed_count)
    
#     # Check if we successfully retrieved tracks
#     if "status" in tracks_response and tracks_response["status"] == "error":
#         return f"Unable to analyze your music preferences: {tracks_response['message']}"
    
#     # Extract the track data
#     favorite_tracks = tracks_response.get("tracks", [])
    
#     if not favorite_tracks:
#         return "I couldn't find any favorite tracks in your TIDAL account. Please make sure you have saved some tracks as favorites."
    
#     # Get recommendations based on these favorite tracks
#     favorite_track_ids = [track["id"] for track in favorite_tracks]
#     recommendations_response = _get_tidal_recommendations(
#         track_ids=favorite_track_ids,
#         limit_per_track=limit_per_track,
#         filter_criteria=filter_criteria
#     )
    
#     # Check if we successfully retrieved recommendations
#     if "status" in recommendations_response and recommendations_response["status"] == "error":
#         return f"Unable to get recommendations: {recommendations_response['message']}"
    
#     # Get the recommendations
#     recommendations = recommendations_response.get("recommendations", [])
    
#     if not recommendations:
#         return "I couldn't find any recommendations based on your favorites. Please try again later or adjust your filtering criteria."
    
#     # Create a description of the user's favorite tracks
#     favorites_info = "\n".join([
#         f"- \"{track['title']}\" by {track['artist']} from the album \"{track['album']}\""
#         for track in favorite_tracks
#     ])
    
#     # Create a description of the recommended tracks
#     recommendations_info = "\n".join([
#         f"- \"{track['title']}\" by {track['artist']} from the album \"{track['album']}\""
#         for track in recommendations
#     ])
    
#     # Prepare the filter criteria description
#     filter_description = f" with an emphasis on {filter_criteria}" if filter_criteria else ""
    
#     # Create the prompt for the LLM
#     prompt = f"""
#     I'm going to help create personalized music recommendations for a user based on their TIDAL listening history{filter_description}.
    
#     First, here are the user's recent favorite tracks that we're using as seeds:
    
#     {favorites_info}
    
#     Based on these favorites, TIDAL has suggested the following tracks:
    
#     {recommendations_info}
    
#     Your task is to:
    
#     1. Analyze the user's favorite tracks to understand their music taste
#     2. Review the recommended tracks from TIDAL
#     3. Select and rank the most appropriate tracks based on the user's taste{filter_description}
#     4. Limit your selection to {max_recommendations} tracks maximum
#     5. For each recommended track, provide:
#        - The track name, artist, album, and its url if available
#        - A brief explanation of why this track might appeal to the user based on their favorites
#        - If applicable, how this track matches their specific filter criteria of "{filter_criteria}"
    
#     Please format your response as a nicely presented list of recommendations with helpful context for each track. Begin with a brief introduction explaining your selection strategy based on the user's taste profile.
    
#     If you're not familiar with any artists or tracks mentioned, you should use internet search capabilities if available to provide more accurate information.
#     """
    
#     # The MCP prompt decorator handles sending this to the LLM and returning the response
#     return prompt

@mcp.tool()
def recommend_tracks(filter_criteria: Optional[str] = None, seed_count: int = 10, limit_per_track: int = 10, max_recommendations: int = 30) -> dict:
    """
    Recommends music tracks based on the user's TIDAL listening history.
    
    USE THIS TOOL WHENEVER A USER ASKS FOR:
    - Music recommendations
    - Track suggestions
    - Music similar to their TIDAL favorites
    - "What should I listen to?"
    - Any request to recommend songs/tracks/music based on their TIDAL history
    
    This function retrieves the user's favorite tracks from TIDAL, gets recommendations
    based on these tracks, and returns a structured dataset that includes both the
    user's favorites and the recommended tracks.
    
    When processing the results of this tool:
    1. Analyze the user's favorite tracks to understand their music taste
    2. Review the recommended tracks from TIDAL
    3. Select and rank the most appropriate tracks based on the user's taste and filter criteria
    4. Limit your selection to the max_recommendations value or less
    5. Group recommendations by similar styles, artists, or moods with descriptive headings
    6. For each recommended track, provide:
       - The track name, artist, album
       - Always include the track's URL to make it easy for users to listen to the track
       - A brief explanation of why this track might appeal to the user based on their favorites
       - If applicable, how this track matches their specific filter criteria       
    7. Format your response as a nicely presented list of recommendations with helpful context (remember to include the track's URL!)
    8. Begin with a brief introduction explaining your selection strategy
    
    [IMPORTANT NOTE] If you're not familiar with any artists or tracks mentioned, you should use internet search capabilities if available to provide more accurate information.
    
    Args:
        filter_criteria: Specific preferences for filtering recommendations (e.g., "relaxing music," 
                         "recent releases," "upbeat," "jazz influences")
        seed_count: Number of tracks from user's history to use as seeds
        limit_per_track: Maximum number of recommendations to get per track
        max_recommendations: Maximum number of tracks to recommend
        
    Returns:
        A dictionary containing both the user's favorite tracks and recommended tracks
    """
    # First, check if the user is authenticated
    auth_check = requests.get(f"{FLASK_APP_URL}/api/auth/status")
    auth_data = auth_check.json()
    
    if not auth_data.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first before I can recommend music. Please use the tidal_login() function."
        }
    
    # Get the user's favorite tracks
    tracks_response = _get_tidal_tracks(limit=seed_count)
    
    # Check if we successfully retrieved tracks
    if "status" in tracks_response and tracks_response["status"] == "error":
        return {
            "status": "error",
            "message": f"Unable to analyze your music preferences: {tracks_response['message']}"
        }
    
    # Extract the track data
    favorite_tracks = tracks_response.get("tracks", [])
    
    if not favorite_tracks:
        return {
            "status": "error",
            "message": "I couldn't find any favorite tracks in your TIDAL account. Please make sure you have saved some tracks as favorites."
        }
    
    # Get recommendations based on these favorite tracks
    favorite_track_ids = [track["id"] for track in favorite_tracks]
    recommendations_response = _get_tidal_recommendations(
        track_ids=favorite_track_ids,
        limit_per_track=limit_per_track,
        filter_criteria=filter_criteria
    )
    
    # Check if we successfully retrieved recommendations
    if "status" in recommendations_response and recommendations_response["status"] == "error":
        return {
            "status": "error",
            "message": f"Unable to get recommendations: {recommendations_response['message']}"
        }
    
    # Get the recommendations
    recommendations = recommendations_response.get("recommendations", [])
    
    if not recommendations:
        return {
            "status": "error",
            "message": "I couldn't find any recommendations based on your favorites. Please try again later or adjust your filtering criteria."
        }
    
    # Return the structured data for Claude to process
    return {
        "status": "success",
        "favorite_tracks": favorite_tracks,
        "recommendations": recommendations[:max_recommendations],  # Limit to max_recommendations
        "filter_criteria": filter_criteria,
        "favorite_count": len(favorite_tracks),        
    }