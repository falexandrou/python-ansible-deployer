"""Helper functions"""
# -*- coding: utf-8 -*-
SCM_GITHUB = 'github'


def scm_commit_url(commit, repository, scm):
    """Returns the commit url"""

    if scm == SCM_GITHUB:
        if repository.startswith('git@github.com:'):
            repository = repository.replace('git@github.com:', '').replace('.git', '')

        return 'https://github.com/{}/commit/{}'.format(repository, commit)

    raise Exception('SCM is not supported yet')


def scm_user_url(user, scm):
    """Returns the url for the SCM user"""
    if scm == SCM_GITHUB:
        return 'https://github.com/{}'.format(user)

    raise Exception('SCM is not supported yet')


class FilterModule:
    """Filters used in the instances role"""
    # pylint: disable=too-few-public-methods,no-self-use
    def filters(self):
        """Filters to be used in the role"""
        return {
            'commit_url': scm_commit_url,
            'user_url': scm_user_url,
        }
