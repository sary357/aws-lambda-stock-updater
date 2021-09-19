import os
from datetime import datetime,timedelta,date
import urllib.request 
import boto3
import botocore

import smtplib
import sys
import json

import gspread
import time
from oauth2client.service_account import ServiceAccountCredentials

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


bucket=os.getenv('S3_BUCKET_NAME', default='')
data_folder=os.getenv('DATA_FOLDER', default=None)

stock_url=os.getenv('TWSE_API_URL', default='http://www.twse.com.tw/exchangeReport/STOCK_DAY_AVG?response=json&date=DATE&stockNo=STOCK_NUMBER&_=CURRENT_TIME')
sender=os.getenv('SENDER', default=None)
recipients=os.getenv('MAIL_RECIPIENTS', default=None)
key_file_name=os.getenv("KEY_FILE", default='').strip()
sheet_key=os.getenv("SHEET_KET", default='1lkFBcY9TezpxHz-tEwTrgWXUlE9didAYDh0b-CnqgdI')

# SMTP Config
EMAIL_HOST = os.getenv('EMAIL_HOST', default=None)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', default=None)
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', default=None)
EMAIL_PORT = int(os.getenv('EMAIL_PORT', default=0))

def download_stock_from_url(stock_number, diff_date=0):    
    yesterday = date.today() - timedelta(diff_date)
    str_yesterday=yesterday.strftime('%Y%m%d')
    current_time=datetime.utcnow()
    try:
        destination_url=stock_url.replace("CURRENT_TIME",current_time.strftime('%s'))
        destination_url=destination_url.replace("DATE", str_yesterday)
        destination_url=destination_url.replace("STOCK_NUMBER", str(stock_number))
        
        print("Download JSON from URL: " + destination_url) 
        with urllib.request.urlopen(destination_url) as f:
            response=f.read().decode('utf-8')
            json_obj=json.loads(response)
            
        if json_obj['stat'] == 'OK':
            tmp_json_obj=json_obj['data']
            max=''
           # print(tmp_json_obj)
            for stock_info in tmp_json_obj:
                if stock_info[0] > max and (stock_info[0][0:2].isnumeric() ):
                    max=stock_info[0]
            for stock_info in tmp_json_obj:
                if stock_info[0] == max:
                    return stock_info
            return None
        else:
            return None
    except Exception as e:
        print('Failed to get info from the URL:("' +destination_url + '") Or the format of API changed.' )
        notify_by_mail("[注意!!] "+current_time+" 無法抓取股市資訊",
        'Failed to get info from the URL:("' +stock_url + '") Or the format of API changed.',1)
        raise

def gsheet(key_file='./maplocationapi01-fb349ce93ae5.json'):
    scopes = ["https://spreadsheets.google.com/feeds"]
 
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
	    key_file, scopes)
 
    client = gspread.authorize(credentials)
 
    sheet = client.open_by_key(sheet_key).worksheet('存股紀錄')
    
    idx=3
    while sheet.cell(idx,2).value != None:
        stock_number=(sheet.cell(idx, 2).value)
        stock_info=download_stock_from_url(stock_number=stock_number)
        if(stock_info!=None):
            date, price=download_stock_from_url(stock_number=stock_number)
            time.sleep(1)
            sheet.update_cell(idx,15, price)
            time.sleep(1)
            sheet.update_cell(idx,16, date[-5:])
            time.sleep(1)
        
        idx=idx+1
        
    sheet.format('o3:p100' ,{'textFormat':{"foregroundColor": {
        "red": 0,
        "green": 0,
        "blue": 0
      }}})
        

def notify_by_mail(mail_subject, mail_body, priority=None):
    current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msg = MIMEText(mail_body+'\n* This report is generated at '+current_time)
    msg['Subject'] = mail_subject
    msg['From'] = sender
    msg['To'] = recipients
    if priority != None and int(priority) >=1 and int(priority)<=5:
        msg['X-Priority'] = str(priority)
   
    s = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
    s.starttls()
    s.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
    s.send_message(msg)
    s.quit()
    
def get_key_file_from_s3():
    s3=boto3.resource('s3')
    try: 
        bucketObj=s3.Bucket(bucket)
        bucketObj.download_file(data_folder+'/'+key_file_name,'/tmp/'+key_file_name)
        print("key file downloaded: {}{}".format('/tmp/', key_file_name))
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object ("+data_folder+'/'+key_file_name+") does not exist.")
            return None
        else:
            raise

def lambda_handler(event, context):
    # TODO implement
    # Step 1: Download google key file
    print("Step 1:")
    get_key_file_from_s3()

    # Step 2: read stock number from google spreadsheet and crawl TWSE to get stock info
    print("Step 2:")
    gsheet('/tmp/'+key_file_name)
    
    return {
        'statusCode': 200,
        'body': json.dumps('No news is good news!')
    }

def google_spreadsheet_test():
    gsheet()

if __name__ == '__main__':
    google_spreadsheet_test()