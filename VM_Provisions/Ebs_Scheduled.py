#Function created as target of event that is launched upon ec2 tag match. Runs on a schedule
#send its results to sns topic
import boto3
import json
import time
import os
from botocore.exceptions import ClientError

ec2client = boto3.client('ec2')
snsclient = boto3.client('sns')



#
def lambda_handler(event, context):
    global event
    event = event
    global variables
    variables = os.environ
    try:
        instance_status = Stop_Instance()
        if instance_status == 'stopped':
            response = ec2client.create_snapshot(
                VolumeId = variables['volumeid']
            )    
            time.sleep(10)   
            data = response['State'] 
            if data == 'pending' or data == 'completed':
                Start_Instance(data)
            else:
                Sns_Notification(instance_status, response['State'] )
        else:
            time.sleep(10)
            Stop_Instance()    
    except ClientError as e:
        print('Client error: %s' % e)
        

        
def Stop_Instance():
    try:
        response = ec2client.stop_instances(
            InstanceIds = [event['instanceid']]
        )
        status = response['StoppingInstances'][0]['CurrentState']['Name']
        return status
    except ClientError as e:
        print('Client error: %s' % e)



def Start_Instance(snapshot_status):
    try:
        
        response = ec2client.start_instances(
            InstanceIds = [
            event['instanceid']
            ] 
        )
        status = response['StartingInstances'][0]['CurrentState']['Name']
        Sns_Notification(snapshot_status, status)
    except ClientError as e:
        print('Client error: %s' % e)



def Sns_Notification(snapshot_status, serverstart_status):
    message_data = {}
    Status = {}
    Status['VolumeId'] = variables['volumeid']
    Status['ScheduledSnapshotDeploymentState'] = snapshot_status
    Status['Instance_State'] = serverstart_status
    message_data['Status'] = Status
    message_data['buildid'] = variables['buildid']
    message_data['function_name'] = 'Ebs_Scheduled'

    try:
        response = snsclient.publish(
            TopicArn = variables['topicarn'], 
            Message = json.dumps(message_data)        
        )
    except ClientError as e:
        print('Client error: %s' % e)


