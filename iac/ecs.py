import logging

import boto3
from botocore.exceptions import ClientError
from taskflow import task

from iac import CONFIG, utils

logger = logging.getLogger(__name__)

client = boto3.client('ecs', config=CONFIG)


class ECSClusterCreate(task.Task):

    def __init__(self, name=None, inject=None):
        super(ECSClusterCreate, self).__init__(name=name, inject=inject)

    def execute(self, clusterName):
        client.create_cluster(
            clusterName=clusterName,
            settings=[
                {
                    'name': 'containerInsights',
                    'value': 'disabled'
                },
            ],
            configuration={
                'executeCommandConfiguration': {
                    'logging': 'DEFAULT',
                }
            },
            capacityProviders=[
                'FARGATE',
                'FARGATE_SPOT',
            ],
        )
        logger.info('Cluster [%s] created successfully.', clusterName)


class ECSRegisterTaskDefinition(task.Task):

    def __init__(self, name=None, provides=None, requires=None, auto_extract=True, rebind=None, inject=None,
                 ignore_list=None, revert_rebind=None, revert_requires=None):
        super(ECSRegisterTaskDefinition, self).__init__(name, provides, requires, auto_extract, rebind, inject,
                                                        ignore_list, revert_rebind, revert_requires)

    def execute(self, family, SQLALCHEMY_DATABASE_URI):
        try:
            client.register_task_definition(
                family=family,
                taskRoleArn='ecsTaskExecutionRole',
                executionRoleArn='ecsTaskExecutionRole',
                networkMode='awsvpc',
                containerDefinitions=[
                    {
                        'name': 'mypoc',
                        'image': '835751565277.dkr.ecr.ap-east-1.amazonaws.com/mypoc:v1.0',
                        'cpu': 0,
                        'portMappings': [
                            {
                                'containerPort': 80,
                                'hostPort': 80,
                                'protocol': 'tcp'
                            },
                        ],
                        'essential': True,
                        'environment': [
                            {
                                'name': 'SQLALCHEMY_DATABASE_URI',
                                'value': SQLALCHEMY_DATABASE_URI
                            }
                        ],
                        'startTimeout': 20,
                        'stopTimeout': 20,
                        'readonlyRootFilesystem': False,
                        'logConfiguration': {
                            'logDriver': 'awslogs',
                            'options': {
                                'awslogs-group': '/ecs/%s' % family,
                                'awslogs-region': 'ap-east-1',
                                'awslogs-stream-prefix': 'ecs'
                            },
                        },
                        # 'healthCheck': {
                        #     'command': [
                        #         'curl -f http://localhost/health || exit 1',
                        #     ],
                        #     'interval': 5,
                        #     'timeout': 3,
                        #     'retries': 3,
                        #     'startPeriod': 20
                        # },
                    },
                ],
                volumes=[],
                placementConstraints=[],
                requiresCompatibilities=[
                    'FARGATE',
                ],
                cpu='256',
                memory='512',
                runtimePlatform={
                    'cpuArchitecture': 'X86_64',
                    'operatingSystemFamily': 'LINUX'
                }
            )
            logger.info('TaskDefinition [%s] registered successfully.', family)
        except ClientError:
            logger.info('TaskDefinition [%s] registered failed.', family, exc_info=True)
            raise


class ECSServiceCreate(task.Task):

    def __init__(self, name=None, provides=None, requires=None, auto_extract=True, rebind=None, inject=None,
                 ignore_list=None, revert_rebind=None, revert_requires=None):
        super(ECSServiceCreate, self).__init__(name, provides, requires, auto_extract, rebind, inject, ignore_list,
                                               revert_rebind, revert_requires)

    def execute(self, cluster, serviceName, taskDefinition, SubnetIds, VpcSecurityGroupIds, TargetGroupArn):
        try:
            r = describe_service(cluster, serviceName)
            if r.get('services'):
                logger.info('Service [%s] already exists, delete it.', serviceName)
                delete_service(cluster, serviceName)
                wait_service_deleted(cluster, serviceName)
            client.create_service(
                cluster=cluster,
                serviceName=serviceName,
                taskDefinition=taskDefinition,
                loadBalancers=[
                    {
                        'targetGroupArn': TargetGroupArn,
                        'containerName': 'mypoc',
                        'containerPort': 80,
                    }
                ],
                desiredCount=1,
                launchType='FARGATE',
                platformVersion='LATEST',
                deploymentConfiguration={
                    'deploymentCircuitBreaker': {
                        'enable': False,
                        'rollback': False
                    },
                    'maximumPercent': 200,
                    'minimumHealthyPercent': 100
                },
                networkConfiguration={
                    'awsvpcConfiguration': {
                        'subnets': SubnetIds,
                        'securityGroups': VpcSecurityGroupIds,
                        'assignPublicIp': 'ENABLED'
                    }
                },
                schedulingStrategy='REPLICA',
                enableECSManagedTags=True,
                propagateTags='NONE',
                enableExecuteCommand=False,
                deploymentController={
                    'type': 'CODE_DEPLOY'
                },
            )
            logger.info('Service [%s] created successfully.', serviceName)
        except ClientError:
            logger.info('Service [%s] created failed.', serviceName, exc_info=True)
            raise


def describe_service(cluster, serviceName):
    return client.describe_services(
        cluster=cluster,
        services=[
            serviceName,
        ]
    )


def delete_service(cluster, serviceName):
    try:
        client.delete_service(
            cluster=cluster,
            service=serviceName,
            force=True
        )

        logger.info('Service [%s] deletion request was submitted successfully.', serviceName)
    except ClientError:
        logger.info('Service [%s] deleted failed.', serviceName, exc_info=True)
        raise


def wait_service_deleted(cluster, serviceName):
    def _check(response):
        services = response.get('services')
        if not services:
            return True
        status = services.pop().get('status')
        if status == 'INACTIVE':
            return True
        logger.info('Service [%s] deletion is not complete, waiting...', serviceName)
        return False

    utils.blocked_until(lambda: describe_service(cluster, serviceName), _check, sleep_time=20, timeout=300)
