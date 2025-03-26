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
from sqlalchemy.exc import SQLAlchemyError
from dateutil.tz import UTC
import urllib

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure database
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL environment variable is not set")

# Handle Heroku's DATABASE_URL format if present
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}

try:
    db = SQLAlchemy(app)
    # Test the database connection
    with app.app_context():
        db.engine.connect()
    print("Successfully connected to PostgreSQL database")
except SQLAlchemyError as e:
    print(f"Error connecting to database: {str(e)}")
    raise

# Initialize SocketIO with CORS settings
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='eventlet')

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

# Initialize the recruiting agent with database instance and Sequence model
agent = RecruitingAgent(db_instance=db, sequence_model=Sequence)

# Define suggested prompts
SUGGESTED_PROMPTS = [
    {
        "id": "software-dev-sequence",
        "text": "Create a recruiting sequence for a software developer",
        "description": "Generate a customized outreach sequence for hiring software developers"
    },
    {
        "id": "data-scientist-sequence",
        "text": "Create a recruiting sequence for a data scientist",
        "description": "Generate a customized outreach sequence for hiring data scientists"
    },
    {
        "id": "product-manager-sequence",
        "text": "Create a recruiting sequence for a product manager",
        "description": "Generate a customized outreach sequence for hiring product managers"
    },
    {
        "id": "senior-engineer-sequence",
        "text": "Create a recruiting sequence for a senior engineer",
        "description": "Generate a customized outreach sequence for hiring senior engineers"
    }
]

# Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

@app.route('/api/suggested-prompts', methods=['GET'])
def get_suggested_prompts():
    """Return a list of suggested prompts for the chat interface."""
    return jsonify(SUGGESTED_PROMPTS)

# Socket.IO events
@socketio.on('connect')
def handle_connect():
    print(f'Client connected with ID: {request.sid}')
    # Create a new chat history entry for this connection
    ChatHistory.get_or_create(request.sid)
    emit('connection_response', {'data': 'Connected', 'socket_id': request.sid})
    
    # Send suggested prompts to the client
    emit('suggested_prompts', {'prompts': SUGGESTED_PROMPTS})

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
            if response_data.get("status") == "success":
                # Extract just the chat response for display
                if response_data.get("chat_response"):
                    display_message = response_data["chat_response"]
                elif response_data.get("tool_result"):
                    # Try to extract from tool result if no chat response
                    display_message = response_data["tool_result"]
                    
                # Check if this is part of the sequence creation flow
                try:
                    tool_result = json.loads(response_data.get("tool_result", "{}"))
                    if tool_result.get("status") == "question" and "sequence_info" in tool_result:
                        # For sequence questions, use the question as the display message
                        display_message = tool_result["question"]
                        
                        # Check if this is the first question with an intro message
                        if "message" in tool_result:
                            display_message = f"{tool_result['message']}\n\n{display_message}"
                except json.JSONDecodeError:
                    # If not a JSON, keep the display message as is
                    pass
                    
                # Check if the tool result is a JSON sequence
                try:
                    tool_result_data = json.loads(display_message)
                    if isinstance(tool_result_data, dict) and "metadata" in tool_result_data and "steps" in tool_result_data:
                        # For sequence results, use a more detailed confirmation message
                        role = tool_result_data['metadata']['role']
                        industry = tool_result_data['metadata']['industry']
                        seniority = tool_result_data['metadata']['seniority']
                        includes_interviews = tool_result_data['metadata'].get('includes_interview_steps', False)
                        campaign_idea = tool_result_data['metadata'].get('campaign_idea', '')
                        
                        display_message = f"I've created a recruiting sequence for a {seniority} {role} position in the {industry} industry."
                        
                        # Add campaign idea if available
                        if campaign_idea:
                            display_message += f"\n\nThis sequence is designed to support your campaign idea: {campaign_idea}"
                        
                        # Count outreach steps and interview steps
                        outreach_steps = 0
                        interview_steps = 0
                        for step in tool_result_data['steps']:
                            step_type = step.get('type', '').lower()
                            if step_type in ['email', 'linkedin', 'call', 'text', 'message']:
                                outreach_steps += 1
                            elif any(keyword in step.get('content', '').lower() for keyword in ['interview', 'screening', 'assessment', 'meeting', 'offer']):
                                interview_steps += 1
                        
                        display_message += f"\n\nThe sequence includes {outreach_steps} outreach steps"
                        if includes_interviews and interview_steps > 0:
                            display_message += f" and {interview_steps} post-outreach interview steps"
                        display_message += "."
                        
                        display_message += "\n\nPlease review it and let me know if you'd like any changes."
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
                # Check if this is a sequence from the generate_sequence tool
                if response_data.get("llm_response", {}).get("action") == "generate_sequence":
                    try:
                        # First try parsing the tool_result directly
                        sequence_data = json.loads(response_data.get("tool_result"))
                        if "metadata" in sequence_data and "steps" in sequence_data:
                            # Emit the sequence update
                            emit('sequence_updated', {'data': sequence_data})
                            print("Emitted sequence_updated from generate_sequence action")
                    except json.JSONDecodeError:
                        pass
                
                # Check if this is an edit_sequence_step action
                if response_data.get("llm_response", {}).get("action") == "edit_sequence_step":
                    try:
                        tool_result = json.loads(response_data["tool_result"])
                        if tool_result.get("status") == "success" and tool_result.get("sequence"):
                            # Emit the updated sequence to all clients
                            emit('sequence_updated', {'data': tool_result["sequence"]}, broadcast=True)
                            print("Emitted sequence_updated from edit_sequence_step action")
                    except json.JSONDecodeError:
                        pass
                    
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
        
        # Send new suggested prompts based on conversation context
        try:
            # For simplicity, we'll just send the default prompts again
            # In a more advanced implementation, you could generate contextual suggestions
            emit('suggested_prompts', {'prompts': SUGGESTED_PROMPTS})
        except Exception as e:
            print(f"Error sending suggested prompts: {str(e)}")
            
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

@socketio.on('edit_sequence_step')
def handle_edit_sequence_step(data):
    try:
        step_id = data.get('step_id', '')
        new_content = data.get('new_content', '')
        
        if not step_id or not new_content:
            emit('error', {'data': "Missing step ID or content"})
            return
            
        # Use the agent's edit_sequence_step method
        input_data = json.dumps({
            "step_id": step_id,
            "new_content": new_content
        })
        result = json.loads(agent._edit_sequence_step(input_data))
        
        if result.get('status') == 'success':
            # Send the updated sequence to all clients
            emit('sequence_updated', {'data': result.get('sequence')}, broadcast=True)
            emit('step_edited', {'step_id': step_id, 'success': True})
        else:
            emit('error', {'data': result.get('message', 'Failed to update sequence step')})
    except Exception as e:
        print(f"Error in handle_edit_sequence_step: {str(e)}")
        emit('error', {'data': f"Error updating sequence step: {str(e)}"})

@socketio.on('get_sequence')
def handle_get_sequence():
    try:
        # Get the most recent sequence
        sequence = Sequence.query.order_by(Sequence.created_at.desc()).first()
        if sequence:
            emit('sequence_updated', {'data': sequence.steps})
        else:
            # Create a default sequence
            input_data = json.dumps({
                "step_id": "1",
                "new_content": "Hello [Candidate's Name], I wanted to reach out about a potential opportunity."
            })
            result = json.loads(agent._edit_sequence_step(input_data))
            if result.get('status') == 'success':
                emit('sequence_updated', {'data': result.get('sequence')})
            else:
                emit('error', {'data': 'Failed to create default sequence'})
    except Exception as e:
        print(f"Error in handle_get_sequence: {str(e)}")
        emit('error', {'data': f"Error retrieving sequence: {str(e)}"})

@socketio.on('get_chat_history')
def handle_get_chat_history(self):
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

@socketio.on('get_suggested_prompts')
def handle_get_suggested_prompts():
    """Send suggested prompts to the client when requested."""
    print(f"Client {request.sid} requested suggested prompts")
    emit('suggested_prompts', {'prompts': SUGGESTED_PROMPTS})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
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