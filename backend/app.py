from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from agent import RecruitingAgent
import os
import json
from datetime import datetime, UTC
from langchain.schema import HumanMessage

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

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    socket_id = db.Column(db.String(100), nullable=False)
    messages = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    @staticmethod
    def get_or_create(socket_id):
        chat_history = ChatHistory.query.filter_by(socket_id=socket_id).first()
        if not chat_history:
            chat_history = ChatHistory(socket_id=socket_id, messages=[])
            db.session.add(chat_history)
            db.session.commit()
        return chat_history

# Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring and CI/CD."""
    try:
        # Check database connection
        with app.app_context():
            db.session.execute('SELECT 1')
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# Socket.IO events
@socketio.on('connect')
def handle_connect():
    print(f'Client connected with ID: {request.sid}')
    # Create a new chat history entry for this connection
    ChatHistory.get_or_create(request.sid)
    emit('connection_response', {'data': 'Connected', 'socket_id': request.sid})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')
    # Optionally, you could clean up old chat histories here
    # chat_history = ChatHistory.query.filter_by(socket_id=request.sid).first()
    # if chat_history:
    #     db.session.delete(chat_history)
    #     db.session.commit()

@socketio.on('chat_message')
def handle_chat_message(data):
    try:
        message = data.get('message', '')
        
        # Get chat history for this connection
        chat_history = ChatHistory.get_or_create(request.sid)
        current_sequence = data.get('current_sequence', [])

        print(f"Received message from {request.sid}: {message}")

        # Process the message using the agent
        response = agent.process_message(message, chat_history.messages, current_sequence)
        
        print(f"Agent response: {response}")

        # Parse the JSON response to extract relevant information for the user
        display_message = response
        try:
            response_data = json.loads(response)
            if response_data.get("status") == "success" and response_data.get("tool_result"):
                # Extract just the tool result for display
                display_message = response_data["tool_result"]
                
                # Check if the tool result is a JSON sequence
                try:
                    tool_result_data = json.loads(display_message)
                    if isinstance(tool_result_data, dict) and "metadata" in tool_result_data and "steps" in tool_result_data:
                        # For sequence results, use a simple confirmation message
                        display_message = "I've created a recruiting sequence based on your requirements."
                except json.JSONDecodeError:
                    # If not a JSON, use the tool result as is
                    pass
        except json.JSONDecodeError:
            # If response isn't valid JSON, keep the original response
            pass

        # Add the new messages to chat history
        current_time = datetime.now(UTC).isoformat()
        new_messages = [
            {"text": message, "sender": "user", "timestamp": current_time},
            {"text": display_message, "sender": "ai", "timestamp": current_time}
        ]
        chat_history.messages = chat_history.messages + new_messages
        chat_history.updated_at = datetime.now(UTC)
        db.session.commit()

        # Check if the response contains a sequence update and handle it
        try:
            response_data = json.loads(response)
            if response_data.get("status") == "success" and response_data.get("tool_result"):
                # Check if the tool result contains a sequence
                try:
                    tool_result = json.loads(response_data["tool_result"])
                    if isinstance(tool_result, dict) and "metadata" in tool_result and "steps" in tool_result:
                        # If it's a sequence, emit a sequence update
                        emit('sequence_updated', {'data': tool_result})
                except json.JSONDecodeError:
                    pass
        except json.JSONDecodeError:
            pass

        # Send the original response to the client
        emit('chat_response', {'data': response})
    except Exception as e:
        print(f"Error in handle_chat_message: {str(e)}")
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
        print(f"Error in handle_sequence_update: {str(e)}")
        emit('error', {'data': f"Error saving sequence: {str(e)}"})

@socketio.on('get_chat_history')
def handle_get_chat_history():
    try:
        chat_history = ChatHistory.get_or_create(request.sid)
        emit('chat_history', {'data': chat_history.messages})
    except Exception as e:
        print(f"Error retrieving chat history: {str(e)}")
        emit('error', {'data': f"Error retrieving chat history: {str(e)}"})

@socketio.on('process_edit')
def handle_process_edit(data):
    try:
        step_id = data.get('step_id', '')
        content = data.get('content', '')
        request_text = data.get('request', 'Refine this step')
        
        # Get chat history for this connection
        chat_history = ChatHistory.get_or_create(request.sid)
        
        print(f"Processing edit from {request.sid} for step {step_id}")
        
        # Create a prompt for the LLM to refine the step
        refinement_prompt = f"""
        Please refine this recruiting sequence step based on the following request:
        
        Request: {request_text}
        
        Current content: {content}
        
        Please improve this message while maintaining its purpose and key information.
        Return ONLY the improved message text without any explanations.
        """
        
        # Process with the LLM
        response = agent.llm([HumanMessage(content=refinement_prompt)])
        refined_content = response.content.strip()
        
        # Send back the refined content
        emit('step_refined', {
            'step_id': step_id,
            'refined_content': refined_content,
            'message': 'I\'ve refined your message to be more effective.'
        })
    except Exception as e:
        print(f"Error in handle_process_edit: {str(e)}")
        emit('error', {'data': f"Error processing edit: {str(e)}"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.getenv('PORT', 5000))
    socketio.run(app, 
                host='0.0.0.0', 
                port=port, 
                debug=True,
                allow_unsafe_werkzeug=True) 