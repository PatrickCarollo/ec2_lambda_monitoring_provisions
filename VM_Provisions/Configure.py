import boto3
import json
import io
import random
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
    buildid = input('enter unique numerical multi-digit number for tag set: ')
    global tag_value 
    tag_value = input('Enter value of tag name "Environment" to deploy provisions to: ').strip()
    global confirm
    confirm = input('"' + tag_value + '"? y/n: ')
    
def Bucket_Create():
    #Creates bucket for template sources and upload destination for CW lambda logs
    try:
        response = s3client.create_bucket(
            Bucket = 'vmmonitoringsresources-' + buildid
        )
        print('Resources bucket launched: '+ 'deploymentresources-' + buildid)
        return response
    except ClientError as e:
        print("Client error: %s" % e)
        return 0


def Create_Bucket_Resources(bkt_status):
    if bkt_status != 0:
        objects = [
            'Ec2_Lambda_Monitoring_Provisions/VM_Provisions/template0.yaml',
            'Ec2_Lambda_Monitoring_Provisions/VM_Provisions/Resource_Discovery_Endpoint.py', 
            'Ec2_Lambda_Monitoring_Provisions/VM_Provisions/Ebs_Scheduled.py'
            'Ec2_Lambda_Monitoring_Provisions/VM_Provisions/Instance_Ids.json'
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
                    obj.write(x, arcname = obj_key)
                object_body.seek(0)
                object_key = zipped_name
            else:
                with open(x) as obj:
                    object_body = obj.read()         
                object_key = obj_key 
            try:
                response = s3client.put_object(
                    Bucket = 'vmmonitoringsresources-' + buildid ,
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



#Gets iam roleARNS for create_stack to assume, these are passed to necessary lambda functions
def Get_CF_Permissions(upload_status):
    if confirm == 'y': 
        role_arns = {}
        role_names = [
            'stacklambdaprovsrole',
            'stackeventec2provsrole'
        ]
    for x in role_names:
        try:
            response = iamclient.get_role(
                RoleName = x
            )
            if 'Arn' in response['Role']:
                role_arns[x] = response['Role']['Arn'].strip()
            else:
                return 0
        except ClientError as e:
            print("Client error: %s" % e)
    print(role_arns)
    return role_arns    



#Stack containing Ec2 discovery Event with Config service -template3.yaml
def Main_Event_Stack(cfroles):
    if cfroles != 0:   
        with open('Ec2_Lambda_Monitoring_Provisions/VM_Provisions/template3.yaml') as obj:
            template = obj.read()
        email = input('Enter email to recieve instance notifications at: ').strip()  
        confirmed_email = input('"' + email + '"?: y/n: ').strip()
        if confirmed_email == 'y':
            try:
                response = cfclient.create_stack(
                    StackName = 'Main-Event-Stack'+ buildid,
                    Capabilities = ['CAPABILITY_NAMED_IAM'],
                    RoleARN = cfroles['stackeventec2provsrole'],
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
                    print('EC2 Config event stack creation initiated success')
                else:
                    print('Logs stack for lambda failed to create')
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
        a = Bucket_Create()
        b = Create_Bucket_Resources(a)
        c = Get_CF_Permissions(b)
        d = Main_Event_Stack(c)
    elif command == 'cleanup':
        h = Get_Resources_For_Deletion()
        Delete_Cf_Stacks(h)
        Delete_Cf_Roles(h)
if __name__ == '__main__':
    main()