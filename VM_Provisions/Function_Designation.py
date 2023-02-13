#Target of create_function cloudtrail event, gets passed the function's ARN that was created and it's tag value
#along with environment variables.
#creates a stack that assigns the discovered function to either be an endpoint of Sns 
#and accept event data from ec2 provisions event functions for system monitoring functions
import boto3
import os

cfclient = boto3.client('cloudformation')
snsclient = boto3.client('sns')


def lambda_handler(event):
    env_variables = os.environ
    response = cfclient.create_stack(
        StackName = 'FunctionAssisgnment',
        Capabilities = ['CAPABILITY_NAMED_IAM'],
        RoleArn = env_variables['cfrole'],
        TemplateURL = 'https://' + 'VMProvisionsResources-'+ env_variables['buildid']+'\
        .s3.amazonaws.com/Resources/template2',
        Tags = [
            {
                'Key': 'buildid',
                'Value': env_variables['buildid']
            }
        ],
        Parameters = [
            {
                'invokationtag': event['tag'],
                'newfunctionarn': event['newfunctionarn'],
                'topicarn': env_variables['topicarn'],
                'buildid': env_variables['buildid']
            }
        ]
    )
    if 'StackId' in response:
        result = 'success'
    else:
        result = 'fail'
    
    data = {}
    function = {}
    function['newfunctionARN'] = event['newfunctionarn']
    function['newfunctionTag'] = event['tag']
    function['functionStackStatus'] = result
    data['discoveredLambdaInfo'] = function
    data['Function_Name'] = 'Function_Designation'
        
    Sns_Notification(data, env_variables['topicarn'])
#posts to topic, the results of this function
def Sns_Notification(message_data, topic) :
    response = snsclient.publish(
        TopicArn = topic ,
        Message = message_data
    )