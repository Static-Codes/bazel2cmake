from typing import Dict, Optional
from .models import BazelLabel, Target

class Resolver:
    """Resolves labels to their appropriate targets across the workspace."""
    def __init__(self):
        self.registry: Dict[BazelLabel, Target] = {}

    def register(self, target: Target):
        self.registry[target.label] = target

    def resolve(self, label: BazelLabel) -> Optional[Target]:
        return self.registry.get(label)

    def get_cmake_target_name(self, label: BazelLabel) -> str:
        # Converts a  BazelLabel into a valid CMake target name
        # For Example:
        # "//package/subpackage:target" -> "package_subpackage_target"
        name = label.package.replace("/", "_")
        if name:
            return f"{name}_{label.target}"
        return label.target
