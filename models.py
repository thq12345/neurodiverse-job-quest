from app import db

class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    q1_answer = db.Column(db.String(1))
    q2_answer = db.Column(db.String(1))
    q3_answer = db.Column(db.String(1))
    q4_answer = db.Column(db.String(1))
    q5_answer = db.Column(db.String(1))
    analysis = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
