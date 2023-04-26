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
env_variables = os.environ


#event as input from EventBridge trigger- details of instance discovered
def lambda_handler(event, context):
    try:
        instance_data = {}
        instance_data['instance_id'] = event['instance_id']
        instance_data['ec2_tags'] = event['ec2_tags']
        instance_data['instance_type'] = event['instance_type']
        instance_data['image_id'] = event['image_id']
        instance_data['detailedmonitoring'] = event['detailedmonitoring']
        instance_data['configuration_details'] = event['configuration_details']
    except:
        instance_data = 'failed to parse instance data from event'
        status = {}
        status['UtilAlarmDeploy'] = 'null'
        status['UpdateIDsList'] = 'null'
        Sns_Notification(instance_data, status)  
    print(event)
    if instance_data['ec2_tags']['Environment'] == env_variables['specified_tag_value']:
        print('tagmatch')
        instance_data['TagMatched'] = True
        Provisions_Stack_Create(instance_data)
    else:
        instance_data['TagMatched'] = False
        status = {}
        status['UtilAlarmDeploy'] = 'null'
        status['UpdateIDsList'] = 'null'
        Sns_Notification(instance_data, status)


#Gets template for monitoring services; a cpu util alarm 
def Get_Template(instance_data):
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
        print('Retrieved s3 template object for util. alarm setup')
        return data
    except ClientError as e:
        print("Client error: %s" % e)
        status = {}
        status['UtilAlarmDeploy'] = 'null'
        status['UpdateIDsList'] = 'null'
        Sns_Notification(instance_data, status) 



#To deploy instance usage monitor with notifications and automated ebs snapshots
def Provisions_Stack_Create(instance_data):
    object_body = Get_Template(instance_data)
    if instance_data['detailedmonitoring'] == 'enabled':
        try:
            for x in instance_data['configuration_details']:
                if x['resourceType'] == 'AWS::EC2::Volume':
                    global volumeid
                    volumeid = x['resourceId']
            response = cfclient.create_stack(
                StackName = 'Ec2Provisions' + env_variables['buildid'] + instance_data['instance_id'],
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
                        'ParameterValue': volumeid
                    },
                    {
                        'ParameterKey': 'instanceid',
                        'ParameterValue': instance_data['instance_id']
                    },
                    {
                        'ParameterKey': 'buildid',
                        'ParameterValue': env_variables['buildid']
                    },
                    {
                        'ParameterKey': 'tagvalue',
                        'ParameterValue': instance_data['ec2_tags']['Environment']
                    }                    
                ]
            )
        except ClientError as e:
            print("Client error: %s" % e)
            status = {}
            status['UtilAlarmDeploy'] = 'failed'
            status['UpdateIDsList'] = 'null'
            Sns_Notification(instance_data, status)
        status = {}
        status['UtilAlarmDeploy'] = 'success'
        Get_Instances_Object(instance_data, status)
        status['UpdateIDsList'] = 'success'
        Sns_Notification(instance_data, status)
    else:
        print('Instance not being monitored')
        status = {}
        status['UtilAlarmDeploy'] = 'failed- monitoring not enabled'
        status['UpdateIDsList'] = 'null'
        Sns_Notification(instance_data, status)
        

#Gets json list object from s3 containing instance ids to run scheduled logic upon
def Get_Instances_Object(instance_data, status):
    try:
        response = s3client.get_object(
            Bucket = 'vmmonitoringsresources-009009',
            Key = 'Resources/Instance_Ids.json'
        )
        print('get_object for instance ids successful')
        body = response['Body'].read().decode('utf-8')
        Put_Object(instance_data, body, status)
    except ClientError as e:
        print("Client error: %s" % e)
        status = {}
        status['UpdateIDsList'] = 'failed'
        Sns_Notification(instance_data, status)        


#Adds new instance details to list and uploads to s3
def Put_Object(instance_data, instance_list_object, status):
    new_ids = {}
    new_ids['instanceid'] = instance_data['instance_id']
    new_ids['volumeid'] = volumeid
    existing_instanceid_list = json.loads(instance_list_object)
    existing_instanceid_list['instanceids'].append(new_ids)
    print(existing_instanceid_list)
    instanceid_object = json.dumps(existing_instanceid_list)
    try:    
        response = s3client.put_object(
            Body = instanceid_object,
            Bucket = 'vmmonitoringsresources-009009',
            Key = 'Resources/Instance_Ids.json'
        )
        print('Updated list for instanceids at: '+ 'Resources/Instance_Ids.json')
    except ClientError as e:
        print("Client error: %s" % e)
        status['UpdateIDsList'] = 'failed'
        Sns_Notification(instance_data, status)        



#Publishes upon any instance launch discovery and sends results of provisions launch if tag is matched; 
#if not, it sends null and instance id
def Sns_Notification(instance_data, status):
    try:
        message_data = {}
        message_data['Ec2_Discovery_Details'] = instance_data
        message_data['Ec2_Monitoring_Provision'] = status
        message_data['Function_Name'] = 'Resource_Discovery_Endpoint'
        message_data['buildid'] = env_variables['buildid']
        
        response = snsclient.publish(
            TopicArn = env_variables['topicarn'],
            Message = json.dumps(message_data)
        )
        return message_data
    except ClientError as e:
        print("Client error: %s" % e)