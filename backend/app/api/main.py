"""
Main application entry point for Uvicorn.
Re-exports the FastAPI application instance from app.py.
"""
from app.api.app import app

__all__ = ["app"]
