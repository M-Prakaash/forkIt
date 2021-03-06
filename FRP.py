#!/usr/bin/env python
# coding: utf-8
# Team:ForkIT
# Members: Karthikeyan, Murali, Prakaash, Vimal.

import os
import re
import pyodbc
from ftplib import FTP
import json
import pandas as pd
import logging
import shutil
import time
import boto3
from datetime import datetime
import hashlib
from mail import EmailProcessor


"""log = r"E:\Developement\Projects\ForkIT\LogDir\fork_it_" + \
    time.strftime("%Y%m%d-%H%M%S")+".log"
logging.basicConfig(filename=log, level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
"""
log = r"E:\Developement\Projects\ForkIT\LogDir\fork_it_mail_" + \
    time.strftime("%Y%m%d-%H%M%S")+".log"
logging.basicConfig(filename=log, level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s: %(message)s', datefmt='%d/%m/%Y %H:%M:%S')



class file_validation:
    def __init__(
        self,
        file_id,
        src_name,
        src_server_name,
        src_file_path,
        file_name_pattern,
        file_element_cnt,
        file_delimiter,
        file_extension,
        tgt_server_name,
        tgt_file_path,
        tgt_file_name,
        failure_notification_email,
        work_directory,
        transform_spec_json,
        sample_file_name
        
    ):
        self.file_id = file_id
        self.src_name = src_name
        self.src_server_name = src_server_name
        self.src_file_path = src_file_path
        self.file_name_pattern = file_name_pattern
        self.file_element_cnt = file_element_cnt
        self.file_delimiter = file_delimiter
        self.file_extension = file_extension
        self.tgt_server_name = tgt_server_name
        self.tgt_file_path = tgt_file_path
        self.tgt_file_name = tgt_file_name
        self.failure_notification_email = failure_notification_email
        self.work_directory = work_directory
        self.transform_spec_json = transform_spec_json
        
    def lt_files_entry(self,file_name,checksum,error_descr,file_size,file_row_count):
        try:
            sql = "insert into forkit.dbo.lt_files values(NEXT VALUE FOR file_batch_key,'"+file_name+"','"+checksum+"','"+self.src_name+"','"+error_descr+"',"+str(file_size)+","+str(file_row_count)+",CURRENT_TIMESTAMP)"
            #sql = 'insert into lt_files values(NEXT VALUE FOR file_batch_key,'+file_name+','+checksum+','+self.src_name+','+str(file_size)+','+str(file_row_count)+',CURRENT_TIMESTAMP)'
            #sql = 'select count(*) from etl_src'
            #print(sql)
        except Exception as e:
            logging.error(e)
        return sql
                    

    def columns_validation(self, file_name):
        logging.info("columns_validation for file : "+file_name)
        os.chdir(self.work_directory)
        if self.file_extension == 'xlsx':
            dataframe1 = pd.read_excel(file_name)
        elif self.file_extension == 'xlsx':
            dataframe1 = pd.read_csv(file_name)
        elif self.file_extension == 'json':
            dataframe1 = pd.read_json(file_name)
        else:
            logging.error('Invalid file extension')
        checksum = hashlib.md5(open(file_name,'rb').read()).hexdigest()
        try:
            cur = conn.cursor()
            cur.execute("select count(*) from forkit.dbo.lt_files where file_checksum = '"+checksum+"'")
            for row in cur:
                if row[0] != 0:
                    error_descr = 'File already processed'
                else:
                    error_descr = ''
            #print(error_descr)
        except Exception as e:
            logging.error(e)
        file_size = os.stat(file_name).st_size
        file_row_count = len(dataframe1.index)
        columns_list = list(dataframe1.columns.values)
        # print(columns_list)
        with open(self.transform_spec_json) as json_file:
            data = json.load(json_file)
            # print (len(data["target_files"]["$BASENAME.csv"]["content"]["sheets"]))
            # print (len(data["target_files"]["$BASENAME.csv"]["content"]["columns"]))
            source_columns_list = []
            for content in data["target_files"]["$BASENAME.xlsx"]["content"]["columns"]:
                source_columns_list.append(content["find"])
            # print(source_columns_list)
            if len(columns_list) == len(source_columns_list):
                if columns_list == source_columns_list:
                    logging.info("Columns are matching")
                    sql = self.lt_files_entry(file_name,checksum,error_descr,file_size,file_row_count)
                    return sql,error_descr
                else:
                    logging.error("Columns are not matching")
                    return False,'error'

    def download_file(self):
        error_descr = ''
        isFileAvailable = 0
        ftp = FTP(self.src_server_name)
        ftp.login(user="u180164016.forkit_ftp", passwd="forkit@123")
        logging.info("Logged into FTP "+self.src_server_name+" successfully")
        os.chdir(self.work_directory)
        ftp.cwd(src_file_path)
        for file_name in ftp.nlst():
            if len(re.split(r"[\W_]", file_name)) == self.file_element_cnt:
                if re.search(self.file_name_pattern, file_name):
                    isFileAvailable = 1
                    localfile = open(file_name, "wb")
                    ftp.retrbinary("RETR " + file_name, localfile.write, 1024)
                    localfile.close()
                    sql,error_descr = self.columns_validation(file_name)
                    if(sql):
                        try:
                            cursor1 = conn.cursor()
                            cursor1.execute(sql)
                            cursor1.close()
                        except Exception as e:
                            logging.error(e)
                        if error_descr== '':
                            shutil.copy(file_name, self.tgt_file_path)
                        else:
                            
                            logging.info(file_name+": already processed hence placed in the target directory")
                        os.remove(file_name)    
                    else:
                        logging.error(
                            file_name+": is not placed in the target directory due to columns mismatch")
            error_descr = ''

        if isFileAvailable == 0:
            logging.info("No files matched the defined global pattern")
        ftp.quit()
        
        
    def download_S3_File(self):
        #connect to s3
        client = boto3.resource('s3', aws_access_key_id=CONFIG["email_aws_access_key_id"],aws_secret_access_key=SECRETS["email_aws_secret_access_key"])
        #used for downloading
        s3 = boto3.client('s3', aws_access_key_id=CONFIG["email_aws_access_key_id"],aws_secret_access_key=SECRETS["email_aws_secret_access_key"])
        bucket = client.Bucket(CONFIG["bucket"])
        folder = self.src_file_path
        error_descr = ''
        for cList in bucket.objects.filter(Prefix=folder):
            cFiles= cList.key
            pattern = self.src_file_path+self.file_name_pattern
            if len(re.split(r"[\W_]", cFiles)) == self.file_element_cnt:
                if re.search(pattern, cFiles):
                    try:
                        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
                        file_name = run_timestamp+self.tgt_file_name
                        os.chdir(self.work_directory)
                        s3.download_file(CONFIG["bucket"],cFiles,file_name)
                        #checksum = hashlib.md5(open(file_name,'rb').read()).hexdigest()
                        sql,error_descr = self.columns_validation(file_name)
                        if(sql):
                            try:
                                cursor2 = conn.cursor()
                                cursor2.execute(sql)
                                cursor2.close()
                            except Exception as e:
                                logging.error(e)
                            if error_descr == '':
                                shutil.copy(file_name, self.tgt_file_path)
                                logging.info(file_name+": is placed in the target directory")
                            else:
                                
                                logging.info(file_name+": already processed hence placed in the target directory")
                            os.remove(file_name)
                            
                        else:
                            logging.error(
                            file_name+": is not placed in the target directory due to columns mismatch")
                    except Exception as e:
                        logging.error(e)
            error_descr = ''
    
   


########################---------Connecting to Database-----########################

#conneting to the SQL server for lookup table
try:
    conn = pyodbc.connect('Driver={SQL Server};'
                      'Server=MURALI\SQLEXPRESS;'
                      'Database=ForkIT;'
                      'Trusted_Connection=yes;')
    logging.info("Connetion to the DB (Server=MURALI\SQLEXPRESS, Database=ForkIT) successfully ")
except Exception:
    logging.error("Counln't connect to DB (Server=MURALI\SQLEXPRESS, Database=ForkIT)")
    

try:
	cursor = conn.cursor()
	cursor.execute("select * from forkit.dbo.etl_src where src_name ='FTP1' ")
	data = cursor.fetchall()
	for row in data:
		(
			file_id,
			src_name,
			src_server_name,
			src_file_path,
			file_name_pattern,
			file_element_cnt,
			file_delimiter,
			file_extension,
			tgt_server_name,
			tgt_file_path,
			tgt_file_name,
			failure_notification_email,
			work_directory,
			transform_spec_json,
			sample_file_name,
		) = row
		table_row = file_validation(
			file_id,
			src_name,
			src_server_name,
			src_file_path,
			file_name_pattern,
			file_element_cnt,
			file_delimiter,
			file_extension,
			tgt_server_name,
			tgt_file_path,
			tgt_file_name,
			failure_notification_email,
			work_directory,
			transform_spec_json,
			sample_file_name,
		)
		table_row.download_file()
	
	cursor.close()

except Exception as e:
	logging.error(e)
    

############################### Downloading files from mail #######################################



SECRETS = {
    "email_aws_secret_access_key": '****************************'
}

CONFIG = {
    "email_rules_file": r"E:\Developement\Projects\ForkIT\email_rules.json",
    "email_s3_inbox_url": "s3://fork-it-mail/Mails",
    "email_s3_attachment_dir": "INBOX",
    "email_aws_access_key_id": "AKIAI6RU7O6X54HDDFTQ",
    "bucket": 'fork-it-mail'
    
}
results = []

try:
    email_proc = EmailProcessor(
            CONFIG["email_rules_file"],
            CONFIG["email_s3_inbox_url"],
            CONFIG["email_s3_attachment_dir"],
            CONFIG["email_aws_access_key_id"],
            SECRETS["email_aws_secret_access_key"])
    
    results = email_proc.check_mail(update=True)
except Exception as e:
    logging.error(e)
    
try:
	cursor = conn.cursor()
	cursor.execute("select * from forkit.dbo.etl_src where src_name ='S3' ")
	data = cursor.fetchall()
	for row in data:
		(
			file_id,
			src_name,
			src_server_name,
			src_file_path,
			file_name_pattern,
			file_element_cnt,
			file_delimiter,
			file_extension,
			tgt_server_name,
			tgt_file_path,
			tgt_file_name,
			failure_notification_email,
			work_directory,
			transform_spec_json,
			sample_file_name,
		) = row
		table_row = file_validation(
			file_id,
			src_name,
			src_server_name,
			src_file_path,
			file_name_pattern,
			file_element_cnt,
			file_delimiter,
			file_extension,
			tgt_server_name,
			tgt_file_path,
			tgt_file_name,
			failure_notification_email,
			work_directory,
			transform_spec_json,
			sample_file_name,
		)
		table_row.download_S3_File()
	
	cursor.close()

except Exception as e:
	logging.error('Error while downloading files from FTP: '+e)
conn.commit()
conn.close()
