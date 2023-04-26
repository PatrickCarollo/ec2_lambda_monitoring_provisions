#Function created as target of event that is launched upon ec2 tag match. Runs on an EventB schedule
#send its results to sns topic
import boto3
import json
import time
import os
from botocore.exceptions import ClientError

ec2client = boto3.client('ec2')
snsclient = boto3.client('sns')
s3client = boto3.client('s3')


#TODO: create loop functionality
def lambda_handler(event, context):

    global variables
    variables = os.environ
    a = Get_List()
    instances_data_list = json.loads(a)
    #begin running logic on instance list data
    response_object = []
    for x in instances_data_list['instanceids']:
        Stop_Instance(x['instanceid'])

        snapshot_state = Create_Snapshot(x['volumeid'])
        start_status = Start_Instance(x['instanceid'])
        stati = {}
        stati['instance'] = x['instanceid']
        stati['snapshotstatus'] = snapshot_state
        stati['startinstansestatus'] = start_status
        response_object.append(stati)
    Sns_Notification(instances_data_list, response_object)
        

def Create_Snapshot(volumeid):
    try:
        response = ec2client.create_snapshot(
            VolumeId = volumeid
        )    
        state = response['State'] 
        print(state)
        return state
    except ClientError as e:
        print('Client error: %s' % e)


def Get_List():
    response = s3client.get_object(
        Bucket = 'vmmonitoringsresources-009009',
        Key = 'Resources/Instance_Ids.json'
    )
    print('get_object for instance ids successful')
    body = response['Body'].read().decode('utf-8')
    print(body)
    return body
    

def Stop_Instance(instanceids):
    try:
        while True:
            response = ec2client.stop_instances(
                InstanceIds = [instanceids]
            )
            status = response['StoppingInstances'][0]['CurrentState']['Name']
            if status != 'stopped':
                print(response)
                time.sleep(16)
            else:
                print(response)
                break
    except ClientError as e:
        print('Client error: %s' % e)



def Start_Instance(instanceids):
    
    try:
        response = ec2client.start_instances(
            InstanceIds = [instanceids]
        )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            status = response['StartingInstances'][0]['CurrentState']['Name']
            return status
    except ClientError as e:
        print('Client error: %s' % e)



def Sns_Notification(instance_data,status):
    print(status)
    message_data = {}
    message_data['Status'] = status
    message_data['buildid'] = variables['buildid']
    message_data['function_name'] = 'Ebs_Scheduled'

    try:
        response = snsclient.publish(
            TopicArn = 'arn:aws:sns:us-east-1:143865003029:VmMonitoring', 
            Message = json.dumps(message_data)        
        )
        print(message_data)
    except ClientError as e:
        print('Client error: %s' % e)
