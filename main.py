import taskflow
from taskflow import engines, task
from taskflow.patterns import unordered_flow, linear_flow, graph_flow

from iac.ec2 import flow_load_default_vpc_info
from iac.ecr import ECRRepositoryCreate
from iac.ecs import ECSClusterCreate, ECSRegisterTaskDefinition, ECSServiceCreate
from iac.elbv2 import create_target_group, create_load_balancer, create_listener
from iac.rds import flow_create_db_instance, gen_db_uri

if __name__ == '__main__':
    db_store = {
        'DBInstanceIdentifier': 'my-db',
        'DBName': 'mypoc',
        'AllocatedStorage': 20,
        'DBInstanceClass': 'db.t3.micro',
        'MasterUserPassword': 'Admin123',
        'DBSubnetGroupName': 'my-db-subnet-group',
        'MultiAZ': False,
    }
    taskflow.engines.run(flow_create_db_instance(),
                         executor='threaded',
                         engine='serial',
                         max_workers=1,
                         store=db_store)

    fargate_store = {
        'repositoryName': 'mypoc',
        'clusterName': 'my-cluster',
        'family': 'mypoc-task-def',
        'serviceName': 'mypoc-svc',
        'DBInstanceIdentifier': 'my-db',
        'MasterUserPassword': 'Admin123',

        'TargetGroupName': 'mypoc-target-group',
        'TargetGroupPort': 80,
        'LBName': 'mypoc-alb',
    }
    flow_fargate_init = unordered_flow.Flow('fargate_init')
    flow_fargate_init.add(
        flow_load_default_vpc_info(),
        ECRRepositoryCreate('create_repo'),
        ECSClusterCreate('create_cluster'),
    )
    flow_task_define = linear_flow.Flow('task_define').add(
        task.FunctorTask(execute=gen_db_uri, provides='SQLALCHEMY_DATABASE_URI'),
        ECSRegisterTaskDefinition('register_task_def'),
    )
    flow_create_alb = linear_flow.Flow('create_alb').add(
        task.FunctorTask(execute=create_target_group, provides='TargetGroupArn'),
        task.FunctorTask(execute=create_load_balancer, provides='LoadBalancerArn',
                         rebind=['LBName', 'SubnetIds', 'VpcSecurityGroupIds']),
        task.FunctorTask(execute=create_listener),
    )

    task_create_svc = ECSServiceCreate('create_service',
                                       rebind=['clusterName', 'serviceName', 'family'])
    flow_create_fargate = graph_flow.Flow('create_fargate').add(
        flow_fargate_init,
        flow_task_define,
        flow_create_alb,
        task_create_svc,
    )
    flow_create_fargate.link(flow_fargate_init, flow_create_alb)
    flow_create_fargate.link(flow_create_alb, task_create_svc)
    flow_create_fargate.link(flow_task_define, task_create_svc)

    taskflow.engines.run(flow_create_fargate, engine='parallel', store=fargate_store)
