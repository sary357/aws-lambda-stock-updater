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

stock_url=os.getenv('TWSE_API_URL', default='https://www.twse.com.tw/exchangeReport/STOCK_DAY_AVG_ALL?re')
sender=os.getenv('SENDER', default=None)
recipients=os.getenv('MAIL_RECIPIENTS', default=None)
key_file_name=os.getenv("KEY_FILE", default='').strip()
sheet_key=os.getenv("SHEET_KET", default='1lkFBcY9TezpxHz-tEwTrgWXUlE9didAYDh0b-CnqgdI')

# SMTP Config
EMAIL_HOST = os.getenv('EMAIL_HOST', default=None)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', default=None)
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', default=None)
EMAIL_PORT = int(os.getenv('EMAIL_PORT', default=0))

def download_stock_from_url():    
    today = date.today() 
    
    try: 
        print("Download JSON from URL: " + stock_url) 
        with urllib.request.urlopen(stock_url) as f:
            response=f.read().decode('utf-8')
            json_obj=json.loads(response)
            
        if json_obj['stat'] == 'OK':
            tmp_json_obj=json_obj['data']
            return tmp_json_obj, json_obj['title'][:10][-6:].replace('月','/').replace('日','')
        else:
            return None
    except Exception as e:
        print('Failed to get info from the URL:("' +stock_url + '") Or the format of API changed.' )
        notify_by_mail("[注意!!] 今天: "+str(today)+" 無法抓取股市資訊",
        'Failed to get info from the URL:("' +stock_url + '") Or the format of API changed.',1)
        raise

def get_stock_price(stock_no, stocks_obj=None):
    if stocks_obj:
        for stock_obj in stocks_obj:
            if stock_obj[0] == str(stock_no):
                return stock_obj[2]
    else:
        return None

def gsheet(key_file='./maplocationapi01-fb349ce93ae5.json'):
    scopes = ["https://spreadsheets.google.com/feeds"]
 
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
	    key_file, scopes)
 
    client = gspread.authorize(credentials)
 
    sheet = client.open_by_key(sheet_key).worksheet('存股紀錄')
    
    stocks_info,stock_close_date=download_stock_from_url()
    
    idx=3
    while sheet.cell(idx,2).value != None and len(sheet.cell(idx,2).value)>0:
        stock_number=(sheet.cell(idx, 2).value)
        price=get_stock_price(stock_number,stocks_info)
        print('fill stock info: {}'.format(stock_number))
        if(price!=None):
            price=price.replace(',','')
            time.sleep(1)
            sheet.update_cell(idx,15, price)
            time.sleep(1)
            sheet.update_cell(idx,16, stock_close_date)
            time.sleep(1)
            
            price_float=float(price)
            price_5_percent=float(sheet.cell(idx,6).value)
            time.sleep(1)

            if price_5_percent>=price_float:
                sheet.update_cell(idx,17, 'V')
            else:
                sheet.update_cell(idx,17, '')
            time.sleep(1)
        
        idx=idx+1
        


def notify_by_mail(mail_subject, mail_body, priority=None):
    current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print('email sent out: {}'.format(mail_subject))
    if EMAIL_HOST != None and EMAIL_PORT != None:
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
        today = date.today() 
        if e.response['Error']['Code'] == "404":
            print("The object ("+data_folder+'/'+key_file_name+") does not exist.")
            notify_by_mail("[注意!!] 今天: "+str(today)+" 無法抓取 key file: "+data_folder+'/'+key_file_name,
            "The object ("+data_folder+'/'+key_file_name+") does not exist.",1)
            raise
        else:
            raise

def lambda_handler(event, context):
    # TODO implement
    # Step 1: Download google key file
    print("Step 1: download google key file")
    get_key_file_from_s3()

    # Step 2: read stock number from google spreadsheet and crawl TWSE to get stock info
    print("Step 2: read stock number from google spreadsheet and crawl TWSE to get stock info")
    gsheet('/tmp/'+key_file_name)
    
    return {
        'statusCode': 200,
        'body': json.dumps('No news is good news!')
    }

def google_spreadsheet_test():
    gsheet()

if __name__ == '__main__':
    google_spreadsheet_test()