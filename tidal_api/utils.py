def format_track_data(track, source_track_id=None):
    """
    Format a track object into a standardized dictionary.
    
    Args:
        track: TIDAL track object
        source_track_id: Optional ID of the track that led to this recommendation
        
    Returns:
        Dictionary with standardized track information
    """
    track_data = {
        "id": track.id,
        "title": track.name,
        "artist": track.artist.name if hasattr(track.artist, 'name') else "Unknown",
        "album": track.album.name if hasattr(track.album, 'name') else "Unknown",
        "duration": track.duration if hasattr(track, 'duration') else 0,
        "url": f"https://tidal.com/browse/track/{track.id}?u"
    }
    
    # Include source track ID if provided
    if source_track_id:
        track_data["source_track_id"] = source_track_id
        
    return track_data

def bound_limit(limit: int, max_n: int = 50) -> int:
    # Ensure limit is within reasonable bounds
    if limit < 1:
        limit = 1
    elif limit > max_n:
        limit = max_n
    print(f"Limit set to {limit} (max {max_n})")    
    return limit
