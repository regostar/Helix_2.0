from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from sqlalchemy.exc import SQLAlchemyError
from config.config import Config
from routes.http_routes import init_http_routes
from routes.socket_routes import init_socket_routes
from models.database import db

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Load configuration
app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = Config.SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = Config.SQLALCHEMY_ENGINE_OPTIONS

try:
    # Initialize database
    db.init_app(app)
    # Test the database connection
    with app.app_context():
        db.create_all()  # Create all tables
        db.engine.connect()
    print("Successfully connected to PostgreSQL database")
except SQLAlchemyError as e:
    print(f"Error connecting to database: {str(e)}")
    raise

# Initialize SocketIO with CORS settings
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='eventlet')

# Initialize routes
init_http_routes(app)
init_socket_routes(socketio, db)

if __name__ == '__main__':
    def find_available_port(start_port, max_port=5010):
        """Find an available port between start_port and max_port."""
        import socket
        for port in range(start_port, max_port + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('', port))
                    return port
                except OSError:
                    continue
        return None

    port = find_available_port(5000)
    if port:
        print(f"Starting server on port {port}")
        socketio.run(app, host='0.0.0.0', port=port)
    else:
        print("No available ports found between 5000 and 5010") 