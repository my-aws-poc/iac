import boto3
from taskflow import task
from taskflow.patterns import linear_flow

from iac import CONFIG

client = boto3.client('ec2', config=CONFIG)


def get_default_vpc():
    response = client.describe_vpcs(
        Filters=[
            {
                'Name': 'is-default',
                'Values': [
                    'true',
                ]
            },

        ],
        DryRun=False,
    )
    vpc = response.get('Vpcs').pop()
    return vpc.get('VpcId')


def get_default_subnet_ids(VpcId):
    response = client.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    VpcId,
                ]
            },
            {
                'Name': 'default-for-az',
                'Values': [
                    'true',
                ]
            },
        ],
        DryRun=False,
    )
    return [sn['SubnetId'] for sn in response['Subnets']]


def get_default_security_group_ids(VpcId):
    response = client.describe_security_groups(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    VpcId,
                ]
            },
        ],
        GroupNames=[
            'default',
        ],
        DryRun=False,
    )
    return [sg['GroupId'] for sg in response['SecurityGroups']]


def flow_load_default_vpc_info() -> linear_flow.Flow:
    """
    requires:
    provides: VpcId, SubnetIds, VpcSecurityGroupIds
    """
    flow = linear_flow.Flow('load_default_vpc_info')
    flow.add(
        task.FunctorTask(execute=get_default_vpc, provides='VpcId'),
        task.FunctorTask(execute=get_default_subnet_ids, provides='SubnetIds'),
        task.FunctorTask(execute=get_default_security_group_ids, provides='VpcSecurityGroupIds'),
    )
    return flow
