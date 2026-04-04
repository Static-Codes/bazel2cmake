from typing import List, Dict, Any, Union
from .models import Target, TargetType, BazelLabel, Select
from .resolver import Resolver

class Generator:

    """Generates a CMakeLists.txt for a provided Bazel project."""
    def __init__(self, resolver: Resolver = None):
        self.output: List[str] = []
        self.resolver = resolver
        self.variable_counter = 0


    def generate_target(self, target: Target):
        
        # Library Generation Rules
        if target.type == TargetType.CC_LIBRARY:
            self.generate_cc_library(target)

        # Binary Generation Rules
        elif target.type == TargetType.CC_BINARY:
            self.generate_cc_binary(target)
        
        # CCTest Generation Rules
        elif target.type == TargetType.CC_TEST:
            self.generate_cc_test(target)
        
        # CCImport Generation Rules for Shared Libraries
        elif target.type == TargetType.CC_IMPORT:
            self.generate_cc_import(target)
        
        # FileGroup Generation Rules
        elif target.type == TargetType.FILEGROUP:
            self.generate_filegroup(target)
        
        # GenRule Generation Rules
        elif target.type == TargetType.GENRULE:
            self.generate_genrule(target)
        
        # ConfigSetting Generation Rules
        elif target.type == TargetType.CONFIG_SETTING:
            self.generate_config_setting(target)


    def generate_config_setting(self, target: Target):
        name = self.get_target_name(target.label)
        option_name = f"ENABLE_{name.upper()}"
        self.output.append(f"option({option_name} \"Enable {name}\" OFF)")


    def generate_cc_library(self, target: Target):
        target_name = self.get_target_name(target.label)
        
        srcs = self.resolve_attribute_value(target_name, "srcs", target.srcs)
        hdrs = self.resolve_attribute_value(target_name, "hdrs", target.hdrs)
        deps = self.resolve_attribute_value(target_name, "deps", target.deps)
        includes = self.resolve_attribute_value(target_name, "includes", target.includes)
        defines = self.resolve_attribute_value(target_name, "defines", target.defines)
        copts = self.resolve_attribute_value(target_name, "copts", target.copts)
        linkopts = self.resolve_attribute_value(target_name, "linkopts", target.linkopts)

        if not srcs and hdrs:
            self.output.append(f"add_library({target_name} INTERFACE)")

            if deps:
                self.output.append(f"target_link_libraries({target_name} INTERFACE {deps})")
            
            if includes:
                self.output.append(f"target_include_directories({target_name} INTERFACE {includes})")
            
            if defines:
                self.output.append(f"target_compile_definitions({target_name} INTERFACE {defines})")

        else:
            self.output.append(f"add_library({target_name} {srcs} {hdrs})")
            if deps:
                self.output.append(f"target_link_libraries({target_name} PRIVATE {deps})")

            if includes:
                self.output.append(f"target_include_directories({target_name} PUBLIC {includes})")
            
            if defines:
                self.output.append(f"target_compile_definitions({target_name} PUBLIC {defines})")

        if copts:
            self.output.append(f"target_compile_options({target_name} PRIVATE {copts})")
        
        if linkopts:
            self.output.append(f"target_link_libraries({target_name} PRIVATE {linkopts})")


    def generate_cc_binary(self, target: Target):
        target_name = self.get_target_name(target.label)
        srcs = self.resolve_attribute_value(target_name, "srcs", target.srcs)
        deps = self.resolve_attribute_value(target_name, "deps", target.deps)
        includes = self.resolve_attribute_value(target_name, "includes", target.includes)
        defines = self.resolve_attribute_value(target_name, "defines", target.defines)
        copts = self.resolve_attribute_value(target_name, "copts", target.copts)
        linkopts = self.resolve_attribute_value(target_name, "linkopts", target.linkopts)
        
        self.output.append(f"add_executable({target_name} {srcs})")
        if deps:
            self.output.append(f"target_link_libraries({target_name} PRIVATE {deps})")
        
        if includes:
            self.output.append(f"target_include_directories({target_name} PRIVATE {includes})")
        
        if defines:
            self.output.append(f"target_compile_definitions({target_name} PRIVATE {defines})")
        
        if copts:
            self.output.append(f"target_compile_options({target_name} PRIVATE {copts})")
        
        if linkopts:
            self.output.append(f"target_link_libraries({target_name} PRIVATE {linkopts})")


    def generate_cc_test(self, target: Target):
        self.generate_cc_binary(target)
        target_name = self.get_target_name(target.label)
        self.output.append(f"add_test(NAME {target_name} COMMAND {target_name})")


    def generate_cc_import(self, target: Target):
        target_name = self.get_target_name(target.label)
        static_library = target.attributes.get("static_library")
        shared_library = target.attributes.get("shared_library")
        interface_library = target.attributes.get("interface_library")
        
        if static_library:
            self.output.append(f"add_library({target_name} STATIC IMPORTED)")
            self.output.append(f"set_target_properties({target_name} PROPERTIES IMPORTED_LOCATION ${{CMAKE_CURRENT_SOURCE_DIR}}/{static_library})")
        
        elif shared_library:
            self.output.append(f"add_library({target_name} SHARED IMPORTED)")
            self.output.append(f"set_target_properties({target_name} PROPERTIES IMPORTED_LOCATION ${{CMAKE_CURRENT_SOURCE_DIR}}/{shared_library})")
            
            if interface_lib:
                self.output.append(f"set_target_properties({target_name} PROPERTIES IMPORTED_IMPLIB ${{CMAKE_CURRENT_SOURCE_DIR}}/{interface_library})")


    def generate_filegroup(self, target: Target):
        target_name = self.get_target_name(target.label)
        srcs = self.resolve_attribute_value(target_name, "srcs", target.srcs)
        
        # For target-based mapping, filegroup uses an INTERFACE library.
        self.output.append(f"add_library({target_name} INTERFACE)")

        # One caveat/edgecase that has been a hassle, is the handling of srcs.
        # add_library(library_name $<TARGET_PROPERTY:fg,SOURCES>) is not guaranteed to be supported across CMake versions.
        # This implementation needs to be further refined, as it currently uses a generic placeholder.
        self.output.append(f"set({target_name}_SRCS {srcs})")


    def generate_genrule(self, target: Target):
        cmd = target.attributes.get("cmd", "")
        outs = target.attributes.get("outs", [])
        srcs_raw = target.srcs
        srcs = self.resolve_attribute_value(target.label.target, "srcs", srcs_raw)
        

        ### NEEDS FIXES ###
        # Once again, this logic lacks nuance due to my inexperience with Bazel.
        # Rough implementation for the genrule command.
        
        # Basic variable replacement for genrule cmd
        # The "add_custom_command" in CMake, doesn't easily allow multiple outs in some variables,
        # This current logic only replaces common outs.
        if outs:
            cmd = cmd.replace("$@", outs[0])
            cmd = cmd.replace("$(OUTS)", " ".join(outs))
        
        if isinstance(srcs_raw, list) and srcs_raw:
            first_src = ""

            if isinstance(srcs_raw[0], BazelLabel):
                first_src = self.get_target_name(srcs_raw[0])

            else:
                first_src = str(srcs_raw[0])
            
            cmd = cmd.replace("$<", first_src)
            cmd = cmd.replace("$(SRCS)", srcs)

        # Handling $(location label)
        # This import can potentially be global
        import re 
        location_matches = re.findall(r"\$\(location ([^\)]+)\)", cmd)
        
        for loc in location_matches:
            label = BazelLabel(loc, current_package=target.label.package)
            target_name = self.get_target_name(label)
            

            ### NEEDS FIXES ###
            # This is a bit simplistic, but often $(location) is used for srcs or outs
            # If it's a target, the current implementation tries to use its output.
            cmd = cmd.replace(f"$(location {loc})", target_name)

        self.output.append(f"add_custom_command(OUTPUT {' '.join(outs)} COMMAND {cmd} DEPENDS {srcs})")
        self.output.append(f"add_custom_target({self.get_target_name(target.label)} ALL DEPENDS {' '.join(outs)})")


    def generate(self, targets: List[Target]) -> str:
        self.output = []
        
        for target in targets:
            self.generate_target(target)
            self.output.append("")

        return "\n".join(self.output)


    def get_target_name(self, label: BazelLabel) -> str:
        if self.resolver:
            return self.resolver.get_cmake_target_name(label)
            
        return label.target


    """ Handling mapping logic for platform specific conditions between Bazel and CMake. """
    def map_condition_to_cmake(self, condition: Any) -> str:
        cond_str = str(condition)
        
        if cond_str == "@platforms//os:linux":
            return "UNIX AND NOT APPLE"
        
        if cond_str == "@platforms//os:windows":
            return "WIN32"
        
        if cond_str == "@platforms//os:macos":
            return "APPLE"
        
        if cond_str == "//conditions:default":
            return "TRUE"
        
        # Currently this logic is incomplete and provides generic mapping for other labels.
        name = cond_str.replace("//", "").replace(":", "_").replace("/", "_").strip("_")
        return f"ENABLE_{name.upper()}"


    def resolve_attribute_value(self, target_name: str, attr_name: str, value: Any) -> str:
        """Resolves an attribute value, and if required, will generate CMake logic for Select."""
        if not isinstance(value, Select):
            
            if isinstance(value, list):
                resolved = []
                
                for inner_value in value:
                    
                    if isinstance(inner_value, BazelLabel):
                        target = self.resolver.resolve(inner_value) if self.resolver else None
                        
                        if target and target.type == TargetType.FILEGROUP:
                            resolved.append(f"${{{self.get_target_name(inner_value)}_SRCS}}")
                        
                        else:
                            resolved.append(self.get_target_name(inner_value))
                    
                    else:
                        resolved.append(str(inner_value))
                
                return " ".join(resolved)
            
            return str(value)

        # Handling Select attributes
        self.variable_counter += 1
        variable_name = f"{target_name}_{attr_name}_{self.variable_counter}"
        
        first = True
        for condition, val in value.conditions.items():
            cmake_cond = self.map_condition_to_cmake(condition)
            if first:
                self.output.append(f"if({cmake_cond})")
                first = False
            
            elif condition == "//conditions:default":
                self.output.append("else()")
            
            else:
                self.output.append(f"elseif({cmake_cond})")
            
            val_str = self.resolve_attribute_value(target_name, attr_name + "_inner", val)
            self.output.append(f"  set({variable_name} {val_str})")
        
        self.output.append("endif()")
        return f"${{{variable_name}}}"
