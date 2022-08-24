# About this repository

Some time ago, I tried to launch a SaaS business that used a friendly UI to launch infrastructure on AWS. Being a developer for nearly 20 years at the time, I completely neglected the "business" part and went crazy on the "SaaS" part.

This repository hosts the deployer app that powered the SaaS app, built in Python and Ansible and does the following:
- Deploys AWS Infrastructure with Ansible. Currently supports
  - RDS databases
  - EC2 Instances
  - S3 buckets
  - Cloudfront CDNs
  - Elasticache clusters
  - NFS storage and more...
- Adds state support to Ansible
- Provides preview subdomains on `myappis.live`
- Ansible roles can be found [here](stackmate/ansible/roles)


# Current status of the project
The project is now being re-written as an Open Source project, using CDKTF and TypeScript in a [new repository](https://github.com/stackmate-io/stackmate). You can find more information on [stackmate.io](https://stackmate.io)

------

### Conventions used here:
1. There's a permanent VPC called `permanent-molecule-test` with id `vpc-09ebb623125812dd5` that is used in the instances & other related tests
2. The test domain is ezploy.eu, all tests should include that domain and every resource tagged with that domain should be safe to delete (except the VPC)
3. There are ready made SSL cecrtificates in the N Virginia region that are used in CDN and other related tests


### Usage

1. Deployment:

```
STACKMATE_OPERATION_ID=123 STACKMATE_PUBLIC_KEY=~/.ssh/id_rsa.pub STACKMATE_PRIVATE_KEY=~/.ssh/id_rsa python3 cli.py --debug=1 --stage=production --path=./tests/data/mock-project deploy --first=1
```
