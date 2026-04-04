from typing import List, Optional, Dict, Any, Set
from enum import Enum, auto


class BazelLabel:
    def __init__(self, label_str: str, current_package: str = "", current_repo: str = ""):
        self.raw_label = label_str
        self.repo = current_repo
        self.package = current_package
        self.target = ""

        if label_str.startswith("@"):
            repo_end = label_str.find("//")
            
            if repo_end != -1:
                self.repo = label_str[1:repo_end]
                label_str = label_str[repo_end:]
            
            else:
                # Handles cases such as "@repo", etc.
                self.repo = label_str[1:]
                label_str = "//"

        if label_str.startswith("//"):

            if ":" in label_str:
                self.package, self.target = label_str[2:].split(":", 1)
            
            else:
                self.package = label_str[2:]
                self.target = self.package.split("/")[-1] if self.package else ""
        
        elif label_str.startswith(":"):
            self.target = label_str[1:]
        
        else:
            # This will result in a relative label without a colon.
            self.target = label_str

   
    """Returning a string representation of the BazelLabel object."""
    def __str__(self) -> str:
        repo_prefix = f"@{self.repo}" if self.repo else ""
        return f"{repo_prefix}//{self.package}:{self.target}"

    """ Overriding the comparison operation for the BazelLabel class """
    def __eq__(self, other_object) -> bool:
        if not isinstance(other_object, BazelLabel):
            return False

        return self.repo == other_object.repo and self.package == other_object.package and self.target == other_object.target

    """ Required to suppress a TypeError, "unhashable type: 'BazelLabel'" """
    def __hash__(self) -> int:
        return hash((self.repo, self.package, self.target))
        

class TargetType(Enum):
    CC_LIBRARY = auto()
    CC_BINARY = auto()
    CC_TEST = auto()
    GENRULE = auto()
    PROTO_LIBRARY = auto()
    CC_IMPORT = auto()
    FILEGROUP = auto()
    CONFIG_SETTING = auto()
    UNKNOWN = auto()

class Select:
    """Represents a Bazel select() expression."""
    def __init__(self, conditions: Dict[str, Any]):
        self.conditions = conditions


    def __add__(self, other) -> Optional["Select"]:
        if isinstance(other, list):
            new_conditions = {key: value + other for key, value in self.conditions.items()}
            return Select(new_conditions)

        elif isinstance(other, Select):
            ### NEEDS FIXES ###
            # This implementation is currently extremely rough.
            # Bazel's Select usually iterates over the same keys or a subset of those keys.
            new_conditions = {}
            for key1, value1 in self.conditions.items():
                for key2, value2 in other.conditions.items():
                    if key1 == key2:
                        new_conditions[key1] = value1 + value2

            return Select(new_conditions)

        return None
        

    def __repr__(self) -> str:
        return f"select({self.conditions})"


class Target:
    """Represents a build target (IR)."""
    def __init__(self, label: BazelLabel, target_type: TargetType):
        self.label = label
        self.type = target_type
        self.srcs: List[str] = []
        self.hdrs: List[str] = []
        self.deps: List[BazelLabel] = []
        self.includes: List[str] = []
        self.defines: List[str] = []
        self.copts: List[str] = []
        self.linkopts: List[str] = []
        self.attributes: Dict[str, Any] = {}

    def __repr__(self) -> str:
        return f"Target({self.label}, type={self.type.name})"
