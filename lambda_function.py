import os
from datetime import datetime,timedelta,date
import urllib.request 
import boto3
import botocore

import smtplib
import sys
import json


from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

bucket=os.environ['S3_BUCKET_NAME']
data_folder=os.environ['DATA_FOLDER']
stock_url=os.environ['TWSE_API_URL']

sender=os.environ['SENDER']
recipients=os.environ['MAIL_RECIPIENTS']
key_file_name=os.environ["KEY_FILE"].strip()

# SMTP Config
EMAIL_HOST = os.environ['EMAIL_HOST']
EMAIL_HOST_USER = os.environ['EMAIL_HOST_USER']
EMAIL_HOST_PASSWORD = os.environ['EMAIL_HOST_PASSWORD']
EMAIL_PORT = int(os.environ['EMAIL_PORT'])

def download_stock_from_url(stock_number, diff_date=0):
######################################################################
######################################################################
    
    result_dic={}
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
            return None;
    except Exception as e:
        print('Failed to get info from the URL:("' +destination_url + '") Or the format of API changed.' )
        notify_by_mail("[注意!!] "+current_time+" 無法抓取股市資訊",
        'Failed to get info from the URL:("' +stock_url + '") Or the format of API changed.',1)
        raise

    
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
        key_file = open('/tmp/'+key_file_name, 'r')
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object ("+data_folder+'/'+key_file_name+") does not exist.")
            return None
        else:
            raise

def lambda_handler(event, context):
    # TODO implement
    download_stock_from_url('2882')
    get_key_file_from_s3()
    return {
        'statusCode': 200,
        'body': json.dumps('No news is good news!')
    }
