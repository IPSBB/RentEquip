import pyodbc
from flask import Blueprint, request
import logging

logging.basicConfig(level=logging.DEBUG)

connection = Blueprint('connection', __name__, template_folder='templates')


def connect_to_qbd():
    con = pyodbc.connect('DSN=Quickbooks Data;')
    return ([con, {"Status": 200, "Message": "Connection Check to Quickbooks Successful"}])


def close_connection_to_qbd(con):
    con.close()


@connection.route('/QBD/test_connection')
def test_QBD_Connection():
    try:
        # print("Hi i m inside try block")
        data = connect_to_qbd()
        # print("Hi", data[0])
        # print("Hi", data[1])
        return data[1]

    except Exception as e:
        # print (e)
        data = 0
        # print ("In Exception")
        return ({"Status": 404, "Message": "Connection Check to Quickbooks Unsuccessful"})

    finally:
        # print("Hi i m inside final block")
        if data != 0:
            close_connection_to_qbd(data[0])
