"""Generates playbooks to be executed by ansible"""
# -*- coding: utf-8 -*-
import os
import hashlib
from stackmate.configurations import OperationsConfiguration
from stackmate.helpers import get_scm_service, get_project_resource_suffix
from stackmate.provisioner import Provisioner
from stackmate.constants import PROVIDER_AWS, STRATEGY_LINEAR, STRATEGY_MITOGEN_LINEAR, \
                                STRATEGY_PARALLEL, STRATEGY_MITOGEN_PARALLEL, \
                                CONNECTION_LOCAL, CONNECTION_SSH, LOCALHOST, BECOME_METHOD_SUDO, \
                                DEPLOYMENT_USER, DEPLOYMENT_SUCCESS, \
                                DEPLOYMENT_FAILURE, STACKMATE_STATE_FACT, CHECK_MODE, \
                                OMNIPRESENT_ROLES, FLATTENED_PROVISION_PARAM_ROLES, \
                                INVENTORY_INCLUDED_ROLES, ENV_MITOGEN_PATH, \
                                APT_RETRIES, APT_DELAY, \
                                LOCAL_DEPLOYMENT_PROJECT_TYPES, FORCED_STRATEGIES_PER_ROLE, \
                                ROLE_TO_DEPENDS_ON_MAPPING, \
                                PREVIEW_DOMAIN, PREVIEW_DOMAIN_HOSTED_ZONE_ID

OPERATIONS = OperationsConfiguration()


class Play:
    """Represents an Ansible play that takes place into a playbook"""
    # pylint: disable=too-many-instance-attributes
    def __init__(self, role, task_vars, **kwargs):
        """Initializes a play"""
        self._role = role
        self.rolename = self._role.get('name')
        self.playname = kwargs.get('playname') or self.rolename

        self._hosts = None
        self._task_vars = task_vars
        self._force_local = kwargs.get('force_local', False)
        self._global_vars = kwargs.get('global_vars', {})

    def get_source(self) -> dict:
        """Returns the source of the play to be executed"""
        return dict(
            name=self.playname,
            hosts=self.hosts,
            connection=self.connection,
            gather_facts=self.gather_facts,
            remote_user=self._role.get('remote_user', DEPLOYMENT_USER),
            strategy=self.strategy,
            tasks=self.tasks,
            become_method=BECOME_METHOD_SUDO,
            check_mode=bool(CHECK_MODE),
        )

    def get_variables(self) -> dict:
        """Returns the variables to be used in a play"""
        return self._global_vars

    @property
    def tasks(self) -> list:
        """Returns the tasks to run during the play"""
        return [{
            'action': 'include_role',
            'args': {'name': self._role['name']},
            'vars': self._task_vars,
        }]

    @property
    def strategy(self):
        """Returns the strategy for the play"""
        rolename = self._role['name']

        if rolename in FORCED_STRATEGIES_PER_ROLE:
            return FORCED_STRATEGIES_PER_ROLE[rolename]

        is_linear = self._role.get('execution', STRATEGY_LINEAR) == STRATEGY_LINEAR

        if os.environ.get(ENV_MITOGEN_PATH):
            return STRATEGY_MITOGEN_PARALLEL if not is_linear else STRATEGY_MITOGEN_LINEAR

        return STRATEGY_PARALLEL if not is_linear else STRATEGY_LINEAR

    @property
    def hosts(self):
        """Returns the hosts for the play to be executed upon"""
        if self._hosts is None:
            self._hosts = self._role.get('hosts', LOCALHOST) if not self._force_local else LOCALHOST
        return self._hosts

    def is_local(self):
        """Returns whether this play should be executed in localhost only"""
        return self.hosts == LOCALHOST

    @property
    def connection(self) -> str:
        """Returns the connection to be used"""
        return CONNECTION_LOCAL if self.is_local() else CONNECTION_SSH

    @property
    def gather_facts(self) -> bool:
        """Returns whether we should gather facts"""
        return self._role.get('gather_facts', not self.is_local())


class Playbook:
    """Represents an ansible playbook"""
    def __init__(self, config, project, state, **kwargs):
        self.config = config
        self.project = project
        self.state = state
        self.extra_vars = kwargs.get('extra_vars', {})
        self._omnipresent_roles = OMNIPRESENT_ROLES.get(self.project.flavor, [])

    @property
    def rolenames(self):
        """Returns the roles to be executed within this playbook"""
        return [r['name'] for r in self.config.get('roles', []) if r.get('name')]

    def get_plays(self, updated_roles: set = None) -> tuple:
        """Returns the list of plays to be executed"""
        plays = []
        updated_roles = updated_roles or set()

        for rolespec in self.config.get('roles', []):
            rolename = rolespec['name']
            provisioner_entries = set(self.config.get('entries', []))
            resources = self.state.get_resources(rolename)
            deplist = []

            # process the state for every deployable that is to be provisioned
            # and add it to the deployables list
            for dep in self.project.deployables_per_role.get(rolename, []):
                dep.process_state(self.state)
                deplist.append(dep)

            # Get the changes that are supposed to happen, then filter
            # by the entries that the current play requires (eg. only terminations)
            changes = Provisioner.changes(
                deplist, resources, updated_roles, provisioner_entries)

            # there aren't any changes to provision and the role should not be always present
            if not changes and rolename not in self._omnipresent_roles:
                continue

            # add the role in the list of pdated ones if there are changes to it
            # (might be omnipresent though)
            if changes:
                updated_roles.add(rolename)
                self.mark_dependants_as_touched(rolename)

            # only store the state when we have provisions or modifications
            store_state = ('provisions' in changes and changes['provisions']) or \
                            ('modifications' in changes and changes['modifications'])

            if rolename in FLATTENED_PROVISION_PARAM_ROLES:
                for deployable in deplist:
                    plays.append(Play(
                        role=rolespec,
                        task_vars=deployable.provision_params,
                        global_vars=self._get_project_vars(),
                        force_local=self._force_local_plays(),
                    ))
            else:
                plays.append(Play(
                    role=rolespec,
                    task_vars=dict(**changes, store_state=bool(store_state)),
                    global_vars=self._get_project_vars(),
                    force_local=self._force_local_plays(),
                ))

        return (plays, updated_roles)

    @property
    def can_run_in_parallel(self) -> bool:
        """Returns whether this play can execute roles in parallel"""
        return bool(self.config.get('parallel'))

    def get_failure_play(self):
        """Returns a special play for when the deployment fails"""
        notifs_deployable = next(
            (d for d in self.project.deployables if d.rolename == 'notifications'), None)

        if not notifs_deployable:
            return None

        task_vars = notifs_deployable.provision_params
        task_vars.update({'deployment_status': DEPLOYMENT_FAILURE})

        return Play(
            role={'name': 'notifications', 'hosts': LOCALHOST, 'execution': STRATEGY_PARALLEL},
            task_vars=task_vars,
            global_vars=self._get_project_vars(),
            force_local=True)

    def mark_dependants_as_touched(self, rolename):
        """Marks dependant resources as tainted"""
        dependants = [
            key for key, roles in ROLE_TO_DEPENDS_ON_MAPPING.items() if rolename in roles
        ]

        for dependant_role in dependants:
            self.state.merge_role_resource_attributes(dependant_role, touched=True)

        self.state.save()

    def _force_local_plays(self):
        """Whether we should force local plays"""
        return self.project.framework in LOCAL_DEPLOYMENT_PROJECT_TYPES

    def _get_cloud_vars(self):
        """Returns the variables for the cloud provider"""
        suffix = get_project_resource_suffix(self.project.repository, self.project.stage)
        resource_hash = hashlib.md5(suffix.encode()).hexdigest()

        if self.project.provider == PROVIDER_AWS:
            return {
                'vpc_name': 'vpc-{}'.format(suffix),
                'subnet_name': 'main-subnet-{}'.format(suffix),
                'alt_subnet_name': 'alt-subnet-{}'.format(suffix),
                'gateway_name': 'gw-{}'.format(suffix),
                'route_name': 'route-{}'.format(suffix),
                'keypair_name': 'keypair-{}'.format(suffix),
                'elasticache_subnet_group_name': 'cache-subnet-{}'.format(suffix),
                'rds_subnet_group_name': 'db-subnet-{}'.format(suffix),
                'elb_security_group_name': 'lb-sg-{}'.format(suffix),
                'elb_name_prefix': 'lb-{}'.format(resource_hash[:15]),
                'elb_long_name': suffix,
                'ses_iam_user': 'ses-smtp-{}'.format(suffix),
                'storage_username': 's3-user-{}'.format(suffix),
                # elb target group name cannot be longer than 32 characters
                'elb_target_group_prefix': 'lbtg-{}'.format(resource_hash[:10]),
                'apt_lock_retries': APT_RETRIES,
                'apt_lock_delay': APT_DELAY,
            }

        return {}

    def _get_project_vars(self):
        """Returns the variables to be used """
        project_vars = dict(
            **self.project.serialize(),
            **self.project.ssh_keys,
            **self._get_cloud_vars(),
            stage=self.project.stage,
            scm=get_scm_service(self.project.repository),
            # the source for the configuration files
            files_source=self.project.rootpath,
            # Set the commit reference
            reference=self.extra_vars.get('commit', {}).get('reference', 'HEAD'),
            # Set the deployment path
            deployment_path=self.project.documentroot,
            # by default we consider the deployment to finish successfully
            deployment_status=DEPLOYMENT_SUCCESS,
            # ansible vars
            ansible_ssh_private_key_file=self.project.ssh_keys['private_key_filename'],
            ansible_check_mode=bool(CHECK_MODE),
            is_on_preview_domain=self.project.domain.endswith(PREVIEW_DOMAIN),
            preview_domain=PREVIEW_DOMAIN,
            preview_domain_hosted_zone_id=PREVIEW_DOMAIN_HOSTED_ZONE_ID,
        )

        # add default values for facts
        project_vars[STACKMATE_STATE_FACT] = []

        # add any extra variables that may be available
        if self.extra_vars:
            project_vars.update(self.extra_vars)

        # add the output from the prerequisites role (if available)
        if self.state.get('prerequisites'):
            preq = self.state.get('prerequisites')

            # there should be 1 entry at most in the prerequisites key
            if len(preq) > 1:
                raise Exception(
                    'There are more than 1 entries in for prerequisites in the state. ' +
                    'Please contact our support and report this as a bug'
                )

            project_vars.update(preq[0].get('output', {}))

        return project_vars

    def get_inventory(self) -> dict:
        """Returns the inventory for the play"""
        # see https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html
        inventory = {'all': {}, 'provisionables': {}}
        # Iterate through the services in the state and filter out the standaloneservices
        deployables = [dep for dep in self.project.deployables if dep.include_in_inventory]

        for deployable in deployables:
            # Only allow hosts for specific roles to be included in the inventory
            if deployable.rolename not in INVENTORY_INCLUDED_ROLES:
                continue

            dep_groups = deployable.host_groups
            dep_resources = self.state.get_deployable_resources(deployable)
            deployable_hosts = []

            for resource in dep_resources.all:
                output = resource.output

                if hasattr(deployable, 'nodes') and output.get('nodes'):
                    deployable_hosts += list([
                        n.get('ip') or n.get('host') for n in output['nodes']
                    ])
                elif output.get('ip'): # prefer IP over hostname
                    deployable_hosts.append(output['ip'])
                elif output.get('host'):
                    deployable_hosts.append(output['host'])

                # add the group and the hosts in the inventory
                for group in dep_groups:
                    for host in deployable_hosts:
                        if group not in inventory:
                            inventory[group] = {}

                        # ansible inventory requires the host ips to be keys
                        inventory['all'][host] = {}
                        inventory[group][host] = {}

                        if deployable.rolename == 'instances':
                            inventory['provisionables'][host] = {}

        return inventory


class PlaybookIterator:
    """Iterates playbooks"""
    # pylint: disable=too-many-instance-attributes
    def __init__(self, operation, project, state, **kwargs):
        self.project = project
        self.state = state
        self.extra_vars = kwargs
        self.operation = operation
        self._idx = -1
        self._config = self._get_config(operation).get('steps', [])
        self._set_iterable()

    def __iter__(self):
        self._set_iterable()
        return self

    def __next__(self):
        if self._idx + 1 >= self._length:
            raise StopIteration

        self._idx += 1
        return self._get_playbook(self._idx)

    def __len__(self):
        return self._length

    def __getitem__(self, idx):
        return self._get_playbook(idx)

    def _set_iterable(self):
        """Makes the iterator iterable"""
        self._idx = -1
        self._steps = self._config
        self._length = len(self._config)

    def _get_config(self, operation):
        """Get the configuration for the operation to execute"""
        config = OPERATIONS.contents.get(operation)

        if not config:
            raise Exception('Operation {} is not available in Stackmate'.format(operation))

        flavor = self.project.flavor

        if flavor not in config.get('flavors', []):
            raise Exception(
                'This operation is not available for the project type {}'.format(flavor))

        return config

    def _get_playbook(self, idx):
        """Returns the playbook for a specific step"""
        return Playbook(
            config=self._steps[idx],
            project=self.project,
            state=self.state,
            extra_vars=self.extra_vars)

    def reset(self):
        """Resets the index to its initial state so that we can iterate once more"""
        self._idx = -1

    def apply_state_changes(self, facts: list):
        """Applies changes to the state as were generated during playbook execution"""
        # since the deployable is in the fact, this practically means
        # that the role was executed (either got provisioned, modified or terminated)
        #
        # Hence, it's OK to replace that the fact represents the actual state for the deployable
        return [
            self.state.update(f['role'], f.get('resources', [])) for f in facts if f.get('role')
        ]

    def commit_state(self):
        """Commits state into the file"""
        return self.state.save()
