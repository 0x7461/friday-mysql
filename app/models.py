from datetime import datetime
from hashlib import md5
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
from flask_login import UserMixin

from app import app
from app import db
from app import login


@login.user_loader
def load_user(id):
    return User.query.get(int(id))

enrollments = db.Table('enrollments',
    db.Column('student_id', db.Integer, db.ForeignKey('students.id')),
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id'))
)

attendances = db.Table('attendances',
    db.Column('student_id', db.Integer, db.ForeignKey('students.id')),
    db.Column('log_id', db.Integer, db.ForeignKey('logs.id'))
)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(64))
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    about_me = db.Column(db.String(256))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    # relationships
    teaching_courses = db.relationship('Course', backref='instructor', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, size)

    def generate_auth_token(self, expiration = 600):
        s = Serializer(app.config['SECRET_KEY'], expires_in = expiration)
        return s.dumps({ 'id': self.id })

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None # valid token, but expired
        except BadSignature:
            return None # invalid token
        user = User.query.get(data['id'])
        return user

class Course(db.Model):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), index=True, unique=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    # relationships
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    logs = db.relationship('Log', backref='course', lazy='dynamic')

    def __repr__(self):
        return '<Course {}>'.format(self.name)

class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), index=True, unique=True, nullable=False)
    name = db.Column(db.String(32), nullable=False)
    email = db.Column(db.String(32), index=True, unique=True, nullable=False)
    # relationships
    enroll = db.relationship('Course', secondary=enrollments, backref=db.backref('enrollees', lazy='dynamic'))
    attend = db.relationship('Log', secondary=attendances, backref=db.backref('attendees', lazy='dynamic'))

    def __repr__(self):
        return '<Student {}>'.format(self.name)

    def get_present_rate_in_course(self, course_id):
        course = Course.query.get(course_id)
        if self in course.enrollees:
            present = 0
            all_classes = course.logs.count()
            for log in course.logs:
                if self in log.attendees:
                    present += 1
            return (present / all_classes)*100
        else:
            return 0

class Log(db.Model):
    __tablename__ = "logs"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime)
    present_rate = db.Column(db.Float)
    # relationships
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))

    def __repr__(self):
        return '<Log on {}>'.format(self.date)

    def get_course_name(self):
        return Course.query.get(self.course_id).name

    def calculate_present_rate(self):
        all_students = (Course.query.get(self.course_id).enrollees).count()
        present_students = self.attendees.count()
        return (present_students / all_students)*100

