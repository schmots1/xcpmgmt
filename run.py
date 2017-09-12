from flask import Flask, render_template, request, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_wtf import Form
from flask_sqlalchemy import SQLAlchemy
from wtforms import TextField, StringField, SubmitField
import os
import glob
#import sqlite3 as sql
from werkzeug import secure_filename
import tarfile

basedir = os.path.abspath(os.path.dirname(__file__))

UPLOAD_FOLDER = './'
ALLOWED_EXTENSIONS = set(['tar', 'tgz', 'gz' 'license'])
app = Flask(__name__)
app.config['SECRET_KEY'] = 'keefer'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'xcp.sqlite')
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
Bootstrap(app)
db = SQLAlchemy(app)


#forms
class migrationForm(Form):
    name = TextField("Migration pair name:")
    source = TextField("Source NFS path:")
    destination = TextField("Destination NFS path:")
    submit = SubmitField("Submit:")


class configForm(Form):
    catalog = TextField("NFS path for catalog:")
    submit = SubmitField("Submit")


class detailForm(Form):
    baseline = SubmitField("Baseline")
    sync = SubmitField("Sync")
    resume = SubmitField("Resume")
    verify = SubmitField("Verify")
    scan = SubmitField("Scan")
    delete = SubmitField("Delete")
    special = TextField("Special scan options:")
    special_scan = SubmitField("Special Scan")

#models
class Options(db.Model):
    __tablename__ = 'options'
    id = db.Column(db.Integer, primary_key=True)
    activated = db.Column(db.String(64))
    catalog = db.Column(db.String(256))

    def __repr__(self):
        return '<Options %r>' % self.activated


class Migrations(db.Model):
    __tablename__ = 'migrations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    source = db.Column(db.String(256))
    destination = db.Column(db.String(256))
    status = db.Column(db.String(256))

    def __repr__(self):
        return '<Migrations %r>' % self.name


#views
@app.route('/', methods=['GET', 'POST'])
def home(): 
   activated = Options.query.filter_by(activated='true').first()
   if activated is None:
       form = configForm()
       if not glob.glob("license"):
           return render_template('upload.html', what = "your license")
       if not glob.glob("*xcp*tgz") and not glob.glob("*xcp*tar"):
           return render_template('upload.html', what = "XCP")
       elif not os.path.isfile("xcp"):
           if glob.glob("*xcp*tgz"):
               xcp_file = glob.glob("*xcp*tgz")[0]
               os.popen("gunzip -d %s" % xcp_file)
           tar_file = glob.glob("*xcp*tar")[0]
           t = tarfile.open(tar_file, 'r')
           for member in t.getmembers():
               member.name = os.path.basename(member.name)
               if member.name == "xcp":
                   t.extract(member, "")
           os.popen("./xcp show localhost")
           os.popen("cp license /opt/NetApp/xFiles/xcp/")
       return redirect(url_for("config"))
   if glob.glob("*.log"):
      logs = glob.glob("*.log")
      for line in range(len(logs)):
         name = logs[line].split(".")
         fileHandle = open ( logs[line],"r" )
         lineList = fileHandle.readlines()
         fileHandle.close()
         log = Migrations.query.filter_by(name=name[0]).first_or_404()
         log.status = lineList[-1]
         db.session.commit()
   migrations = Migrations.query.order_by(Migrations.name).all()
   return render_template('home.html', migrations = migrations)


@app.route('/config', methods=['GET', 'POST'])
def config():
   form = configForm()
   if form.validate_on_submit():
       catalog = Options(catalog = form.catalog.data, activated = "true")
       print(catalog)
       db.session.add(catalog)
       db.session.commit()
       print(form.catalog.data)
       os.popen('sed -i "s/^\(catalog =\).*/catalog = %s/g" /opt/NetApp/xFiles/xcp/xcp.ini' % form.catalog.data.replace("/","\/"))
       os.popen('./xcp activate')
       return redirect(url_for('home'))
   return render_template('config.html', form = form)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
   file = request.files['file']
   #if file and allowed_file(file.filename):
   filename = secure_filename(file.filename)
   file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
   return redirect(url_for("home"))


@app.route('/add', methods=['GET', 'POST'])
def add():
   form = migrationForm()
   if form.validate_on_submit():
       migration = Migrations(name = form.name.data, source = form.source.data, destination = form.destination.data)
       db.session.add(migration)
       db.session.commit()
       os.popen('echo "Pair added" > %s.log' % form.name.data)
       return redirect(url_for('home'))
   return render_template('add.html', form = form)


@app.route('/detail/<name>', methods=['GET', 'POST'])
def detail(name):
    form = detailForm()
    migrate = Migrations.query.filter_by(name = name).first_or_404()
    if form.validate_on_submit():
        if form.scan.data:
            os.system("./xcp scan --html %s > templates/%s.html" % (migrate.source, migrate.name))
            return render_template('%s.html' % migrate.name)
        if form.baseline.data:
            os.popen("screen -S %s -d -m /bin/bash -c './xcp copy --newid %s %s %s &> %s.log && echo \"Baseline complete\" >> %s.log'" %(migrate.name, migrate.name, migrate.source, migrate.destination, migrate.name, migrate.name))
        if form.sync.data:
            os.popen("screen -S %s -d -m /bin/bash -c './xcp sync -id %s &> %s.log && echo \"Sync complete\" >> %s.log'" %(migrate.name, migrate.name, migrate.name, migrate.name))
        if form.delete.data:
            db.session.delete(migrate)
            db.session.commit()
        if form.verify.data:
            os.popen("screen -S %s -d -m /bin/bash -c './xcp verify %s %s &> %s.log'" %(migrate.name, migrate.source, migrate.destination, migrate.name))
        return redirect(url_for('home'))
    return render_template('detail.html', form = form, migrate = migrate)

if __name__ == '__main__':
    db.create_all()
    db.session.commit()
    app.run(host='0.0.0.0', debug = True)
