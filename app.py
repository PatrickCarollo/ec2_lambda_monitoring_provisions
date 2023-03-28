#my sample lambda app code
import boto3
import json
import random
import os
import base64
s3client = boto3.client('s3')

def lambda_handler(event, context):
    #Accessing bucket name from this Lambda's environment variables
    env_variables = os.environ
    bkt_name = env_variables['userbucket'].strip()
    table_name = env_variables['usertable'].strip()
    #parsing request data
    object_name = event['queryStringParameters']['name'].strip()
    ids = event['queryStringParameters']['id'].strip()
    user= event['queryStringParameters']['user'].strip()
    body_data = event['body']
    #Creating dict for uploads
    request_data = {}
    request_data['bkt_name'] = bkt_name
    request_data['table_name'] = table_name
    request_data['name'] = object_name
    request_data['id'] = ids
    request_data['user'] = user 
    request_data['body_data'] = body_data
    x = Image_Storage(request_data)
    if x != False:
        y = DB_Write(request_data, x)
        if y != False:
            response_data = {
                'ObjectLocation': x,
                'DatabaseUpdated': json.dumps(y)
            }
        else:
            response_data = 'Error.. database write item fail'
    else:
        response_data = 'Error.. put_object for image fail'
    #Main response 
    main_response_object = {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps(response_data)
    }
    return main_response_object #end
    


def Image_Storage(request_data):
    key = 'Images/' + request_data['name']+ '.txt'
    response = s3client.put_object(
        Body = request_data['body_data'],
        Bucket = request_data['bkt_name'],
        Key = key
    )
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        
        data = request_data['bkt_name'] + '/' + key
    else:
        data = False
    return data



def DB_Write(request_data, s3_key):
    dbclient = boto3.client('dynamodb')
    response = dbclient.put_item(
        TableName = request_data['table_name'],
        Item = {
            'name': { 'S': request_data['name']},
            'id': {'S': request_data['id']},
            'user': {'S': request_data['user']},
            'itempath': {'S': s3_key}
        }
    )
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        data = True
    else:
        data = False
    return data 
        