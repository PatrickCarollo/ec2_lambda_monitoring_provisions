#Runs upon ec2 discovery config event, passed instance id as event input and other variables as environment.
#Created in initial launch
import boto3
import json
import yaml
from botocore.exceptions import ClientError
import os

ec2client = boto3.client('ec2')
cfclient = boto3.client('cloudformation')
snsclient = boto3.client('sns')

env_variables = os.environ

#Gets details on instance discovered
def lambda_handler(event, context):
    global instance_id
    instance_id = event['instanceid']
    global env_variables
    env_variables = os.environ
    try:
        response = ec2client.describe_instances(
            InstanceIds = [
                instance_id
            ]
        )
        if 'Reservations' in response:
            for x in response['Reservations']:
                instance = x['Instances'][0]
                data = {
                    'imageid': instance['ImageId'],
                    'instancetype': instance['InstanceType'],
                    'monitoring': instance['Monitoring'],
                    'ebsid': instance['BlockDeviceMappings'][0]['Ebs']['VolumeId'],
                    'tagvalue': instance['Tags'][0]['Value']
                }
            Provisions_Stack_Create(data)
        else:
            stack_status = 'error'
            Sns_Notification(data, stack_status)
    except ClientError as e:
        print("Client error: %s" % e)



#To deploy instance usage monitor with notifications and automated ebs snapshots
def Provisions_Stack_Create(instance_data):
    if instance_data['tagvalue'] == env_variables['specifiedtagvalue']:
        tag_match = True
        object_url = 'https://{}.s3.amazonaws.com/{}'.format('VMProvisionsResources-' + env_variables['buildid'],
        'Resources/template0')
        try:
            response = cfclient.create_stack(
                StackName = 'Ec2Provisions' + env_variables['buildid'] ,
                Capabilities = ['CAPABILITY_NAMED_IAM'],
                RoleArn = env_variables['cfrole'],
                TemplateURL = object_url,
                Tags=[
                    {
                        'Key': 'buildid',
                        'Value': env_variables['buildid']
                    }
                ],
                Parameters = [
                    {
                        'ParameterKey': 'volumeid',
                        'ParameterValue': instance_data['ebsid']
                    },
                    {
                        'ParameterKey:': 'instanceid',
                        'ParameterValue': instance_id
                    },
                    {
                        'ParameterKey:': 'buildid',
                        'ParameterValue': env_variables['buildid']
                    },

                ]
            )
            if 'StackId' in response:
                status = 'Success'
            else:
                status = 'Fail'
            data = {'tagmatched': tag_match, 'Provisions_Stack_Create_Status': status}
            Sns_Notification(instance_data, data)
        except ClientError as e:
            print("Client error: %s" % e)
    else:
        tag_match = False
        data = {'tagmatched': tag_match, 'Provisions_Stack_Create_Status': 'null'}
        Sns_Notification(instance_data, data)



#Publishes upon any instance launch discovery and sends results of provisions launch if tag is matched; 
#if not, it sends null and instance id
def Sns_Notification(instance_data, stack_status):
    message_data = {}
    Ec2_Discovery_Status = {}
    Ec2_Discovery_Status['Discovered_Instance_Details'] = instance_data
    Ec2_Discovery_Status['MonitoringservicesdeployStatus'] = stack_status
    message_data['Ec2_Discovery_Status'] = Ec2_Discovery_Status
    message_data['Function_Name'] = 'Resource_Discovery_Endpoint'
    message_data['buildid'] = env_variables['buildid']
    
    response = snsclient.publish(
        TopicArn = os.environ['topicarn'] ,
        Message = message_data
    )

