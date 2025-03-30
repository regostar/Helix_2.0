from flask import Blueprint, jsonify, Flask
from models.sequence import Sequence
from models.chat_history import ChatHistory
from agent import RecruitingAgent
from flask_sqlalchemy import SQLAlchemy

# Create Blueprint
api_bp = Blueprint('api', __name__)

# Health check endpoint
@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

# Initialize routes with dependencies
def init_routes(app: Flask, db: SQLAlchemy, agent: RecruitingAgent):
    """Initialize routes with required dependencies"""
    app.register_blueprint(api_bp, url_prefix='/api') 