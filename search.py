"""Search functionality for Project Knowledge Base."""

import json
from datetime import datetime
from typing import List, Optional

from db import Database


def format_timestamp(ts: float) -> str:
    """Format Unix timestamp to ISO date string."""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def format_search_results(results: List[dict], query: str) -> dict:
    """Format search results into PRD-specified JSON format."""
    formatted = []
    for item in results:
        # Remove rank field (don't expose FTS5 rank to users)
        item.pop('rank', None)
        
        # Convert timestamps
        if 'created_at' in item:
            item['created_at'] = format_timestamp(item['created_at'])
        if 'updated_at' in item:
            item['updated_at'] = format_timestamp(item['updated_at'])
        
        # Add project name if we have project_id
        if 'project_id' in item and item['project_id']:
            # We'll need to fetch project name separately if needed
            # For now, just keep project_id
            pass
        
        formatted.append(item)
    
    return {
        "success": True,
        "query": query,
        "results": formatted,
        "count": len(formatted)
    }


def search(query: str, project_id: Optional[str] = None,
           search_type: Optional[str] = None, db: Optional[Database] = None) -> dict:
    """Search across the knowledge base and return formatted results."""
    if db is None:
        db = Database()
    
    results = db.search(query, project_id, search_type)
    return format_search_results(results, query)


def get_recent_items(limit: int = 10, db: Optional[Database] = None) -> dict:
    """Get recent items when no search query is provided (like session_search behavior)."""
    if db is None:
        db = Database()
    
    # Get recent projects
    projects = db.list_projects()
    recent_projects = []
    for p in projects[:limit]:
        item = {
            'type': 'project',
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'status': p.status,
            'created_at': format_timestamp(p.created_at),
            'updated_at': format_timestamp(p.updated_at)
        }
        recent_projects.append(item)
    
    # Get recent tasks
    tasks = db.list_tasks()
    recent_tasks = []
    for t in tasks[:limit]:
        item = {
            'type': 'task',
            'id': t.id,
            'project_id': t.project_id,
            'title': t.title,
            'status': t.status,
            'priority': t.priority,
            'created_at': format_timestamp(t.created_at),
            'updated_at': format_timestamp(t.updated_at)
        }
        recent_tasks.append(item)
    
    # Get recent notes
    notes = db.list_notes(limit=limit)
    recent_notes = []
    for n in notes:
        item = {
            'type': 'note',
            'id': n.id,
            'project_id': n.project_id,
            'content': n.content[:100] + '...' if len(n.content) > 100 else n.content,
            'tags': n.tags,
            'created_at': format_timestamp(n.created_at)
        }
        recent_notes.append(item)
    
    # Combine and sort by recency
    all_items = recent_projects + recent_tasks + recent_notes
    all_items.sort(key=lambda x: x.get('updated_at', x.get('created_at', '')), reverse=True)
    
    return {
        "success": True,
        "query": None,
        "results": all_items[:limit],
        "count": len(all_items[:limit])
    }