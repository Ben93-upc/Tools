UniversalBuilder - README (v2.3) 
🚀 Overview 
bluider_parallel.py is a Python script that enables the compilation and execution of code in C++, Java, Rust, Python, and compiles C++ modules into Python via PyBind11. It is designed to work seamlessly from Jupyter Notebooks, VS Code, or any Python script.

✨ Key Features 
🎯 Multi-language: C++, Java, Rust, Python. 
🐍 Native C++ Bindings: Compiles C++ files directly into Python modules (.pyd/.so) using PyBind11. 
🚀 Native Parallelization: Compiles C++, Java, and Rust in parallel. 
💾 Smart Caching: Hash-based, skips recompilation if files have not changed. 
📊 Built-in Profiling: Measures compilation and execution time (where applicable). 
🎨 Jupyter Drag-and-Drop: Drag files into the notebook, build_from_file recognizes them. 
📁 Multi-file: Automatically groups files of the same language (C++ and Java). 
🐍 Virtual Environment: Native support for specifying a Python venv. 
🔄 Automatic Recognition: Detects the file extension and uses the correct compiler.


📦 Ideal Use Case For using multiple languages (Python, C++, Rust, Java), compiling, testing, and executing everything from a single notebook and/or Python script.

Python

# A single line to compile 3 languages and run 1 script!
builder.build_and_run_mixed([
    'algorithm.cpp',
    'DataProcessor.java',
    'optimizer.rs',
    'analysis.py'
])

# Compile a high-performance C++ module for Python
builder.build_from_file('fast_module.cpp', pybind=True)

# ...then use it directly!
import fast_module
print(fast_module.somma(10, 20))


🔧 Installation Prerequisites

Bash

# Python 3.7+
python --version

# PyBind11 (Required for module compilation)
pip install pybind11

# One or more compilers:

# C++ (Linux/macOS)
g++ --version
# (May require 'python3-dev' or similar: sudo apt install python3-dev)

# C++ (Windows)
# Install: Visual Studio Build Tools or Community Edition
# https://visualstudio.microsoft.com/downloads/

# Java
javac -version

# Rust
rustc --version
Setup Download the file

Bash

# Copy UniversalBuilder.py into your directory
# (renamed from builder-parallel.py for clarity)
cp UniversalBuilder.py ./
Import the module

Python

from UniversalBuilder import UniversalBuilder

# Check compiler availability
UniversalBuilder.check_toolchain()
Compile files

Python

builder = UniversalBuilder()
builder.build_and_run_mixed(['main.cpp', 'Main.java'])


💡 Detailed Usage
Basic Configuration

Python

# Minimal setup (uses defaults)
builder = UniversalBuilder()

# Full setup
builder = UniversalBuilder(
    verbose=True,               # Print details
    cache_enabled=True,         # Enable caching
    cache_dir=".builder_cache", # Where to save cache
    python_venv_path='.venv',   # Path to the virtual environment (used for Python and PyBind11)
    parallel_enabled=True,      # Enable parallelization
    max_workers=None            # Auto-detect CPU (e.g., 8 if 8 cores)
)
Compiling Multi-file C++ (Executable)

Python

# Single file
builder.build_and_run_cpp('main.cpp')

# Multi-file
builder.build_and_run_cpp([
    'src/main.cpp',
    'src/algorithms.cpp',
    'src/utils.cc',       # Different extensions supported
    'src/io.cxx'
])

# With custom executable name
builder.build_and_run_cpp(['main.cpp', 'utils.cpp'], exe_name='myapp')

# With profiling (measure time)
builder.build_and_run_cpp(['main.cpp'], profile=True)
Compiling Multi-file Java

Python

# Single file
builder.build_and_run_java('HelloWorld.java')

# Multi-file
builder.build_and_run_java([
    'Main.java',
    'Database.java',
    'Utils.java'
])
# ⚠️ NOTE: 'main' class name must match the first file
Compiling Rust

Python

# Release (fast to run, but slow to compile)
builder.build_and_run_rust('main.rs', optimization='release')

# Debug (fast to compile)
builder.build_and_run_rust('main.rs', optimization='debug')
Running Python

Python

# Single script (uses the configured venv!)
builder.build_and_run_python('script.py')

# Script that accesses packages in the venv
builder = UniversalBuilder(python_venv_path='.venv')
builder.build_and_run_python('script.py')
MIXED Compilation (for Executables)

Python

# A single call to compile and run ALL executables
builder.build_and_run_mixed([
    # C++ multi-file
    'main.cpp',
    'utils.cpp',
    
    # Java
    'Main.java',
    'Utils.java',
    
    # Rust
    'optimizer.rs',
    
    # Python
    'analysis.py'
])
Compiling a PyBind11 Module This method compiles a C++ file into a Python module (.pyd or .so) but does not run it. The compiled module can be imported by Python.

Python

# 1. Compile a single C++ file into a Python module
# The module name will be 'fast_math'
success = builder.build_from_file(
    'fast_math.cpp', 
    pybind=True
)

if success:
    import fast_math
    print(fast_math.add(5, 10))

# 2. Compile multi-file C++ into a module
# You must specify a name for the module
success = builder.build_from_file(
    ['module_main.cpp', 'helper.cpp'], 
    pybind=True, 
    module_name='my_custom_module'
)

if success:
    import my_custom_module
    my_custom_module.do_something()
Drag-and-Drop (Automatic Recognition) The build_from_file method is the smartest way to use the builder. It automatically detects what to do based on the extension and flags.

Python

# Automatically detects language and compiles/runs
builder.build_from_file('script.py')      # Runs with Python
builder.build_from_file('main.cpp')       # Compiles and Runs C++
builder.build_from_file('Main.java')      # Compiles and Runs Java
builder.build_from_file('main.rs')        # Compiles and Runs Rust

# Special recognition for PyBind11
# Detects .cpp, but pybind=True tells it to compile a module
builder.build_from_file(
    'my_module.cpp', 
    pybind=True
)


📚 Full API Main Methods

Python

# 1. MIXED BUILD (Executables)
builder.build_and_run_mixed(
    file_paths: Union[str, List[str]],
    profile: bool = False,
    parallel: Optional[bool] = None
) -> bool

# 2. C++ EXECUTABLE
builder.build_and_run_cpp(
    src_files: Union[str, List[str]],
    exe_name: Optional[str] = None,
    profile: bool = False
) -> bool

# 3. JAVA
builder.build_and_run_java(
    src_files: Union[str, List[str]],
    profile: bool = False
) -> bool

# 4. RUST
builder.build_and_run_rust(
    src_file: str,
    exe_name: Optional[str] = None,
    optimization: str = "release",
    profile: bool = False
) -> bool

# 5. PYTHON
builder.build_and_run_python(
    py_files: Union[str, List[str]],
    profile: bool = False
) -> bool

# 6. PYBIND11 MODULE (Compilation only)
builder.build_pybind_module(
    src_files: Union[str, List[str]], 
    module_name: Optional[str] = None, 
    profile: bool = False
) -> Optional[Path] # Returns the path to the module on success

# 7. DRAG-AND-DROP (AUTO-DETECTION)
builder.build_from_file(
    file_path: Union[str, List[str]],
    exe_name: Optional[str] = None,
    profile: bool = False,
    **kwargs # To pass 'pybind=True', 'module_name', etc.
) -> bool

# 8. UTILITIES
UniversalBuilder.check_toolchain()      # Check compilers
builder.get_parallel_info()             # Parallelization info
builder.get_python_info()               # Python info
builder.get_cache_stats()               # Cache info
builder.clear_cache()                   # Clear cache


⚙️ Advanced Configuration Setup with Virtual Environment The builder will automatically use the specified venv both to run Python scripts (.py) and to find Python and PyBind11 "headers" when compiling modules.

Bash

# Create venv
python -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate

# Install pybind11 IN the venv
pip install pybind11 numpy
Python

# Create builder that uses this venv
builder = UniversalBuilder(python_venv_path='.venv')

# This will compile using the .venv includes
builder.build_from_file('my_module.cpp', pybind=True)

# This will run the script using the .venv interpreter
builder.build_from_file('script.py')
Parallelization Configuration

Python

import os

# Auto-detect (default)
builder = UniversalBuilder(max_workers=None)
# Uses os.cpu_count() (e.g., 8 if 8 cores)

# Limit to N workers
builder = UniversalBuilder(max_workers=2)

# Disable parallelization
builder = UniversalBuilder(parallel_enabled=False)


🎁 Setup Checklist [ ] Python 3.7+ installed [ ] pip install pybind11 (for C++ -> Python Modules) [ ] g++ or MSVC installed (for C++) [ ] 'python-dev' / Build Tools installed (for PyBind11 headers) [ ] javac installed (for Java) [ ] rustc installed (for Rust) [ ] UniversalBuilder.py in directory [ ] Created venv (optional but recommended) [ ] Check toolchain: UniversalBuilder.check_toolchain() [ ] First build: builder.build_from_file('test.cpp') [ ] First PyBind11 build: builder.build_from_file('test_mod.cpp', pybind=True) Debug:

Python

# Enable verbose mode
builder = UniversalBuilder(verbose=True)

# See all commands it runs
# See detailed stderr
# See profiling output
Common Causes of Error: ❌ File not found → Use the correct absolute or relative path. ❌ Missing compiler → Run UniversalBuilder.check_toolchain(). ❌ Python module missing → Install in the venv and point python_venv_path to it. ❌ PyBind11 error 'headers not found' → Ensure pip install pybind11 has been run and that you have python-dev (Linux) or Visual Studio Build Tools (Windows). ❌ ImportError after PyBind11 compilation → Ensure the compiled .pyd/.so is in the same folder as your Python script or in sys.path.


🙏 Credits
Built with:
Python standard library
GCC/Clang/MSVC
Java compiler
Rust compiler
PyBind11
concurrent.futures

Version: 2.3 (PyBind11 Integration) Date: November 2025 Author: Benito Addonizio
