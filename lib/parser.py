from typing import List, Dict, Any, Callable, Union
from .models import Target, BazelLabel, TargetType, Select
import os

class Parser:
    """Parses BUILD files by executing them in a global environment."""
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.targets: List[Target] = []
        self.current_package = ""
        self.workspace_name = "GeneratedCMakeProject"


    def add_target(self, target_type: TargetType, **kwargs):
        name = kwargs.get("name")
        if not name:
            return

        label = BazelLabel(f":{name}", current_package=self.current_package)
        target = Target(label, target_type)
        
        # The labels themselves are not modified below, however, the labels within them are resolved.
        target.srcs = self.resolve_labels_in_attribute(kwargs.get("srcs", []))
        target.hdrs = self.resolve_labels_in_attribute(kwargs.get("hdrs", []))
        target.deps = self.resolve_labels_in_attribute(kwargs.get("deps", []))
        target.includes = kwargs.get("includes", [])
        target.defines = kwargs.get("defines", [])
        target.copts = kwargs.get("copts", [])
        target.linkopts = kwargs.get("linkopts", [])
        target.attributes = kwargs
        self.targets.append(target)


    def do_glob(self, include: List[str], exclude: List[str] = None, exclude_directories: int = 1, allow_empty: bool = True) -> List[str]:
        import glob
        import fnmatch
        
        files = []
        package_dir = os.path.join(self.workspace_root, self.current_package)
        
        for pattern in include:
            
            # Instead of passing this condition as a function parameter;
            # Initializing this boolean within the loop is the most optimal solution.
            recursive = "**" in pattern

            matches = glob.glob(os.path.join(package_dir, pattern), recursive=recursive)
            for m in matches:
                if exclude_directories and os.path.isdir(m):
                    continue
                rel_path = os.path.relpath(m, package_dir)
                files.append(rel_path)
        
        if exclude:
            files = [f for f in files if not any(fnmatch.fnmatch(f, pat) for pat in exclude)]
            
        return sorted(list(set(files)))


    def get_globals(self) -> Dict[str, Any]:
        return {
            "cc_library": lambda **kwargs: self.add_target(TargetType.CC_LIBRARY, **kwargs),
            "cc_binary": lambda **kwargs: self.add_target(TargetType.CC_BINARY, **kwargs),
            "cc_test": lambda **kwargs: self.add_target(TargetType.CC_TEST, **kwargs),
            "cc_import": lambda **kwargs: self.add_target(TargetType.CC_IMPORT, **kwargs),
            "filegroup": lambda **kwargs: self.add_target(TargetType.FILEGROUP, **kwargs),
            "genrule": lambda **kwargs: self.add_target(TargetType.GENRULE, **kwargs),
            "proto_library": lambda **kwargs: self.add_target(TargetType.PROTO_LIBRARY, **kwargs),
            "config_setting": lambda **kwargs: self.add_target(TargetType.CONFIG_SETTING, **kwargs),
            "glob": self.do_glob,
            "select": self.select,
            "package": lambda **kwargs: None,
            "load": lambda *args, **kwargs: None,
            "exports_files": lambda *args, **kwargs: None,
            "licenses": lambda *args: None,
            "workspace": self.workspace,
            "http_archive": lambda **kwargs: None,
        }

    
    def parse_build_file(self, file_path: str, package_path: str) -> List[Target]:
        self.current_package = package_path
        old_targets_count = len(self.targets)

        # Using the contents from the provided file_path in a call to get_globals
        with open(file_path, "r") as f:
            content = f.read()
            exec(content, self.get_globals())
        
        return self.targets[old_targets_count:]


    def parse_workspace_file(self, file_path: str):
        self.workspace_name = "GeneratedCMakeProject"
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                content = f.read()
                exec(content, self.get_globals())
        return self.workspace_name


    def resolve_labels_in_attribute(self, attribute_value: Any):
        if isinstance(attribute_value, str):
            # If these conditions are not met, the attribute_value itself is returned.
            if attribute_value.startswith("//") or attribute_value.startswith(":") or attribute_value.startswith("@"):
                return BazelLabel(attribute_value, current_package=self.current_package)

        # Recursive call to return a list of BazelLabel(s)
        elif isinstance(attribute_value, list):
            return [self.resolve_labels_in_attribute(value) for value in attribute_value]
        
        # Recursive call to return a dict of BazelLabel(s)
        elif isinstance(attribute_value, dict):
            return {key: self.resolve_labels_in_attribute(value) for key, value in attribute_value.items()}
        
        # 
        elif isinstance(attribute_value, Select):
            return Select(self.resolve_labels_in_attribute(attribute_value.conditions))
        
        return attribute_value


    def select(self, conditions: Dict[str, Any]) -> Select:
        return Select(conditions)


    def workspace(self, name: str):
        self.workspace_name = name