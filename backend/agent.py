from typing import List, Dict, Any
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
import json
import os
from dotenv import load_dotenv

load_dotenv()

class RecruitingAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            temperature=0.7,
            model="gpt-4",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )
        self.tools = self._get_tools()
        self.prompt = self._create_prompt()
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

    def _create_prompt(self) -> PromptTemplate:
        template = """You are Helix, an AI-powered recruiting outreach agent. Your goal is to help HR professionals create effective recruiting sequences.

Current conversation:
{chat_history}

Current sequence:
{current_sequence}

Available tools:
{tools}

Tool names: {tool_names}

Human: {input}
Helix: Let's approach this step by step:

1) First, let's analyze the user's input and determine what they want to do.
2) Then, we'll either:
   - Ask clarifying questions if we need more information
   - Generate or modify the sequence based on their requirements
   - Provide feedback on the current sequence

{agent_scratchpad}"""
        return PromptTemplate(template=template)

    def _create_agent(self) -> AgentExecutor:
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt,
        )
        return AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=self.tools,
            verbose=True,
        )

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
            result = self.agent.invoke(
                {
                    "input": message,
                    "chat_history": chat_history,
                    "current_sequence": current_sequence,
                }
            )
            return result["output"]
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}" 