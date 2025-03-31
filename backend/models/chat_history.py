from datetime import datetime, UTC
from .database import db

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    socket_id = db.Column(db.String(100), nullable=False)
    messages = db.Column(db.JSON, nullable=False, default=list)
    sequence_id = db.Column(db.Integer, db.ForeignKey('sequence.id'), nullable=True)
    # every chat is related to one sequence, it cannot be related to multiple sequences
    # a new chat has to be created for a new sequence
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


    @staticmethod
    def get_or_create(socket_id, session=None):
        if session is None:
            session = db.session
        chat_history = session.query(ChatHistory).filter_by(socket_id=socket_id).first()
        if not chat_history:
            chat_history = ChatHistory(socket_id=socket_id, messages=[])
            session.add(chat_history)
            session.commit()
        return chat_history
    
    def to_dict(self):
        return {
            'id': self.id,
            'socket_id': self.socket_id,
            'messages': self.messages,
            'sequence_id': self.sequence_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 