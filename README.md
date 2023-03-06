 # Ec2_Lambda_Monitoring_Provisions
Set of scripts that deploy automated compute service provisioning based on specific event parameters.


(2/12/23 Currently in proof of concept state only. Will be executable on any AWS account soon.)
OUTLINE:
To be deployed in AWS VPC for scalable provisioning that monitors and logs Ec2 and Lambda
in the context of this infrastructure.
It does this by first creating an an AWS Config EventBridge Ec2 discovery rule based on tag values
with a Lambda function as a target. This target function deploys
10 a stack of resources consisting of a Ec2 CPU util monitor and a schedule-based EBS lambda snapshot function. 
Both send their execution results to an Sns topic with a user-inputed Email subscribed. Along with these
resources, in the initial deployment, a CloudTrail event meant for scalablity to detect any 
new functions created for this project is also deployed.
This event has it's own Lambda target that designates the newly created function based on tag value;
either an event-triggered function and adds it to Ec2 EventBridge rule target as a main provision,
or as an SNS endpoint function and subscribes it to the SNS Topic to aggregate/filter or have 
automated responses based on the received execution details.


Prerequisites & run instructions:

1. Create IAM roles for Cloudformation stack creation using CLI commands provided in repository.

2. Run "Instance_Provisioning-py" with a "deploy" input command, and follow input prompts

3. Run Test_Resources_Launch.py and view if resources were correctly configured with monitoring provisions

#Provided email should recieve info data upon any success/fail action once deployed.







Notable limitations:

In deployed Cloudwatch Event, Ec2 instance restarts upon meeting utilization threshold:
    This action is there for ease of testing and has a narrow practical use outside outside of use with EC2 autoscaling group.

Cloudformation create_stack upon every matching new function discovery Cloudtrail event trigger:
    This may not be the most efficient or scalable compared to an update_stack but
    for the context of this project creating a new stack requires the least developmental work for simple testing


-Architected and developed by Patrick Carollo
