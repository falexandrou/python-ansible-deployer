# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import os
from datetime import datetime
from ansible.utils.unsafe_proxy import AnsibleUnsafeText
from stackmate.helpers import read_yaml, write_yaml, get_project_name, \
                              get_project_resource_suffix, list_chunks

OUTPUT_PATH = '/tmp/somefile.yml'
FILE_CONTENT = {
    'something': 123,
    'is_cool': True,
    'funny': 53.42,
    'list_of_things': [
        'a list',
        'of things',
    ],
    'something_else': {
        'somewhere': 'far',
        'beyond': 10,
    },
    'set_of_options': {'abc', 'def', 'ghi', 'jkl'},
    'name': AnsibleUnsafeText('my name is John'),
    'created_at': datetime.now(),
}


def describe_read_yaml():
    def it_reads_the_file(project_path):
        file = os.path.join(project_path, 'config.yml')
        content = read_yaml(file)
        assert content
        assert isinstance(content, dict)
        assert content['framework'] == 'rails'

    def it_writes_the_file():
        assert write_yaml(OUTPUT_PATH, FILE_CONTENT) is True

    def it_can_read_a_generated_file():
        assert write_yaml(OUTPUT_PATH, FILE_CONTENT)
        retrieved = read_yaml(OUTPUT_PATH)
        assert retrieved
        assert retrieved == FILE_CONTENT


def describe_get_project_name():
    def it_returns_the_vpc_name_according_to_the_repository(project):
        assert project.repository
        project_name = get_project_name(project.repository)
        assert project_name == 'stackmate-cli'


def describe_get_project_resource_suffix():
    def it_returns_the_project_resource_suffix(project, stage):
        suffix = get_project_resource_suffix(project.repository, stage)
        assert project.repository
        assert suffix == 'stackmate-cli-production'


def describe_list_chunks():
    lst = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]
    expected_chunks = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 0]]
    assert list_chunks(lst, chunk_size=4) == expected_chunks
