import boto3
import json
import io
import random
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED
from botocore.exceptions import ClientError
snsclient = boto3.client('sns')
lambdaclient = boto3.client('lambda')
eventclient = boto3.client('events')
iamclient = boto3.client('iam')
s3client = boto3.client('s3')
cfclient = boto3.client('cloudformation')

command = input('deploy/cleanup: ')



#Sets global variables for setup of resources
def Set_Variables():
    global buildid
    buildid = input('enter unique numerical multi-digit number for tag set')
    global tag_value 
    tag_value = input('Enter value of tag name "Environment" to deploy provisions to: ').strip()
    global confirm
    confirm = input('"' + tag_value + '"? y/n: ')
    


#Gets iam roleARNS for create_stack to assume, these are passed to necessary lambda functions

def Get_CF_Permissions():
    if confirm == 'y': 
        role_arns = {}
        role_names = [
            'stacklambdaprovsrole',
            'stackeventforec2role'
        ]
    for x in role_names:
        try:
            response = iamclient.get_role(
                RoleName = x
            )
            if 'Arn' in response['Role']:
                role_arns[x] = response['Role']['Arn'].strip()
                return role_arns
            else:
                return 0
        except ClientError as e:
            print("Client error: %s" % e)
    return role_arns    



#Stack containing Ec2 discovery Event with Config service
def Main_Event_Stack(cfroles):
    if cfroles != 0:   
        with open('Ec2_Lambda_Monitoring_Provisions/VM_Provisions/template3.yaml') as obj:
            template = obj.read()
        email = input('Enter email to recieve instance notifications at: ').strip()  
        confirmed_email = input('"' + email + '"?: y/n')
        if confirmed_email == 'y':
            try:
                response = cfclient.create_stack(
                    StackName = 'Main-Event-Stack'+ buildid,
                    Capabilities = ['CAPABILITY_NAMED_IAM'],
                    RoleARN = cfroles['stackeventforec2role'],
                    TemplateBody = template,
                    Parameters = [
                        {
                            'ParameterKey': 'buildid',
                            'ParameterValue': buildid
                        },
                        {
                            'ParameterKey': 'specifiedtagvalue',
                            'ParameterValue': tag_value
                        },
                        {
                            'ParameterKey': 'personalemail',
                            'ParameterValue': email
                        }
                    ]
                )
                if 'StackId' in response:
                    data = response['StackId']
                    print('launched stack for lambda execution lgos')
                else:
                    print('Logs stack for lambda failed to create')
                    data = 0
                return data
            except ClientError as e:
                print('Client error: %s' % e)    



#Creates bucket for template source and upload destination for CW lambda logs
def Create_Bucket_Resources(stack_status):
    if stack_status != 0:
        objects = [
            'Ec2_Lambda_Monitoring_Provisions//VM_Provisions/template0.yaml',
            'Ec2_Lambda_Monitoring_Provisions//VM_Provisions/Ebs_Scheduled.py',
            'Ec2_Lambda_Monitoring_Provisions//VM_Provisions/template2.yaml',
            'Ec2_Lambda_Monitoring_Provisions//VM_Provisions/SnsEndpoint_LogsUploader.py' ,
            'Ec2_Lambda_Monitoring_Provisions//VM_Provisions/Resource_Discovery_Endpoint.py' 
        ]    
        successes = []
        for x in objects:
            index1 = x.find('/')
            index2 = x.find('/',index1+1)
            obj_key = x[index2+1:]
            if '.py' in obj_key:
                integ = obj_key.find('.py')
                zipped_name = obj_key[:integ] + '.zip'
                object_body = io.BytesIO()
                with ZipFile(object_body,'w',ZIP_DEFLATED) as obj:
                    obj.write(x, arcname = 'testfile.py')
                object_body.seek(0)
                object_key = zipped_name
            else:
                with open(x) as obj:
                    object_body = obj.read()         
                object_key = obj_key 
            try:
                response = s3client.put_object(
                    Bucket = 'vmprovisionsresources-' + buildid ,
                    Body = object_body , 
                    Key = 'Resources/'+ object_key
                )
                if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                    print('object resource upload status: success '+ object_key)
                    data = successes.append(response['ResponseMetadata']['HTTPStatusCode'])
                else: 
                    data = 0
            except ClientError as e:
                print('Client error: %s' % e) 
    else:
        print('failed at subscribe SNS')
        return data

 

#Launches stack containing logs manager function, event for monitoring lambdas and iam permissions
#template1
def Diagnostics_Stack(cfroles, upload_status):
    if upload_status != 0:
        with open('Ec2_Lambda_Monitoring_Provisions//VM_Provisions/template1.yaml') as templateobj:
            template = templateobj.read()
        try:
            response = cfclient.create_stack(
                StackName = 'CWLogsUpload'+ buildid,
                Capabilities = ['CAPABILITY_NAMED_IAM'],
                TemplateBody = template,
                RoleArn = cfroles['stacklambdaprovsrole'],
                Tags = [
                    {
                        'Key': 'buildid',
                        'Value': buildid
                    }
                ],
                Parameters = [
                    {
                        'ParameterKey': 'buildid',
                        'ParameterValue': buildid
                    },
                    {
                        'ParameterKey': 'specifiedtagvalue',
                        'ParameterValue': tag_value 
                    }
                ]
            )
            if 'StackId' in response:
                data = response['StackId']
                print('launched stack for lambda execution logs')
            else:
                print('Provisions stack for lambda failed to create')
                data = 0
            return data
        except ClientError as e:
            print('Client error: %s' % e)    



#Returns roles and stack ARNs in a dict that is used to delete them
def Get_Resources_For_Deletion():
    taggingclient = boto3.client('resourcegroupstaggingapi')
    buildid_tag_val = input('Enter numerical digit buildid tag value to cleanup assosiated resources: ').strip()
    resources = {}
    types = [['cloudformation:stack'], ['iam:role']]
    for x in types:
        try:
            response = taggingclient.get_resources( 
                ResourceTypeFilters = x,
                TagFilters = [
                    {
                        'Key': 'buildid',
                            'Values': [ buildid_tag_val]
                    }
                ]
            )
            resources[x[0]] = response
        except ClientError as e:
            print('Client error: %s' % e)        
    print(resources)
    return resources    



#slices out identifiers and deletes
def Delete_Cf_Stacks(resources):
    if resources != 0:
        for x in resources['cloudformation:stack']['ResourceTagMappingList']:
            data = x['ResourceARN']
            index1 = data.find('/')
            index2 = data.find('/',index1+1)
            stack_name = data[data.index('/')+1: index2]
            try:
                response = cfclient.delete_stack(
                    StackName = stack_name,
                )
                if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                    print('Stack resource successfully deleted')
            except ClientError as e:
                print('Client error: %s' % e)        



#slices out identifiers and deletes
def Delete_Cf_Roles(resources):
    for x in resources['iam:role']['ResourceTagMappingList']:
        data = x['ResourceARN']
        role_name = data[data.index('/')+1:]
        try:
            response = iamclient.delete_role(
                RoleName = role_name
            )
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                print('iam roles successfully deleted')
        except ClientError as e:
            print('Client error: %s' % e)        



def main():    
    if command == 'deploy':
        Set_Variables()
        q = Get_CF_Permissions()
        a = Main_Event_Stack(q)
        o = Create_Bucket_Resources(a)
        Diagnostics_Stack(q,o)
    elif command == 'cleanup':
        h = Get_Resources_For_Deletion()
        Delete_Cf_Stacks(h)
        Delete_Cf_Roles(h)
if __name__ == '__main__':
    main()