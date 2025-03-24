# Project Helix - AI Recruiting Agent

Helix is an AI-powered recruiting outreach system that automates and enhances the candidate outreach process. The system helps HR professionals create personalized recruiting sequences, load candidate data, and send customized outreach messages.

## Key Features

- **AI-Generated Recruiting Sequences**: Create customized outreach sequences based on role, industry, and company type
- **CSV Candidate Management**: Load, filter, and manage candidate profiles from CSV files
- **Email Integration**: Send personalized emails to candidates with dynamic content
- **LinkedIn Outreach**: Prepare personalized LinkedIn messages
- **Email Personalization**: Automatically personalize messages using candidate information

## Setup Instructions

### Backend Setup

1. Navigate to the `backend` directory:
   ```
   cd backend
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.example` and add your credentials:
   ```
   cp .env.example .env
   ```
   - Add your OpenAI API key
   - Configure email settings (SMTP server, username, password)

5. Start the backend server:
   ```
   python app.py
   ```

### Frontend Setup

1. Navigate to the `frontend` directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm start
   ```

4. Access the application at `http://localhost:3000`

## Using the System

### Creating a Recruiting Sequence

1. Start a conversation with the AI agent by entering details about the role
2. The AI will generate a customized recruiting sequence with multiple steps
3. You can edit, add, or remove steps in the sequence
4. Each step includes content and personalization tips

### Loading Candidate Data

1. Go to the "Candidates" tab
2. Click "Upload CSV" and select your candidate CSV file
3. Click "Process" to load the data
4. The system will display a table of candidates

### Sending Personalized Emails

1. From the Candidates tab, click the email icon next to a candidate
2. The system will use the template from your sequence
3. Preview the personalized email
4. Click "Send Email" to deliver the message

### Best Practices

- Use placeholder variables in your templates: `{name}`, `{role}`, `{experience}`
- Segment candidates based on experience and job fit
- Follow up with candidates after initial outreach
- Track response rates to optimize your sequences

## CSV Format

Your CSV file should include at least the following columns:
- `name`: Candidate's full name
- `email`: Candidate's email address

Optional but recommended columns:
- `role`: Current or target role
- `experience`: Years of experience
- `skills`: Key skills or technologies
- `linkedin`: LinkedIn profile URL

## Email Configuration

For email functionality, you need to configure the following in your `.env` file:
- `SMTP_SERVER`: Your email server (e.g., smtp.gmail.com)
- `SMTP_PORT`: Server port (typically 587 for TLS)
- `SMTP_USERNAME`: Your email address
- `SMTP_PASSWORD`: Your password or app password
- `FROM_EMAIL`: The email address to send from

## License

This project is proprietary and confidential. 