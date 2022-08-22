"""Provisioner for deployables"""
# -*- coding: utf-8 -*-
from stackmate.resources import ResourceList
from stackmate.types import DeployableList
from stackmate.constants import STATE_CREDENTIAL_KEYS, PROVIDER_AWS


class Provisioner:
    """Generates the provision variables to be used in playbooks"""
    # pylint: disable=R0903
    @staticmethod
    def changes(deployables: DeployableList, resource_list: ResourceList, \
            updated_roles: set = None, entries: set = None):
        """Generates the provisions for a given deployable"""
        resource_list.modify_touched_resources()
        resource_list.terminate_unused_resources(deployables)

        updated_roles = updated_roles or set()
        mod_keys = ['provisions', 'modifications', 'terminations']
        entries = entries or set(mod_keys)

        # Go through modifications & new provisions
        for deployable in deployables:
            # if the deployable depends upon a group that has changed. If so, mark it as modified
            dependencies_modified = deployable.depends_on and (
                updated_roles & set(deployable.depends_on))

            # check whether we should re-generate credentials
            regenerate_credentials = Provisioner.should_regenerate_credentials(
                deployable, resource_list)

            if dependencies_modified or regenerate_credentials:
                resource_list.modify(deployable)

            if deployable.nodes_expandable:
                Provisioner.process_deployable_nodes(deployable, resource_list)
            else:
                Provisioner.process_single_deployable(deployable, resource_list)

        changeset = resource_list.serialize()

        changes = {k: v if k in entries else [] for k, v in changeset.items()}

        changes.update({
            'unchanged': changeset['unchanged'],
            'has_changes': any(changeset[k] for k in entries),
        })

        return changes if changes['has_changes'] else {}

    @staticmethod
    def should_regenerate_credentials(deployable, resource_list: ResourceList) -> bool:
        """Whether we should re-generate credentials"""
        if deployable.rolename not in STATE_CREDENTIAL_KEYS:
            return False

        provider = deployable.provider if hasattr(deployable, 'provider') else None
        if not provider or provider != PROVIDER_AWS:
            return False

        credential_keys = STATE_CREDENTIAL_KEYS[deployable.rolename]
        resources = resource_list.all

        return any(
            not c for res in resources for k, c in res.output.items() if k in credential_keys
        )

    @staticmethod
    def process_single_deployable(deployable, resource_list) -> ResourceList:
        """Processes a single deployable (that does not contains nodes)"""
        existing_resources = resource_list.find(deployable)
        ignored_keys = deployable.diff_ignored_keys()

        # the deployable was not found in the list, needs to be provisioned
        if not existing_resources:
            resource_list.provision(deployable)

        # the deployable was found in the list
        for res in existing_resources:
            diff = {
                k:v for k, v in res.diff_params(deployable).items() if k not in ignored_keys
            }

            # if any of the modified keys is included in the list of attributes
            # that trigger an instance replacement, add the resource to the terminations list
            # otherwise add the resource in the modifications list
            if any([k in deployable.replacement_triggers for k in diff]):
                resource_list.terminate(deployable)
                resource_list.provision(deployable)
            elif diff != {}:
                resource_list.modify(deployable)

    @staticmethod
    def process_deployable_nodes(deployable, resource_list) -> ResourceList:
        """Expands the nodes in provisions"""
        count = deployable.nodes if hasattr(deployable, 'nodes') and deployable.nodes else 1
        ignored_keys = deployable.diff_ignored_keys()
        existing_resources = []

        for dep_res in resource_list.find(deployable):
            existing_resources += dep_res.node_list()

        # clear the resource list and use the existing resources found for the nodes
        resource_list.reset(existing_resources)

        # the deployable requests X nodes to be present where X is less than what we have now
        # this means we should terminate the excess resources
        node_resource_count = len(existing_resources)

        if count < node_resource_count:
            terminated = node_resource_count - count
            excess = existing_resources[-terminated:]
            resource_list.remove(*excess)

        # Get the deployable as expanded nodes
        node_resources = deployable.as_node_resources()

        if not existing_resources:
            resource_list.append(*node_resources)
            return

        # Iterate through the resources we populated for the ondes
        for node_res in node_resources:
            # node resource not found in the list of the ones we have, add it
            pparams = node_res.provision_params
            found = any(
                n.provision_params['name'] == pparams['name'] for n in existing_resources
            )

            if not found:
                resource_list.append(node_res)
                continue

            # Try and look for existing nodes, if there are any changes, apply them
            for res in existing_resources:
                # get the diff but ignore the name
                diff = {
                    k:v for k, v in node_res.diff_params(res).items() if k not in ignored_keys
                }

                if any([k in deployable.replacement_triggers for k in diff]):
                    resource_list.remove(res)
                    resource_list.append(node_res)
                elif diff != {}:
                    resource_list.replace(node_res, res)
