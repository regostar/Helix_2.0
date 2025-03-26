from app import app, db
from dotenv import load_dotenv
import os

def init_db():
    """Initialize the database with required tables."""
    try:
        with app.app_context():
            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Error initializing database: {str(e)}")
        raise

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Check if DATABASE_URL is set
    if not os.getenv('DATABASE_URL'):
        print("❌ Error: DATABASE_URL environment variable is not set")
        exit(1)
    
    # Initialize database
    init_db() 