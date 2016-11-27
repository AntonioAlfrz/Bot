import sqlite3

table_name = 'APPOINTMENTS'
db = None
connection = None
date_format = "%H:%M - %d/%m/%Y"


def create_table(user):
    global db
    global connection
    db = sqlite3.connect(user + ".sql")
    connection = db.cursor()
    connection.execute('CREATE TABLE IF NOT EXISTS '+table_name+' (DATE INT, TIME INT, NAME TEXT)')


def insert(user, fecha, hora, text):
    create_table(user)
    connection.execute("INSERT INTO "+table_name+" (date,time,name) VALUES (?,?,?)", (fecha, hora, text))
    db.commit()
    db.close()


def query(user, date):
    create_table(user)
    my_list = []
    for row in connection.execute("SELECT * FROM " + table_name+" WHERE date=?", (date,)):
        print row
        my_list.append(row)
    db.close()
    return my_list


def all(user):
    create_table(user)
    my_list = ["Calendario:"]
    for row in connection.execute("SELECT * FROM "+table_name):
        print row
        my_list.append(row)
    db.close()
    return my_list


def delete(user, date):
    create_table(user)
    connection.execute("DELETE FROM " + table_name + " WHERE date=?", (date,))
    db.commit()
    db.close()
