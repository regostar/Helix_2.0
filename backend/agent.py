from typing import List, Dict, Any
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.tools import Tool
from langchain.schema import HumanMessage, SystemMessage
import json
import os
from dotenv import load_dotenv
import datetime

load_dotenv()

SYSTEM_TEMPLATE = """You are Helix, an AI-powered recruiting outreach agent. Your goal is to help HR professionals create effective recruiting sequences.

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