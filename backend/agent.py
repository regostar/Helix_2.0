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
            response = self.llm(self.prompt.format_messages(**prompt_variables))
            llm_response = response.content.strip()
            
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
            
            # Find the matching tool
            tool = next((t for t in self.tools if t.name == tool_name), None)
            if tool is None:
                return json.dumps({
                    "status": "error",
                    "llm_response": llm_response,
                    "error": f"Tool '{tool_name}' not found",
                    "tool_result": None
                })
            
            # Execute the tool
            tool_result = tool.func(tool_input)
            return json.dumps({
                "status": "success",
                "llm_response": parsed_response,
                "tool_result": tool_result,
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
                        "tool_result": None
                    })
                
                tool_result = tool.func(tool_input)
                return json.dumps({
                    "status": "success",
                    "llm_response": parsed_retry,
                    "tool_result": tool_result,
                    "error": None
                })
                
            except Exception as retry_error:
                return json.dumps({
                    "status": "error",
                    "llm_response": llm_response,
                    "retry_response": retry_llm_response if 'retry_llm_response' in locals() else None,
                    "error": str(retry_error),
                    "tool_result": None
                }) 