**IaC POC for AWS.**

使用 [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) 访问 AWS Web Service。
使用 [OpenStack TaskFlow](https://docs.openstack.org/taskflow/latest/user/index.html) 实现基础设施管理流程的控制。

### 快速开始

##### 1. 确认 IAM 用户权限

* AmazonRDSFullAccess
* AmazonEC2FullAccess
* AmazonEC2ContainerRegistryFullAccess
* AmazonECS_FullAccess
* AmazonECSTaskExecutionRolePolicy
* EC2InstanceProfileForImageBuilderECRContainerBuilds
* AWSAppRunnerServicePolicyForECRAccess

##### 2. 确认 ~/.aws/credentials 凭证配置

##### 3. 运行

```
python main.py
```

### 资源清单

* mysql
* alb, target group, listener
* ecr
* ecs cluster, task definition, service
