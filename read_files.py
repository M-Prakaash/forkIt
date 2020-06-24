# -*- coding: utf-8 -*-
"""
Created on Wed Jun 24 01:55:35 2020

@author: welcome
"""
import os
import json
import pandas as pd 

os.chdir('E:\Developement\Projects\ForkIT')
dataframe1 = pd.read_excel('telus.xlsx')
print(dataframe1.dtypes)
columns_list  = list(dataframe1.columns.values)
print(columns_list)
with open('telus.json') as json_file:
    data = json.load(json_file)
    # print (len(data["target_files"]["$BASENAME.csv"]["content"]["sheets"]))
    # print (len(data["target_files"]["$BASENAME.csv"]["content"]["columns"]))
    source_columns_list = []
    with open('out.txt', 'w') as f:
        for content in data['target_files']['$BASENAME.csv']['content']['columns']:
           source_columns_list.append(content['find'])
    print(source_columns_list)
    if len(columns_list)==len(source_columns_list):
        if columns_list==source_columns_list:
            print ('Columns are matching')
        else:
            print('columns are not matching')