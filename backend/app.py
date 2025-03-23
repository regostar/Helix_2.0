from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from agent import RecruitingAgent
import os
import json

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///helix.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Initialize SocketIO with CORS settings
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='eventlet')

# Initialize the recruiting agent
agent = RecruitingAgent()

# Models
class Sequence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    steps = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

# Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

# Socket.IO events
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connection_response', {'data': 'Connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('chat_message')
def handle_chat_message(data):
    try:
        message = data.get('message', '')
        chat_history = data.get('chat_history', [])
        current_sequence = data.get('current_sequence', [])

        print(f"Received message: {message}")  # Debug log

        # Process the message using the agent
        response = agent.process_message(message, chat_history, current_sequence)
        
        print(f"Agent response: {response}")  # Debug log

        # Check if the response contains a sequence update
        try:
            sequence_data = json.loads(response)
            if isinstance(sequence_data, list):
                emit('sequence_updated', {'data': sequence_data})
                response = "I've updated the sequence based on your requirements."
        except json.JSONDecodeError:
            pass

        emit('chat_response', {'data': response})
    except Exception as e:
        print(f"Error in handle_chat_message: {str(e)}")  # Debug log
        emit('chat_response', {'data': f"Error processing message: {str(e)}"})

@socketio.on('sequence_update')
def handle_sequence_update(data):
    try:
        sequence = data.get('sequence', [])
        # Save the sequence to the database
        new_sequence = Sequence(
            title="Recruiting Sequence",
            steps=sequence
        )
        db.session.add(new_sequence)
        db.session.commit()
        emit('sequence_updated', {'data': sequence})
    except Exception as e:
        print(f"Error in handle_sequence_update: {str(e)}")  # Debug log
        emit('error', {'data': f"Error saving sequence: {str(e)}"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, 
                host='0.0.0.0', 
                port=5000, 
                debug=True,
                allow_unsafe_werkzeug=True) 