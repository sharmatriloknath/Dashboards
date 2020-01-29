# from odoo import models, fields, api
# import pyodbc
# import psycopg2
# import datetime
# from datetime import timedelta
# import sys
# from odoo.exceptions import UserError, AccessError, ValidationError
# import pprint
#
#
# sys.setrecursionlimit(1500)
# class MachineRawPunch(models.Model):
#
#     _name = "machine.raw.punch"
#
#     machine_raw_punch_id=fields.Integer(String='Machine Punch')
#     card_no=fields.Integer("card no")
#     punch_datetime=fields.Datetime(string="Punch Datetime")
#     p_day=fields.Char("P day")
#     is_manual=fields.Char("Is Manual")
#     pay_no=fields.Char()
#     machine_code=fields.Integer(string="Machine Code")
#     date_time=fields.Datetime("datetime")
#     connection_status=False
#     try:
#         conn = pyodbc.connect(
#             'Driver={/opt/microsoft/msodbcsql17/lib64/libmsodbcsql-17.3.so.1.1};Server=localhost;Database=test;UID=SA;PWD=Trilok@123')
#         print("what connection returns",conn)
#         connection_status=True
#         print("Connection Established successfully:.................")
#         cursor = conn.cursor()
#         # record = []
#     except Exception as e:
#         sql_name=type(e).__name__
#         sql_message=str(e)
#         print("The SQL server is not running right now")
#
#
#     try:
#         connection = psycopg2.connect(user="priyanka",
#                                       password="Trilok@123",
#                                       host="127.0.0.1",
#                                       port="5432",
#                                       database="arke_2may")
#         print('Connection establish successfully')
#         cur = connection.cursor()
#         # Print PostgreSQL Connection properties
#         print(connection.get_dsn_parameters(), "\n")
#
#         def process_demo_scheduler_queue(self):
#             print("schedular is ready")
#             print("Schedular is running........................")
#             self.check_last_run_status()
#             if (self.connection):
#                 self.connection.commit()
#             #     self.cur.close()
#             #     self.connection.close()
#             #     self.cursor.close()
#             #     self.conn.close()
#
#     except (Exception, psycopg2.Error) as error:
#         print("The name of exception is {}: and the message is {}:".format(type(error.__name__,str(error))))
#         print("Error while connecting to PostgreSQL", error)
#         raise Exception(error)
#
#     def check_server_is_running_or_not(self,runtime):
#         print("Check wheather server is running or not if not what is the error")
#         if self.connection_status==False:
#             Error_query="insert into attendance_error(process_name,run_time,error_name,error_message) values('%s','%s','%s','%s')"%('SQL server not running',runtime,
#                                                                                                                                     self.sql_name,str(self.sql_message).replace("'","''"))
#             self.cur.execute(Error_query)
#             print("Insertion is successfull errors got inserted")
#             if (self.connection):
#                 self.connection.commit()
#                 # self.connection.close()
#                 raise ValidationError("You are not connected with Server(SQL SERVER)")
#             exit()
#
#
#
#     def check_last_run_status(self):
#         print("wel come to this first function")
#
#         query = 'select last_run,interval from process_model'
#         self.cur.execute(query)
#         record = self.cur.fetchone()
#         f_datetime = record[0]
#         interval_time = record[1]
#         from_datetime=datetime.datetime.strptime(f_datetime,'%Y-%m-%d %H:%M:%S')
#         print(from_datetime.second)
#         to_datetime = from_datetime + timedelta(days=interval_time)
#         current_date = datetime.datetime.now()
#         if current_date > to_datetime:
#             runtime = datetime.datetime.now()
#             self.get_data(runtime, from_datetime, to_datetime)
#         queryupdate = "UPDATE process_model SET last_run = '%s', next_run = '%s'"%(to_datetime,to_datetime)
#         self.cur.execute(queryupdate)
#         return True
#
#     def get_data(self,runtime, from_datetime, to_datetime):
#         print("wel come to the get functioon")
#         # f_date = from_datetime.strftime('%Y-%m-%d %H:%M:%S')
#         # t_date = to_datetime.strftime('%Y-%m-%d %H:%M:%S')
#         # r_time = runtime
#         print("helloooooooooooooooooooooooooooo",from_datetime,to_datetime,from_datetime.strftime('%Y-%m-%d %H:%M:%S'))
#         self.check_server_is_running_or_not(runtime)
#         query3 = "select count(*) from machinerawpunch where Dateime1 > '%s' and Dateime1 <= '%s'" %(from_datetime.strftime('%Y-%m-%d %H:%M:%S'),to_datetime.strftime('%Y-%m-%d %H:%M:%S'))
#         # query3="SELECT count(*) FROM machinerawpunch where Dateime1>'2018-05-10 14:19:34' and Dateime1<='2018-05-12 14:24:34';"
#         self.cursor.execute(query3)
#         count1 = self.cursor.fetchval()
#         print("count after fetching",count1)
#         if count1 > 0:
#             record=[]
#             self.cursor.execute("SELECT * FROM machinerawpunch where Dateime1 > '%s' and Dateime1 <= '%s'" %(from_datetime.strftime('%Y-%m-%d %H:%M:%S'),to_datetime.strftime('%Y-%m-%d %H:%M:%S')))
#             row = self.cursor.fetchall()
#             for r in row:
#                 t = (
#                     r[0], r[1], (r[2]).strftime('%Y-%m-%d %H:%M:%S'), r[3], r[4], 'NULL' if r[5] is None else r[5],
#                     r[6],
#                     (r[7]).strftime('%Y-%m-%d %H:%M:%S'))
#                 record.append(t)
#             print(record)
#             self.get_insertion(runtime, count1, from_datetime, to_datetime,record)
#         return True
#
#
#     def get_insertion(self,runtime, count1, from_datetime, to_datetime,record):
#         print("record hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",record)
#
#         for row in record:
#             att_id = self.env['machine.raw.punch'].search_count([('machine_raw_punch_id','=',row[0]),('punch_datetime','=',row[2])])
#             print("already exists data inside postgrel database",att_id)
#             if att_id:
#                 continue
#             query4 = "insert into machine_raw_punch(machine_raw_punch_id,card_no,punch_datetime,p_day,is_manual,pay_no,machine_code,date_time) values(%s,%s,%s,%s,%s,%s,%s,%s)"
#             self.cur.executemany(query4, [row])
#         print("Insertion is successful...................................................")
#         query5 = "select count(*) from machine_raw_punch where date_time > '%s' and date_time <= '%s'"  %(from_datetime.strftime('%Y-%m-%d %H:%M:%S'),to_datetime.strftime('%Y-%m-%d %H:%M:%S'))
#         self.cur.execute(query5)
#         count2 = self.cur.fetchone()
#         print("count 2 after insertion into postgrel",count2[0])
#
#         status_up=''
#         if count1 != count2[0]:
#             status_up = 'Failed'
#             raise ValidationError("The data is not copied and inserted properly")
#         else:
#             status_up = str('success')
#         print ("staus uppppppppppppppppppppp",status_up,type(status_up))
#         query6 = "insert into attendance_logging(runtime,from_time,to_time,previous_table_data,current_table_data,status1) values ('%s','%s','%s',%s,%s,'%s')"%(runtime.strftime('%Y-%m-%d %H:%M:%S.%f'), from_datetime.strftime('%Y-%m-%d %H:%M:%S'), to_datetime.strftime('%Y-%m-%d %H:%M:%S'), count1, count2[0], status_up)
#         self.cur.execute(query6)
#         return True
#
#
# class AttendanceLogging(models.Model):
#
#     _name = 'attendance.logging'
#     runtime=fields.Datetime("Run Time")
#     from_time=fields.Datetime("from time")
#     to_time=fields.Datetime("to time")
#     previous_table_data=fields.Integer("SQL table data")
#     current_table_data=fields.Integer("current table data")
#     status=fields.Char("Status")
#     status1 = fields.Char("Status")
#
#
#
# class ProcessMaster(models.Model):
#
#     _name = "process.model"
#     process_name=fields.Char('process name')
#     last_run=fields.Datetime("last run")
#     next_run=fields.Datetime("next run")
#     interval=fields.Integer("how much time schedular run")
#
#
# class AttendanceError(models.Model):
#
#     _name = "attendance.error"
#
#     process_name=fields.Char("process name")
#     run_time=fields.Datetime("run time")
#     error_code=fields.Integer("error code")
#     error_message=fields.Char("error message")
#     error_name=fields.Char("error name")
