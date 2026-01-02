from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.files import copy, save
import os
import yaml
from pathlib import Path

class Lib_stm32Conan(ConanFile):
    name = "lib_stm32"
    version = "1.0.0"

    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # 'project.package.shared' is guaranteed to be a boolean by sbuilder.py
    default_options = {"shared": False, "fPIC": True}

    # Export manifest and source directories
    exports_sources = ".vsetting/manifest.yaml", ".vsetting/toolchains/*", "02-SRC/*", "include/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        
        pass
        


    def _generate_cmake_lists(self, manifest):
        """Internal helper to generate CMakeLists.txt from manifest in the cache."""
        # Use 'package' config by default for conan create
        cfg_name = 'package'
        if cfg_name not in manifest.get('configurations', {}):
            # Fallback to default_config if 'package' is missing
            cfg_name = manifest.get('default_config', 'build')
            
        cfg = manifest['configurations'][cfg_name] 
        
        target_name = manifest.get('name', 'project').replace('-', '_')
        out_type = cfg.get('output_type', 'static')
        
        # Simple header-only check
        if out_type == 'header_only':
             cmake = f"cmake_minimum_required(VERSION 3.15)\nproject({target_name} NONE)\n"
             cmake += f"add_library({target_name} INTERFACE)\n"
             return cmake

        cmake = [
            "cmake_minimum_required(VERSION 3.15)",
            f"project({target_name} LANGUAGES C CXX ASM)",
            "set(CMAKE_CXX_STANDARD 17)",
            ""
        ]

        # Gather sources based on glob-like patterns from manifest
        # In the cache, project_dir is the current directory
        sources = []
        
        # Combine src_path and src_cfg_path for compilation (local build in cache)
        # Note: cfg.get returns the lists from manifest.yaml directly
        src_patterns = cfg.get('src_path', []) + cfg.get('src_cfg_path', [])
        
        for pat in src_patterns:
            # Convert glob to cmake format or just use file(GLOB)
            # We use ${{ }} to escape curly braces for Python f-string so they appear as {{ }} for CMake (if needed)
            # Actually, for CMake file(GLOB ...), we just need the path. 
            # ${CMAKE_CURRENT_SOURCE_DIR} needs to be generated.
            # In Python f-string, ${{ produces {.
            cmake.append(f'file(GLOB_RECURSE SRC_{len(sources)} RELATIVE ${{CMAKE_CURRENT_SOURCE_DIR}} "{pat}")')
            sources.append(f"${{SRC_{len(sources)}}}")

        if out_type == 'executable':
            cmake.append(f"add_executable({target_name} {' '.join(sources)})")
        else:
            lib_type = "STATIC" if out_type == 'static' else "SHARED"
            cmake.append(f"add_library({target_name} {lib_type} {' '.join(sources)})")

        # Include paths (Standard)
        inc_dirs = []
        for pat in cfg.get('inc_path', []):
            # We assume patterns like 'include/**' or '02-SRC/**/*.h'
            # For CMake, we want the base directories
            base = pat.split('/*')[0]
            if base not in inc_dirs:
                inc_dirs.append(base)

        # Config Include paths (Build only, not exported)
        inc_cfg_dirs = []
        for pat in cfg.get('inc_cfg_path', []):
            base = pat.split('/*')[0]
            if base not in inc_cfg_dirs and base not in inc_dirs:
                inc_cfg_dirs.append(base)
        
        if inc_dirs or inc_cfg_dirs:
            cmake.append(f"target_include_directories({target_name} PUBLIC")
            # Standard: Build and Install interfaces
            for d in inc_dirs:
                cmake.append(f"    $<BUILD_INTERFACE:${{CMAKE_CURRENT_SOURCE_DIR}}/{d}>")
                cmake.append(f"    $<INSTALL_INTERFACE:include>")
            # Config: Build interface only
            for d in inc_cfg_dirs:
                cmake.append(f"    $<BUILD_INTERFACE:${{CMAKE_CURRENT_SOURCE_DIR}}/{d}>")
            cmake.append(")")

        # Compile options
        c_flags = cfg.get('compiler_flags', [])
        if c_flags:
            cmake.append(f"target_compile_options({target_name} PRIVATE {' '.join(c_flags)})")

        # Linker flags
        l_flags = cfg.get('linker_flags', [])
        if l_flags:
            cmake.append(f"target_link_options({target_name} PRIVATE {' '.join(l_flags)})")

        # Linker flags/script if any
        ls = cfg.get('linker_script')
        if ls:
            # Note: We expect the linker script to be in exports_sources
            cmake.append(f"target_link_options({target_name} PRIVATE -T${{CMAKE_CURRENT_SOURCE_DIR}}/{ls})")
            
        if cfg.get('use_nosys_specs'):
            cmake.append(f"target_link_options({target_name} PRIVATE --specs=nosys.specs)")

        # Install rules
        cmake.append(f"install(TARGETS {target_name} EXPORT {target_name}Targets DESTINATION lib)")
        cmake.append(f"install(EXPORT {target_name}Targets DESTINATION lib/cmake/{target_name})")
        
        # Install headers (only standard include paths)
        for d in inc_dirs:
             cmake.append(f'install(DIRECTORY ${{CMAKE_CURRENT_SOURCE_DIR}}/{d}/ DESTINATION include OPTIONAL FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp")')
             
        # Install sources (only standard src paths) if output_type implies source distribution
        # We iterate over unique base directories of src_path
        src_dirs_to_install = []
        for pat in cfg.get('src_path', []):
             base = pat.split('/*')[0]
             if base not in src_dirs_to_install:
                 src_dirs_to_install.append(base)
        
        for d in src_dirs_to_install:
             cmake.append(f'install(DIRECTORY ${{CMAKE_CURRENT_SOURCE_DIR}}/{d}/ DESTINATION src OPTIONAL FILES_MATCHING PATTERN "*.c" PATTERN "*.cpp" PATTERN "*.s" PATTERN "*.S")')

        return "\n".join(cmake)


    def generate(self):
        # 1. Standard Conan generators
        deps = CMakeDeps(self)
        deps.generate()
        
        tc = CMakeToolchain(self)
        # Use the toolchain file exported to .vsetting if it exists
        manifest_path = Path(self.source_folder) / ".vsetting" / "manifest.yaml"
        if manifest_path.exists():
            with open(manifest_path, "r") as f:
                manifest = yaml.safe_load(f)
            
            # Find toolchain for current (package) config
            cfg = manifest.get('configurations', {}).get('package', manifest.get('configurations', {}).get('build', {}))
            tc_name = cfg.get('toolchain_file')
            if tc_name:
                tc_file = Path(self.source_folder) / ".vsetting" / "toolchains" / tc_name
                if tc_file.exists():
                    tc.user_toolchain = [str(tc_file)]
                    # Force Cross-compilation settings to override 'default' profile (Windows/x86_64)
                    tc.variables["CMAKE_SYSTEM_NAME"] = "Generic"
                    tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "arm"
                    tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
                    
                    # Try to disable architecture flags (e.g. -m64) which cause errors for ARM
                    try:
                        tc.blocks["arch_flags"].enabled = False
                    except Exception:
                        pass

                    print(f"Injecting user toolchain: {tc_file}")

                    # Also force compiler if defined in manifest to prevent MinGW detection
                    compiler_cfg = cfg.get('compiler')
                    if compiler_cfg and isinstance(compiler_cfg, str):
                        # Simple heuristic: if compiler is 'arm-none-eabi-gcc', assume g++
                        cc = compiler_cfg
                        cxx = compiler_cfg.replace('gcc', 'g++') if 'gcc' in compiler_cfg else compiler_cfg
                        tc.variables["CMAKE_C_COMPILER"] = cc
                        tc.variables["CMAKE_CXX_COMPILER"] = cxx
                        tc.variables["CMAKE_ASM_COMPILER"] = cc
        
        tc.generate()

        # 2. Self-generate CMakeLists.txt if building in cache
        if manifest_path.exists():
            with open(manifest_path, "r") as f:
                manifest = yaml.safe_load(f)
            cmake_content = self._generate_cmake_lists(manifest)
            save(self, os.path.join(self.source_folder, "CMakeLists.txt"), cmake_content)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Copy the generated CMakeLists.txt to the package folder for the deployer
        copy(self, "CMakeLists.txt", self.source_folder, self.package_folder)

    def package_info(self):
        target_name = "lib_stm32".replace('-', '_')
        self.cpp_info.libs = [target_name]