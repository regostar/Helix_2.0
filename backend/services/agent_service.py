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
from datetime import datetime, UTC
from flask_socketio import emit
from backend.models.sequence import Sequence
from backend import db
from backend.services.prompts import SYSTEM_TEMPLATE, HUMAN_TEMPLATE

class RecruitingAgent:
    def __init__(self, db_instance=None, sequence_model=None):
        self.llm = ChatOpenAI(
            temperature=0.7,
            model="gpt-4",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )
        self.db = db_instance
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
        """Generate a customized recruiting sequence based on the given requirements."""
        try:
            analysis_prompt = f"""Analyze these recruiting requirements and return ONLY a JSON object with the following fields:
            Requirements: {requirements}

IMPORTANT: Respond with ONLY a JSON object containing these exact fields:
{{
    "role_title": "the job title",
    "industry": "the industry",
    "seniority": "Junior/Mid/Senior",
    "key_skills": ["skill1", "skill2", ...],
    "company_type": "Startup/Enterprise/Agency"
}}"""
            
            analysis = self.llm([HumanMessage(content=analysis_prompt)])
            parsed_analysis = json.loads(analysis.content.strip())
            
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
]"""
            
            sequence_response = self.llm([HumanMessage(content=sequence_prompt)])
            sequence_steps = json.loads(sequence_response.content.strip())
            
            # Create a new sequence in the database
            new_sequence = Sequence(
                title=f"{parsed_analysis['role_title']} Recruiting Sequence",
                steps=sequence_steps
            )
            if self.db:
                self.db.session.add(new_sequence)
                self.db.session.commit()
            
            return json.dumps({
                "status": "success",
                "metadata": parsed_analysis,
                "steps": sequence_steps
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            })

    def _modify_sequence(self, modifications: str) -> str:
        """Modify the sequence based on user feedback."""
        try:
            # Get the most recent sequence
            sequence = Sequence.query.order_by(Sequence.created_at.desc()).first()
            if not sequence:
                return json.dumps({
                    "status": "error",
                    "message": "No sequence found to modify"
                })
            
            # Create prompt for modification
            modification_prompt = f"""Modify this sequence based on the following feedback:
Feedback: {modifications}

Current sequence:
{json.dumps(sequence.steps, indent=2)}

Return ONLY the modified sequence as a JSON array with the same structure."""
            
            response = self.llm([HumanMessage(content=modification_prompt)])
            modified_steps = json.loads(response.content.strip())
            
            # Update the sequence
            sequence.steps = modified_steps
            if self.db:
                self.db.session.commit()
            
            return json.dumps({
                "status": "success",
                "sequence": modified_steps
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            })

    def _provide_feedback(self, sequence: str) -> str:
        """Provide feedback on the current sequence."""
        try:
            feedback_prompt = f"""Analyze this recruiting sequence and provide feedback:
{sequence}

Focus on:
1. Message effectiveness
2. Timing and pacing
3. Personalization opportunities
4. Professional tone
5. Call-to-action clarity

Return the feedback as a JSON object with these fields:
{{
    "overall_rating": 1-10,
    "strengths": ["point1", "point2", ...],
    "areas_for_improvement": ["point1", "point2", ...],
    "specific_suggestions": ["suggestion1", "suggestion2", ...]
}}"""
            
            response = self.llm([HumanMessage(content=feedback_prompt)])
            feedback = json.loads(response.content.strip())
            
            return json.dumps({
                "status": "success",
                "feedback": feedback
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            })

    def _edit_sequence_step(self, input_data: str) -> str:
        """Edit a specific step in the sequence."""
        try:
            data = json.loads(input_data)
            step_id = data.get("step_id")
            new_content = data.get("new_content")
            
            if not step_id or not new_content:
                return json.dumps({
                    "status": "error",
                    "message": "Missing step_id or new_content"
                })
            
            # Get the most recent sequence
            sequence = Sequence.query.order_by(Sequence.created_at.desc()).first()
            if not sequence:
                return json.dumps({
                    "status": "error",
                    "message": "No sequence found"
                })
            
            # Update the specified step
            steps = sequence.steps
            for step in steps:
                if step["id"] == step_id:
                    step["content"] = new_content
                    break
            
            # Save the updated sequence
            sequence.steps = steps
            if self.db:
                self.db.session.commit()
            
            return json.dumps({
                "status": "success",
                "sequence": steps
            })
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            })

    def _generate_job_description(self, requirements: str) -> str:
        """Generate a job description based on the given requirements."""
        try:
            prompt = f"""Create a professional job description based on these requirements:
{requirements}

The job description should include:
1. Job Title
2. About the Company
3. Job Overview
4. Key Responsibilities
5. Required Qualifications
6. Preferred Qualifications
7. Benefits and Perks
8. How to Apply

Return the job description as a JSON object with these sections as keys."""

            response = self.llm([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            })

    def _load_csv_candidates(self, file_path: str) -> str:
        """Load and filter candidate data from a CSV file."""
        try:
            df = pd.read_csv(file_path)
            self.candidate_data = df.to_dict('records')
            return json.dumps({
                "status": "success",
                "message": f"Loaded {len(self.candidate_data)} candidates",
                "candidates": self.candidate_data
            })
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            })

    def _send_personalized_email(self, data: str) -> str:
        """Send a personalized email to a candidate."""
        try:
            email_data = json.loads(data)
            to_email = email_data.get("email")
            subject = email_data.get("subject")
            body = email_data.get("body")

            if not all([to_email, subject, body, self.smtp_username, self.smtp_password]):
                return json.dumps({
                    "status": "error",
                    "message": "Missing required email information or SMTP credentials"
                })

            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            return json.dumps({
                "status": "success",
                "message": f"Email sent to {to_email}"
            })
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            })

    def _prepare_linkedin_message(self, data: str) -> str:
        """Prepare a personalized LinkedIn message."""
        try:
            profile_data = json.loads(data)
            prompt = f"""Create a personalized LinkedIn message for this candidate:
Profile: {json.dumps(profile_data, indent=2)}

The message should:
1. Be professional and friendly
2. Reference specific points from their profile
3. Explain why they would be a good fit
4. Include a clear call to action

Keep it concise (max 2000 characters for LinkedIn)."""

            response = self.llm([HumanMessage(content=prompt)])
            return json.dumps({
                "status": "success",
                "message": response.content.strip()
            })
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            })

    def _merge_candidate_data(self, data: str) -> str:
        """Merge and deduplicate candidate data from multiple sources."""
        try:
            sources = json.loads(data)
            all_candidates = []
            
            for source in sources:
                if isinstance(source, list):
                    all_candidates.extend(source)
                elif isinstance(source, str) and source.endswith('.csv'):
                    df = pd.read_csv(source)
                    all_candidates.extend(df.to_dict('records'))

            # Deduplicate based on email
            df = pd.DataFrame(all_candidates)
            df = df.drop_duplicates(subset=['email'], keep='first')
            
            return json.dumps({
                "status": "success",
                "candidates": df.to_dict('records')
            })
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            })

    def process_message(self, message: str, chat_history: List[Dict], current_sequence: List[Dict]) -> str:
        """Process a user message and return the appropriate response."""
        try:
            # Format the chat history and current sequence
            formatted_history = self._format_chat_history(chat_history)
            formatted_sequence = self._format_sequence(current_sequence)
            
            # Create the messages for the LLM
            messages = [
                SystemMessage(content=SYSTEM_TEMPLATE.format(
                    tools="\n".join(t.description for t in self.tools),
                    tool_names=", ".join(t.name for t in self.tools)
                )),
                HumanMessage(content=HUMAN_TEMPLATE.format(
                    chat_history=formatted_history,
                    current_sequence=formatted_sequence,
                    input=message
                ))
            ]
            
            # Get the LLM's response
            response = self.llm(messages)
            
            try:
                # Parse the response
                parsed_response = json.loads(response.content.strip())
                action = parsed_response.get("action")
                action_input = parsed_response.get("action_input")
                
                # Find and execute the appropriate tool
                for tool in self.tools:
                    if tool.name == action:
                        result = tool.func(action_input)
                        return json.dumps({
                            "status": "success",
                            "tool_result": result,
                            "llm_response": parsed_response
                        })
                
                return json.dumps({
                    "status": "error",
                    "message": f"Unknown action: {action}"
                })
                
            except json.JSONDecodeError:
                return json.dumps({
                    "status": "error",
                    "message": "Invalid response format from LLM"
                })
                
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            }) 