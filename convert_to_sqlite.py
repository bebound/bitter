import glob
import os
import sqlite3


def create_table():
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute(
        """CREATE TABLE user(username TEXT, password TEXT, home_latitude REAL, home_suburb TEXT, full_name TEXT, listens TEXT, email TEXT, bleats TEXT, detail TEXT, enabled TEXT, activated TEXT, notification TEXT)""")
    c.execute(
        """CREATE TABLE bleat(id TEXT,latitude REAL, time REAL, longitude REAL, bleat TEXT, username TEXT, reply REAL)""")
    conn.commit()
    conn.close()


def insert_user():
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    for path in glob.glob('dataset-large/users/*'):
        print(path)
        with open(os.path.join(path, 'bleats.txt'), 'r') as f:
            bleats = f.read().replace('\n', ' ')
        with open(os.path.join(path, 'details.txt'), 'r') as f:
            username = ''
            password = ''
            home_latitude = ''
            home_suburb = ''
            full_name = ''
            listens = ''
            email = ''
            detail = ''
            enabled = '1'
            activated = '1'
            notification = '0'

            lines = [_.strip() for _ in f.readlines()]
            for line in lines:
                if line.startswith('username'):
                    username = line.split(':')[-1].strip()
                if line.startswith('password'):
                    password = line.split(':')[-1].strip()
                if line.startswith('home_latitude'):
                    home_latitude = line.split(':')[-1].strip()
                if line.startswith('home_suburb'):
                    home_suburb = line.split(':')[-1].strip()
                if line.startswith('full_name'):
                    full_name = line.split(':')[-1].strip()
                if line.startswith('listens'):
                    listens = line.split(':')[-1].strip()
                if line.startswith('email'):
                    email = line.split(':')[-1].strip()

        c.execute(
            "insert into user values ('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(username,
                                                                                                           password,
                                                                                                           home_latitude,
                                                                                                           home_suburb,
                                                                                                           full_name,
                                                                                                           listens,
                                                                                                           email,
                                                                                                           bleats,
                                                                                                           detail,
                                                                                                           enabled,
                                                                                                           activated,
                                                                                                           notification))
    conn.commit()
    conn.close()


def insert_bleat():
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    for path in glob.glob('dataset-large/bleats/*'):
        print(path)
        id = path.split('/')[-1]
        with open(path, 'r') as f:
            username = ''
            latitude = ''
            time = ''
            longitude = ''
            bleat = ''
            reply = ''

            lines = [_.strip() for _ in f.readlines()]
            for line in lines:
                if line.startswith('username'):
                    username = line.split(':')[-1].strip()
                if line.startswith('latitude'):
                    latitude = line.split(':')[-1].strip()
                if line.startswith('time'):
                    time = line.split(':')[-1].strip()
                if line.startswith('longitude'):
                    longitude = line.split(':')[-1].strip()
                if line.startswith('bleat'):
                    bleat = line.split(':')[-1].strip()
        try:
            c.execute(
                'insert into bleat values ("{}","{}","{}","{}","{}","{}","{}")'.format(id, latitude, time, longitude,
                                                                                       bleat,
                                                                                       username, reply))
        except:
            c.execute(
                "insert into bleat values ('{}','{}','{}','{}','{}','{}','{}')".format(id, latitude, time, longitude,
                                                                                       bleat,
                                                                                       username, reply))
    conn.commit()
    conn.close()


def main():
    create_table()
    insert_user()
    insert_bleat()


if __name__ == "__main__":
    main()
