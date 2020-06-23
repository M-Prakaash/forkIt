#!/usr/bin/env python
# coding: utf-8
# Team:ForkIT
# Members: Karthikeyan, Murali, Prakaash, Vimal.

import os,re
import pyodbc
from ftplib import FTP
###########
class file_validation:
    def __init__(self,file_id,src_name,src_server_name,src_file_path,file_name_pattern,file_element_cnt,file_delimiter, file_extension,tgt_server_name,tgt_file_path,tgt_file_name,failure_notification_email, reason,sample_file_name):
        self.file_id=file_id
        self.src_name=src_name
        self.src_server_name=src_server_name
        self.src_file_path=src_file_path
        self.file_name_pattern=file_name_pattern
        self.file_element_cnt=file_element_cnt
        self.file_delimiter =file_delimiter 
        self.file_extension=file_extension
        self.tgt_server_name=tgt_server_name
        self.tgt_file_path=tgt_file_path
        self.tgt_file_name=tgt_file_name
        self.failure_notification_email =failure_notification_email 
        self.reason=reason

    
            
    def download_file(self):
        ftp = FTP(self.src_server_name)
        ftp.login(user='u180164016.forkit_ftp', passwd = 'forkit@123')
        os.chdir(self.tgt_file_path)
        ftp.cwd(src_file_path)
        for file_name in ftp.nlst():
            if len(re.split('[\W_]',file_name)) == self.file_element_cnt:
                if re.search(self.file_name_pattern,file_name):
                    localfile = open(file_name, 'wb')
                    ftp.retrbinary('RETR ' + file_name, localfile.write, 1024)
                    localfile.close()
        ftp.quit()

########################---------Connecting to Database-----########################
conn = pyodbc.connect('Driver={SQL Server};'
                      'Server=MURALI\SQLEXPRESS;'
                      'Database=ForkIT;'
                      'Trusted_Connection=yes;')


cursor = conn.cursor()
cursor.execute('select * from etl_src where file_id = 101')


data = cursor.fetchall()

for row in data:
    file_id,src_name,src_server_name,src_file_path,file_name_pattern,file_element_cnt,file_delimiter, file_extension,tgt_server_name,tgt_file_path,tgt_file_name,failure_notification_email, reason,sample_file_name = row
    table_row = file_validation(file_id,src_name,src_server_name,src_file_path,file_name_pattern,file_element_cnt,file_delimiter, file_extension,tgt_server_name,tgt_file_path,tgt_file_name,failure_notification_email, reason,sample_file_name)

table_row.download_file()

cursor.close()
conn.close()
