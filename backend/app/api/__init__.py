# noqa: F401
"""DocuStruct AI — API Package.

Exports the FastAPI application instance for use by Uvicorn
and test clients.
"""

from app.api.app import app

__all__ = ["app"]
