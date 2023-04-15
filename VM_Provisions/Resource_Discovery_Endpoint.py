#Runs upon ec2 discovery config event, passed instance id as event input and other variables as environment.
#Created in initial launch
import boto3
import json
from botocore.exceptions import ClientError
import os

ec2client = boto3.client('ec2')
cfclient = boto3.client('cloudformation')
snsclient = boto3.client('sns')
s3client = boto3.client('s3')
dbclient = boto3.client('dynamodb')
env_variables = os.environ


#Gets details on instance discovered
def lambda_handler(event, context):

    try:

        instance_data = {}
        instance_data['instance_id'] = event['instance_id']
        instance_data['ec2_tags'] = event['ec2_tags']
        instance_data['instance_type'] = event['instance_type']
        instance_data['image_id'] = event['image_id']
        instance_data['detailedmonitoring'] = event['detailedmonitoring']
        instance_data['volume_data'] = event['volume_data']
        
        Provisions_Stack_Create(instance_data)
    except:
        stack_status = 'null'
        instance_data = 'failed to parse instanced data from event'
        Sns_Notification(instance_data, stack_status)        
        

def Get_Template():
    try:
        object_data = env_variables['bucketkey']
        ind = object_data.find('/')
        bucket_name = object_data[:ind]
        key = object_data[ind+1:]
        
        response = s3client.get_object(
            Bucket = bucket_name,
            Key = key
        )
        data = response['Body'].read().decode('utf-8')
        return data
    except ClientError as e:
        print("Client error: %s" % e)
        stack_status = 'null'
        Sns_Notification(data, stack_status) 




#To deploy instance usage monitor with notifications and automated ebs snapshots
def Provisions_Stack_Create(instance_data):
    if instance_data['ec2_tags'] == env_variables['specified_tag_value']:
        object_body = Get_Template()
        try:
            response = cfclient.create_stack(
                StackName = 'Ec2Provisions' + env_variables['buildid'] ,
                Capabilities = ['CAPABILITY_NAMED_IAM'],
                RoleARN = env_variables['cfrole'],
                TemplateBody = object_body,
                Tags = [
                    {
                        'Key': 'buildid',
                        'Value': env_variables['buildid']
                    }
                ],
                Parameters = [
                    {
                        'ParameterKey': 'volumeid',
                        'ParameterValue': instance_data['volume_data']
                    },
                    {
                        'ParameterKey': 'instanceid',
                        'ParameterValue': instance_data['instance_id']
                    },
                    {
                        'ParameterKey': 'buildid',
                        'ParameterValue': env_variables['buildid']
                    }
                ]
            )
            stack_data = {'tagmatched': True, 'Begin_Ec2_Provisions_Stack': True}
            Sns_Notification(instance_data, stack_data)
            Update_Instances_Object(instance_data)
        except ClientError as e:
            print("Client error: %s" % e)
            stack_data = {'tagmatched': True, 'Begin_Ec2_Provisions_Stack': False}
            Sns_Notification(instance_data, stack_data)
    else:
        stack_data = {'tagmatched': False}
        Sns_Notification(instance_data, stack_data)



def Update_Instances_Object(instance_data):

    try:
        #TODO:update table api
        )
        
    
    


#Publishes upon any instance launch discovery and sends results of provisions launch if tag is matched; 
#if not, it sends null and instance id
def Sns_Notification(instance_data, stack_status):
    try:
        message_data = {}
        Ec2_Discovery_Details = {}
        Ec2_Discovery_Details['Discovered_Instance_Details'] = instance_data
        Ec2_Discovery_Details['MonitoringservicesdeployStatus'] = stack_status
        message_data['Ec2_Discovery_Details'] = Ec2_Discovery_Details
        message_data['Function_Name'] = 'Resource_Discovery_Endpoint'
        message_data['buildid'] = env_variables['buildid']
        
        response = snsclient.publish(
            TopicArn = env_variables['topicarn'],
            Message = json.dumps(message_data)
        )
        return message_data
    except ClientError as e:
        print("Client error: %s" % e)