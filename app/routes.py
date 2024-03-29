from flask import render_template, flash, redirect, url_for, request, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app
from app.forms import LoginForm, DateForm
from app.models import User
from elasticsearch import Elasticsearch
import base64
import time
from datetime import datetime
from dateutil import tz,parser
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import socket
import jsonify

sched = BackgroundScheduler()

es = Elasticsearch()
# es = Elasticsearch([{'host': '192.168.43.122', 'port': 9200}])
# es_index = 'my_index'
es_index = 'pigeon-image-test2'

old = {}

@app.route('/')
@app.route('/index')
@app.route('/index/<path:path>', methods=['GET', 'POST'])
@login_required
def index(path=None):
    # host_ = "http://localhost:5601"
    host_ = 'http://{}:5601'.format(socket.gethostbyname(socket.gethostname()))

    res = host_  +  """/app/kibana#/dashboard/c1221060-917f-11e9-ba43-3b55f2d261b4?embed=true&_g=()"""

    return render_template('index.html', res=res)


@app.route('/picture_search', methods=['GET', 'POST'])
@login_required
def picture_search(dic = None, hits = None, form = None):
    global es_index, old
    if request.method == 'POST':
        if dic and hits and form:
            return render_template('picture.html', title='Bird Pictures', form=old['form'], res=old['dic'], hits=old['hits'])

    form = DateForm()
    dic = {}

    if form.is_submitted():

        ts = request.form['date'] + 'T' + request.form['time']
        te = request.form['date2'] + 'T' + request.form['time2']
        date_object = time.strptime(ts, '%Y-%m-%dT%H:%M')
        date2_object = time.strptime(te, '%Y-%m-%dT%H:%M')
        date_utc = time.strftime("%Y-%m-%dT%H:%M:%S",time.gmtime(time.mktime(date_object)))
        date2_utc = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.mktime(date2_object)))

        body = {
            "size": 1000,
            "_source": [ "timestamp", "orginal_image", "found.bird", "dayofweek_text"],
            "query": {
                "range": {
                    "timestamp": {
                        'gte': date_utc,
                        "lte": date2_utc
                    }
                }
            },
            "sort": [
                {"timestamp": {"order": "asc"}}
            ]
        }
        res = es.search(index=es_index, doc_type='_doc', body=body, scroll='1m')
        # for i in res['hits']['total']:
        #     print(i)
        # print(res['hits']['total']['value'])
        hits = res['hits']['total']['value']
        res = res['hits']['hits']

        for e, i in enumerate(res):
            # print(i['_source']['timestamp'])
            try:
                new_time = datetime.strptime(i['_source']['timestamp'], '%Y-%m-%dT%H:%M:%S')
            except:
                try:
                    new_time = datetime.strptime(i['_source']['timestamp'], '%Y-%m-%dT%H:%M:%S+07:00')
                except:
                    new_time = datetime.strptime(i['_source']['timestamp'], '%Y-%m-%dT%H:%M:%S.%f+07:00')

            from_zone = tz.gettz('UTC')
            to_zone = tz.gettz('Asia/Bangkok')
            utc = new_time.replace(tzinfo=from_zone)
            central = utc.astimezone(to_zone)
            central = str(central)[:str(central).index('+')]
            # print(new_time, central)
            try:
                dic[i['_id']] = {'time': central, 'numDetect': i['_source']['found']['bird'], 'index': e + 1, 'dayofweek':i['_source']['dayofweek_text']}
            except:
                pass

            # print(i['_id'], new_time, central)
            old['dic'] = dic
            old['hits'] = hits
            old['form'] = form

        return render_template('picture.html', title='Bird Pictures', form=form, res=dic, hits=hits)
    return render_template('picture.html', title='Bird Pictures', form=form, res=dic)

@app.route('/render_img/<path:path>', methods=['POST'])
@login_required
def render_img(path):
    global es_index, old
    # print(path)
    body = {
        "_source": ["orginal_image","original_image"],
        "query": {
            "match": {
                "_id": {
                    "query": path,
                }
            }
        }
    }
    res = es.search(index=es_index, doc_type='_doc', body=body, scroll='1m')['hits']['hits']
    try:
        aa = str.encode(res[0]['_source']['orginal_image'])
    except:
        aa = str.encode(res[0]['_source']['original_image'])
    aa = aa[2:-1]
    # print(type(aa))
    # print()
    jpg_original = base64.b64decode(aa)
    # print(jpg_original)

    # cv2.imshow('sas', jpg_original)
    # Write to a file to show conversion worked
    # temp_image = 'app/static/temp_'+path+'.jpg'
    temp_image = 'app/static/temp_image.jpg'
    with open(temp_image, 'wb') as f_output:
    	f_output.write(jpg_original)
    print('Save IMAGE Success')
    # return render_template('blank.html', img = temp_image, title='Picture')
    # return render_template('picture.html', title='Bird Pictures', form=form_, res=session['dic'], hits=session['hits'])
    return render_template('picture.html', title='Bird Pictures', **old)




@app.route('/live')
@login_required
def live():
    return redirect('http://172.27.228.190:5000/')
    # return redirect('http://192.168.1.11:5000/')
    # return redirect('http://192.168.43.153:5000/')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Login', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

def lineNotify(file=None):
    url = 'https://notify-api.line.me/api/notify'
    token = 'nxq3ujARCV0PjPejkewDeMkMgo4MmSFrwaPZWH8eX8D'	#EDIT
    headers = {'Authorization':'Bearer '+token}

    body = {
        "size": 100,
        "query": {
            "range": {
                "my_timestamp": {
                    "gte": "02/08/2019",
                    "lte": "02/08/2019",
                    "format": "MM/dd/yyyy"
                }
            }
        }
    }
    res = es.search(index=es_index, doc_type='image', body=body, scroll='1m')
    res = res['hits']['hits']
    num = 0
    for i in res:
        num += i['_source']['numDetect']
    msg = '\nFound >>> {}\nTotalBirds >>> {}'.format(str(len(res)), str(num))
    return requests.post(url, headers=headers , data = {'message':msg}, files=file)

@sched.scheduled_job('cron', year='*', month='*', day='*', week='*', hour='*', minute='*', second='30')
def timed_job():
    print('This job is running.')
    lineNotify()

@app.route('/run-tasks')
@login_required
def run_tasks():
    print('run...1')
    sched.start()
    # print('run...2')
    return 'Scheduled several long running tasks', 200

@app.route('/stop-tasks')
@login_required
def stop_tasks():
    sched.shutdown()
    return 'Shutdown Scheduled', 200

@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "content=0"
    r.headers['Cache-Control'] = 'public, max-age=0'

    return r
