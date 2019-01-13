from app import app, db
from app.models import User, Course, Student, Log

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Course': Course, 'Student': Student, 'Log': Log}

if __name__ == '__main__':
    # app.run()
    # app.run(host='192.168.1.105')
    app.run(host='0.0.0.0')