import logging

import boto3
from botocore.exceptions import ClientError
from taskflow import task

from iac import CONFIG

logger = logging.getLogger(__name__)

client = boto3.client('ecr', config=CONFIG)


class ECRRepositoryCreate(task.Task):

    def __init__(self, name=None, inject=None):
        super(ECRRepositoryCreate, self).__init__(name=name, inject=inject)

    def execute(self, repositoryName, imageTagMutability='MUTABLE'):
        try:
            client.create_repository(
                repositoryName=repositoryName,
                imageTagMutability=imageTagMutability,
            )
            logger.info('Repository [%s] created successfully.', repositoryName)
        except client.exceptions.RepositoryAlreadyExistsException:
            logger.info('Repository [%s] already exists, do nothing.', repositoryName)
        except ClientError:
            logger.info('Repository [%s] created failed.', repositoryName, exc_info=True)
            raise
