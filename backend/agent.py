from typing import List, Dict, Any
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.tools import Tool
from langchain.schema import HumanMessage, SystemMessage
import json
import os
from dotenv import load_dotenv

load_dotenv()

SYSTEM_TEMPLATE = """You are Helix, an AI-powered recruiting outreach agent. Your goal is to help HR professionals create effective recruiting sequences.

Available tools:
{tools}

IMPORTANT: You MUST use one of these exact tool names: {tool_names}. Do not try to use any other tool names.

You must respond in JSON format with an action and action_input. The action MUST be one of the exact tool names listed above.

For example:
{{
    "action": "generate_sequence",
    "action_input": "Create a sequence for a senior software engineer role"
}}

or 

{{
    "action": "ask_clarifying_question",
    "action_input": "What industry is this role in?"
}}"""

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
        # Generate a sequence based on requirements
        sequence = [
            {
                "id": "1",
                "type": "email",
                "content": "Initial outreach email introducing the company and role",
                "delay": 0,
            },
            {
                "id": "2",
                "type": "linkedin",
                "content": "Follow-up LinkedIn message to connect",
                "delay": 2,
            },
            {
                "id": "3",
                "type": "call",
                "content": "Schedule initial phone call to discuss the role",
                "delay": 3,
            },
        ]
        return json.dumps(sequence)

    def _modify_sequence(self, modifications: str) -> str:
        # Modify the sequence based on user feedback
        return "I've modified the sequence according to your requirements."

    def _provide_feedback(self, sequence: str) -> str:
        # Provide feedback on the current sequence
        return "Here's my analysis of the current sequence..."

    def process_message(self, message: str, chat_history: List[Dict], current_sequence: List[Dict]) -> str:
        """Process a user message and return a response."""
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
            
            # Parse the response
            try:
                parsed_response = self.output_parser.parse(response.content)
                tool_name = parsed_response["action"]
                tool_input = parsed_response["action_input"]
                
                # Find the matching tool
                tool = next((t for t in self.tools if t.name == tool_name), None)
                if tool is None:
                    return f"I apologize, but I couldn't find the tool '{tool_name}'"
                
                # Execute the tool
                result = tool.func(tool_input)
                return result
                
            except Exception as parse_error:
                # If parsing fails, try to get a more structured response
                retry_message = f"""I couldn't understand the format of your previous response. 
                Please provide your response in the following format:
                {{
                    "action": "tool_name",
                    "action_input": "input for the tool"
                }}
                Previous error: {str(parse_error)}"""
                
                # Add retry message to prompt variables
                prompt_variables["input"] = retry_message
                retry_response = self.llm(self.prompt.format_messages(**prompt_variables))
                
                try:
                    parsed_retry = self.output_parser.parse(retry_response.content)
                    tool_name = parsed_retry["action"]
                    tool_input = parsed_retry["action_input"]
                    
                    tool = next((t for t in self.tools if t.name == tool_name), None)
                    if tool is None:
                        return f"I apologize, but I couldn't find the tool '{tool_name}'"
                    
                    result = tool.func(tool_input)
                    return result
                    
                except Exception as retry_error:
                    return f"I apologize, but I'm having trouble processing your request. Error: {str(retry_error)}"
                
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}" 