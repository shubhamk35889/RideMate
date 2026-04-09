import sys
import os

# Add the parent directory to the path so we can import our app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app import app as flask_app
    app = flask_app
except Exception as e:
    print(f"Error importing Flask app: {e}")
    from flask import Flask
    app = Flask(__name__)
    
    @app.route("/")
    def error_handler():
        return {"error": str(e)}, 500

