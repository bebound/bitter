#!/usr/bin/python -u

# Author: Hang Lei
# Wirte for http://www.cse.unsw.edu.au/~cs2041/15s2/assignments/bitter/
# A small website looks like twitter...

import cgi
import cgitb
import Cookie
import datetime
import hashlib
import os
import re
import sqlite3
import time
import uuid

from mail import Mail

DEBUG = 0
DATASET_PATH = 'dataset-large'
USER_PATH = os.path.join(DATASET_PATH, 'users')
BLEATS_PATH = os.path.join(DATASET_PATH, 'bleats')


class Header(object):
    def __init__(self):
        common_header = 'Content-Type: text/html'
        self.headers = []
        self.headers.append(common_header)

    def set_cookie(self, key, value):
        self.headers.append('Set-Cookie: {0}={1}'.format(key, value))

    def get_header(self):
        return '\n'.join(self.headers) + '\n'


def get_cookie():
    # return the received cookie
    cookies = Cookie.SimpleCookie(os.environ.get("HTTP_COOKIE", ""))
    return cookies


def get_file_content(file='base'):
    # return file content (usually is html file in template folder)
    if file:
        with open(os.path.join('template', file + '.html')) as f:
            return f.read().strip()
    else:
        return ''


def extend(base, **extend):
    # Django extend method
    base = get_file_content(base)

    return base.format(**extend)


def check_user_enabled(userinfo):
    # check whether user is enabled by dict userinfo
    return userinfo['enabled'] == '1'


def exec_sql(statement):
    if DEBUG:
        print 'exec sql:', statement
    with sqlite3.connect('db.sqlite3') as conn:
        c = conn.cursor()
        c.execute(statement)
        return c.fetchall()


def parse_bleat_sql(raw_result):
    results = []
    for i in raw_result:
        result = dict()
        result['id'] = str(i[0])
        result['latitude'] = str(i[1])
        result['time'] = str(i[2])
        result['longitude'] = str(i[3])
        result['bleat'] = str(i[4])
        result['username'] = str(i[5])
        result['reply'] = str(i[6])
        results.append(result)
    return results


def get_bleatinfo(id=''):
    if id:
        result = exec_sql('select * from BLEAT where id=\'{0}\''.format(id))
        return parse_bleat_sql(result)[0]


def get_all_bleats(limit=30):
    # get all bleats
    all_bleats = exec_sql(
        'select * from bleat order by time desc limit {0}'.format(limit))
    return parse_bleat_sql(all_bleats)


def get_related_bleats(username=''):
    if username:
        userinfo = get_userinfo(username)
        if userinfo:
            listens = userinfo['listens'].split()
            listens = ['"' + i + '"' for i in listens]
            listens_string = ','.join(listens)
            related_bleats = exec_sql(
                'select * from bleat where username in ({0}) or bleat like \'%@{1}%\' order by time desc'.format(
                    listens_string, username))
            return parse_bleat_sql(related_bleats)


def get_user_bleats(username=''):
    if username:
        related_bleat = exec_sql('select * from bleat where username = "{0}" order by time desc'.format(username))
        return parse_bleat_sql(related_bleat)


def get_bleats_html(bleats):
    div_template = """<div class="ui relaxed selection list">{lists}</div>"""
    list_template = """<div class="item">
                <div class="ui grid">
                    <div class="two wide column">
                        <a href="?url=bleats&user={username}">
                            <img class="ui avatar image left floated" src="{image_url}">
                        </a>
                    </div>
                    <div class="fourteen wide column">
                        <div class="content">
                            <a class="header" href="?url=bleats&user={username}">{username}</a>
                            <div class="description"><a href="?url=bleatinfo&bleat={bleatid}">{bleat}</a>
                            <div class="lable">{time}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>"""
    if bleats:
        lists = []
        for bleat in bleats:
            image_url = os.path.join(USER_PATH, bleat['username'], 'profile.jpg')
            time = datetime.datetime.fromtimestamp(float(bleat['time'])).strftime('%Y-%m-%d %H:%M:%S')

            list = list_template.format(image_url=image_url, username=bleat['username'], bleat=bleat['bleat'],
                                        bleatid=bleat['id'], time=time)
            lists.append(list)
        return div_template.format(lists='\n'.join(lists))


def get_user_listens(username=''):
    # return user listens
    if username:
        userinfo = get_userinfo(username)
        return userinfo['listens'].split()


def get_user_follower(username=''):
    # return user followers
    if username:
        result = exec_sql("select * from USER where listens LIKE '%{0}%'".format(username))
        users = parse_user_sql(result)
        return [user['username'] for user in users]


def hash(string):
    return hashlib.sha256(string).hexdigest()


def safe_string(string):
    # escape strings get from user to prevent XSS attack
    return cgi.escape(string) if string else ''


def login(parameters):
    # login controller
    username = safe_string(parameters.getvalue('username'))
    password = safe_string(parameters.getvalue('password'))
    result = exec_sql(
        "select * from USER where username='{0}' and password='{1}' and activated='1'".format(username,
                                                                                              password))
    if result:
        header = Header()
        header.set_cookie('username', username)
        header.set_cookie('session', hash(username + password))
        print header.get_header()
        print extend('notification', title='Success', header='Success',
                     message='Login successfully', redirect='?url=homepage')
    else:
        login_page(error='1')


def login_page(error=''):
    # render login page, is error='1' print error information
    if error:
        header = Header()
        print header.get_header()
        print extend('login',
                     error='<div class="ui message"><ul class="list"><li>username or password invalid</li></ul></div>')
    else:
        header = Header()
        print header.get_header()
        print extend('login', error='')


def logout():
    # logout controller
    header = Header()
    header.set_cookie('username', '')
    header.set_cookie('session', '')
    print header.get_header()
    print extend('notification', title='Success', header='Success',
                 message='Logout successfully', redirect='?url=homepage')


def parse_user_sql(raw_result):
    # parse sql result to list contains dict
    results = []
    for i in raw_result:
        result = dict()
        result['username'] = str(i[0])
        result['password'] = str(i[1])
        result['home_latitude'] = str(i[2])
        result['home_suburb'] = str(i[3])
        result['full_name'] = str(i[4])
        result['listens'] = str(i[5])
        result['email'] = str(i[6])
        result['bleats'] = str(i[7])
        result['detail'] = str(i[8])
        result['enabled'] = int(str(i[9])) if i[9] is not None and i[9] else 0
        result['activated'] = int(str(i[10])) if i[10] is not None and i[10] else 0
        result['notification'] = int(str(i[11])) if i[11] is not None and i[11] else 0
        results.append(result)
    return results


def get_userinfo(username='', force=False):
    # return the first userinfo
    if username:
        if not force:
            result = exec_sql("select * from USER where username='{0}' and enabled='1'".format(username))
        else:
            result = exec_sql("select * from USER where username='{0}'".format(username))
        if result:
            return parse_user_sql(result)[0]


def get_cookie_value(key):
    cookie = get_cookie()
    if key in cookie:
        return cookie[key].value
    return ''


def get_current_userinfo():
    # return current logined userinfo
    username = get_cookie_value('username')
    if username:
        return get_userinfo(username, force=True)
    return None


def check_login_user():
    # verify user login info from cookie
    username = get_cookie_value('username')
    session = get_cookie_value('session')
    if username and session:
        userinfo = get_current_userinfo()
        if userinfo:
            return hash(username + userinfo['password']) == session and userinfo['activated']
    return False


def notlogin_homepage():
    # render homepage for notlogined user
    header = Header()
    print header.get_header()

    bleats_html = get_bleats_html(get_all_bleats())
    content = extend('notlogin_homepage', content=bleats_html)

    print extend('base', header=get_file_content('notlogin_header'), content=content, title='Bitter')


def get_userlist_html(userlist):
    # render userlist html
    div_template = """<div class="ui middle aligned selection list">{lists}</div>"""
    list_template = """
<div class="item">
    <img class="ui avatar image" src="{image_url}">
    <div class="content">
        <a class="header" href="?url=bleats&user={username}">{username}</a>
    </div>
</div>"""
    if userlist:
        lists = []
        for username in userlist:
            image_url = os.path.join(USER_PATH, username, 'profile.jpg')
            list = list_template.format(image_url=image_url, username=username)
            lists.append(list)
        return div_template.format(lists='\n'.join(lists))


def listen_html():
    # render listen form
    return """<div class="row">
    <form class="ui form right floated" method="post" action="?url=listen&user={username}">
        <input type="submit" value="listen" class="ui submit button">
    </form>
</div>"""


def unlisten_html():
    # render unlisten form
    return """<div class="row">
    <form class="ui form right floated" method="post" action="?url=unlisten&user={username}">
        <input type="submit" value="unlisten" class="ui submit button">
    </form>
</div>"""


def is_listen(username, target_user):
    # check is username listen for target_user
    userinfo = get_userinfo(username)
    return target_user in userinfo['listens'].split()


def notfound(redirect='?url=homepage'):
    header = Header()
    print header.get_header()
    print extend('404', title='404', redirect=redirect)


def userinfo(parameters, page=None):
    # render the main page for user
    if check_login_user():
        header_html = get_file_content('logined_header')
    else:
        header_html = get_file_content('notlogin_header')
    if 'user' in parameters:
        user = get_userinfo(parameters['user'].value)
    else:
        user = get_current_userinfo()
    if user:
        username = user['username']
        cur_user = get_current_userinfo()
        same_user = True if user == cur_user else False
        if same_user or not cur_user:
            listenhtml = ''
        elif is_listen(cur_user['username'], username):
            listenhtml = unlisten_html().format(username=username)
        else:
            listenhtml = listen_html().format(username=username)
        profile_img = os.path.join(USER_PATH, username, 'profile.jpg')
        content_html = ''
        if page is None:
            content_html = get_bleats_html(get_related_bleats(username))
        elif page == 'bleats':
            content_html = get_bleats_html(get_user_bleats(username))
        elif page == 'listens':
            content_html = get_userlist_html(get_user_listens(username))
        elif page == 'followers':
            content_html = get_userlist_html(get_user_follower(username))

        header = Header()
        print header.get_header()
        content = extend('login_homepage', profile_img=profile_img, listen_html=listenhtml,
                         content_html=content_html, **user)

        print extend('base', header=header_html, content=content,
                     title='Bitter - ' + user['username'])
    else:
        notfound()


def homepage(parameters):
    # render user homepage
    if check_login_user():
        userinfo(parameters)

    else:
        notlogin_homepage()

    if DEBUG:
        print "".join("<!-- %s=%s -->\n" % (p, parameters.getvalue(p)) for p in parameters)


def search_user(keyword):
    result = exec_sql(
        "select * from (select * from user where username like '%{keyword}%' or full_name like '%{keyword}%') where enabled='1'".format(
            keyword=keyword))
    return parse_user_sql(result) if result else []


def search_bleats(keyword):
    result = exec_sql('select * from bleat where bleat like \'%{keyword}%\' order by time desc'.format(keyword=keyword))
    return parse_bleat_sql(result) if result else []


def search(keyword, type='', page=''):
    # render search result page
    if not type:
        # search user and bleats
        target_users = [i['username'] for i in search_user(keyword)]
        target_bleats = search_bleats(keyword)

        user_html = get_userlist_html(target_users) if target_users else ''
        bleats_html = get_bleats_html(target_bleats) if target_users else ''
        content_html = """<h4 class="ui horizontal divider header">
  <i class="tag icon"></i>
  User
</h4>""" + user_html + """<h4 class="ui horizontal divider header">
  <i class="comment icon"></i>
  Bleats
</h4>""" + bleats_html
        header = Header()
        print header.get_header()

        content = extend('notlogin_homepage', content=content_html)

        if get_current_userinfo():
            header_html = get_file_content('logined_header')
        else:
            header_html = get_file_content('notlogin_header')
        print extend('base', header=header_html, content=content, title='Bitter Search - ' + keyword)


def reg_page(error=''):
    # render reg page
    if error:
        header = Header()
        print header.get_header()
        content = extend('user_form', action_url='?url=regform',
                         error='<div class="ui message"><ul class="list"><li>username or password invalid</li></ul></div>')
        print extend('reg', content=content)
    else:
        header = Header()
        print header.get_header()
        content = extend('user_form', action_url='?url=regform', error='')
        print extend('reg', content=content)


def hash_activate(username):
    return hash(username + 'activate')


def reg(parameters):
    # reg controller
    email = safe_string(parameters.getvalue('email'))
    username = safe_string(parameters.getvalue('username'))
    password = safe_string(parameters.getvalue('password'))
    full_name = safe_string(parameters.getvalue('full_name'))
    home_latitude = safe_string(parameters.getvalue('home_latitude'))
    home_suburb = safe_string(parameters.getvalue('home_suburb'))
    detail = safe_string(parameters.getvalue('detail'))
    detail = ''.join(['<p>' + i + '</p>' for i in detail.split('\n')])

    result = exec_sql(
        "select * from USER where username='{0}'".format(username))
    if result:
        reg_page(error='Username already exist')
    elif len(username) <= 4 or len(password) < 6:
        reg_page(error='Username must contains at least 4 characters, password must contains at least 6 characters')
    else:
        exec_sql("insert into user VALUES ('{0}','{1}','{2}','{3}','{4}','','{5}','','{6}','1','','')".format(username,
                                                                                                              password,
                                                                                                              home_latitude,
                                                                                                              home_suburb,
                                                                                                              full_name,
                                                                                                              email,
                                                                                                              detail))
        code = hash_activate(username)
        mail = Mail(email, 'Activate your account',
                    'Click this link to activate your account: {2}?url=activate&code={0}&username={1}'.format(
                        code, username, os.environ['SCRIPT_URI']))
        mail.send()

        header = Header()
        print header.get_header()
        print extend('notification', title='Success', header='Success',
                     message='Please check your email to activate your account', redirect='?url=homepage')


def activate_user(username):
    exec_sql("update user set activated='1' where username='{0}'".format(username))
    os.mkdir(os.path.join(USER_PATH, username))


def activate(parameters):
    # activate user if the code is correct
    code = parameters['code'].value
    username = parameters['username'].value
    if hash_activate(username) == code:
        activate_user(username)
        header = Header()
        print header.get_header()
        print extend('notification', title='Success', header='Success',
                     message='Your account has been activated', redirect='?url=homepage')
    else:
        header = Header()
        print header.get_header()
        print extend('notification', title='Failed', header='Failed',
                     message='The activate code is invaliad', redirect='?url=homepage')


def get_largest_bleat_id():
    # return the largest bleat id in the database
    result = exec_sql('select * from bleat order by id desc limit 1')
    return parse_bleat_sql(result)[0]['id']


def notification_bleat(bleat, userinfo):
    if userinfo['email']:
        mail = Mail(userinfo['email'], 'A bleats mentions you', 'The bleat is "{0}"'.format(bleat))
        mail.send()


def notification_reply(username, bleat, userinfo):
    if userinfo['email']:
        message = '{0} reply "{1}"'.format(username, bleat)
        mail = Mail(userinfo['email'], 'One reply your bleat', message)
        mail.send()


def add_bleats(parameters):
    # add bleats form controller
    bleat = parameters['bleat'].value
    bleat = bleat[:141] if len(bleat) > 142 else bleat
    user = get_current_userinfo()
    username = user['username']
    reply = parameters['reply'].value if 'reply' in parameters else ''
    redirect = parameters['redirect'].value if 'reply' in parameters else '?url=homepage'
    bleat = cgi.escape(bleat)
    id = str(int(get_largest_bleat_id()) + 1)
    timestamp = time.time()
    exec_sql(
        "insert into bleat values('{0}','','{1}','','{2}','{3}','{4}')".format(id, timestamp, bleat, username, reply))
    new_user_bleats = user['bleats'] + ' ' + id
    exec_sql("update user set bleats='{0}' where username='{1}'".format(new_user_bleats, username))

    names = re.findall(r'@(\w+)', bleat)
    for name in names:
        userinfo = get_userinfo(name)
        if userinfo and userinfo['notification']:
            notification_bleat(bleat, userinfo)
    if reply:
        original_bleat = get_bleatinfo(reply)
        notification_reply(username, bleat, get_userinfo(original_bleat['username']))

    header = Header()
    print header.get_header()
    print extend('notification', title='Success', header='Success', message='Your bleat has been submitted',
                 redirect=redirect)


def notification_listen(follower, userinfo):
    if userinfo['email']:
        mail = Mail(userinfo['email'], 'New follower', 'The new follower is "{0}"'.format(follower))
        mail.send()


def listen(parameters):
    # listen user controller
    target_user = parameters['user'].value
    current_user = get_current_userinfo()
    listens = current_user['listens'].split()
    listens.append(target_user)
    listens = ' '.join(listens)
    exec_sql("update user set listens='{0}' where username='{1}'".format(listens, current_user['username']))
    if get_userinfo(target_user)['notification']:
        notification_listen(current_user['username'], get_userinfo(target_user))
    header = Header()
    print header.get_header()
    print extend('notification', title='Success', header='Success',
                 message='Listen successfully', redirect='?url=bleats&user={0}'.format(target_user))


def unlisten(parameters):
    # unlisten user controller
    target_user = parameters['user'].value
    current_user = get_current_userinfo()
    listens = current_user['listens'].split()
    listens.remove(target_user)
    listens = ' '.join(listens)
    exec_sql("update user set listens='{0}' where username='{1}'".format(listens, current_user['username']))
    header = Header()
    print header.get_header()
    print extend('notification', title='Success', header='Success',
                 message='Unlisten successfully', redirect='?url=bleats&user={0}'.format(target_user))


def delete_bleat(parameters):
    bleat = parameters['bleat'].value
    username = get_current_userinfo()['username']
    exec_sql("delete from bleat where id='{0}' and username='{1}'".format(bleat, username))

    header = Header()
    print header.get_header()
    print extend('notification', title='Success', header='Success',
                 message='Delete bleat successfully', redirect='?url=bleats')


def get_bleatinfo_html(bleats):
    # render the bleat and its rely html
    div_template = """<div class="ui grid" id="container">
    <div class="ui segment sixteen wide column">
        <div class="ui relaxed selection list">
        {lists}
        </div>
    </div>
    <div class="sixteen wide column">
        <form class="ui form" action="?url=addbleat" method="post" id="bleat">
            <div class="ui grid">
                <div class="thirteen wide column left floated">
                    <div class="ui field">
                        <textarea rows="2" name="bleat" form="bleat"></textarea>
                    </div>
                </div>
                <input type="hidden" name="reply" value="{id}">
                <input type="hidden" name="redirect" value="?url=bleatinfo&bleat={id}">
                <div class="three wide column right floated center aligned middle aligned">
                    <input type="submit" value="Reply Bleat" class="ui submit button"/>
                </div>
            </div>
        </form>
    </div>
</div>
"""
    list_template = """<div class="item">
    <div class="ui grid">
        <div class="two wide column">
            <img class="ui avatar image left floated" src="{image_url}">
        </div>
        <div class="twelve wide column">
            <div class="content">
                <a class="header" href="?url=bleats&user={username}">{username}</a>

                <div class="description">{bleat}</div>
                <div class="lable">{time}</div>
            </div>
        </div>
        <div class="two wide column">
            <div class="content">
                {delete}
            </div>
        </div>

    </div>
</div>"""
    lists = []
    current_user = get_current_userinfo()['username']
    id = bleats[0]['id']
    for bleat in bleats:
        username = bleat['username']
        if bleat['username'] == current_user:
            delete = """<form class="ui form" action="?url=deletebleat" method="post">
            <input type="hidden" name="bleat" value="{id}">
        <input type="submit" value="Delete" class="ui fluid large teal submit button"/>
    </form>""".format(id=bleat['id'])
        else:
            delete = ''
        time = datetime.datetime.fromtimestamp(float(bleat['time'])).strftime('%Y-%m-%d %H:%M:%S')
        image_url = os.path.join(USER_PATH, username, 'profile.jpg')
        list = list_template.format(image_url=image_url, username=username, bleat=bleat['bleat'], time=time,
                                    delete=delete)
        lists.append(list)
    return div_template.format(lists='\n'.join(lists), id=id)


def bleatinfo(parameters):
    # render the bleatinfo page
    id = parameters['bleat'].value
    bleats = [get_bleatinfo(id)]
    reply = parse_bleat_sql(exec_sql("select * from bleat where reply='{0}'".format(id)))
    bleats.extend(reply)

    header = Header()
    print header.get_header()
    header = get_file_content('logined_header') if get_current_userinfo() else get_file_content('notlogin_header')
    content = get_bleatinfo_html(bleats)
    print extend('base', title='Bitter', header=header, content=content)


def setting_page(error=''):
    userinfo = get_current_userinfo()
    header = Header()
    print header.get_header()
    content = extend('settings', error=error, **userinfo)
    print extend('base', title='Bitter - Settings', header=get_file_content('logined_header'),
                 content=content)


def setting_form(parameters):
    username = get_current_userinfo()['username']
    password = safe_string(parameters.getvalue('password'))
    full_name = safe_string(parameters.getvalue('full_name'))
    home_latitude = safe_string(parameters.getvalue('home_latitude'))
    home_suburb = safe_string(parameters.getvalue('home_suburb'))
    detail = safe_string(parameters.getvalue('detail'))

    result = exec_sql(
        "select * from USER where username='{0}'".format(username))
    if not result:
        print setting_page(error='Username not exist')
    elif len(password) < 6 and password:
        print setting_page(
            error='Password must contains at least 6 characters')
    else:
        if password:
            exec_sql("update user set password='{0}' where username='{1}'".format(password, username))
        if full_name:
            exec_sql("update user set full_name='{0}' where username='{1}'".format(full_name, username))
        if home_latitude:
            exec_sql("update user set home_latitude='{0}' where username='{1}'".format(home_latitude, username))
        if home_suburb:
            exec_sql("update user set home_suburb='{0}' where username='{1}'".format(home_suburb, username))
        if detail:
            exec_sql("update user set detail=\"{0}\" where username='{1}'".format(detail.replace('"', ''), username))
        header = Header()
        print header.get_header()
        print extend('notification', title='Success', header='Success',
                     message='Update settings successfully', redirect='?url=settings')


def changepic(parameters):
    username = get_current_userinfo()['username']
    if 'pic' in parameters:
        pic = parameters['pic']
        with open(os.path.join(USER_PATH, username, 'profile.jpg'), 'wb') as f:
            f.write(pic.file.read())
        header = Header()
        print header.get_header()
        print extend('notification', title='Success', header='Success',
                     message='Update avatar successfully', redirect='?url=settings')
    else:
        setting_page('Avatar is null')


def deletepic():
    username = get_current_userinfo()['username']
    os.remove(os.path.join(USER_PATH, username, 'profile.jpg'))
    header = Header()
    print header.get_header()
    print extend('notification', title='Success', header='Success',
                 message='Delete avatar successfully', redirect='?url=settings')


def forgetpwd(error=''):
    header = Header()
    print header.get_header()

    print extend('forget', error=error)


def forgetform(parameters):
    username = parameters.getvalue('username')
    email = parameters.getvalue('email')
    result = exec_sql("select * from user where username='{0}' and email='{1}'".format(username, email))
    if result:
        newpwd = str(uuid.uuid1())
        exec_sql("update user set password='{0}' where username='{1}'".format(newpwd, username))
        mail = Mail(email, 'Your new password', 'Your new password is {0}'.format(newpwd))
        mail.send()
        header = Header()
        print header.get_header()
        print extend('notification', title='Success', header='Success',
                     message='Reset password successfully, please check your email', redirect='?url=homepage')
    else:
        forgetpwd('Invaliad username and email')


def suspend_account():
    username = get_current_userinfo()['username']
    exec_sql("update user set enabled='0' where username='{0}'".format(username))
    header = Header()
    print header.get_header()
    print extend('notification', title='Success', header='Success',
                 message='Suspend account successfully', redirect='?url=settings')


def unsuspend_account():
    username = get_current_userinfo()['username']
    exec_sql("update user set enabled='1' where username='{0}'".format(username))
    header = Header()
    print header.get_header()
    print extend('notification', title='Success', header='Success',
                 message='Unsuspend account successfully', redirect='?url=settings')


def delete_account():
    username = get_current_userinfo()['username']
    exec_sql("delete from user where username='{0}'".format(username))
    exec_sql("delete from bleat where username='{0}'".format(username))
    header = Header()
    print header.get_header()
    print extend('notification', title='Success', header='Success',
                 message='Delete account successfully', redirect='?url=settings')


def enable_notification():
    username = get_current_userinfo()['username']
    exec_sql("update user set notification='1' where username='{0}'".format(username))
    header = Header()
    print header.get_header()
    print extend('notification', title='Success', header='Success',
                 message='Enable notification successfully', redirect='?url=settings')


def disable_notification():
    username = get_current_userinfo()['username']
    exec_sql("update user set notification='0' where username='{0}'".format(username))
    header = Header()
    print header.get_header()
    print extend('notification', title='Success', header='Success',
                 message='Disable notification successfully', redirect='?url=settings')


def main():
    cgitb.enable()
    parameters = cgi.FieldStorage()

    if 'url' not in parameters:
        homepage(parameters)
    else:
        if parameters['url'].value == 'homepage':
            homepage(parameters)
        elif parameters['url'].value == 'login':
            login_page()
        elif parameters['url'].value == 'loginform':
            login(parameters)
        elif parameters['url'].value == 'logout':
            logout()
        elif parameters['url'].value == 'bleats':
            userinfo(parameters, 'bleats')
        elif parameters['url'].value == 'listens':
            userinfo(parameters, 'listens')
        elif parameters['url'].value == 'followers':
            userinfo(parameters, 'followers')
        elif parameters['url'].value == 'search' and 'keyword' in parameters:
            search(parameters['keyword'].value)
        elif parameters['url'].value == 'reg':
            reg_page()
        elif parameters['url'].value == 'regform':
            reg(parameters)
        elif parameters['url'].value == 'activate':
            activate(parameters)
        elif parameters['url'].value == 'addbleat':
            add_bleats(parameters)
        elif parameters['url'].value == 'userinfo':
            userinfo(parameters)
        elif parameters['url'].value == 'userbleats':
            userinfo(parameters, 'bleats')
        elif parameters['url'].value == 'userlistens':
            userinfo(parameters, 'listens')
        elif parameters['url'].value == 'userfollowers':
            userinfo(parameters, 'followers')
        elif parameters['url'].value == 'listen':
            listen(parameters)
        elif parameters['url'].value == 'unlisten':
            unlisten(parameters)
        elif parameters['url'].value == 'bleatinfo':
            bleatinfo(parameters)
        elif parameters['url'].value == 'settings':
            setting_page()
        elif parameters['url'].value == "settingform":
            setting_form(parameters)
        elif parameters['url'].value == "changepic":
            changepic(parameters)
        elif parameters['url'].value == "forgetpwd":
            forgetpwd()
        elif parameters['url'].value == "forgetform":
            forgetform(parameters)
        elif parameters['url'].value == "deletepic":
            deletepic()
        elif parameters['url'].value == "suspendaccount":
            suspend_account()
        elif parameters['url'].value == "unsuspendaccount":
            unsuspend_account()
        elif parameters['url'].value == "deleteaccount":
            delete_account()
        elif parameters['url'].value == "deletebleat":
            delete_bleat(parameters)
        elif parameters['url'].value == "enablenotification":
            enable_notification()
        elif parameters['url'].value == "disablenotification":
            disable_notification()
        else:
            homepage(parameters)


if __name__ == '__main__':
    main()
