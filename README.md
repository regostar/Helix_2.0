# Helix - AI-Powered Recruiting Sequence Generator

Helix is a real-time recruiting sequence generation and management system that uses AI to help create personalized recruiting sequences.

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