"""WSGI entrypoint used by Docker / gunicorn."""
from src.api.app import create_app

app = create_app()
