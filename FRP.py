# -*- coding: utf-8 -*-
"""
Created on Sun Jun 21 09:17:21 2020

@author: Murali
"""
#!/usr/bin/env python
# coding: utf-8
# Team:ForkIT
# Members: Karthikeyan, Murali, Prakaash, Vimal.

import os
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
        self.sample_file_name=sample_file_name
    
    def download_file(self):
        ftp = FTP(self.src_server_name)
        ftp.login(user='u180164016.forkit_ftp', passwd = 'forkit@123')
        os.chdir(self.tgt_file_path)
        ftp.cwd(src_file_path)
        localfile = open(sample_file_name, 'wb')
        ftp.retrbinary('RETR ' + sample_file_name, localfile.write, 1024)
        ftp.quit()
        localfile.close()


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

########################---------Connecting to ftp and downloading the file-----########################
#pip install pyftpdlib
#domain name or server ip:
