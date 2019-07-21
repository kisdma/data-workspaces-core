# Copyright 2018,2019 by MPI-SWS and Data-ken Research. Licensed under Apache 2.0. See LICENSE.txt.

# The resource factory registry
RESOURCE_TYPES = { }

def register_resource_type(scheme, factory):
    """
    Register a ResourceFactory object for the specified scheme
    """
    global RESOURCE_TYPES
    RESOURCE_TYPES[scheme] = factory

from ..resources.git_resource import GitRepoFactory, GitRepoSubdirFactory
register_resource_type('git', GitRepoFactory)
register_resource_type('git-subdirectory', GitRepoSubdirFactory)

from ..resources.local_file_resource import LocalFileFactory
register_resource_type('file', LocalFileFactory)

from ..resources.rclone_resource import RcloneFactory
register_resource_type('rclone', RcloneFactory)