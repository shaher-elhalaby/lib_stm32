#This file is NOT used by sbuilder.py, it is here for reference and manual use.
#sbuilder.py uses the conan-generated toolchain file.
#This template can be used for projects that don't use Conan.

# --- Toolchain for arm-none-eabi-gcc  ---
set(CMAKE_SYSTEM_NAME               Generic)
set(CMAKE_SYSTEM_PROCESSOR          arm)
# Use STATIC_LIBRARY for try-compile in this cross-compile context
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)
# Assume compiler works for cross-compilation context to avoid CMake trying
# to link test executables against missing host libraries during configure.
set(CMAKE_C_COMPILER_WORKS TRUE CACHE BOOL "Assume C compiler works for cross-compilation")
set(CMAKE_CXX_COMPILER_WORKS TRUE CACHE BOOL "Assume C++ compiler works for cross-compilation")

# --- Cross-compilation Tools ---
set(TOOLCHAIN_PREFIX                arm-none-eabi-)
set(CMAKE_C_COMPILER                ${TOOLCHAIN_PREFIX}gcc)
set(CMAKE_CXX_COMPILER              ${TOOLCHAIN_PREFIX}g++)
set(CMAKE_ASM_COMPILER              ${CMAKE_C_COMPILER})
set(CMAKE_AR                        ${TOOLCHAIN_PREFIX}ar)
set(CMAKE_OBJCOPY                   ${TOOLCHAIN_PREFIX}objcopy)
set(CMAKE_RANLIB                    ${TOOLCHAIN_PREFIX}ranlib)

# --- Build Flags (Configured via manifest) ---
# We keep these empty here so they don't conflict with manifest flags
set(CMAKE_C_FLAGS_INIT "" CACHE STRING "C Compiler Base Flags" FORCE)
set(CMAKE_CXX_FLAGS_INIT "" CACHE STRING "C++ Compiler Base Flags" FORCE)
set(CMAKE_ASM_FLAGS_INIT "" CACHE STRING "ASM Compiler Flags" FORCE)
set(CMAKE_EXE_LINKER_FLAGS_INIT "" CACHE STRING "Linker Flags" FORCE)

# --- Search Paths ---
set(CMAKE_FIND_ROOT_PATH "C:/Program Files (x86)/GNU Arm Embedded Toolchain/10 2021.10")
set(CMAKE_PROGRAM_PATH "C:/Program Files (x86)/GNU Arm Embedded Toolchain/10 2021.10/bin")
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)