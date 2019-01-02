"""
API for selected Data Workspaces management functions.
"""
from collections import namedtuple
import os
from os.path import isdir, join, dirname, abspath, expanduser, curdir
import json

from dataworkspaces import __version__
from .errors import ApiParamError
from .resources.resource import CurrentResources
from .commands.snapshot import get_snapshot_history_file_path

__api_version__ = '0.1'


def get_version():
    return __version__

def get_api_version():
    return __api_version__


def _get_workspace(caller_workspace_arg=None):
    """For commands that execute in the context of a containing
    workspace, find the nearest containging workspace and return
    its absolute path. If the caller provides one, we validate it
    and return it. Otherwise, we search outward from the current directory.
    Throws an ApiParamError exception if the workspace was invalid
    or could not be found.
    """
    if caller_workspace_arg is not None:
        workspace_dir = abspath(expanduser(caller_workspace_arg))
        if not isdir(workspace_dir):
            raise ApiParamError("Workspace directory %s does not exist" %
                                workspace_dir)
        dws_dir = join(workspace_dir, '.dataworkspace')
        if not isdir(dws_dir) or not os.access(dws_dir, os.W_OK):
            raise ApiParamError("Provided directory for workspace %s has not been initialized as a data workspace" % workspace_dir)
        else:
            return workspace_dir
    else:
        curr_dir_abs = abspath(expanduser(curdir))
        curr_base = curr_dir_abs
        while curr_base != '/':
            if isdir(join(curr_base, '.dataworkspace')) and os.access(curr_base, os.W_OK):
                return curr_base
            else:
                curr_base = dirname(curr_base)
        raise ApiParamError("Cound not find an enclosing data workspace starting from %s"%
                            curr_dir_abs)


ResourceInfo=namedtuple('ResourceInfo',
                        ['name', 'role', 'type', 'local_path'])

def get_resource_info(workspace_dir=None):
    """Returns a list of ResourceInfo instances, describing the resources
    defined for this workspace.
    """
    workspace_dir = _get_workspace(workspace_dir)
    current_resources = CurrentResources.read_current_resources(workspace_dir,
                                                                batch=True,
                                                                verbose=False)
    return [
        ResourceInfo(r.name, r.role, r.scheme,
                     r.get_local_path_if_any())
        for r in current_resources.resources
    ]


SnapshotInfo=namedtuple('SnapshotInfo',
                        ['snapshot_number', 'hash', 'tag', 'timestamp', 'message'])


def get_snapshot_history(workspace_dir=None):
    """Get the history of snapshots, starting with the oldest first.
    Returns a list of SnapshotInfo instances, containing the snapshot number,
    hash, tag, timestamp, and message.
    """
    workspace_dir = _get_workpace(workspace_dir)
    with open(get_snapshot_history_file_path(workspace_dir), 'r') as f:
        data = json.load(f)
    return [
        SnapshotInfo(snapshot_number, s['hash'], s['tag'], s['timestamp'],
                     s['message'])
        for (snapshot_number, s) in enumerate(data)
    ]


