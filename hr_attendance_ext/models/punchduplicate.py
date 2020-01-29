from odoo import models, fields, api
import pyodbc
import psycopg2
import datetime
from datetime import timedelta
import sys
from odoo.exceptions import UserError, AccessError, ValidationError
import pprint


sys.setrecursionlimit(1500)
class MachineRawPunch(models.Model):

    _name = "machine.raw.punch"

    machine_raw_punch_id=fields.Integer(String='Machine Punch')
    card_no=fields.Integer("card no")
    punch_datetime=fields.Datetime(string="Punch Datetime")
    p_day=fields.Char("P day")
    is_manual=fields.Char("Is Manual")
    pay_no=fields.Char()
    machine_code=fields.Integer(string="Machine Code")
    date_time=fields.Datetime("datetime")
    connection_status=False
    # conn=None

    def check_server_is_running_or_not(self,connection,runtime):
        print("Check wheather server is running or not if not what is the error")
        if self.connection_status==False:
            cur = connection.cursor()
            Error_query="insert into attendance_error(process_name,run_time,error_name,error_message) values('%s','%s','%s','%s')"%('SQL server not running',runtime,
                                                                                                                  self.sql_name,str(self.sql_message).replace("'","''"))
            cur.execute(Error_query)
            print("Insertion is successfull errors got inserted")
            if (connection):
                connection.commit()
                # self.connection.close()
                raise ValidationError("You are not connected with Server(SQL SERVER)")
            exit()

    def process_demo_scheduler_queue(self):
        print("schedular is ready")
        print("Schedular is running........................")
        try:
            conn = pyodbc.connect(
                'Driver={/opt/microsoft/msodbcsql17/lib64/libmsodbcsql-17.3.so.1.1};Server=localhost;Database=test;UID=SA;PWD=Trilok@123')
            # self.conn=conn
            print("what connection returns", conn)
            self.connection_status = True
            print("Connection Established successfully:.................")
            cursor = conn.cursor()
            # # record = []
        except Exception as e:
            self.sql_name = type(e).__name__
            self.sql_message = str(e)
            print("The SQL server is not running right now")

        try:
            connection = psycopg2.connect(user="priyanka",
                                          password="a",
                                          host="127.0.0.1",
                                          port="5432",
                                          database="ARKE_NOV")
            print('Connection establish successfully')
            cur = connection.cursor()
            # # Print PostgreSQL Connection properties
            print(connection.get_dsn_parameters(), "\n")
        except (Exception, psycopg2.Error) as error:
            print("The name of exception and the message is {}:".format(str(error)))
            print("Error while connecting to PostgreSQL", error)
            raise Exception(error)
        self.check_last_run_status(conn,connection)
        if connection:
            connection.commit()
            cur.close()
            connection.close()
            cursor.close()
            conn.close()

    def check_last_run_status(self,conn,connection):
        print("wel come to this first function")

        query = 'select last_run,interval from process_model'
        cur=connection.cursor()
        cur.execute(query)
        record = cur.fetchone()
        f_datetime = record[0]
        interval_time = record[1]
        from_datetime=datetime.datetime.strptime(f_datetime,'%Y-%m-%d %H:%M:%S')
        print("the from date is",from_datetime)
        print(from_datetime.second)
        to_datetime = from_datetime + timedelta(days=interval_time)
        current_date = datetime.datetime.now()
        print("how are you peoplessssssssssssssssssss")
        if current_date > to_datetime:
            runtime = datetime.datetime.now()
            print("how are you peoplessssssssssssssssssss")
            # self.check_server_is_running_or_not(connection,runtime)
            self.get_data(conn,connection,runtime, from_datetime,to_datetime)
            queryupdate = "UPDATE process_model SET last_run = '%s', next_run = '%s'"%(to_datetime,to_datetime)
            cur.execute(queryupdate)
        return True

    def get_data(self,conn,connection,runtime, from_datetime,to_datetime):
        print("wel come to the get functioon")
        # f_date = from_datetime.strftime('%Y-%m-%d %H:%M:%S')
        # t_date = to_datetime.strftime('%Y-%m-%d %H:%M:%S')
        # r_time = runtime
        print("helloooooooooooooooooooooooooooo",from_datetime,to_datetime,from_datetime.strftime('%Y-%m-%d %H:%M:%S'))
        cursor=conn.cursor()
        # query3 = "select count(*) from machinerawpunch where Dateime1 > '%s' and Dateime1 <= '%s'" %(from_datetime.strftime('%Y-%m-%d %H:%M:%S'),to_datetime.strftime('%Y-%m-%d %H:%M:%S'))
        query3="SELECT count(*) FROM machinerawpunch where Dateime1>'2017-12-21 10:44:48' and Dateime1<='2019-11-02 11:08:32';"
        cursor.execute(query3)
        count1 = cursor.fetchval()
        print("count after fetching",count1)
        if count1 > 0:
            record=[]
            # cursor.execute("SELECT * FROM machinerawpunch where Dateime1 > '%s' and Dateime1 <= '%s'" %(from_datetime.strftime('%Y-%m-%d %H:%M:%S'),to_datetime.strftime('%Y-%m-%d %H:%M:%S')))
            cursor.execute("SELECT * FROM machinerawpunch where Dateime1>'2017-12-21 10:44:48' and Dateime1<='2019-11-02 11:08:32';")
            row = cursor.fetchall()
            for r in row:
                t = (
                    r[0], r[1], (r[2]).strftime('%Y-%m-%d %H:%M:%S'), r[3], r[4], 'NULL' if r[5] is None else r[5],
                    r[6],
                    (r[7]).strftime('%Y-%m-%d %H:%M:%S'))
                record.append(t)
            print(record)
            self.get_insertion(connection,runtime, count1, from_datetime, to_datetime,record)
        return True


    def get_insertion(self,connection,runtime, count1, from_datetime, to_datetime,record):
        print("record hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",record)
        status_up = ''
        count2=0
        count3=0

        try:
            cur=connection.cursor()
            for row in record:
                att_id = self.env['machine.raw.punch'].search_count([('machine_raw_punch_id','=',row[0]),('punch_datetime','=',row[2])])
                print("already exists data inside postgrel database",att_id)
                if att_id:
                    continue
                query4 = "insert into machine_raw_punch(machine_raw_punch_id,card_no,punch_datetime,p_day,is_manual,pay_no,machine_code,date_time) values(%s,%s,%s,%s,%s,%s,%s,%s)"
                cur.executemany(query4, [row])

            print("Insertion is successful...................................................")
            # query5 = "select count(*) from machine_raw_punch where date_time > '%s' and date_time <= '%s'"  %(from_datetime.strftime('%Y-%m-%d %H:%M:%S'),to_datetime.strftime('%Y-%m-%d %H:%M:%S'))
            query5 = "select count(*) from machine_raw_punch where date_time > '2017-12-21 10:44:48' and date_time <= '2019-11-02 11:08:32'"
            cur.execute(query5)
            count = cur.fetchone()
            if count:
                count2 = count[0]
            print("count 2 after insertion into postgrel",count2)
            print("count 2 after insertion into postgrel", count1)
            count3 = count1 - count2
            print('count1 type',type(count1), type(count2),type(count3))


            print('count33333',count3)

            # print(a)
            # status_up = ''
            # status_up=''
            if count1 != count2:
                status_up = 'Failed'
                # raise ValidationError("The data is not copied and inserted properly")
                error_message = 'The data is not copied and inserted properly'
                print('suuuuuuuulllllll111111111111')
                query8 = "insert into attendance_error(process_name,run_time,error_name,error_message,sql_count,postgresql_count,error_count) values ('%s','%s','%s','%s','%s','%s','%s')" % (
                    'Insertion Error', runtime.strftime('%Y-%m-%d %H:%M:%S.%f'),'Count Error', error_message, count1, count2,count3)
                cur.execute(query8)
                print('suuuuuuuulllllll')
            else:
                status_up = str('success')
            print ("staus uppppppppppppppppppppp",status_up,type(status_up))
            # query6 = "insert into attendance_logging(runtime,from_time,to_time,previous_table_data,current_table_data,status1) values ('%s','%s','%s',%s,%s,'%s')"%(runtime.strftime('%Y-%m-%d %H:%M:%S.%f'), from_datetime.strftime('%Y-%m-%d %H:%M:%S'), to_datetime.strftime('%Y-%m-%d %H:%M:%S'), count1, count2[0], status_up)
            # cur.execute(query6)

        except Exception as e:
            name = type(e).__name__
            message = str(e)
            print('hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh',name,message)
            query7 = "insert into attendance_error(process_name,run_time,error_name,error_message,sql_count,postgresql_count,error_count) values ('%s','%s','%s','%s','%s','%s','%s')" % (
            'Insertion Error',runtime.strftime('%Y-%m-%d %H:%M:%S.%f'),name,message, count1, count2,count3)
            cur.execute(query7)

        query6 = "insert into attendance_logging(runtime,from_time,to_time,previous_table_data,current_table_data,status1) values ('%s','%s','%s',%s,%s,'%s')" % (
        runtime.strftime('%Y-%m-%d %H:%M:%S.%f'), from_datetime.strftime('%Y-%m-%d %H:%M:%S'),
        to_datetime.strftime('%Y-%m-%d %H:%M:%S'), count1, count2, status_up)
        cur.execute(query6)
        # print(a)
        return True



class AttendanceLogging(models.Model):

    _name = 'attendance.logging'
    runtime=fields.Datetime("Run Time")
    from_time=fields.Datetime("from time")
    to_time=fields.Datetime("to time")
    previous_table_data=fields.Integer("SQL table data")
    current_table_data=fields.Integer("current table data")
    status=fields.Char("Status")
    status1 = fields.Char("Status")



class ProcessMaster(models.Model):

    _name = "process.model"
    process_name=fields.Char('process name')
    last_run=fields.Datetime("last run")
    next_run=fields.Datetime("next run")
    interval=fields.Integer("how much time schedular run")


class AttendanceError(models.Model):

    _name = "attendance.error"

    process_name=fields.Char("process name")
    run_time=fields.Datetime("run time")
    error_code=fields.Integer("error code")
    error_message=fields.Char("error message")
    error_name=fields.Char("error name")
    sql_count=fields.Integer("sql fetching count")
    postgresql_count=fields.Integer("postgresql count")
    error_count=fields.Integer("error count")
