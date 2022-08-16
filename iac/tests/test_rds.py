from unittest import TestCase, mock

import botocore
import taskflow
from taskflow import engines

from iac.rds import flow_create_db_instance

origin_func = botocore.client.BaseClient._make_api_call


def mock_make_api_call(self, operation_name, api_params):
    if operation_name == 'DescribeVpcs':
        return response_describe_vpcs
    if operation_name == 'DescribeSubnets':
        return response_describe_subnets
    if operation_name == 'DescribeSecurityGroups':
        return response_describe_security_groups
    if operation_name == 'CreateDBSubnetGroup':
        return {}
    if operation_name == 'CreateDBInstance':
        return {}
    if operation_name == 'DescribeDBInstances':
        return response_describe_db_instances

    return origin_func(self, operation_name, api_params)


class TestRDS(TestCase):

    @mock.patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call)
    def test_flow_create_db_instance(self):
        store = {
            'DBInstanceIdentifier': 'my-db',
            'DBName': 'mypoc',
            'AllocatedStorage': 20,
            'DBInstanceClass': 'db.t3.micro',
            'MasterUserPassword': '1',
            'DBSubnetGroupName': 'my-db-subnet-group',
            'MultiAZ': False,
        }
        taskflow.engines.run(flow_create_db_instance(), executor='threaded', engine='serial', store=store)


response_describe_vpcs = {
    'Vpcs': [
        {
            'VpcId': 'VpcId',
        },
    ],
}

response_describe_subnets = {
    'Subnets': [
        {
            'SubnetId': 'SubnetId',
        },
    ],
}

response_describe_security_groups = {
    'SecurityGroups': [
        {
            'GroupId': 'GroupId',
        },
    ],
}

response_describe_db_instances = {
    'DBInstances': [
        {'DBInstanceIdentifier': 'my-db',
         'DBInstanceClass': 'db.t3.micro',
         'Engine': 'mysql',
         'DBInstanceStatus': 'available',
         'MasterUsername': 'admin',
         'DBName': 'mypoc',
         'Endpoint': {'Address': 'my-db.xxx.ap-east-1.rds.amazonaws.com', 'Port': 3306},
         'AllocatedStorage': 20,
         'VpcSecurityGroups': [{'VpcSecurityGroupId': 'GroupId', 'Status': 'active'}],
         'AvailabilityZone': 'ap-east-1b',
         'MultiAZ': False,
         'EngineVersion': '8.0.28',
         }
    ]
}
