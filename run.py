from flask import Flask, render_template, request, redirect, url_for
from flask_bootstrap import Bootstrap
import os
import glob
import sqlite3 as sql

app = Flask(__name__)
Bootstrap(app)

@app.route('/')
def home(): 
   con = sql.connect(dbname)
   con.row_factory = sql.Row
   cur = con.cursor()
   cur.execute("select * from `migration`")
   rows = cur.fetchall()
   return render_template('home.html', rows = rows)

if __name__ == '__main__':
    dbname = 'xcp.sqlite'
    con = sql.connect(dbname)
    con.row_factory = sql.Row
    cur = con.cursor()
    cur.execute("create table if not exists `migration` (`name` text,`source` text,`destination` text)")
    cur.execute("create table if not exists `options` (`activated` text,`catalog` text)")
    app.run(host='0.0.0.0', debug = True)
