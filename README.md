# AutoAWS

A Python script that requests a spot EC2 instance. Use InstanceId to control the instance.

## Prerequisites

* Python 3
* [Boto 3](https://boto3.readthedocs.io/en/latest/)
* [AWS CLI](https://aws.amazon.com/cli/)

## Setup

### Boto 3 [Install](https://boto3.readthedocs.io/en/latest/guide/quickstart.html#installation)

<pre>
$ pip install boto3
</pre>

### AWS CLI Configure

* Create Access Key for Your AWS Account. Instructions can be found at https://docs.aws.amazon.com/general/latest/gr/managing-aws-access-keys.html

* Configure AWS CLI using AWS Access Key ID and AWS Secret Access Key
  * <pre>$ aws configure</pre>
  * <pre>AWS Access Key ID [None]: 'ACCESS_KEY_ID'
    AWS Secret Access Key [None]: 'SECRET_ACCESS_KEY'
    Default region name [None]:'Region'
    Default output format [None]: ENTER</pre>

* To use multiple profiles set the system environment `AWSACC` with the name of the profile in `.aws/config`

## Configuration File

List of a configure fields

* `tag`: Name of the instance
* `team`, `created_by`, `application`: extra tags
* `ami`: AMI_ID - Get the appropriate AMI ID for your region from http://aws.amazon.com/amazon-linux-ami/
* `key_pair`: Named keypair on EC2 for instance creation
* `security_group`: Named security_group on EC2 for instance creation
* `max_bid`: Max bid price for spot instance. Current bid prices can be found at https://aws.amazon.com/ec2/spot/pricing/
* `type`: Type of EC2 instance. List can be found at https://aws.amazon.com/ec2/instance-types/
* `availability_zone`: AvailablityZone code (eg. 'us-west-1a'). List of regions can be found at https://docs.aws.amazon.com/general/latest/gr/rande.html#ec2_region
* `subnet_id`" subnet id for the AZ
* `product_description`: 'Linux/UNIX' or 'Windows'
* `public_ip` Public IP you want to attach (can leave blank)
* `iam_role` ARN of IAM role for instance (can leave blank)

\*Refer to `example-config.cfg` file.

You can add user data by creating a `userdata.txt` file.

## Request EC2 Spot Instance

```
from ec2 import AutoEC2
ec2 = AutoEC2()

# show instances
ec2.instances 

# create a new instance based on config file
inst = ec2.create("config.cfg")

# destroy the instance
ec2.destroy(inst["InstanceId"])
```