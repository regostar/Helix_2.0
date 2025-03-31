from datetime import datetime
from .database import db

class Sequence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    steps = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Relationship to chat histories
    chat_histories = db.relationship('ChatHistory', backref='sequence', lazy=True)
    # one-to-many relationship to ChatHistory using db.relationship
    # Reasoning - One sequence can have many chat sessions
    # many socket sessions also
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'steps': self.steps,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 