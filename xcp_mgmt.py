import glob
import os
import sqlite3 as sql

def kill():
    name = raw_input("Migration pair job to cancel")
    os.popen("screen -X -S %s quit" % name)
    menu()


def jobs():
    cur.execute("select * from `migration`")
    results = cur.fetchall()
    for line in range(len(results)):
        name = results[line][0]
        source = results[line][1]
        destination = results[line][2]
        print("%s: %s -> %s" % (name, source, destination))
    raw_input("\nPress Enter to continue")
    menu()


def status():
    if not glob.glob('*.log'):
        print("No status to report")    
    status_file = glob.glob('*.log')
    for line in range(len(status_file)):
        name = status_file[line].split(".")
        fileHandle = open ( status_file[line],"r" )
        lineList = fileHandle.readlines()
        fileHandle.close()
        print("%s: %s" % (name[0], lineList[-1]))
    raw_input("\nPress Enter to continue")
    menu()


def verify():
    name = raw_input("Migration pair to verify: ")
    cur.execute("select * from `migration` where `name` like '%s'" % name)
    results = cur.fetchall()
    source = results[0][1]
    destination = results[0][2]
    os.popen("screen -S %s -d -m /bin/bash -c 'xcp verify %s %s &> %s.log && echo \"Verify complete\" >> %s.log'" %(name, source, destination, name, name))
    menu()


def resume():
    name = raw_input("Migration pair to resume: ")
    cur.execute("select * from `migration` where `name` like '%s'" % name)
    results = cur.fetchall()
    source = results[0][1]
    destination = results[0][2]
    os.popen("screen -S %s -d -m /bin/bash -c 'xcp resume -id %s'" %(name, name))
    menu()


def sync():
    name = raw_input("Migration pair to sync: ")
    cur.execute("select * from `migration` where `name` like '%s'" % name)
    results = cur.fetchall()
    source = results[0][1]
    destination = results[0][2]
    os.popen("screen -S %s -d -m /bin/bash -c 'xcp sync -id %s &> %s.log && echo \"Sync complete\" >> %s.log'" %(name, name, name, name))
    menu()


def baseline():
    name = raw_input("Migration pair to baseline: ")
    cur.execute("select * from `migration` where `name` like '%s'" % name)
    results = cur.fetchall()
    source = results[0][1]
    destination = results[0][2]
    os.popen("screen -S %s -d -m /bin/bash -c 'xcp copy --newid %s %s %s &> %s.log && echo \"Baseline complete\" >> %s.log'" %(name, name, source, destination, name, name))
    menu()


def add():
    name = raw_input("Name for migration pair: ")
    source = raw_input("Source NFS path: ")
    destination = raw_input("Destination NFS path: ")
    cur.execute("insert into `migration` (`name`,`source`,`destination`) values('%s','%s','%s')" % (name, source, destination))
    os.system("xcp scan -stats %s" % source)
    menu()


def menu():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("XCP Management")
    print("\n")
    print("1. Add migration pair")
    print("2. Baseline migration pair")
    print("3. Sync migration pair")
    print("4. Resume interupted migration pair operation")
    print("5. Verify migration pair copy")
    print("6. View status report")
    print("7. View configured migration pairs")
    #print("\n")
    selection = raw_input("Selection: ")
    if selection == "1":
        add()
    elif selection == "2":
        baseline()
    elif selection == "3":
        sync()
    elif selection == "4":
        resume()
    elif selection == "5":
        verify()
    elif selection == "6":
        status()
    elif selection == "7":
        jobs()
    elif selection == "kill":
        kill()

if __name__ == '__main__':
    dbname = 'xcp.sqlite'
    con = sql.connect(dbname)
    con.row_factory = sql.Row
    cur = con.cursor()
    cur.execute("create table if not exists `migration` (`name` text,`source` text,`destination` text)")
    cur.execute("create table if not exists `options` (`activated` text,`catalog` text)")
    
    cur.execute("select * from `options`")
    results = cur.fetchall()
    if len(results) < 1:
        cur.execute("insert into `options` (`activated`,`catalog`) values('false','nfsserver:/share')")
        print ("Default options set")
    cur.execute("select * from `options`")
    results = cur.fetchall()
    for line in range(len(results)):
        activated = results[line][0]
        if activated == "false":
            print("Not yet configured")
            catalog = raw_input("\nFull NFS path to Catalog: ")
            os.popen("screen -d -m xcp activate")
            cur.execute("update `options` set `catalog` = '%s'" % catalog)
            catalog = catalog.replace("/","\/")
            os.popen('sed -i "s/^\(catalog =\).*/catalog = %s/g" /opt/NetApp/xFiles/xcp/xcp.ini' % catalog)
            os.rename("license", "/opt/NetApp/xFiles/xcp/license")
            os.popen("screen -d -m xcp activate")
            cur.execute("update `options` set `activated` = 'true'")
    menu()
    con.commit()
