# Helix - AI-Powered Recruiting Outreach Agent

Helix is an intelligent recruiting outreach agent that transforms how HR finds top talent through a chat-driven interface and dynamic sequence generation.

## Features

- 🤖 AI-powered chat interface for natural interaction
- 📝 Dynamic sequence generation in real-time
- ✏️ Live editing capabilities
- 🔄 Real-time updates and synchronization
- 🎯 Guided prompts for campaign customization

## Tech Stack

### Frontend
- React with TypeScript
- Socket.io for real-time communication
- Modern UI components and styling

### Backend
- Flask (Python)
- PostgreSQL database
- Langchain for LLM integration
- Socket.io for real-time updates

## Getting Started

### Prerequisites
- Node.js (v16 or higher)
- Python 3.8+
- PostgreSQL
- npm or yarn

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/helix.git
cd helix
```

2. Set up the frontend:
```bash
cd frontend
npm install
```

3. Set up the backend:
```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Create .env files in both frontend and backend directories
# See .env.example files for required variables
```

5. Start the development servers:
```bash
# Terminal 1 - Frontend
cd frontend
npm i
npm start

# Terminal 2 - Backend
cd backend
python app.py
```

## Project Structure

```
helix/
├── frontend/           # React frontend application
├── backend/           # Flask backend application
├── docs/             # Documentation
└── README.md         # Project documentation
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by SellScale's Selix
- Built with modern AI and web technologies
- Special thanks to the open-source community 


## DATABASE Migrations

```bash
pip install Flask-Migrate
```

Update app.py to use Flask-Migrate

```bash
# To initialize the database - RUN ONLY ONCE
python init_db.py


# start here for Migrations
flask db migrate -m "Description of your changes"

# Review the files in migrations/versions/

# to apply the migration
flask db upgrade

# Rollback -
flask db downgrade
```