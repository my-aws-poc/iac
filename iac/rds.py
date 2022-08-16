import logging

import boto3
from botocore.exceptions import ClientError
from taskflow import task
from taskflow.patterns import linear_flow

from iac import CONFIG, utils
from iac.ec2 import flow_load_default_vpc_info

logger = logging.getLogger(__name__)
client = boto3.client('rds', config=CONFIG)


def create_db_subnet_group(DBSubnetGroupName, SubnetIds):
    try:
        client.create_db_subnet_group(
            DBSubnetGroupName=DBSubnetGroupName,
            DBSubnetGroupDescription=DBSubnetGroupName,
            SubnetIds=SubnetIds,
            Tags=[]
        )
        logger.info('DBSubnetGroup [%s] created successfully.', DBSubnetGroupName)
    except client.exceptions.DBSubnetGroupAlreadyExistsFault:
        logger.info('DBSubnetGroup [%s] already exists, do nothing.', DBSubnetGroupName)
    except ClientError:
        logger.info('DBSubnetGroup [%s] created failed.', DBSubnetGroupName)
        raise


def create_db_instance(DBInstanceIdentifier, DBName, AllocatedStorage, DBInstanceClass, MasterUserPassword,
                       VpcSecurityGroupIds, DBSubnetGroupName, MultiAZ):
    try:
        client.create_db_instance(
            DBName=DBName,
            DBInstanceIdentifier=DBInstanceIdentifier,
            AllocatedStorage=AllocatedStorage,
            DBInstanceClass=DBInstanceClass,
            Engine='mysql',
            MasterUsername='admin',
            MasterUserPassword=MasterUserPassword,
            DBSecurityGroups=[],
            VpcSecurityGroupIds=VpcSecurityGroupIds,
            # AvailabilityZone='ap-east-1a',
            DBSubnetGroupName=DBSubnetGroupName,
            PreferredMaintenanceWindow='fri:08:51-fri:09:21',
            DBParameterGroupName='default.mysql8.0',
            BackupRetentionPeriod=0,
            PreferredBackupWindow='12:13-12:43',
            Port=3306,
            MultiAZ=MultiAZ,
            EngineVersion='8.0.28',
            AutoMinorVersionUpgrade=True,
            LicenseModel='general-public-license',
            OptionGroupName='default:mysql-8-0',
            PubliclyAccessible=False,
            StorageType='gp2',
            StorageEncrypted=True,
            CopyTagsToSnapshot=True,
            MonitoringInterval=0,
            EnableIAMDatabaseAuthentication=True,
            DeletionProtection=False,
            MaxAllocatedStorage=AllocatedStorage * 2,
            BackupTarget='region',
            NetworkType='IPV4'
        )
        logger.info('DBInstance [%s] creation request was submitted successfully.', DBInstanceIdentifier)
    except client.exceptions.DBInstanceAlreadyExistsFault:
        logger.info('DBInstance [%s] already exists, do nothing.', DBInstanceIdentifier)
    except ClientError:
        logger.info('DBInstance [%s] created failed.', DBInstanceIdentifier)
        raise


def describe_db_instances(DBInstanceIdentifier):
    return client.describe_db_instances(DBInstanceIdentifier=DBInstanceIdentifier)


def wait_db_available(DBInstanceIdentifier):
    def _check(response):
        instance = response.get('DBInstances').pop()
        status = instance.get('DBInstanceStatus')
        if status != 'available':
            logger.info('Waiting for the DBInstance [%s] to become available, current status: [%s].',
                        DBInstanceIdentifier, status)
            return False
        logger.info('DBInstance [%s] is now available.', DBInstanceIdentifier)
        return True

    utils.blocked_until(lambda: describe_db_instances(DBInstanceIdentifier), _check, sleep_time=20, timeout=300)


def gen_db_uri(DBInstanceIdentifier, MasterUserPassword):
    """
    :return: sqlalchemy db uri,
             like 'mysql+pymysql://admin:password@db-1.xxxxx.ap-east-1.rds.amazonaws.com/dbname'
    """
    response = describe_db_instances(DBInstanceIdentifier)
    instance = response.get('DBInstances').pop()
    endpoint = instance['Endpoint']
    uri = f"mysql+pymysql://{instance['MasterUsername']}:{MasterUserPassword}@" \
          f"{endpoint['Address']}:{endpoint['Port']}/{instance['DBName']}"
    return uri


def flow_create_db_instance() -> linear_flow.Flow:
    """
    requires: DBInstanceIdentifier, MasterUserPassword, AllocatedStorage, DBInstanceClass, DBSubnetGroupName,
              DBName, MultiAZ
    provides:
    """
    flow = linear_flow.Flow('create_db_instance')
    flow.add(
        flow_load_default_vpc_info(),
        task.FunctorTask(execute=create_db_subnet_group),
        task.FunctorTask(execute=create_db_instance),
        task.FunctorTask(execute=wait_db_available),
    )
    return flow
