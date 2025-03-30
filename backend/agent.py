from typing import List, Dict, Any
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.tools import Tool
from langchain.schema import HumanMessage, SystemMessage
import json
import os
import csv
import smtplib
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import datetime
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, UTC
from flask_socketio import emit
from config.config import (
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    FROM_EMAIL,
    OPENAI_API_KEY
)
from openai import (
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
    APIError,
    BadRequestError,
    AuthenticationError,
    PermissionDeniedError
)

load_dotenv()

SYSTEM_TEMPLATE = """You are Helix, an AI-powered recruiting outreach agent. Your goal is to help HR professionals create effective recruiting sequences and manage candidate outreach.

Available tools:
{tools}

IMPORTANT INSTRUCTIONS:
1. You MUST use one of these exact tool names: {tool_names}
2. You MUST respond with ONLY a JSON object
3. The JSON object MUST have exactly these fields:
   - "action": Must be one of the tool names listed above
   - "action_input": The input string for the chosen tool
4. Do not include ANY other text before or after the JSON
5. The response must be valid JSON that can be parsed by json.loads()
6. When editing a sequence step, ALWAYS use the tool name "edit_sequence_step", NOT "modify_sequence_step"

Example valid responses:
{{
    "action": "generate_sequence",
    "action_input": "Create a sequence for a senior software engineer role"
}}

{{
    "action": "ask_clarifying_question",
    "action_input": "What industry is this role in?"
}}

{{
    "action": "generate_job_description",
    "action_input": "Create a job description for a senior software engineer role"
}}

{{
    "action": "edit_sequence_step",
    "action_input": "{{\\"step_id\\": \\"1\\", \\"new_content\\": \\"Updated message content\\"}}"
}}

Remember: ONLY return the JSON object, nothing else."""

HUMAN_TEMPLATE = """Current conversation:
{chat_history}

Current sequence:
{current_sequence}

User request: {input}"""

# This will be populated from app.py when the agent is initialized
db = SQLAlchemy()
Sequence = None

class RecruitingAgent:
    def __init__(self, db_instance=None, sequence_model=None):
        self.llm = ChatOpenAI(
            temperature=0.7,
            model="gpt-4",
            openai_api_key=OPENAI_API_KEY,
        )
        self.db = db_instance
        # Set the global db instance
        if db_instance:
            db = db_instance
        # Set the global Sequence model
        if sequence_model:
            Sequence = sequence_model
        self.tools = self._get_tools()
        self.prompt = self._create_prompt()
        self.output_parser = self._create_output_parser()
        self.agent = self._create_agent()
        self.smtp_server = SMTP_SERVER
        self.smtp_port = SMTP_PORT
        self.smtp_username = SMTP_USERNAME
        self.smtp_password = SMTP_PASSWORD
        self.from_email = FROM_EMAIL
        self.candidate_data = []

    def _get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="ask_clarifying_question",
                func=self._ask_clarifying_question,
                description="Ask a clarifying question to better understand the user's requirements"
            ),
            Tool(
                name="generate_job_description",
                func=self._generate_job_description,
                description="Generate a job description based on the user's requirements"
            ),
            Tool(
                name="generate_sequence",
                func=self._generate_sequence,
                description="Generate a new recruiting sequence based on the user's requirements"
            ),
            Tool(
                name="edit_sequence_step",
                func=self._edit_sequence_step,
                description="Edit a specific step in the recruiting sequence"
            ),
            Tool(
                name="modify_sequence",
                func=self._modify_sequence,
                description="Modify the existing sequence based on user feedback"
            ),
            Tool(
                name="provide_feedback",
                func=self._provide_feedback,
                description="Provide feedback on the current sequence"
            ),
            Tool(
                name="load_csv_candidates",
                func=self._load_csv_candidates,
                description="Load candidate data from a CSV file and filter based on criteria"
            ),
            Tool(
                name="send_personalized_email",
                func=self._send_personalized_email,
                description="Send a personalized email to a candidate based on their profile"
            ),
            Tool(
                name="prepare_linkedin_message",
                func=self._prepare_linkedin_message,
                description="Prepare a personalized LinkedIn message for outreach"
            ),
            Tool(
                name="merge_candidate_data",
                func=self._merge_candidate_data,
                description="Merge and deduplicate candidate data from multiple sources"
            )
        ]

    def _format_chat_history(self, chat_history: List[Dict]) -> str:
        return "\n".join(
            f"{'Human' if msg['sender'] == 'user' else 'Helix'}: {msg['text']}"
            for msg in chat_history
        )

    def _format_sequence(self, sequence: List[Dict]) -> str:
        if not sequence:
            return "No sequence created yet."
        return "\n".join(
            f"Step {i+1}: {step['type']} - {step['content']} (Delay: {step['delay']} days)"
            for i, step in enumerate(sequence)
        )

    def _create_output_parser(self):
        response_schemas = [
            ResponseSchema(
                name="action",
                description="The action to take. Must be one of: ask_clarifying_question, generate_sequence, modify_sequence, provide_feedback, edit_sequence_step",
            ),
            ResponseSchema(
                name="action_input",
                description="The input to provide to the tool. For generate_sequence, provide the requirements. For ask_clarifying_question, provide the question. For modify_sequence, provide the modifications. For provide_feedback, provide the sequence to analyze. For edit_sequence_step, provide a JSON string with step_id and new_content.",
            ),
        ]
        return StructuredOutputParser.from_response_schemas(response_schemas)

    def _create_prompt(self) -> ChatPromptTemplate:
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=SYSTEM_TEMPLATE),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", HUMAN_TEMPLATE),
        ])
        return prompt

    def _create_agent(self):
        return {
            "llm": self.llm,
            "tools": self.tools,
            "prompt": self.prompt,
            "output_parser": self.output_parser
        }

    def _ask_clarifying_question(self, question: str) -> str:
        return f"Could you please clarify: {question}"

    def _generate_sequence(self, requirements: str) -> str:
        """Generate a customized recruiting sequence based on the given requirements.
        
        Args:
            requirements (str): String containing role, industry, seniority, and other requirements
            
        Returns:
            str: JSON string containing the generated sequence
        """
        try:
            # Get initial response from LLM to analyze requirements
            analysis_prompt = f"""Analyze these recruiting requirements and return ONLY a JSON object with the following fields:
            Requirements: {requirements}

IMPORTANT: Respond with ONLY a JSON object containing these exact fields:
{{
    "role_title": "the job title",
    "industry": "the industry",
    "seniority": "Junior/Mid/Senior",
    "key_skills": ["skill1", "skill2", ...],
    "company_type": "Startup/Enterprise/Agency"
}}

Do not include any other text before or after the JSON."""
            
            analysis = self.llm([HumanMessage(content=analysis_prompt)])
            parsed_analysis = json.loads(analysis.content.strip())
            
            # Get sequence structure based on analysis
            sequence_prompt = f"""Generate a recruiting sequence as a JSON array based on this analysis:
{json.dumps(parsed_analysis, indent=2)}

IMPORTANT: Respond with ONLY a JSON array of sequence steps. Each step must have these exact fields:
[
    {{
        "id": "1",
        "type": "email/linkedin/call/other",
        "content": "detailed message content",
        "delay": number_of_days,
        "personalization_tips": "how to personalize this message"
    }},
    ...
]

The sequence should:
1. Match the seniority level ({parsed_analysis['seniority']})
2. Be appropriate for {parsed_analysis['industry']} industry
3. Highlight these skills: {', '.join(parsed_analysis['key_skills'])}
4. Reflect {parsed_analysis['company_type']} company culture

Do not include any other text before or after the JSON array."""
            
            sequence_response = self.llm([HumanMessage(content=sequence_prompt)])
            sequence = json.loads(sequence_response.content.strip())
            
            # Add metadata to the sequence
            final_sequence = {
                "metadata": {
                    "role": parsed_analysis["role_title"],
                    "industry": parsed_analysis["industry"],
                    "seniority": parsed_analysis["seniority"],
                    "company_type": parsed_analysis["company_type"],
                    "generated_at": datetime.now(UTC).isoformat()
                },
                "steps": sequence
            }
            
            return json.dumps(final_sequence, indent=2)
            
        except json.JSONDecodeError as e:
            return json.dumps({
                "error": "Failed to parse LLM response",
                "details": str(e),
                "raw_response": analysis.content if 'analysis' in locals() else None
            })
        except Exception as e:
            return json.dumps({
                "error": "Failed to generate sequence",
                "details": str(e),
                "raw_response": analysis.content if 'analysis' in locals() else None
            })

    def _modify_sequence(self, modifications: str) -> str:
        # Modify the sequence based on user feedback
        return "I've modified the sequence according to your requirements."

    def _provide_feedback(self, sequence: str) -> str:
        # Provide feedback on the current sequence
        return "Here's my analysis of the current sequence..."

    def _load_csv_candidates(self, input_text: str) -> str:
        """
        Load candidate profiles from a CSV file and filter based on criteria.
        
        Args:
            input_text: Contains file_path and filter criteria in the format 
                       "file_path: /path/to/csv, role: software engineer, experience: 3+ years"
        
        Returns:
            JSON string with filtered candidate profiles
        """
        try:
            # Parse input
            params = {}
            for part in input_text.split(','):
                if ':' in part:
                    key, value = part.split(':', 1)
                    params[key.strip().lower()] = value.strip()
            
            file_path = params.get('file_path', '')
            role_filter = params.get('role', '').lower()
            experience_filter = params.get('experience', '').lower()
            
            # Validate file path
            if not file_path or not os.path.exists(file_path):
                return json.dumps({
                    "error": "Invalid or missing file path",
                    "candidates": []
                })
            
            # Read CSV
            candidates = []
            try:
                # Try pandas first (handles more formats)
                df = pd.read_csv(file_path)
                candidates = df.to_dict('records')
            except:
                # Fallback to standard csv library
                with open(file_path, 'r', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    candidates = list(reader)
            
            # Filter candidates
            filtered_candidates = []
            for candidate in candidates:
                # Convert all keys to lowercase for case-insensitive matching
                candidate_lower = {k.lower(): v for k, v in candidate.items()}
                
                # Check if candidate matches role filter
                role_match = True
                if role_filter and 'role' in candidate_lower:
                    role_match = role_filter in candidate_lower['role'].lower()
                
                # Check if candidate matches experience filter
                exp_match = True
                if experience_filter and 'experience' in candidate_lower:
                    # Simple numeric extraction for experience 
                    try:
                        exp_value = int(''.join(filter(str.isdigit, candidate_lower['experience'])))
                        req_exp = int(''.join(filter(str.isdigit, experience_filter)))
                        exp_match = exp_value >= req_exp
                    except:
                        exp_match = True  # If we can't parse, don't filter out
                
                if role_match and exp_match:
                    filtered_candidates.append(candidate)
            
            # Store for later use
            self.candidate_data = filtered_candidates
            
            return json.dumps({
                "total_candidates": len(candidates),
                "filtered_candidates": len(filtered_candidates),
                "candidates": filtered_candidates[:10],  # Return only first 10 for preview
                "message": f"Successfully loaded {len(filtered_candidates)} candidates matching criteria from {len(candidates)} total."
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": f"Failed to process CSV: {str(e)}",
                "candidates": []
            })

    def _send_personalized_email(self, input_text: str) -> str:
        """
        Send a personalized email to a candidate.
        
        Args:
            input_text: JSON string containing email template and candidate info
            
        Returns:
            JSON string with status and details
        """
        try:
            # Parse the input
            input_data = json.loads(input_text)
            template = input_data.get('template', '')
            candidate_info = input_data.get('candidate', {})
            subject = input_data.get('subject', 'Exciting Opportunity')
            
            # Validate inputs
            if not template:
                return json.dumps({"error": "Email template is required"})
            if not candidate_info:
                return json.dumps({"error": "Candidate information is required"})
            if not candidate_info.get('email'):
                return json.dumps({"error": "Candidate email is required"})
                
            # Personalize the email
            personalized_email = template
            for key, value in candidate_info.items():
                placeholder = f"{{{key}}}"
                personalized_email = personalized_email.replace(placeholder, str(value))
            
            # Setup email
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = candidate_info.get('email')
            msg['Subject'] = subject
            
            # Attach email body
            msg.attach(MIMEText(personalized_email, 'html'))
            
            # For testing purposes, we'll just simulate sending
            if not self.smtp_username or not self.smtp_password:
                return json.dumps({
                    "status": "simulated",
                    "message": "Email would be sent (credentials not configured)",
                    "to": candidate_info.get('email'),
                    "subject": subject,
                    "body_preview": personalized_email[:100] + "..."
                })
            
            # Actual sending (commented for safety)
            try:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                text = msg.as_string()
                server.sendmail(self.from_email, candidate_info.get('email'), text)
                server.quit()
                return json.dumps({
                    "status": "sent",
                    "message": f"Email successfully sent to {candidate_info.get('email')}",
                    "subject": subject
                })
            except Exception as email_error:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to send email: {str(email_error)}",
                    "to": candidate_info.get('email')
                })
            
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON in input"})
        except Exception as e:
            return json.dumps({"error": f"Failed to process email: {str(e)}"})

    def _prepare_linkedin_message(self, input_text: str) -> str:
        """
        Prepare a personalized LinkedIn message for a candidate.
        
        Args:
            input_text: JSON string containing template and candidate info
            
        Returns:
            JSON string with personalized message
        """
        try:
            # Parse the input
            input_data = json.loads(input_text)
            template = input_data.get('template', '')
            candidate_info = input_data.get('candidate', {})
            
            # Validate inputs
            if not template:
                return json.dumps({"error": "Message template is required"})
            if not candidate_info:
                return json.dumps({"error": "Candidate information is required"})
            
            # Personalize the message
            personalized_message = template
            for key, value in candidate_info.items():
                placeholder = f"{{{key}}}"
                personalized_message = personalized_message.replace(placeholder, str(value))
            
            return json.dumps({
                "status": "success",
                "linkedin_message": personalized_message,
                "candidate_name": candidate_info.get('name', 'Unknown'),
                "message": "LinkedIn message prepared successfully."
            })
            
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON in input"})
        except Exception as e:
            return json.dumps({"error": f"Failed to prepare LinkedIn message: {str(e)}"})

    def _merge_candidate_data(self, input_text: str) -> str:
        """
        Merge and deduplicate candidate data from multiple sources.
        
        Args:
            input_text: JSON string containing candidate lists or criteria
            
        Returns:
            JSON string with merged, deduplicated data
        """
        try:
            input_data = json.loads(input_text)
            csv_candidates = input_data.get('csv_candidates', [])
            web_candidates = input_data.get('web_candidates', [])
            
            # If no specific candidates provided, use the stored candidate data
            if not csv_candidates and self.candidate_data:
                csv_candidates = self.candidate_data
            
            # Combine all candidates
            all_candidates = csv_candidates + web_candidates
            
            # Deduplicate by email
            unique_candidates = {}
            for candidate in all_candidates:
                email = candidate.get('email', '').lower()
                if email and email not in unique_candidates:
                    unique_candidates[email] = candidate
            
            merged_candidates = list(unique_candidates.values())
            
            return json.dumps({
                "status": "success",
                "total_candidates": len(merged_candidates),
                "candidates": merged_candidates[:20],  # Return first 20 for preview
                "message": f"Successfully merged and deduplicated data resulting in {len(merged_candidates)} unique candidates."
            }, indent=2)
            
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON in input"})
        except Exception as e:
            return json.dumps({"error": f"Failed to merge candidate data: {str(e)}"})

    def _generate_job_description(self, requirements: str) -> str:
        """Generate a job description based on the given requirements.
        
        Args:
            requirements (str): String containing role details and requirements
            
        Returns:
            str: JSON string containing the generated job description
        """
        try:
            # First, analyze the requirements to extract key information
            analysis_prompt = f"""Analyze these job requirements and return ONLY a JSON object with the following fields:
            Requirements: {requirements}

IMPORTANT: Respond with ONLY a JSON object containing these exact fields:
{{
    "role_title": "the job title",
    "department": "the department",
    "location": "the location (remote/hybrid/onsite)",
    "employment_type": "full-time/part-time/contract",
    "experience_level": "entry/mid/senior/lead",
    "key_skills": ["skill1", "skill2", ...],
    "responsibilities": ["responsibility1", "responsibility2", ...],
    "requirements": ["requirement1", "requirement2", ...],
    "preferred_qualifications": ["qualification1", "qualification2", ...],
    "benefits": ["benefit1", "benefit2", ...]
}}

Do not include any other text before or after the JSON."""
            
            analysis = self.llm([HumanMessage(content=analysis_prompt)])
            parsed_analysis = json.loads(analysis.content.strip())
            
            # Generate the job description based on the analysis
            description_prompt = f"""Generate a professional job description based on this analysis:
{json.dumps(parsed_analysis, indent=2)}

IMPORTANT: Respond with ONLY a JSON object containing these exact fields:
{{
    "title": "Job Title",
    "company": "Company Name",
    "location": "Location",
    "employment_type": "Employment Type",
    "description": "Full job description text",
    "requirements": "Requirements section text",
    "benefits": "Benefits section text"
}}

The description should be well-formatted, professional, and include all the key information from the analysis.
Do not include any other text before or after the JSON."""
            
            description = self.llm([HumanMessage(content=description_prompt)])
            return description.content.strip()
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Error generating job description: {str(e)}"
            })

    def _edit_sequence_step(self, input_data: str) -> str:
        """Edit a specific step in the recruiting sequence.
        
        Args:
            input_data (str): JSON string containing step_id and new_content
            
        Returns:
            str: JSON string containing the updated sequence
        """
        try:
            # Parse the input data
            data = json.loads(input_data)
            step_id = data.get('step_id')
            new_content = data.get('new_content')
            
            if not step_id or not new_content:
                return json.dumps({
                    "status": "error",
                    "message": "Missing step_id or new_content in the request"
                })
            
            # Get the current sequence from the database
            sequence = self.db.session.query(Sequence).order_by(Sequence.created_at.desc()).first()
            
            # If no sequence exists, create a default one
            if not sequence:
                # Create a default recruiting sequence with some steps
                default_steps = [
                    {
                        "id": "1",
                        "type": "email",
                        "content": "Hello [Candidate's Name], I came across your profile and was impressed by your background. I wanted to reach out about a potential opportunity at our company that might align with your skills and interests.",
                        "delay": 0,
                        "personalization_tips": "Reference specific skills or experiences from their profile."
                    },
                    {
                        "id": "2",
                        "type": "linkedin",
                        "content": "Hi [Candidate's Name], I recently emailed you regarding an opportunity at our company. I'd love to connect and discuss how your experience might be a great fit for our team.",
                        "delay": 3,
                        "personalization_tips": "Mention something specific about their LinkedIn profile that caught your attention."
                    },
                    {
                        "id": "3",
                        "type": "email",
                        "content": "Hello again [Candidate's Name], I wanted to follow up on my previous message about the role at our company. I'd be happy to provide more information or answer any questions you might have.",
                        "delay": 7,
                        "personalization_tips": "Reference any mutual connections or shared experiences."
                    }
                ]
                
                # Create new sequence
                new_sequence = Sequence(
                    title="Default Recruiting Sequence",
                    steps=default_steps
                )
                self.db.session.add(new_sequence)
                self.db.session.commit()
                
                # Use the newly created sequence
                sequence = new_sequence
            
            # Update the specific step
            steps = sequence.steps
            updated = False
            for step in steps:
                if step.get('id') == step_id:
                    step['content'] = new_content
                    updated = True
                    break
            
            # If step_id not found, add a new step
            if not updated:
                new_step = {
                    "id": step_id,
                    "type": "email",
                    "content": new_content,
                    "delay": 3,
                    "personalization_tips": "Personalize based on candidate's background."
                }
                steps.append(new_step)
            
            # Save the updated sequence
            sequence.steps = steps
            sequence.updated_at = datetime.now(UTC)
            self.db.session.commit()
            
            # Return success response with updated sequence
            return json.dumps({
                "status": "success",
                "message": "Step updated successfully",
                "sequence": steps
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Error editing sequence step: {str(e)}"
            })

    def process_message(self, message: str, chat_history: List[Dict], current_sequence: List[Dict]) -> str:
        """Process a user message and return a response.
        
        Returns:
            str: A JSON string containing the LLM response and tool result
        """
        try:
            # Format the chat history into messages
            formatted_chat_history = [
                HumanMessage(content=msg["text"]) if msg["sender"] == "user" 
                else SystemMessage(content=msg["text"])
                for msg in chat_history
            ]
            
            # Format the sequence
            formatted_sequence = self._format_sequence(current_sequence)
            
            # Create the prompt variables
            prompt_variables = {
                "chat_history": formatted_chat_history,
                "input": message,
                "current_sequence": formatted_sequence,
                "tools": "\n".join(t.description for t in self.tools),
                "tool_names": ", ".join(t.name for t in self.tools)
            }

            # Get the response using the prompt template
            try:
                response = self.llm(self.prompt.format_messages(**prompt_variables))
                llm_response = response.content.strip()
            except RateLimitError as e:
                print(f"OpenAI API Rate Limit Error: {str(e)}")
                return json.dumps({
                    "status": "error",
                    "message": "We've reached our API usage limit. Please try again later or contact support.",
                    "error_type": "rate_limit"
                })
            except APIConnectionError as e:
                print(f"OpenAI API Connection Error: {str(e)}")
                return json.dumps({
                    "status": "error",
                    "message": "Unable to connect to the AI service. Please check your internet connection and try again.",
                    "error_type": "connection_error"
                })
            except APITimeoutError as e:
                print(f"OpenAI API Timeout Error: {str(e)}")
                return json.dumps({
                    "status": "error",
                    "message": "The AI service is taking too long to respond. Please try again.",
                    "error_type": "timeout_error"
                })
            except BadRequestError as e:
                print(f"OpenAI API Bad Request Error: {str(e)}")
                return json.dumps({
                    "status": "error",
                    "message": "Invalid request to the AI service. Please try again.",
                    "error_type": "bad_request"
                })
            except AuthenticationError as e:
                print(f"OpenAI API Authentication Error: {str(e)}")
                return json.dumps({
                    "status": "error",
                    "message": "Authentication failed with the AI service. Please contact support.",
                    "error_type": "authentication_error"
                })
            except PermissionDeniedError as e:
                print(f"OpenAI API Permission Error: {str(e)}")
                return json.dumps({
                    "status": "error",
                    "message": "You don't have permission to use this service. Please contact support.",
                    "error_type": "permission_error"
                })
            except APIError as e:
                print(f"OpenAI API Error: {str(e)}")
                return json.dumps({
                    "status": "error",
                    "message": "An error occurred with the AI service. Please try again later.",
                    "error_type": "api_error"
                })
            except Exception as e:
                print(f"Unexpected error in LLM call: {str(e)}")
                return json.dumps({
                    "status": "error",
                    "message": "An unexpected error occurred while processing your request. Please try again.",
                    "error_type": "unexpected_error"
                })
            
            # Try to parse as JSON first
            try:
                json_response = json.loads(llm_response)
                if isinstance(json_response, dict) and "action" in json_response and "action_input" in json_response:
                    parsed_response = json_response
                else:
                    raise ValueError("Response missing required fields")
            except (json.JSONDecodeError, ValueError) as e:
                # If direct JSON parsing fails, try using the output parser
                parsed_response = self.output_parser.parse(llm_response)
            
            tool_name = parsed_response["action"]
            tool_input = parsed_response["action_input"]
            
            # Handle the case where tool_name is modify_sequence_step instead of edit_sequence_step
            if tool_name == "modify_sequence_step":
                tool_name = "edit_sequence_step"
                parsed_response["action"] = "edit_sequence_step"
            
            # Find the matching tool
            tool = next((t for t in self.tools if t.name == tool_name), None)
            if tool is None:
                return json.dumps({
                    "status": "error",
                    "llm_response": llm_response,
                    "error": f"Tool '{tool_name}' not found",
                    "tool_result": None,
                    "chat_response": f"I apologize, but I encountered an error processing your request."
                })
            
            # Execute the tool
            tool_result = tool.func(tool_input)
            
            # Parse tool result for edit_sequence_step
            if tool_name == "edit_sequence_step":
                try:
                    result_json = json.loads(tool_result)
                    # Check if we need to emit a sequence update
                    if result_json.get("status") == "success" and "sequence" in result_json:
                        # Emit a sequence_updated event to update all clients
                        try:
                            # This might fail if not in a SocketIO context
                            emit('sequence_updated', {'data': result_json["sequence"]}, broadcast=True, namespace='/')
                            print(f"Successfully emitted sequence_updated event with sequence data")
                        except Exception as e:
                            print(f"Could not emit sequence update: {str(e)}")
                except Exception as e:
                    print(f"Error parsing edit_sequence_step result: {str(e)}")

            # Generate appropriate chat response based on the tool and result
            chat_response = ""
            if tool_name == "generate_sequence":
                try:
                    sequence_data = json.loads(tool_result)
                    if "metadata" in sequence_data:
                        chat_response = f"I've created a recruiting sequence for a {sequence_data['metadata']['role']} position. Please review it and let me know if you'd like any changes."
                    else:
                        chat_response = "I've created a recruiting sequence based on your requirements. Please review it and let me know if you'd like any changes."
                except:
                    chat_response = "I've created a recruiting sequence based on your requirements. Please review it and let me know if you'd like any changes."
            elif tool_name == "ask_clarifying_question":
                chat_response = tool_input
            elif tool_name == "modify_sequence" or tool_name == "edit_sequence_step":
                # Check if the operation was successful
                try:
                    result_json = json.loads(tool_result)
                    if result_json.get("status") == "success":
                        chat_response = "I've updated the sequence based on your feedback. Please review the changes and let me know if you'd like any further adjustments."
                    else:
                        chat_response = f"I couldn't update the sequence: {result_json.get('message', 'An error occurred')}"
                except:
                    chat_response = "I've modified the sequence based on your feedback. Please review the changes and let me know if you'd like any further adjustments."
            elif tool_name == "provide_feedback":
                chat_response = tool_result
            else:
                chat_response = "I've processed your request. Is there anything specific you'd like me to explain or modify?"

            return json.dumps({
                "status": "success",
                "llm_response": parsed_response,
                "tool_result": tool_result,
                "chat_response": chat_response,
                "error": None
            })
                
        except Exception as e:
            # If we get here, both JSON parsing and output parser failed
            retry_message = """Your last response was not in the correct format. Please respond ONLY with a JSON object like this:
            {
                "action": "tool_name",
                "action_input": "input for the tool"
            }
            No other text should be included."""
            
            # Try one more time with the retry message
            try:
                prompt_variables["input"] = retry_message
                retry_response = self.llm(self.prompt.format_messages(**prompt_variables))
                retry_llm_response = retry_response.content.strip()
                
                parsed_retry = json.loads(retry_llm_response)
                tool_name = parsed_retry["action"]
                tool_input = parsed_retry["action_input"]
                
                tool = next((t for t in self.tools if t.name == tool_name), None)
                if tool is None:
                    return json.dumps({
                        "status": "error",
                        "llm_response": retry_llm_response,
                        "error": f"Tool '{tool_name}' not found",
                        "tool_result": None,
                        "chat_response": "I apologize, but I encountered an error processing your request."
                    })
                
                tool_result = tool.func(tool_input)

                # Generate chat response for retry case
                chat_response = "I've processed your request after a small hiccup. Is there anything specific you'd like me to explain or modify?"

                return json.dumps({
                    "status": "success",
                    "llm_response": parsed_retry,
                    "tool_result": tool_result,
                    "chat_response": chat_response,
                    "error": None
                })
                
            except Exception as retry_error:
                return json.dumps({
                    "status": "error",
                    "llm_response": llm_response,
                    "retry_response": retry_llm_response if 'retry_llm_response' in locals() else None,
                    "error": str(retry_error),
                    "tool_result": None,
                    "chat_response": "I apologize, but I encountered an error processing your request. Could you please try rephrasing your message?"
                }) 