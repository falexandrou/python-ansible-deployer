### Conventions

1. The software dependencies should be targeted in a group called 'provisionables'
2. The version provided should be a minor version eg. 1.15 instead of patch 1.15.5
3. All dependencies should be installed by using an asterisk as their version
4. There is default VPC and its corresponding subnet groups in AWS prefixed with `permanent-molecule-test`

### Required Variables
deployment_user: stackmate
ssh_port: 22
keypair_name: stackmate_keypair
flavor: instances
provider: aws
stage: staging / production
region: eu-central-1 / eu-west-1
public_key:
providers:
  aws:
    access_key: "{{ lookup('env', 'STACKMATE_ACCESS_KEY') }}"
    secret: "{{ lookup('env', 'STACKMATE_SECRET') }}"

### Variables provided by the state (requires subsequent reloads)
vpc_id:
vpc_subnet_id:

### Configurable variables (and their defaults)
distro: ubuntu
timezone: Etc/UTC


### How-to

#### Upgrade ubuntu
1. go to https://cloud-images.ubuntu.com/locator/ec2/
2. pick the AMIs that correspond to the distribution
3. Update at instances/defaults/main.yml
4. Update the repositories for python, nginx, ruby, nodejs

### Upgrade dependencies
1. Update the default & available version in stackmate.yml
2. Run tests
3. Publish

#### Known issues
1. When using ansible-mitogen out of a docker container where `/usr/bin/python` is not available, use the master version from GitHub, version 0.2.9 requests for that path
1. Some times, when trying to provision an S3 bucket that has been provisioned before, the operation gets stuck there. The solution is to rename the S3 bucket


### ENVIRONMENT variables to be used when running the deployer:
ENV_CHECK_MODE = 'STACKMATE_DRY_RUN'
ENV_PUBLIC_KEY = 'STACKMATE_PUBLIC_KEY'
ENV_PRIVATE_KEY = 'STACKMATE_PUBLIC_KEY'

*github integration*
- STACKMATE_GITHUB_ID
- STACKMATE_GITHUB_SECRET
- STACKMATE_GITHUB_TOKEN

*slack integration*
- STACKMATE_SLACK_TOKEN

*email integration*
- STACKMATE_SENDGRID_TOKEN
