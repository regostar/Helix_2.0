from flask import request
from flask_socketio import emit
from datetime import datetime, UTC
import json
from models.chat_history import ChatHistory
from models.sequence import Sequence
from services.agent_service import RecruitingAgent

# Initialize the recruiting agent
agent = None

def init_socket_routes(socketio, db_instance):
    global agent
    agent = RecruitingAgent(db_instance=db_instance, sequence_model=Sequence)

    @socketio.on('connect')
    def handle_connect():
        print(f'Client connected with ID: {request.sid}')
        ChatHistory.get_or_create(request.sid)
        emit('connection_response', {'data': 'Connected', 'socket_id': request.sid})

    @socketio.on('disconnect')
    def handle_disconnect():
        print(f'Client disconnected: {request.sid}')

    @socketio.on('chat_message')
    def handle_chat_message(data):
        try:
            message = data.get('message', '')
            chat_history = ChatHistory.get_or_create(request.sid)
            current_sequence = data.get('current_sequence', [])

            print(f"Received message from {request.sid}: {message}")
            response = agent.process_message(message, chat_history.messages, current_sequence)
            print(f"Agent response: {response}")

            display_message = response
            try:
                response_data = json.loads(response)
                if response_data.get("status") == "success" and response_data.get("tool_result"):
                    display_message = response_data["tool_result"]
                    try:
                        tool_result_data = json.loads(display_message)
                        if isinstance(tool_result_data, dict) and "metadata" in tool_result_data and "steps" in tool_result_data:
                            display_message = "I've created a recruiting sequence based on your requirements."
                    except json.JSONDecodeError:
                        pass
            except json.JSONDecodeError:
                pass

            current_time = datetime.now(UTC).isoformat()
            new_messages = [
                {"text": message, "sender": "user", "timestamp": current_time},
                {"text": display_message, "sender": "ai", "timestamp": current_time}
            ]
            chat_history.messages = chat_history.messages + new_messages
            chat_history.updated_at = datetime.now(UTC)
            db_instance.session.commit()

            try:
                response_data = json.loads(response)
                if response_data.get("status") == "success" and response_data.get("tool_result"):
                    if response_data.get("llm_response", {}).get("action") == "edit_sequence_step":
                        try:
                            tool_result = json.loads(response_data["tool_result"])
                            if tool_result.get("status") == "success" and tool_result.get("sequence"):
                                emit('sequence_updated', {'data': tool_result["sequence"]}, broadcast=True)
                                print("Emitted sequence_updated from edit_sequence_step action")
                        except json.JSONDecodeError:
                            pass
                        
                    try:
                        tool_result = json.loads(response_data["tool_result"])
                        if isinstance(tool_result, dict) and "metadata" in tool_result and "steps" in tool_result:
                            emit('sequence_updated', {'data': tool_result})
                    except json.JSONDecodeError:
                        pass
            except json.JSONDecodeError:
                pass

            emit('chat_response', {'data': response})
        except Exception as e:
            print(f"Error in handle_chat_message: {str(e)}")
            emit('chat_response', {'data': f"Error processing message: {str(e)}"})

    @socketio.on('sequence_update')
    def handle_sequence_update(data):
        try:
            sequence = data.get('sequence', [])
            new_sequence = Sequence(
                title="Recruiting Sequence",
                steps=sequence
            )
            db_instance.session.add(new_sequence)
            db_instance.session.commit()
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
                
            input_data = json.dumps({
                "step_id": step_id,
                "new_content": new_content
            })
            result = json.loads(agent._edit_sequence_step(input_data))
            
            if result.get('status') == 'success':
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
            sequence = Sequence.query.order_by(Sequence.created_at.desc()).first()
            if sequence:
                emit('sequence_updated', {'data': sequence.steps})
            else:
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
    def handle_get_chat_history(data=None):
        try:
            chat_history = ChatHistory.get_or_create(request.sid)
            emit('chat_history', {'data': chat_history.messages})
        except Exception as e:
            print(f"Error in handle_get_chat_history: {str(e)}")
            emit('error', {'data': f"Error retrieving chat history: {str(e)}"}) 