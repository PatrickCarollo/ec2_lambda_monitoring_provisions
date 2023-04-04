### An endpoint of SNS, accepts message data upon ec2 provisioning function's invokation containing execution data as json
import boto3
import json
from datetime import datetime 
s3client = boto3.client('s3')
logsclient = boto3.client('logs')



#Checks for errors then uploads message to s3 if none are found
def lambda_handler(event, context):

    message_data = event['Records'][0]['Sns']['Message']
    if ['stopped', 'error', 'failed', 'null'] in json.dumps(message_data):
        path_key = 'LambdaLogs/ErrDetectedLogs/' + message_data['function_name'] + ':'+ json.dumps(datetime.now())
        object_body = Fetch_Err_Logs(message_data['function_name'])    
    else:  
        path_key = 'LambdaLogs/SuccessLogs/' + message_data['function_name'] + ':'+ json.dumps(datetime.now())
        object_body = json.dumps(message_data)

    response = s3client.putobject(
        Bucket = 'VMProvisionsResources-' + event['build_id'],
        Key = path_key,
        Body = object_body
    )



#Fetches cloudwatch logs event upon error found in the Sns message   
def Fetch_Err_Logs(function_name):
    logsclient = boto3.client('logs')
    response = logsclient.get_log_events(
        logGroupName = 'aws/lambda/{}'.format(function_name),
        logStreamName =  Get_Stream(function_name),
        limit = 32
    )
    return response['events']



#Returns name of the most recent log stream in log group name of function
def Get_Stream(function_name):
    response = logsclient.describe_log_streams(
        logGroupName = '/aws/lambda/{}'.format(function_name),
        orderBy = 'LastEventTime',
        limit = 1,
        descending = True
    
    )
    return response['logStreams'][0]['logStreamName']