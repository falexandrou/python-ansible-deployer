"""
Stackmate CLI

Commands explanation & specs:

state        Inspect the project's state
    - verify state is present inside the project directory under .stackmate
    - print state for given branch

validate     Validate YAML configuration file
    - make sure the project type is supported
    - make sure there are encrypted credentials for all services

deploy       Deploy a project
rollback     Roll back to the previous release
    - check if there's a more up-to date version of the state in the remote repo
    - extract playbook
    - create ansible config on the fly
    - execute playbook

"""
# -*- coding: utf-8 -*-

import os
import click
from stackmate.operations import DeploymentOperation, RollbackOperation
from stackmate.constants import ENV_STACKMATE_OPERATION_ID

@click.group()
@click.option('--stage', required=True)
@click.option('--path', default=os.getcwd(), \
    type=click.Path(), help='The path to the project configuration file')
@click.option('--debug/--no-debug', default=False, \
    help='Print the playbook to be executed, do not deploy')
@click.option('--url', 'operation_url', default=None, help='The URL for the deployment')
@click.pass_context
def cli(ctx, stage, path=os.getcwd(), **kwargs):
    """
    Stackmate CLI

    try out our hosted version at https://stackmate.io
    """

    # ensure that ctx.obj exists and is a dict
    # (in case `cli()` is called by means other than the `if` block below
    ctx.ensure_object(dict)

    ctx.obj = {
        'path': path,
        'stage': stage,
        'debug': kwargs.get('debug', False),
        'operation_url': kwargs.get('operation_url'),
        'operation_id': os.environ.get(ENV_STACKMATE_OPERATION_ID),
    }


@cli.command(name='state')
def state_commands():
    """Inspect the project's state"""


@cli.command(name='validate')
def validate_config():
    """Validate YAML configuration file"""


@cli.command()
@click.option('--first/--no-first', 'is_first_deployment', default=False)
@click.option('--commit', 'commit_reference', default=None)
@click.option('--author', 'commit_author', default=None)
@click.option('--message', 'commit_message', default=None)
@click.pass_context
def deploy(ctx, **kwargs):
    """
    Deploy a project
    USAGE
        STACKMATE_PUBLIC_KEY=... STACKMATE_PRIVATE_KEY=... \
            python3 cli.py --stage=production --path=./tests/data/mock-project deploy
    """
    DeploymentOperation(**dict(**ctx.obj, **kwargs)).run()


@cli.command()
@click.option('--steps', default=1, help='How many releases to roll back to')
@click.pass_context
def rollback(ctx, **kwargs):
    """Roll back to the previous release"""
    RollbackOperation(**dict(**ctx.obj, **kwargs)).run()


def main():
    """Main command group"""
    cli() # pylint: disable=no-value-for-parameter
