"""Helper functions"""
# -*- coding: utf-8 -*-
import re
import random
import hashlib
import string
from functools import reduce
from operator import iconcat
import yaml
from ansible.utils.unsafe_proxy import AnsibleUnsafeText

BLOCKSIZE = 65536
DEFAULT_REMOVED_CHARS = ["'", '"', '`', ',', '\\']

# See https://github.com/yaml/pyyaml/issues/234
# See https://stackoverflow.com/questions/25108581/python-yaml-dump-bad-indentation
class YamlDumper(yaml.Dumper): # pylint: disable=too-many-ancestors
    """Identation fix for yaml"""
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


yaml.add_representer(
    AnsibleUnsafeText, lambda d, v: d.represent_scalar('tag:yaml.org,2002:str', str(v)))


def random_string(length=16, with_special_chars=True, remove_chars=None):
    """
    Returns a random alphanumeric string
    """
    characters = string.ascii_uppercase + string.ascii_lowercase + string.digits

    if with_special_chars:
        characters = characters + string.punctuation

    remove_chars = DEFAULT_REMOVED_CHARS if remove_chars is None else remove_chars
    characters = characters.replace(''.join(remove_chars), '')

    return ''.join(random.choice(characters) for _ in range(length))


def load_yaml(contents):
    """Loads a YAML string into an object"""
    return yaml.load(contents, Loader=yaml.FullLoader) if contents else {}


def dump_yaml(contents) -> str:
    """Dumps a yaml into a string"""
    yaml_str = yaml.dump(contents, \
                         Dumper=YamlDumper,
                         allow_unicode=True,
                         explicit_start=True,
                         default_flow_style=False,
                         encoding='utf-8',
                         indent=2)

    return yaml_str.decode('utf-8')


def read_yaml(path):
    """Reads a YAML file and returns its contents"""
    contents = None

    with open(path) as file:
        contents = file.read()
        file.close()

    return load_yaml(contents)


def write_yaml(path, contents=""):
    """Writes a YAML file"""
    with open(path, 'w') as file:
        file.write(dump_yaml(contents))
        file.close()

    return True


def reduce_bool_list(booleans, initial=True):
    """
    Evaluate the validation results

    Reduces from a list of booleans (eg. [True, False, True, True])
    to a single boolean (True or False)
    """
    return reduce(lambda x, cur: x and cur, booleans, initial)


def flatten(subject):
    """flattens a list of lists"""
    return reduce(iconcat, subject, [])


def get_scm_service(repository):
    """Extracts the scm service from the repository"""
    if 'github.com' in repository:
        return 'github'

    return None


def collect(key: str, subject) -> list:
    """Collects entries that are under the same key in a given dict"""
    if not isinstance(subject, dict):
        return []

    collected = []
    for k, value in subject.items():
        if k == key and value:
            collected.append(value)
        elif isinstance(value, dict):
            collected += collect(key, value)
        elif isinstance(value, list):
            collected = collected + [collect(key, v) for v in value if isinstance(v, dict)]

    return flatten(list(filter(None, collected)))


def file_contents_hash(filepath):
    """Returns the MD5 hash of a file's contents"""
    hasher = hashlib.md5()

    with open(filepath, 'rb') as filehandle:
        buf = filehandle.read(BLOCKSIZE)
        while buf:
            hasher.update(buf)
            buf = filehandle.read(BLOCKSIZE)

    return hasher.hexdigest()


def string_hash(txt):
    """Returns the MD5 hash for a given string"""
    return hashlib.md5(txt.encode('utf-8')).hexdigest()


def as_diffable(obj):
    """Returns a dictionary as a frozen set that can be used for comparison"""
    if not isinstance(obj, dict):
        raise ValueError('A diffable should be a dictionary')

    diffable = {}

    for key, value in obj.items():
        if isinstance(value, list):
            if all([isinstance(v, dict) for v in value]):
                value = frozenset([frozenset(v) for v in value])
            else:
                value = frozenset(sorted(value))
        elif isinstance(value, dict):
            value = as_diffable(value)
        elif isinstance(value, set):
            value = frozenset(list(value))

        diffable[key] = value

    return frozenset(diffable.items())


def diff_dictionaries(dict1, dict2):
    """Returns the diff between two dictionaries"""
    return dict(as_diffable(dict1) - as_diffable(dict2))


def get_project_name(repository):
    """Returns the project's name based on the repository"""
    [reponame] = str(repository).split('/')[-1:]

    if not reponame:
        raise ValueError('The repository name specified in the project is invalid')

    return reponame.replace('.git', '')


def get_project_resource_suffix(repository, stage):
    """Returns the name to assign to the vpc after the repository"""
    return '{repo}-{stage}'.format(repo=get_project_name(repository), stage=stage.strip())


def jinja_safe(value):
    """Make sure the value is not of jinja format (eg. {{test}}"""
    return re.sub(r'^{{(.*)}}$', '\\1', value).strip()


def list_chunks(lst, chunk_size):
    """Split list into evenly sized chunks"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
