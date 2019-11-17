#!/usr/bin/python

import sys, requests, json, sqlite3, flask
from flask import request, jsonify
from sqlite3 import Error

app = flask.Flask(__name__)
app.config["DEBUG"] = True
#############################################################Database functions
def create_connection(database):
    conn = None
    try:
        conn = sqlite3.connect(database)
        return conn
    except Error as e:
        print(e)
    return conn

def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)

def create_userinfo(conn, userinfo):
    sql = ''' INSERT INTO userinfo(login,github_id)
              VALUES(?,?) '''
    cur = conn.cursor()
    try:
        cur.execute(sql, userinfo)
    except Error as e:
        print(e)
        print("Failed to insert user information")
        sys.exit(2)
    return cur.lastrowid

def create_repo(conn, repo):
    sql = ''' INSERT INTO repo(name,description,license,language,user_id)
              VALUES(?,?,?,?,?) '''
    cur = conn.cursor()
    try:
        cur.execute(sql, repo)
    except Error as e:
        print(e)
        print("Failed to insert repo information")
        sys.exit(2)
    return cur.lastrowid
########################Quick fetch function when queired username doesn't exist
def quick_fetch(username):
    #Getting user's info and his repos json
    print (username)
    try:
        userinfoRequest = requests.get("https://api.github.com/users/%s" % (username))
        repoRequest = requests.get("https://api.github.com/users/%s/repos?per_page=100" % (username))
    except requests.exceptions.RequestException as e:
        print(e)
        sys.exit(2)
    #For existing user create info structures and define db schema
    if userinfoRequest.status_code != 404:
        userinfoList = json.loads((userinfoRequest).text)
        repoList = json.loads((repoRequest).text)
        database = "./test.db"
        sql_create_userinfo_table = """CREATE TABLE IF NOT EXISTS userinfo (
                                    id integer PRIMARY KEY,
                                    login text NOT NULL,
                                    github_id integer unique
                                    );"""
        sql_create_repo_table = """CREATE TABLE IF NOT EXISTS repo (
                                id integer PRIMARY KEY,
                                name text NOT NULL,
                                description text,
                                license text,
                                language text,
                                user_id,
                                FOREIGN KEY (user_id) REFERENCES userinfo (id),
                                unique (name, user_id)
                                );"""
        #Create tables and populate userinfo table
        with create_connection(database) as conn:
            try:
                create_table(conn, sql_create_userinfo_table)
                create_table(conn, sql_create_repo_table)
            except Error as e:
                print(e)
                sys.exit(2)
            userinfo = (userinfoList.get('login'), userinfoList.get('id'));
            user_id = create_userinfo(conn, userinfo)
            #For users with repos populate repo table
            if repoRequest.status_code != 404:
                for repo in repoList:
                    try:
                        if repo['license'] != None:
                            license = repo.get('license', "")
                            license_name = str(license.get('name', ""))
                            query_params = (repo['name'], repo['description'], license_name, repo['language'], user_id)
                            create_repo(conn, query_params)
                    except Error as e:
                        print(e)
                        continue
    return()
#####################################################################API routes
@app.route('/', methods=['GET'])
def home():
    return '''<h1>Git info about users</h1>
<p>A prototype API for returning cached user info.</p>
<p>Usage: /api/repo?login= for list of repos, /api/userinfo/all for list of users</p>'''


@app.route('/api/userinfo/all', methods=['GET'])
def api_all():
    conn = sqlite3.connect('test.db')
    cur = conn.cursor()
    all_users = cur.execute('SELECT * FROM userinfo;').fetchall()
    return jsonify(all_users)

@app.errorhandler(404)
def page_not_found(e):
    return "<h1>404</h1><p>The resource could not be found.</p>", 404

@app.route('/api/repo', methods=['GET'])
def api_filter():
    query_parameters = request.args
    login = query_parameters.get('login')
    github_id = query_parameters.get('github_id')
    query = "SELECT * FROM userinfo INNER JOIN repo ON userinfo.id = repo.user_id WHERE"
    to_filter = []
    if login:
        query += ' login=? AND'
        to_filter.append(login)
    if github_id:
        query += ' github_id=? AND'
        to_filter.append(github_id)
    if not (login or github_id):
        return page_not_found(404)
    query = query[:-4] + ';'
    conn = sqlite3.connect('test.db')
    cur = conn.cursor()
    results = cur.execute(query, to_filter).fetchall()
    if not (results):
        quick_fetch(login)
        return('No such record as of now, try again later')
    return jsonify(results)

app.run()
