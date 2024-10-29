# AWS EC2 Automated Monitoring System

An automated EC2 instance monitoring system that provides tag-based monitoring, automated EBS snapshots, and CPU utilization alerts using AWS CloudFormation, Lambda, EventBridge, and CloudWatch.

## Features

- Automatic EC2 instance discovery based on tags
- CPU utilization monitoring with automated alerts
- Scheduled EBS volume snapshots
- Email notifications for system events
- Tag-based monitoring deployment
- Automatic instance reboot on high CPU usage

## Maintenance and Limitations(10/'24)
This project was created mainly as an demonstration of tools rather than a hyper-practical implementation. 
While this system can still be effective and convinient in small-scale projects for automatic basic provisioning, AWS has built-in options that would be utilized in larger projects. For example as a part of an Auto-scaling group there would be visibility in scale-in, scale-out thresholds in terms of CPU util, and have automatic restarts build into policy, as well as simply scale-in new Instances instead of reboots.

## Prerequisites

- AWS Account with appropriate permissions
- Python 3.7 or higher
- AWS CLI configured with appropriate credentials
- Boto3 library installed
- EC2 instances with appropriate tags

### Setup

1. Clone the repository:
```
git clone [repository-url]
cd aws-ec2-monitoring
```

2. Install required Python packages:
```
pip install boto3
```
- CPU utilization threshold is set to 5% by default (adjustable in template0.yaml)
- Snapshot schedule is set to 15 minutes for testing (adjustable in template3.yaml)
- All resources are tagged with a build ID for easy tracking and cleanup


## Initial Deployment

1. Run the configuration script:
```
Configure.py
```

2. When prompted, enter:
- `deploy` as the command
- A unique numerical build ID
- The environment tag value to monitor

### Monitoring Configuration

Tag your EC2 instances with:
```json
{
    "Environment": "your-environment-value"
}
```
## Cleanup

1. Run the configuration script:
```
python Configure.py
```

2. When prompted:
- Enter `cleanup` as the command
- Provide the build ID to cleanup

## Components

### 1. Configuration (`Configure.py`)
- Handles system deployment and cleanup
- Creates necessary S3 buckets
- Deploys CloudFormation stacks

### 2. Resource Discovery (`Resource_Discovery_Endpoint.py`)
- Processes EC2 instance discovery events
- Deploys monitoring based on tags
- Updates instance tracking

### 3. EBS Management (`Ebs_Scheduled.py`)
- Manages automated snapshots
- Handles instance stop/start
- Sends status notifications

### 4. CloudFormation Templates
- `template0.yaml`: Instance monitoring stack
- `template3.yaml`: Main event stack




## Security Considerations

- IAM roles follow least privilege principle, but still should be reviewed according to compliance
- Resources are isolated by build ID via Resources in IAM policy
- SNS topics require subscription confirmation
- S3 buckets that hold instance IDshave restricted access

## Troubleshooting

Common issues and solutions:

1. **Instance Not Being Monitored**
   - Verify instance tags
   - Check detailed monitoring is enabled in respective instance's settings in console
   - Review Lambda function logs for code errors

2. **Missing Snapshots**
   - Check EventBridge rule status
   - Verify Lambda execution role permissions
   - Review Lambda function logs for code errors

3. **No Notifications**
   - Confirm SNS subscription in SNS>Topics- check email
   - Check email spam folder
   - Verify SNS topic permissions, that there are no deny policies



