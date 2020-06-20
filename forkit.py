#!/usr/bin/env python
# coding: utf-8
# Team:ForkIT
# Members: Karthikeyan, Murali, Prakaash, Vimal.

import pyodbc
from ftplib import FTP

########################---------Connecting to Database-----########################
conn = pyodbc.connect('Driver={SQL Server};'
                      'Server=DESKTOP-RIJEQ44;'
                      'Database=AdventureWorks;'
                      'Trusted_Connection=yes;')
cursor = conn.cursor()
cursor.execute('select * from Person.CountryRegion')
for row in cursor:
    print(row);
########################---------Connecting to ftp and downloading the file-----########################
#pip install pyftpdlib
#domain name or server ip:
ftp = FTP('ftp.icrepair.in')
ftp.login(user='u180164016.forkit_ftp', passwd = 'forkit@123')
def forkIt():
    filename = 'FinancialSample.xlsx'
    localfile = open(filename, 'wb')
    ftp.retrbinary('RETR ' + filename, localfile.write, 1024)
    ftp.quit()
    localfile.close()
forkIt()