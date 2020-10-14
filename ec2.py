import boto3, os
from time import sleep
import configparser
import sys
import base64
import pandas as pd
from datetime import datetime, timedelta


class AutoEC2:
    def __init__(self, profile=os.getenv("AWSACC")):
        super().__init__()
        self.session = boto3.session.Session(profile_name=profile)
        self.client = self.session.client("ec2")
        self.instances = self._get_instances()

    @staticmethod
    def read_user_data():
        user_data = ""
        if os.path.exists("userdata.txt"):
            with open("userdata.txt", "r") as f:
                user_data = f.read()
        return user_data

    def _get_instances(self):
        response = self.client.describe_instances()
        reservations = response["Reservations"]
        df = pd.DataFrame()

        if len(reservations) > 0:
            r_instances = [inst for resv in reservations for inst in resv["Instances"]]
            inst_details = [
                {
                    "InstanceId": inst["InstanceId"],
                    "PublicIpAddress": inst["PublicIpAddress"]
                    if "PublicIpAddress" in inst.keys()
                    else None,
                    "InstanceType": inst["InstanceType"],
                    "state": inst["State"]["Name"],
                    "name": [k["Value"] for k in inst["Tags"] if k["Key"] == "Name"][0]
                    if "Tags" in inst.keys()
                    else None,
                }
                for inst in r_instances
            ]
            df = pd.DataFrame(inst_details)
            df = df[df.state != "terminated"].reset_index(drop=True)

        self.instances = df

        return df

    def get_spot_price(self, config):
        price_history = self.client.describe_spot_price_history(
            MaxResults=10,
            InstanceTypes=[config.get("EC2", "type")],
            ProductDescriptions=[config.get("EC2", "product_description")],
        )
        return float(price_history["SpotPriceHistory"][0]["SpotPrice"])

    def associate_address(self, instance_id, public_ip=""):
        if public_ip == "":
            return None
        while True:
            try:
                res = self.client.associate_address(
                    InstanceId=instance_id, PublicIp=public_ip
                )
                assert res["ResponseMetadata"]["HTTPStatusCode"] == 200
                break
            except boto3.exceptions.botocore.client.ClientError as e:
                sleep(5)
        return res

    def provision_instance(self, config):
        user_data = self.read_user_data()
        print(user_data)
        user_data_encode = (base64.b64encode(user_data.encode())).decode("utf-8")
        req = self.client.request_spot_instances(
            InstanceCount=1,
            Type="one-time",
            InstanceInterruptionBehavior="terminate",
            ## TODO.. below doesn't work, instance doesn't die but spot request dies
            # ValidUntil=datetime.utcnow()+timedelta(hours=int(config.get('EC2', 'valid_hours'))),
            LaunchSpecification={
                "SecurityGroups": [config.get("EC2", "security_group")],
                "ImageId": config.get("EC2", "ami"),
                "InstanceType": config.get("EC2", "type"),
                "KeyName": config.get("EC2", "key_pair"),
                "Placement": {
                    "AvailabilityZone": config.get("EC2", "availability_zone")
                },
                "SubnetId": config.get("EC2", "subnet_id"),
                "UserData": user_data_encode,
                "IamInstanceProfile": {"Arn": config.get("EC2", "iam_role")},
            },
            SpotPrice=config.get("EC2", "max_bid"),
        )
        print(
            "Spot request created, status: " + req["SpotInstanceRequests"][0]["State"]
        )
        print("Waiting for spot provisioning")
        while True:
            sleep(1)
            current_req = self.client.describe_spot_instance_requests(
                SpotInstanceRequestIds=[
                    req["SpotInstanceRequests"][0]["SpotInstanceRequestId"]
                ]
            )
            if current_req["SpotInstanceRequests"][0]["State"] == "active":
                print(
                    "Instance allocated ,Id: ",
                    current_req["SpotInstanceRequests"][0]["InstanceId"],
                )
                instance = self.client.describe_instances(
                    InstanceIds=[current_req["SpotInstanceRequests"][0]["InstanceId"]]
                )["Reservations"][0]["Instances"][0]
                self.client.create_tags(
                    Resources=[current_req["SpotInstanceRequests"][0]["InstanceId"]],
                    Tags=[
                        {"Key": "Name", "Value": config.get("EC2", "tag")},
                        {"Key": "CreatedBy", "Value": config.get("EC2", "created_by")},
                        {"Key": "Team", "Value": config.get("EC2", "team")},
                        {
                            "Key": "Application",
                            "Value": config.get("EC2", "application"),
                        },
                    ],
                )
                return instance
            print("Waiting...", sleep(10))

    def destroy_instance(self, instance_id):
        try:
            tags_terminate = self.instances.loc[
                self.instances.InstanceId == instance_id, "name"
            ].tolist()

            print("Terminating", instance_id)
            self.client.terminate_instances(InstanceIds=[instance_id])
            print("Termination complete (", instance_id, ")")

            if len(tags_terminate) and ~pd.isnull(tags_terminate[0]):
                self.client.delete_tags(
                    Resources=[instance_id],
                    Tags=[
                        {"Key": "Name", "Value": tags_terminate},
                    ],
                )
        except:
            print("Failed to terminate:", sys.exc_info()[0])

    def create(self, config_file):

        config = configparser.ConfigParser()
        config.read(config_file)

        spot_price = self.get_spot_price(config)
        print(f"Spot price ${str(spot_price)}")
        if spot_price > float(config.get("EC2", "max_bid")):
            print("Spot price more than bid, not creating an instnace.")
            inst = None
        else:
            # make spot instance
            inst = self.provision_instance(config)
            # add public ip
            self.associate_address(
                inst["InstanceId"], config.get("EC2", "public_ip_address")
            )

        return inst

    def destroy(self, instance_id):
        self.destroy_instance(instance_id)
        self._get_instances()
        return None


if __name__ == "__main__":

    ec2 = AutoEC2()
