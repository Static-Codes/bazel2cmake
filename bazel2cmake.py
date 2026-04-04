#!/usr/bin/env python3
# Copyright 2026 Static Codes 
# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
sys.dont_write_bytecode = True


import os
import getopt
from lib.generator import Generator
from lib.parser import Parser
from lib.resolver import Resolver

def print_help():
    print(
        "\n[ -h | --help ]\n\n"
        "Displays this message.\n"
        "\n-------------------------------------------------------------------------------\n"
    )

    print(
        "[ -d | --directory=<dir> ]\n\n"
        "By default, bazel2cmake uses the current working directory for execution.\n"
        "By passing this flag the working directory will be changed to reflect the provided directory.\n"
        "\n-------------------------------------------------------------------------------\n"
    )

    print(
        "[ -e | --exclude=<dir1> | --exclude=<dir1:dir2:etc> ]\n\n"
        "By passing this flag the provided directories will be skipped during execution.\n"
        "\n-------------------------------------------------------------------------------\n"
    )

    print(
        "[ -c | --disable-comments ]\n\n"
        "By default, bazel2cmake generates comments in the newly created CMakeLists.txt\n"
        "By passing this flag, these comments will NOT be generated.\n"
        "\n-------------------------------------------------------------------------------\n"
    )

    print(
        "[ -r | --recursive ]\n\n"
        "By default bazel2cmake enables recursive directory walking.\n"
        "By passing this flag, recursion will be enabled.\n"
        "\n-------------------------------------------------------------------------------\n"
    )

def find_build_files(root_dir, recursive=True, exclude_dirs=None):
    if exclude_dirs is None:
        exclude_dirs = []
    
    build_files = []
    if not recursive:

        for build_file in ["BUILD", "BUILD.bazel"]:
            path = os.path.join(root_dir, build_file)

            if os.path.exists(path):
                build_files.append(path)
        
        return build_files

    for root, directory, files in os.walk(root_dir):
        # Skipping hidden directories and .git
        directory[:] = [directory for directory in directory if not directory.startswith('.') and directory != 'build']
        
        relative_root = os.path.relpath(root, root_dir)

        if relative_root != ".":

            # Checking if the current directory is to be excluded
            if any(relative_root == ex or relative_root.startswith(directory + os.sep) for directory in exclude_dirs):
                dirs[:] = [] 
                continue

        if "BUILD" in files:
            build_files.append(os.path.join(root, "BUILD"))

        elif "BUILD.bazel" in files:
            build_files.append(os.path.join(root, "BUILD.bazel"))
    
    return build_files

def main():
    try:
        options, arguments = getopt.getopt(sys.argv[1:], "hd:e:cr", 
            ["help", "directory=", "exclude=", "disable-comments", "--no-recursion"])
    except getopt.GetoptError as err:
        print(err)
        print_help()
        sys.exit(2)

    workspace_root = os.getcwd()
    exclude_dirs = []
    recursive = True
    disable_comments = False

    for option, arguments in options:
        if option in ("-h", "--help"):
            print_help()
            sys.exit()
        
        elif option in ("-d", "--directory"):
            workspace_root = os.path.abspath(arguments)
        
        elif option in ("-e", "--exclude"):
            exclude_dirs = arguments.split(':')
        
        elif option in ("-c", "--disable-comments"):
            disable_comments = True

        elif option in ("-r", "--no-recursion"):
            recursive = False

    build_files = find_build_files(workspace_root, recursive, exclude_dirs)
    
    parser = Parser(workspace_root)
    resolver = Resolver()
    
    workspace_file = os.path.join(workspace_root, "WORKSPACE")
    if not os.path.exists(workspace_file):
        workspace_file = os.path.join(workspace_root, "WORKSPACE.bazel")
    
    project_name = parser.parse_workspace_file(workspace_file)
    
    # Parsing all the resolved targets across all build files recognized by lib.parser
    for build_file in build_files:
        package_path = os.path.relpath(os.path.dirname(build_file), workspace_root)
        
        # Pre-emptively handling root directory issues.
        if package_path == ".":
            package_path = ""
        
        targets = parser.parse_build_file(build_file, package_path)
        
        for target in targets:
            resolver.register(target)
    
    # Performing further parsing and grouping operations to properly map the targets prior to generation.
    targets_by_package = {}
    for target in parser.targets:
        package = target.label.package
        
        # Creating an empty entry since the current package has not been targetted.
        if package not in targets_by_package:
            targets_by_package[package] = []

        targets_by_package[package].append(target)
    
    generator = Generator(resolver)
    watermark = "# This file was generated from using bazel2cmake.\n\n# https://github.com/Static-Codes/bazel2cmake\n\n"
    
    comment = watermark if not disable_comments else ""

    # Generating the individual non-root CMakeLists.txt files for each package.
    packages = sorted(targets_by_package.keys())
    for package in packages:
        cmake_content = generator.generate(targets_by_package[package])
        
        # If a root package is present, it will be handled after execution of the current for loop concludes.
        if package == "":
            continue
            
        package_directory = os.path.join(workspace_root, package)
        output_file = os.path.join(package_directory, "CMakeLists.txt")
        
        with open(output_file, "w") as f:
            f.write(comment + cmake_content)

        print(f"[SUCCESS]: CMakeLists.txt file generated in package sub-directory: '{package_directory}'")

    # Generating the root CMakeLists.txt file, which also handles root packages.
    root_targets = targets_by_package.get("", [])
    root_cmake_content = generator.generate(root_targets)
    
    root_template = f"""{comment}\
cmake_minimum_required(VERSION 3.10)
project({project_name})

enable_testing()

include_directories(${{{{CMAKE_SOURCE_DIR}}}})

{{root_content}}

{{subdirectories}}
"""
    subdirs_content = ""
    for package in packages:
        
        if package == "":
            continue

        subdirs_content += f"add_subdirectory({package})\n"
        
    root_output = os.path.join(workspace_root, "CMakeLists.txt")
    
    with open(root_output, "w") as f:    
        f.write(root_template.format(
            root_content=root_cmake_content,
            subdirectories=subdirs_content
        ))
    
    print(f"[SUCCESS]: CMakeLists.txt file generated in project root directory: '{workspace_root}'")

if __name__ == "__main__":
    main()
