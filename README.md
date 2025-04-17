# Helix - AI-Powered Recruiting Sequence Generator

Helix is a real-time recruiting sequence generation and management system that uses AI to help create personalized recruiting sequences.

Developed Helix, an AI recruiting assistant using Flask, React, Langchain, GPT-4, enabling real-time chat and dynamic outreach—cut recruiter effort by 70%.

Built modular backend with PostgreSQL & SQLAlchemy, ensuring fast response times (<300ms) and reliable sequence generation.

Designed real-time frontend with React + Socket.IO, doubling user engagement through interactive, live sequence editing.

## Product

![image](https://github.com/user-attachments/assets/969d8140-0383-406b-81c6-78b73b4d762d)


## Architecture

![image](https://github.com/user-attachments/assets/99f3e7ee-d9cc-482e-a087-b4af9aa57660)


# Helix 2.0

Helix 2.0 is an experimental Agentic AI framework designed for orchestrating autonomous and semi-autonomous agents capable of complex task execution. The system leverages a modular architecture where agents collaborate, plan, and act towards goals in a dynamic environment.

---

## 🚀 Features

- 🧠 **Agentic AI Framework**: Modular agents with memory, reasoning, and planning capabilities.
- 🔄 **Looped Execution**: Recursive task decomposition and feedback-driven refinement.
- 🧩 **Tool Usage**: Agents interact with various tools including search engines, file systems, and data parsers.
- 🗃️ **Memory System**: Contextual memory for relevant task history and decision making.
- 📡 **Planning Engine**: High-level decomposition of user goals into executable subtasks.
- 🧾 **Task & Subtask Management**: Threaded communication between agents with execution chains.
- 📁 **File I/O Support**: Handle file creation, reading, and writing as part of task execution.
- 🧪 **Built-in Eval & Logging**: Agent outputs can be traced and evaluated for quality.

---

## 🧰 Tech Stack

| Layer             | Technology                          |
|------------------|--------------------------------------|
| Programming Lang | Python 3.11                          |
| Agent Framework  | Langchain |
| LLM Backend      | Langchain, OpenAI GPT (via `openai` SDK)       |
| Planning Module  | GPT-based task planner               |
| Search Tool      | DuckDuckGo API                      |
| Web Integration  | Gradio (planned )         |
| Web backend  | Flask, SQLAlchemy       |
| Frontend  | Typescript, React, Tailwindcss, MaterialUI    |
| Database | Postgresql    |

---

## 🧠 Agentic AI Flow

Helix 2.0 adopts a goal-oriented, modular agent architecture where agents autonomously collaborate to decompose, plan, and solve problems.

### 🔁 Flow Overview

1. **User Input**: A goal or query is submitted by the user.
2. **Planner Agent**: (complete)
   - Decomposes the goal into high-level subtasks.
   - Assigns subtasks to specialized agents.
3. **Executor Agents**: (In progress)
   - Perform subtasks (e.g., web search, csv manipulation, file manipulation).
   - Loop with memory context and tool access.
4. **Memory Module**:
   - Stores past actions and retrieved data.
   - Supports retrieval of relevant context for each task loop.
5. **Controller**:
   - Manages the communication between agents.
   - Monitors task completion, success/failure, and reassignments if needed.
6. **Result Aggregation**:
   - Final response or output is composed and returned to the user.

### 📌 Key Agents

- `PlannerAgent`: Converts user goals into executable plans.
- `ExecAgent`: Executes subtasks using reasoning and tool access. (In progress)
- `MemoryAgent`: Handles context persistence and lookup.
- `ToolAgent`: Interfaces with tools like DuckDuckGo or file ops.
- `Controller`: Orchestrates the entire workflow and manages state.

---

## Demo

https://www.loom.com/share/dfa8e90aa633443a9ef4de9f50ddfe72?sid=18512ac9-c625-4567-b92f-6572cf32d124


## Prerequisites

- Docker
- Docker Compose
- OpenAI API Key

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/yourusername/helix.git
cd helix
```

2. Create a `.env` file in the root directory and add your environment variables:
```bash
cp .env.example .env
```
Edit the `.env` file and add your OpenAI API key and other configuration values.

3. Build and start the containers:
```bash
docker-compose up --build
```

The application will be available at:
- Frontend: http://localhost:80
- Backend API: http://localhost:5000

## Architecture

The application consists of three main services:
- Frontend (React + TypeScript)
- Backend (Flask + Socket.IO)
- Database (PostgreSQL)

## Development

To run the services individually for development:

### Frontend
```bash
cd frontend
npm install
npm start
```

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
flask run
```

## Production Deployment

1. Update the environment variables in `.env` for production settings
2. Build and deploy the containers:
```bash
docker-compose -f docker-compose.yml up -d
```

## Environment Variables

Key environment variables that need to be set:

- `OPENAI_API_KEY`: Your OpenAI API key
- `DATABASE_URL`: PostgreSQL connection string
- `FLASK_ENV`: Set to 'production' for production deployment
- `SECRET_KEY`: Flask secret key for session management

## Features

- Real-time chat interface with AI
- Suggested prompts for sequence generation
- Dynamic sequence editing and management
- WebSocket-based real-time updates
- Responsive and modern UI
- Docker containerization for easy deployment

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details 
