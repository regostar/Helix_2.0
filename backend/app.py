from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from agent import RecruitingAgent
import os
from sqlalchemy.exc import SQLAlchemyError
from config.config import (
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    SQLALCHEMY_ENGINE_OPTIONS
)
from models.sequence import Sequence
from models.chat_history import ChatHistory
from routes.api_routes import init_routes
from routes.socket_routes import init_socket_routes

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = SQLALCHEMY_ENGINE_OPTIONS

try:
    db = SQLAlchemy(app)
    # Test the database connection and create tables
    with app.app_context():
        db.engine.connect()
        db.create_all()
    print("Successfully connected to PostgreSQL database and created tables")
except SQLAlchemyError as e:
    print(f"Error connecting to database: {str(e)}")
    raise

# Initialize SocketIO with CORS settings
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='eventlet')

# Initialize the recruiting agent with database instance and Sequence model
agent = RecruitingAgent(db_instance=db, sequence_model=Sequence)

# Initialize routes
init_routes(app, db, agent)
init_socket_routes(socketio, db, agent)

if __name__ == '__main__':
    def find_available_port(start_port, max_port=5010):
        """Find an available port starting from start_port up to max_port."""
        import socket
        for port in range(start_port, max_port + 1):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('0.0.0.0', port))
                    return port
            except OSError:
                continue
        raise RuntimeError(f"No available ports found between {start_port} and {max_port}")

    try:
        port = int(os.getenv('PORT', 5000))
        # Try to find an available port if the default is in use
        port = find_available_port(port)
        print(f"Starting server on port {port}")
        socketio.run(app, 
                    host='0.0.0.0', 
                    port=port, 
                    debug=True,
                    allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"Error starting server: {str(e)}")
        print("Please make sure no other application is using the port")
        print("You can also try running the application with a different port by setting the PORT environment variable") 