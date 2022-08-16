import logging

import boto3
from botocore.exceptions import ClientError

from iac import CONFIG, utils

logger = logging.getLogger(__name__)

client = boto3.client('elbv2', config=CONFIG)


def create_load_balancer(LBName, Subnets, SecurityGroups) -> str:
    """
    :return: LoadBalancerArn
    """
    try:
        client.create_load_balancer(
            Name=LBName,
            Subnets=Subnets,
            SecurityGroups=SecurityGroups,
            Scheme='internet-facing',
            Type='application',
            IpAddressType='ipv4',
        )
        logger.info('LoadBalancer [%s] created successfully.', LBName)
    except client.exceptions.DuplicateLoadBalancerNameException:
        logger.info('LoadBalancer [%s] already exists, do nothing.', LBName)
    except ClientError:
        logger.info('LoadBalancer [%s] created failed.', LBName, exc_info=True)
        raise
    return describe_load_balancer(LBName).get('LoadBalancerArn')


def describe_load_balancer(LBName):
    response = client.describe_load_balancers(
        Names=[
            LBName,
        ]
    )
    lbs = response.get('LoadBalancers')
    return lbs.pop() if lbs else None


def wait_lb_active(LBName):
    def _check(lb):
        status = lb.get('State').get('Code')
        if status != 'active':
            logger.info('Waiting for the LB [%s] to become active, current status: [%s].',
                        LBName, status)
            return False
        logger.info('LB [%s] is now available.', LBName)
        return True

    utils.blocked_until(lambda: describe_load_balancer(LBName), _check)


def create_target_group(TargetGroupName, TargetGroupPort, VpcId) -> str:
    """
    :return: TargetGroupArn
    """
    try:
        client.create_target_group(
            Name=TargetGroupName,
            Protocol='HTTP',
            ProtocolVersion='HTTP1',
            Port=TargetGroupPort,
            VpcId=VpcId,
            HealthCheckProtocol='HTTP',
            TargetType='ip',
        )
        logger.info('TargetGroup [%s] created successfully.', TargetGroupName)
    except client.exceptions.DuplicateTargetGroupNameException:
        logger.info('TargetGroup [%s] already exists, do nothing.', TargetGroupName)
    except ClientError:
        logger.info('TargetGroup [%s] created failed.', TargetGroupName, exc_info=True)
        raise
    return describe_target_group(TargetGroupName).get('TargetGroupArn')


def describe_target_group(TargetGroupName):
    response = client.describe_target_groups(
        Names=[
            TargetGroupName,
        ]
    )
    tgs = response.get('TargetGroups')
    return tgs.pop() if tgs else None


def create_listener(LoadBalancerArn, TargetGroupArn):
    try:
        client.create_listener(
            LoadBalancerArn=LoadBalancerArn,
            Protocol='HTTP',
            Port=80,
            DefaultActions=[
                {
                    'Type': 'forward',
                    'TargetGroupArn': TargetGroupArn,
                    'Order': 1,
                    'ForwardConfig': {
                        'TargetGroups': [
                            {
                                'TargetGroupArn': TargetGroupArn,
                                'Weight': 1
                            },
                        ],
                        'TargetGroupStickinessConfig': {
                            'Enabled': False,
                            'DurationSeconds': 3600
                        }
                    }
                },
            ],
        )
        logger.info('Listener created successfully.')
    except client.exceptions.DuplicateListenerException:
        logger.info('Listener already exists, do nothing.')
    except ClientError:
        logger.info('Listener created failed.', exc_info=True)
        raise
