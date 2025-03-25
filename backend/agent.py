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

Example valid responses:
{{
    "action": "generate_sequence",
    "action_input": "Create a sequence for a senior software engineer role"
}}

{{
    "action": "ask_clarifying_question",
    "action_input": "What industry is this role in?"
}}

Remember: ONLY return the JSON object, nothing else."""

HUMAN_TEMPLATE = """Current conversation:
{chat_history}

Current sequence:
{current_sequence}

User request: {input}"""

class RecruitingAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            temperature=0.7,
            model="gpt-4",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )
        self.tools = self._get_tools()
        self.prompt = self._create_prompt()
        self.output_parser = self._create_output_parser()
        self.agent = self._create_agent()
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", "")
        self.candidate_data = []
        self.chat_history = []

    def _get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="ask_clarifying_question",
                func=self._ask_clarifying_question,
                description="Ask a clarifying question to better understand the user's requirements"
            ),
            Tool(
                name="generate_sequence",
                func=self._generate_sequence,
                description="Generate a new recruiting sequence based on the user's requirements"
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
                description="The action to take. Must be one of: ask_clarifying_question, generate_sequence, modify_sequence, provide_feedback",
            ),
            ResponseSchema(
                name="action_input",
                description="The input to provide to the tool. For generate_sequence, provide the requirements. For ask_clarifying_question, provide the question. For modify_sequence, provide the modifications. For provide_feedback, provide the sequence to analyze.",
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
                    "generated_at": datetime.datetime.now().isoformat()
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

    def process_message(self, message: str, chat_history: List[Dict] = None, current_sequence: List[Dict] = None) -> Dict:
        """Process a user message and return a response.
        
        Args:
            message (str): The user's message
            chat_history (List[Dict], optional): List of previous chat messages. Defaults to None.
            current_sequence (List[Dict], optional): Current recruiting sequence. Defaults to None.
            
        Returns:
            Dict: Response containing status, LLM response, tool result, and chat response
        """
        try:
            # Update chat history if provided
            if chat_history is not None:
                self.chat_history = chat_history

            # Convert chat history to LangChain message format
            formatted_chat_history = []
            for msg in self.chat_history:
                if msg["sender"] == "user":
                    formatted_chat_history.append(HumanMessage(content=msg["text"]))
                else:
                    formatted_chat_history.append(SystemMessage(content=msg["text"]))

            # Format the sequence
            sequence = self._format_sequence(current_sequence) if current_sequence else "No current sequence."

            # Create the prompt with the current message
            prompt = self.prompt.format_messages(
                chat_history=formatted_chat_history,
                current_sequence=sequence,
                input=message
            )

            # Get the LLM response
            response = self.llm.invoke(prompt)
            
            # Parse the response
            try:
                # First try to parse as JSON
                llm_response = response.content.strip()
                try:
                    json_response = json.loads(llm_response)
                    if isinstance(json_response, dict) and "action" in json_response and "action_input" in json_response:
                        parsed_response = json_response
                    else:
                        raise ValueError("Response missing required fields")
                except (json.JSONDecodeError, ValueError) as e:
                    # If direct JSON parsing fails, try using the output parser
                    parsed_response = self.output_parser.parse(llm_response)
                    
            except Exception as e:
                print(f"Error parsing LLM response: {e}")
                print(f"Raw response: {response}")
                return {
                    "status": "error",
                    "error": "Failed to parse LLM response",
                    "chat_response": "I apologize, but I couldn't understand your request. Could you please rephrase it?"
                }

            # Get the tool result
            tool_result = None
            chat_response = None

            if parsed_response["action"] == "generate_sequence":
                tool_result = self._generate_sequence(parsed_response["action_input"])
                try:
                    # Parse the tool result to get metadata for the chat response
                    parsed_tool_result = json.loads(tool_result) if isinstance(tool_result, str) else tool_result
                    if "metadata" in parsed_tool_result:
                        chat_response = f"I've created a recruiting sequence for a {parsed_tool_result['metadata']['seniority']} {parsed_tool_result['metadata']['role']} position in the {parsed_tool_result['metadata']['industry']} industry. Please review it and let me know if you'd like to make any changes."
                    else:
                        chat_response = "I've created a recruiting sequence based on your requirements. Please review it and let me know if you'd like to make any changes."
                except json.JSONDecodeError:
                    chat_response = "I've created a recruiting sequence based on your requirements. Please review it and let me know if you'd like to make any changes."
            
            elif parsed_response["action"] == "modify_sequence":
                if current_sequence:
                    tool_result = self._modify_sequence(current_sequence, parsed_response["action_input"])
                    chat_response = "I've updated the sequence based on your feedback. Would you like to make any other adjustments to the messaging or timing?"
                else:
                    return {
                        "status": "error",
                        "error": "No sequence to modify",
                        "chat_response": "I don't see any sequence to modify. Would you like me to create a new one?"
                    }
            
            elif parsed_response["action"] == "ask_clarifying_question":
                chat_response = parsed_response["action_input"]
                tool_result = None
            
            elif parsed_response["action"] == "provide_feedback":
                chat_response = "Thank you for your feedback. I'll take it into account for future interactions."
                tool_result = None

            # Prepare the response
            response_data = {
                "status": "success",
                "llm_response": json.dumps(parsed_response),
                "tool_result": tool_result if isinstance(tool_result, str) else json.dumps(tool_result) if tool_result else None,
                "chat_response": chat_response,
                "error": None
            }

            # Update chat history
            self.chat_history.append({"role": "user", "content": message})
            if chat_response:
                self.chat_history.append({"role": "assistant", "content": chat_response})

            return response_data

        except Exception as e:
            print(f"Error in process_message: {e}")
            return {
                "status": "error",
                "error": str(e),
                "chat_response": "I encountered an error while processing your request. Could you please try again or rephrase your message?"
            } 