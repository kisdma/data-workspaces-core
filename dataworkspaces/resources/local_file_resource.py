# Copyright 2018,2019 by MPI-SWS and Data-ken Research. Licensed under Apache 2.0. See LICENSE.txt.
"""
Resource for files living in a local directory 
"""
from errno import EEXIST
import os
from os.path import join, exists
from typing import List, Pattern, Tuple, Optional, Set, Union
import json

from dataworkspaces.errors import ConfigurationError
from dataworkspaces.utils.subprocess_utils import call_subprocess
from dataworkspaces.utils.git_utils import GIT_EXE_PATH, is_git_staging_dirty
from dataworkspaces.workspace import Workspace, Resource, LocalStateResourceMixin,\
    FileResourceMixin, SnapshotResourceMixin, JSONDict, JSONList,\
    ResourceRoles, ResourceFactory
import dataworkspaces.resources.hashtree as hashtree
from dataworkspaces.utils.snapshot_utils import move_current_files_local_fs
import dataworkspaces.backends.git as git_backend


LOCAL_FILE = 'file'


def _relative_rsrc_dir_for_git_workspace(role, name):
    return '.dataworkspace/' + LOCAL_FILE + '/' + role + '/' + name


class LocalFileResource(Resource, LocalStateResourceMixin, FileResourceMixin, SnapshotResourceMixin):
    def __init__(self, name:str, role:str, workspace:Workspace,
                 local_path:str, ignore:List[str]=[], compute_hash:bool=False):
        super().__init__(LOCAL_FILE, name, role, workspace)
        self.local_path = local_path
        self.ignore = ignore
        self.compute_hash = compute_hash
        if isinstance(workspace, git_backend.Workspace):
            # if the workspace is a git repo, then we can store our
            # hash files there.
            self.rsrcdir = os.path.join(workspace.workspace_dir,
                                        _relative_rsrc_dir_for_git_workspace(self.role,
                                                                             self.name))
        else:
            # If the workspace is not a git repo, we store the hash
            # files under the local path. Note that this is not going
            # to be replicated to other workspace instances, unless you
            # are using a shared file system (e.g. NFS).
            # TODO: add an API to the workspace for storing this arbitrary
            # data. It will also need changes to the hashtree file.
            self.rsrcdir = os.path.abspath(os.path.join(self.local_path, '.hashes'))
            self.ignore.append('.hashes')

    def get_params(self) -> JSONDict:
        return {
            'resource_type':self.resource_type,
            'name':self.name,
            'role':self.role,
            'local_path':self.local_path,
            'compute_hash':self.compute_hash
        }

    def get_local_path_if_any(self):
        return self.local_path

    def results_move_current_files(self, rel_dest_root:str, exclude_files:Set[str],
                                   exclude_dirs_re:Pattern) -> None:
        move_current_files_local_fs(self.name, self.local_path, rel_dest_root,
                                    exclude_files, exclude_dirs_re,
                                    verbose=self.workspace.verbose)


    def add_results_file(self, data:Union[JSONDict,JSONList], rel_dest_path:str) -> None:
        """save JSON results data to the specified path in the resource.
        """
        assert self.role==ResourceRoles.RESULTS
        abs_dest_path = os.path.join(self.local_path, rel_dest_path)
        parent_dir = os.path.dirname(abs_dest_path)
        if not os.path.isdir(parent_dir):
            os.makedirs(parent_dir)
        with open(abs_dest_path, 'w') as f:
            json.dump(data, f, indent=2)

    def get_local_params(self) -> JSONDict:
        return {} # TODO: local filepath can override global path

    def pull_precheck(self) -> None:
        """Nothing to do, since we donot support sync.
        """
        pass

    def pull(self) -> None:
        """Nothing to do, since we donot support sync.
        """
        pass

    def push_precheck(self) -> None:
        """Nothing to do, since we donot support sync.
        """
        pass

    def push(self) -> None:
        """Nothing to do, since we donot support sync.
        """
        pass


    def snapshot_precheck(self) -> None:
        pass

    def snapshot(self) -> Tuple[Optional[str], Optional[str]]:
        if self.compute_hash:
            h = hashtree.generate_sha_signature(self.rsrcdir, self.local_path, ignore=self.ignore,
                                                verbose=self.workspace.verbose)
        else:
            h = hashtree.generate_size_signature(self.rsrcdir, self.local_path, ignore=self.ignore,
                                                 verbose=self.workspace.verbose)
        assert os.path.exists(os.path.join(self.rsrcdir, h))
        if isinstance(self.workspace, git_backend.Workspace):
            workspace_path = self.workspace.get_workspace_local_path_if_any()
            assert workspace_path is not None
            if is_git_staging_dirty(workspace_path,
                                    subdir=_relative_rsrc_dir_for_git_workspace(self.role, self.name)):
                call_subprocess([GIT_EXE_PATH, 'commit', '-m',
                                 "Add snapshot hash files for resource %s" % self.name],
                                cwd=workspace_path, verbose=self.workspace.verbose)
        return (h, None)


    def restore_precheck(self, hashval):
        # TODO: look at handling of restore - we probably want to do a compare and error out if
        # different. This would mean passing in both the compare and restore hashes.
        if self.compute_hash:
            rc = hashtree.check_sha_signature(hashval, self.rsrcdir, self.local_path, ignore=self.ignore,
                                              verbose=self.workspace.verbose)
        else:
            rc = hashtree.check_size_signature(hashval, self.rsrcdir, self.local_path, ignore=self.ignore,
                                               verbose=self.workspace.verbose)
        if not rc:
            print("ERROR IN RESTORE")
            raise ConfigurationError("Local file structure not compatible with saved hash")

    def restore(self, hashval):
        pass # local files: do nothing to restore

    def delete_snapshot(self, workspace_snapshot_hash:str, resource_restore_hash:str,
                        relative_path:str) -> None:
        pass

    def validate_subpath_exists(self, subpath:str) -> None:
        super().validate_subpath_exists(subpath)
    
    def __str__(self):
        return "Local directory %s in role '%s'" % (self.local_path, self.role)


class LocalFileFactory(ResourceFactory):
    def from_command_line(self, role, name, workspace, local_path, compute_hash):
        """Instantiate a resource object from the add command's arguments"""
        if not os.path.isdir(local_path):
            raise ConfigurationError(local_path + ' does not exist')
        if not os.access(local_path, os.R_OK): 
            raise ConfigurationError(local_path + ' does not have read permission')
        if isinstance(workspace, git_backend.Workspace):
            workspace_path = workspace.get_workspace_local_path_if_any()
            assert workspace_path is not None
            hash_path = join(workspace_path, _relative_rsrc_dir_for_git_workspace(role, name))
            try:
                os.makedirs(hash_path)
                with open(os.path.join(hash_path, 'dummy.txt'), 'w') as f:
                    f.write("Placeholder to ensure directory is added to git\n")
                call_subprocess([GIT_EXE_PATH, 'add',
                                 join(_relative_rsrc_dir_for_git_workspace(role, name), 'dummy.txt')],
                                cwd=workspace_path)
                call_subprocess([GIT_EXE_PATH, 'commit', '-m',
                                 "Adding resource %s" % name],
                                        cwd=workspace_path)
            except OSError as exc:
                if exc.errno == EEXIST and os.path.isdir(hash_path):
                    pass
                else: raise
        else:
            non_git_hashes = join(local_path, '.hashes')
            if not exists(non_git_hashes):
                os.mkdir(non_git_hashes)
        return LocalFileResource(name, role, workspace, local_path, compute_hash=compute_hash)

    def from_json(self, params:JSONDict, local_params:JSONDict,
                  workspace:Workspace) -> LocalFileResource:
        """Instantiate a resource object from saved params and local params"""
        return LocalFileResource(params['name'], params['role'], workspace, params['local_path'],
                                 compute_hash=params['compute_hash'])

    def has_local_state(self) -> bool:
        return True

    def clone(self, params:JSONDict, workspace:Workspace) -> LocalStateResourceMixin:
        """Instantiate a resource that was created remotely. We need to verify that
        the local copy of the data exists -- we are not responsible for making certain
        it is in th correct place.
        TODO: if the local copy does not exist, and we are in interactive (not batch) mode,
        then we should ask the user for the local location and store it in local_params.
        """
        name = params['name']
        local_path = params['local_path']
        local_params = {} # type: JSONDict
        if not exists(local_path):
            raise ConfigurationError("Local files resource %s is missing from %s." % (name, local_path))
        if not isinstance(workspace, git_backend.Workspace):
            non_git_hashes = join(local_path, '.hashes')
            if not exists(non_git_hashes):
                os.mkdir(non_git_hashes)
        return self.from_json(params, local_params, workspace)

    def suggest_name(self, workspace, local_path, compute_hash):
        return os.path.basename(local_path)

