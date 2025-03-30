from flask_socketio import emit
from flask import request, current_app
from models.sequence import Sequence
from models.chat_history import ChatHistory
from agent import RecruitingAgent
from datetime import datetime, UTC
from langchain.schema import HumanMessage
import json

def init_socket_routes(socketio, db, agent):
    """Initialize socket routes with required dependencies"""
    
    @socketio.on('connect')
    def handle_connect(auth=None):
        try:
            print(f'Client connected with ID: {request.sid}')
            # Create a new chat history entry for this connection
            with current_app.app_context():
                session = db.session.registry()
                # 
                try:
                    chat_history = ChatHistory.get_or_create(request.sid, session)
                    session.commit()
                except Exception as e:
                    session.rollback()
                    print(f"Error creating chat history: {str(e)}")
                finally:
                    session.close()
            emit('connection_response', {'data': 'Connected', 'socket_id': request.sid})
        except Exception as e:
            print(f"Error in handle_connect: {str(e)}")
            emit('error', {'data': f"Connection error: {str(e)}"})

    @socketio.on('disconnect')
    def handle_disconnect():
        try:
            print(f'Client disconnected: {request.sid}')
        except Exception as e:
            print(f"Error in handle_disconnect: {str(e)}")

    @socketio.on('chat_message')
    def handle_chat_message(data):
        try:
            message = data.get('message', '')
            print(f"Received message thr socket: {message}")
            response = None
            display_message = None
            
            # Get chat history for this connection
            with current_app.app_context():
                session = db.session.registry()
                try:
                    chat_history = ChatHistory.get_or_create(request.sid, session)
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
                    session.commit()
                except Exception as e:
                    session.rollback()
                    print(f"Error in chat message handling: {str(e)}")
                    raise
                finally:
                    session.close()

            # Check if the response contains a sequence update and handle it
            if response:
                try:
                    response_data = json.loads(response)
                    if response_data.get("status") == "success" and response_data.get("tool_result"):
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
            if response:
                emit('chat_response', {'data': response})
            else:
                emit('error', {'data': 'No response generated'})
        except Exception as e:
            print(f"Error in handle_chat_message: {str(e)}")
            emit('error', {'data': f"Error processing message: {str(e)}"})

    @socketio.on('sequence_update')
    def handle_sequence_update(data):
        try:
            sequence = data.get('sequence', [])
            # Save the sequence to the database
            with current_app.app_context():
                session = db.session.registry()
                try:
                    new_sequence = Sequence(
                        title="Recruiting Sequence",
                        steps=sequence
                    )
                    session.add(new_sequence)
                    session.commit()
                except Exception as e:
                    session.rollback()
                    print(f"Error saving sequence: {str(e)}")
                    raise
                finally:
                    session.close()
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
            with current_app.app_context():
                session = db.session.registry()
                try:
                    sequence = session.query(Sequence).order_by(Sequence.created_at.desc()).first()
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
                    session.rollback()
                    print(f"Error getting sequence: {str(e)}")
                    raise
                finally:
                    session.close()
        except Exception as e:
            print(f"Error in handle_get_sequence: {str(e)}")
            emit('error', {'data': f"Error retrieving sequence: {str(e)}"})

    @socketio.on('get_chat_history')
    def handle_get_chat_history(data):
        try:
            with current_app.app_context():
                session = db.session.registry()
                try:
                    chat_history = ChatHistory.get_or_create(request.sid, session)
                    emit('chat_history', {'data': chat_history.messages})
                except Exception as e:
                    session.rollback()
                    print(f"Error getting chat history: {str(e)}")
                    raise
                finally:
                    session.close()
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
            with current_app.app_context():
                session = db.session.registry()
                try:
                    chat_history = ChatHistory.get_or_create(request.sid, session)
                except Exception as e:
                    session.rollback()
                    print(f"Error getting chat history: {str(e)}")
                    raise
                finally:
                    session.close()
            
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