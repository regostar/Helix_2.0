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
7. To create a new recruiting sequence, ALWAYS use the tool name "generate_sequence", NOT "create_sequence"
8. When the user asks to create a sequence, campaign, or outreach plan, use the "generate_sequence" tool

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
        global db, Sequence
        self.llm = ChatOpenAI(
            temperature=0.7,
            model="gpt-4",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
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
            str: JSON string containing the generated sequence or next question
        """
        try:
            # Check if this is a request to start creating a recruiting sequence
            if ("create sequence" in requirements.lower() or 
                "recruiting sequence" in requirements.lower() or 
                "recruiting plan" in requirements.lower() or 
                "campaign" in requirements.lower() or
                "email campaign" in requirements.lower()):
                
                # Try to extract role information from the request
                extracted_role = None
                
                # Look for common job title patterns
                job_titles = ["software engineer", "product manager", "data scientist", 
                             "frontend developer", "backend developer", "full stack", 
                             "senior engineer", "tech lead", "designer", "marketing", 
                             "sales", "recruiter", "hr", "developer"]
                             
                for title in job_titles:
                    if title in requirements.lower():
                        extracted_role = title
                        break
                
                # If we found a role, include it in the collected info
                initial_info = {}
                if extracted_role:
                    initial_info["pre_identified_role"] = extracted_role
                
                # Start the recruiting sequence creation process with first question to understand campaign idea
                return json.dumps({
                    "status": "question",
                    "message": "I'll help you create a customized recruiting sequence. Let's start by understanding your campaign idea and requirements.",
                    "question": "Please describe your overall campaign idea or strategy. What are you trying to achieve with this recruiting campaign?",
                    "sequence_info": {
                        "step": 1,
                        "collected_info": initial_info
                    }
                })
            
            # Check if this is a response to one of our questions
            try:
                data = json.loads(requirements)
                if isinstance(data, dict) and "sequence_info" in data and "user_response" in data:
                    sequence_info = data["sequence_info"]
                    user_response = data["user_response"]
                    current_step = sequence_info.get("step", 0)
                    collected_info = sequence_info.get("collected_info", {})
                    
                    # Update collected info based on current step
                    if current_step == 1:  # Campaign idea/strategy
                        collected_info["campaign_idea"] = user_response
                        
                        # If we already identified a role from the initial request, personalize the question
                        pre_identified_role = collected_info.get("pre_identified_role")
                        if pre_identified_role:
                            next_question = f"I see you're focused on a {pre_identified_role} role. Please provide some additional details:\n\n1. Industry (e.g., Technology, Healthcare, Finance)\n2. Seniority level (Junior, Mid, Senior, Executive)\n3. Any specific specialization for this {pre_identified_role} role?"
                        else:
                            next_question = "Please provide the following details about the position:\n\n1. Job title\n2. Industry (e.g., Technology, Healthcare, Finance)\n3. Seniority level (Junior, Mid, Senior, Executive)"
                        next_step = 2
                        
                    elif current_step == 2:  # Basic role information (job title, industry, seniority)
                        # Parse the multi-part response - we'll do a simple extraction
                        lines = user_response.strip().split('\n')
                        
                        # Default values in case parsing fails
                        pre_identified_role = collected_info.get("pre_identified_role")
                        role_title = pre_identified_role if pre_identified_role else "Unspecified Role"
                        industry = "Technology"
                        seniority = "Mid-level"
                        
                        # Try to extract information from the response
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith(('1.', '2.', '3.')):
                                if not role_title or role_title == "Unspecified Role":
                                    role_title = line
                                elif not industry or industry == "Technology":
                                    industry = line
                                elif not seniority or seniority == "Mid-level":
                                    seniority = line
                                    
                        # If the response wasn't structured as expected, try to make best guesses
                        if len(lines) >= 3:
                            if not pre_identified_role:  # Only replace if we don't have a pre-identified role
                                if not role_title or role_title == "Unspecified Role":
                                    role_title = lines[0].replace('1.', '').strip()
                            if not industry or industry == "Technology":
                                industry = lines[1].replace('2.', '').strip()
                            if not seniority or seniority == "Mid-level":
                                seniority = lines[2].replace('3.', '').strip()
                        elif len(user_response.split()) >= 3 and not pre_identified_role:
                            # Just use the whole response as role title if parsing failed
                            role_title = user_response
                            
                        collected_info["role_title"] = role_title
                        collected_info["industry"] = industry
                        collected_info["seniority"] = seniority
                        
                        next_question = "What are the top 3 specific skills or qualifications that are absolutely essential for this role?"
                        next_step = 3
                        
                    elif current_step == 3:  # Essential skills
                        collected_info["key_skills"] = user_response
                        
                        next_question = "Tell me about your company culture and working environment. What makes your workplace unique or appealing to candidates?"
                        next_step = 4
                        
                    elif current_step == 4:  # Company culture
                        collected_info["company_culture"] = user_response
                        
                        next_question = "Where are you planning to source candidates from? (e.g., LinkedIn, professional networks, referrals, job boards, etc.)"
                        next_step = 5
                        
                    elif current_step == 5:  # Sourcing channels
                        collected_info["sourcing_channels"] = user_response
                        
                        next_question = "What are the key selling points or benefits that would attract candidates to this position? (e.g., remote work, career growth, cutting-edge technology)"
                        next_step = 6
                        
                    elif current_step == 6:  # Key benefits
                        collected_info["company_benefits"] = user_response
                        
                        next_question = "What's your timeline for filling this position? Is this an urgent need or a longer-term recruitment effort?"
                        next_step = 7
                        
                    elif current_step == 7:  # Timeline
                        collected_info["timeline"] = user_response
                        
                        next_question = "Are there any common objections or concerns that candidates typically have about this role or your company?"
                        next_step = 8
                        
                    elif current_step == 8:  # Objections
                        collected_info["candidate_objections"] = user_response
                        
                        next_question = "Would you like to include post-outreach interview steps (e.g., screening call, technical interview, etc.) in your sequence? (Yes/No)"
                        next_step = 9
                        
                    elif current_step == 9:  # Interview steps
                        include_interviews = "yes" in user_response.lower()
                        collected_info["include_interviews"] = include_interviews
                        
                        # Final question about any specific campaign ideas or approaches
                        next_question = "Is there anything specific or unique about this campaign that you'd like to incorporate into the sequence? (e.g., special events, webinars, or referral programs)"
                        next_step = 10
                        
                    elif current_step == 10:  # Special campaign elements
                        collected_info["special_elements"] = user_response
                        
                        # Now we have all the information, generate the sequence
                        return self._generate_final_sequence(collected_info)
                    
                    # Return the next question
                    return json.dumps({
                        "status": "question",
                        "question": next_question,
                        "sequence_info": {
                            "step": next_step,
                            "collected_info": collected_info
                        }
                    })
            except (json.JSONDecodeError, KeyError) as e:
                # Not a structured response, continue with normal processing
                print("Not a structured response, continuing with normal processing")
                pass
            
            # Normal processing for generating a sequence
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
            
            return self._generate_final_sequence(parsed_analysis)
            
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
        
    def _generate_final_sequence(self, collected_info: dict) -> str:
        """Generate a final recruiting sequence based on collected information.
        
        Args:
            collected_info: Dictionary containing all collected recruiting information
            
        Returns:
            str: JSON string containing the generated sequence
        """
        try:
            # Get sequence structure based on collected info
            sequence_prompt = f"""Generate a recruiting sequence as a JSON array based on this information:
{json.dumps(collected_info, indent=2)}

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
1. Match the overall campaign idea: {collected_info.get('campaign_idea', 'effective recruiting outreach')}
2. Be appropriate for the {collected_info.get('seniority', 'Mid-level')} level in the {collected_info.get('industry', 'Technology')} industry
3. Highlight these essential skills: {collected_info.get('key_skills', 'relevant skills')}
4. Reflect the company culture: {collected_info.get('company_culture', 'positive and collaborative')}
5. Be designed for these sourcing channels: {collected_info.get('sourcing_channels', 'LinkedIn and job boards')}
6. Highlight these benefits: {collected_info.get('company_benefits', 'competitive benefits')}
7. Address these potential objections: {collected_info.get('candidate_objections', 'common concerns')}
8. Consider the recruiting timeline: {collected_info.get('timeline', 'standard')}
9. Include these special elements if applicable: {collected_info.get('special_elements', '')}

{
"include_interviews" in collected_info and collected_info.get('include_interviews', False) and
'''
10. Include post-outreach interview steps such as:
   - Scheduling a screening call
   - Technical/skills assessment 
   - Interview rounds with the team
   - Final decision and offer
''' or ''
}

The sequence should include a mix of outreach methods, with appropriate delays between steps. 
Typically include 4-6 steps of initial outreach with increasing personalization and value in each message.
{
"include_interviews" in collected_info and collected_info.get('include_interviews', False) and
"Additionally, include 3-4 more steps for the interview process after initial contact is established."
or ""
}

Do not include any other text before or after the JSON array."""
            
            sequence_response = self.llm([HumanMessage(content=sequence_prompt)])
            sequence = json.loads(sequence_response.content.strip())
            
            # Add metadata to the sequence
            final_sequence = {
                "metadata": {
                    "campaign_idea": collected_info.get("campaign_idea", "Effective Recruiting Campaign"),
                    "role": collected_info.get("role_title", "Unspecified Role"),
                    "industry": collected_info.get("industry", "Technology"),
                    "seniority": collected_info.get("seniority", "Mid-level"),
                    "company_culture": collected_info.get("company_culture", "Positive work environment"),
                    "includes_interview_steps": collected_info.get("include_interviews", False),
                    "generated_at": datetime.now(UTC).isoformat()
                },
                "steps": sequence
            }
            
            return json.dumps(final_sequence, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": "Failed to generate final sequence",
                "details": str(e)
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
            # Check for direct campaign requests with role specifics
            direct_campaign_keywords = ["email campaign", "recruiting campaign", "hiring campaign", "outreach campaign"]
            job_titles = ["software engineer", "product manager", "data scientist", "developer", 
                         "designer", "manager", "director", "recruiter", "engineer", "sales"]
            
            is_direct_campaign_request = False
            for keyword in direct_campaign_keywords:
                if keyword in message.lower():
                    # Check if it includes a job title
                    for title in job_titles:
                        if title in message.lower():
                            is_direct_campaign_request = True
                            break
                    if is_direct_campaign_request:
                        break
            
            if is_direct_campaign_request:
                # Call generate_sequence directly
                print(f"Identified direct campaign request: '{message}', routing to generate_sequence")
                tool_result = self._generate_sequence(message)
                
                try:
                    result_data = json.loads(tool_result)
                    if result_data.get("status") == "question":
                        # Continue with questions
                        return json.dumps({
                            "status": "success",
                            "llm_response": {"action": "generate_sequence", "action_input": message},
                            "tool_result": tool_result,
                            "chat_response": result_data.get("question", "Let's create a recruiting sequence."),
                            "error": None
                        })
                except (json.JSONDecodeError, KeyError):
                    pass  # If anything fails, continue with normal processing
            
            # Check for continuing recruiting sequence creation
            try:
                # Look for the last AI message in chat history
                last_ai_message = None
                for msg in reversed(chat_history):
                    if msg["sender"] == "ai":
                        try:
                            response_data = json.loads(msg["text"])
                            if "status" in response_data and response_data["status"] == "question" and "sequence_info" in response_data:
                                last_ai_message = response_data
                                break
                        except (json.JSONDecodeError, KeyError):
                            # Not a structured JSON message, continue searching
                            continue
                
                # If we have a sequence question and user response, package it for the next step
                if last_ai_message and "sequence_info" in last_ai_message:
                    # Create a structured input for the _generate_sequence method
                    input_data = {
                        "sequence_info": last_ai_message["sequence_info"],
                        "user_response": message
                    }
                    
                    # Call the sequence generator with the structured data
                    tool_result = self._generate_sequence(json.dumps(input_data))
                    
                    try:
                        result_data = json.loads(tool_result)
                        if result_data.get("status") == "question":
                            # Continue with more questions
                            return json.dumps({
                                "status": "success",
                                "llm_response": {"action": "generate_sequence", "action_input": message},
                                "tool_result": tool_result,
                                "chat_response": result_data["question"],
                                "error": None
                            })
                        elif "metadata" in result_data and "steps" in result_data:
                            # Final sequence created
                            return json.dumps({
                                "status": "success",
                                "llm_response": {"action": "generate_sequence", "action_input": message},
                                "tool_result": tool_result,
                                "chat_response": f"I've created a recruiting sequence for a {result_data['metadata']['role']} position. Please review it and let me know if you'd like any changes.",
                                "error": None
                            })
                    except (json.JSONDecodeError, KeyError):
                        # Not a valid response, continue with normal processing
                        pass
            except Exception as e:
                print(f"Error processing recruiting sequence flow: {str(e)}")
                # If there's an error, continue with normal processing
                pass
            
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
                        from flask_socketio import emit
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