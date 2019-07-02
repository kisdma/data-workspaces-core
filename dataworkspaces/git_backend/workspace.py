"""
Subclasses of workspace abstract classes for workspace APIs.
"""

from os.path import exists
import json
from typing import Dict, Any, Iterable, Optional, List, Tuple, NamedTuple

import dataworkspaces.workspace as ws
from dataworkspaces.workspace import JSONDict
from dataworkspaces.errors import ConfigurationError, InternalError
from dataworkspaces.utils.git_utils import commit_changes_in_repo


CONFIG_FILE_PATH='.dataworkspace/config.json'
LOCAL_PARAMS_PATH='.dataworkspace/local_params.json'
RESOURCES_FILE_PATH='.dataworkspace/resources.json'
RESOURCE_LOCAL_PARAMS_PATH='.dataworkspaces/resource_local_params.json'
SNAPSHOT_DIR_PATH='.dataworkspace/snapshots'
SNAPSHOT_METADATA_DIR_PATH='.dataworkspace/snapshot_metadata'


class Workspace(ws.Workspace, ws.SyncedWorkspaceMixin):
    def __init__(self, workspace_dir:str, batch:bool=False,
                 verbose:bool=False):
        self.workspace_dir = workspace_dir
        cf_data = self._load_json_file(CONFIG_FILE_PATH)
        super().__init__(cf_data['name'], cf_data['dws-version'], batch, verbose)
        self.global_params = cf_data['global_params']
        self.local_params = self._load_json_file(LOCAL_PARAMS_PATH)
        self.resource_params = self._load_json_file(RESOURCES_FILE_PATH)
        self.resource_params_by_name = {} # type: Dict[str, JSONDict]
        for r in self.resource_params:
            self.resource_params_by_name[r['name']] = r
        self.resource_local_params_by_name = \
            self._load_json_file(RESOURCE_LOCAL_PARAMS_PATH) # type: Dict[str,JSONDict]

    def _load_json_file(self, relative_path):
        f_path = join(self.workspace_dir, relative_path)
        if not exists(f_path):
            raise ConfigurationError("Did not find workspace metadata file %s"
                                     % f_path)
        with open(f_path, 'r') as f:
            return json.load(f)

    def _save_json_to_file(self, obj, relative_path):
        f_path = join(self.workspace_dir, relative_path)
        with open(f_path, 'r') as f:
            json.dump(obj, f_path, indent=2)

    def get_global_params(self) -> JSONDict:
        """Get a dict of configuration parameters for this workspace,
        which apply across all instances.
        """
        return self.global_params

    def get_local_params(self) -> JSONDict:
        """Get a dict of configuration parameters for this particular
        install of the workspace (e.g. local filesystem paths, hostname).
        """
        return self.local_params

    def set_global_param(self, name:str, value:Any) -> None:
        """Setting does not necessarily take effect until save() is called"""
        data = self.get_global_params()
        data[name] = value
        self._save_json_to_file({'name':self.name,
                                 'dws-version':self.dws_version,
                                 'global_params':data},
                                CONFIG_FILE_PATH)

    def set_local_param(self, name:str, value:Any) -> None:
        data = self.get_local_params()
        data[name] = value
        self._save_json_to_file(data, LOCAL_PARAMS_PATH)

    def get_resource_names(self) -> Iterable[str]:
        return self.resource_params_by_name.keys()

    def _get_resource_params(self, resource_name) -> JSONDict:
        """Get the parameters for this resource from the workspace's
        metadata store - used when instantitating resources. Show
        throw an exception if resource does not exist.
        """
        if resource_name not in self.resource_params_by_name:
            raise ConfigurationError("A resource by the name '%s' does not exist in this workspace"%
                                     resource_name)
        return self.resource_params_by_name[resource_name]

    def _get_resource_local_params(self, resource_name:str) -> Optional[JSONDict]:
        """If a resource has local parameters defined for it, return them.
        Otherwise, return None.
        """
        if resource_name in self.resource_local_params_by_name:
            return self.resource_local_params_by_name[resource_name]
        else:
            return None

    def _add_params_for_resource(self, resource_name:str, params:JSONDict) -> None:
        """
        Add the necessary state for a new resource to the workspace.
        """
        assert params['name']==resource_name
        self.resource_params.append[params]
        self.resource_params_by_name[resource_name] = params
        self._save_json_to_file(self.resource_params, RESOURCES_FILE_PATH)

    def _add_local_params_for_resource(self, resource_name:str,
                                       local_params:JSONDict)->None:
        """
        Add local params either for a new or cloned resource.
        """
        self.resource_local_params_by_name[resource_name] = local_params
        self._save_json_to_file(self.resource_local_params_by_name,
                                RESOURCE_LOCAL_PARAMS_PATH)

    def save(self) -> None:
        """Save the current state of the workspace"""
        commit_changes_in_repo(self.workspace_dir, "", verbose=self.verbose)

    def pull_prechecks(self, only:Optional[List[str]]=None,
                       skip:Optional[List[str]]=None,
                       only_workspace:bool=False) -> None:
        pass

    def pull(self, only:Optional[List[str]]=None,
             skip:Optional[List[str]]=None,
             only_workspace:bool=False) -> None:
        """Download latest updates from remote origin. By default,
        includes any resources that support syncing via the
        LocalStateResourceMixin.
        """
        pass

    def push_prechecks(self, only:Optional[List[str]]=None,
                       skip:Optional[List[str]]=None,
                       only_workspace:bool=False) -> None:
        pass

    def push(self, only:Optional[List[str]]=None,
             skip:Optional[List[str]]=None,
             only_workspace:bool=False) -> None:
        """Upload updates to remote origin. By default,
        includes any resources that support syncing via the
        LocalStateResourceMixin.
        """
        pass


def load_workspace(workspace_dir:str, batch=False, verbose=False) -> ws.Workspace:
    return Workspace(workspace_dir, batch, verbose)