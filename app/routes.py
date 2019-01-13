import os
import datetime
import base64
import uuid
import xlsxwriter
from flask import render_template, redirect, url_for, request, g, jsonify, abort, send_file
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from flask_admin import Admin, AdminIndexView, BaseView, expose
from flask_admin.contrib.sqla import ModelView

from app import app
from app import db
from app import auth
from app import ma
from app.models import User, Course, Student, Log
from app.forms import LoginForm, RegistrationForm, EditProfileForm
from face import trainer
from face import recognizer

############################# WEB ##############################################

# Admin views
class CustomAdminView(AdminIndexView):
    def is_accessible(self):
        if current_user.is_authenticated:
            if current_user.is_admin:
                return True
            return False
        return False

class StudentImagesView(BaseView):
    @expose('/')
    def index(self):
        return self.render('admin/simages.html')

class LogImagesView(BaseView):
    @expose('/')
    def index(self):
        return self.render('admin/limages.html')

admin = Admin(app, index_view=CustomAdminView())
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Course, db.session))
admin.add_view(ModelView(Student, db.session))
admin.add_view(ModelView(Log, db.session))
# admin.add_view(StudentImagesView(name='Manage Students Images', endpoint='simages'))
# admin.add_view(LogImagesView(name='Manage Logs Images', endpoint='limages'))


# Not admin views
@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.datetime.now()
        db.session.commit()

@app.route('/')
@app.route('/index')
@login_required
def index():
    return render_template("home.html", title='Home', courses=current_user.teaching_courses)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html', title='Sign Up', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user.html', user=user)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile', form=form)

@app.route('/course/<code>')
@login_required
def course(code):
    course = Course.query.filter_by(code=code).first_or_404()
    return render_template('course.html', course=course)

@app.route('/contact_admin')
def contact_admin():
    return render_template('contact_admin.html')

@app.route('/retrain')
@login_required
def retrain():
    if current_user.is_admin:
        print("Re-training algo...")
        trainer.train()
        messag4admin = "Re-train :: Done!"
        return render_template('home.html',msg=messag4admin)
    else:
        abort(404)

@app.route('/export/<course_code>')
@login_required
def export(course_code):
    print("Exporting data for course:", course_code)
    # make directory for exported data
    exported_dir = os.path.join(os.getcwd(), "data/exported")
    if not os.path.exists(exported_dir):
        os.makedirs(exported_dir)
    # create workbook and sheets
    workbook_path = os.path.join(exported_dir, course_code + '.xlsx')
    workbook_attendances = xlsxwriter.Workbook(workbook_path)
    worksheet = workbook_attendances.add_worksheet(course_code)
    # header row style
    header_style = workbook_attendances.add_format()
    header_style.set_bold(True)
    header_style.set_font_color('white')
    header_style.set_bg_color('blue')
    header_cols = ['No.', 'Student Code', 'Student Name']
    worksheet.set_row(0, None, header_style)

    # write data to xlsx file
    course = Course.query.filter_by(code=course_code).first()
    dates = [log.date.isoformat() for log in course.logs]
    header_cols += dates
    worksheet.write_row('A1', header_cols)
    students_list = course.enrollees.all()
    for student in students_list:
        row = students_list.index(student) + 1
        worksheet.write(row, 0, row)
        worksheet.write(row, 1, student.code)
        worksheet.write(row, 2, student.name)
        for log in course.logs:
            if student in log.attendees:
                col = header_cols.index(log.date.isoformat())
                worksheet.write(row, col, 'X')
    workbook_attendances.close()
    # send file to user
    timestamp = datetime.datetime.now().replace(microsecond=0).isoformat()
    attachment_filename = timestamp.replace(':','').replace('-', '') + '_' + course.code + '.xlsx'
    return send_file(workbook_path, as_attachment=True, attachment_filename=attachment_filename)


############################# API ##############################################

LOG_IMAGES = os.path.join(os.getcwd(), "data/log-images")

# Flask-Marshmallow Schema
class StudentSchema(ma.ModelSchema):
    enroll = ma.Nested('CourseSchema', only=('code', 'name'), many=True)
    class Meta:
        model = Student

class LogSchema(ma.ModelSchema):
    attendees = ma.Nested('StudentSchema', only=('id', 'code', 'name'), many=True)
    class Meta:
        model = Log

class CourseSchema(ma.ModelSchema):
    enrollees = ma.Nested(StudentSchema, exclude=('attend', ), many=True)
    logs = ma.Nested(LogSchema, many=True)
    class Meta:
        model = Course

class UserSchema(ma.ModelSchema):
    teaching_courses = ma.Nested(CourseSchema, many=True)
    class Meta:
        fields = ('id', 'username', 'fullname', 'teaching_courses')

# auth callback
@auth.verify_password
def verify_password(username_or_token, password):
    # first try to authenticate by token
    user = User.verify_auth_token(username_or_token)
    if not user:
        # try to authenticate with username/password
        user = User.query.filter_by(username=username_or_token).first()
        if not user or not user.check_password(password):
            return False
    g.user = user
    return True


# User Auth With Token
@app.route('/api/login', methods=['GET', 'POST'])
@auth.login_required
def api_login():
    us = UserSchema()
    udata = us.dump(g.user).data
    message = "Hello {}!".format(g.user.username)
    token = g.user.generate_auth_token().decode('ascii')
    return jsonify({"message": message, "userdata": udata , "token10": token })

# Course
@app.route('/api/courses/<string:clist>', methods=['GET'])
@auth.login_required
def get_list_courses(clist):
    cs = CourseSchema(many=True)
    clist_int = [int(i) for i in clist.split(',') if i.strip().isdigit()]
    return_courses = []
    for _id in clist_int:
        c = Course.query.get(_id)
        if c:
            return_courses.append(c)
    return jsonify({"courses" : cs.dump(return_courses).data})

# Student
@app.route('/api/students/<string:slist>', methods=['GET'])
@auth.login_required
def get_list_students(slist):
    ss = StudentSchema(many=True)
    slist_int = [int(i) for i in slist.split(',') if i.strip().isdigit()]
    return_students = []
    for _id in slist_int:
        s = Student.query.get(_id)
        if s:
            return_students.append(s)
    return jsonify({"students" : ss.dump(return_students).data})

# Log
@app.route('/api/logs/<string:llist>', methods=['GET'])
@auth.login_required
def get_list_logs(llist):
    ls = LogSchema(many=True)
    llist_int = [int(i) for i in llist.split(',') if i.strip().isdigit()]
    return_logs = []
    for _id in llist_int:
        l = Log.query.get(_id)
        if l:
            return_logs.append(l)
    return jsonify({"logs" : ls.dump(return_logs).data})

# Attendance Check
@app.route('/api/checker', methods=['GET', 'POST'])
# @auth.login_required
def checker():
    if request.method == 'POST':
        print("Create log folder if not exists...")
        if not os.path.exists(LOG_IMAGES):
            os.makedirs(LOG_IMAGES)        
        
        if 'image' not in request.values:
            message = "no image in req!"
            result = "error"
            print(result, message, sep="-> ")
            # return jsonify({"result" : result, "message" : message, "data" : {}})
        elif 'cid' not in request.values:
            message = "no cid in req!"
            result = "error"
            print(result, message, sep="-> ")
            # return jsonify({"result" : result, "message" : message, "data" : {}})
        else:
            cid = request.values['cid']
            print("cid from req ->", cid)
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            saving_folder = os.path.join(LOG_IMAGES, cid, today)
            if not os.path.exists(saving_folder):
                os.makedirs(saving_folder)
            dest_file = os.path.join(saving_folder, uuid.uuid4().hex + ".jpg")
            print("New log image path ->", dest_file)
            print("Getting the image...")
            b64image = request.values['image']
            with open(dest_file, "wb") as f:
                f.write(base64.decodebytes(b64image.encode()))
            print("Saved at", dest_file)

            print("Recognizing people in new image...")
            print("=== Recognizer Begin ===")
            recognized_students = recognizer.recognize(dest_file)
            print("=== Recognizer End ===")

            # Create a log entry
            print("Creating a Log entry in DB...")
            log_date = datetime.datetime.now().date()
            log_create_time = datetime.datetime.now()
            # find log of cid and created today
            old = Log.query.filter_by(course_id=cid).filter_by(date=log_date).first()
            # if there is none then create a new one, if there is a log then update it
            if old is None:
                print("Creating new log...")
                new_log = Log(date=log_date, created_at=log_create_time)
                new_log.course_id = cid
                print("Adding attendees...")
                for std in recognized_students:
                    s = Student.query.filter_by(code=std).first()
                    if s is not None:
                        new_log.attendees.append(s)
                rate = new_log.calculate_present_rate()
                new_log.present_rate = rate
                db.session.add(new_log)
                db.session.commit()
            else:
                print("Update old log...")
                for std in recognized_students:
                    s = Student.query.filter_by(code=std).first()
                    if s is not None:
                        old.attendees.append(s)
                old.created_at = log_create_time
                rate = old.calculate_present_rate()
                old.present_rate = rate
                db.session.commit()
            print("Done! Sending results...")
            result = "ok"
            message = "Found " + str(len(recognized_students)) + " student(s)"
        return jsonify({"result" : result, "message" : message, "data" : recognized_students})
    else:
        result = "error"
        message = "Please make a POST request!"
        print(result, message, sep="-> ")
        return jsonify({"result" : result, "message" : message, "data" : {}})
