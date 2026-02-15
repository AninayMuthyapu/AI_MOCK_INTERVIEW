"""In-memory session state management."""
from typing import Dict, Any

# In-memory session stores
session_data: Dict[str, Any] = {}
sessions: Dict[str, Any] = {}

# In-memory user store (will be replaced with PostgreSQL in production)
users_store: Dict[str, Dict[str, Any]] = {}
