 A Multi-Language Build & Run-Time Orchestrator

**Builder** is a single-file Python class that provides a unified, high-level interface for compiling, running, and managing code across C++, Rust, Java, and Python.

It is designed to eliminate the friction of polyglot development by abstracting away complex build commands (`g++`, `cl`, `javac`, `maturin`, `cargo`) behind a single, intelligent API. It features smart caching, parallel execution, and first-class support for building Python extension modules.

## Key Features

* **Multi-Language Support**: Compiles and runs C++ (.cpp, .cc), Java (.java), Rust (.rs), and Python (.py).
* **Smart Caching**: Automatically hashes source files and skips recompilation if no changes are detected.
* **Parallel Compilation**: The `build_and_run_mixed` method can compile C++, Java, and Rust targets concurrently, saving time on large projects.
* **Dual-Mode Philosophy**: Understands the *purpose* of your build:
    * **Executable Mode (Default)**: Builds standalone executables for C++, Java, and Rust.
    * **Module Mode (Flag-activated)**: Builds libraries/modules intended for *import* into Python.
* **First-Class Module Support**:
    * **C++**: `pybind=True` builds C++ sources into a Python module (.pyd/.so) using **PyBind11**.
    * **Rust**: `pyo3=True` builds a Rust Cargo project into a Python module using **Maturin/PyO3**.
    * **Java**: `jar=True` builds Java sources into a `.jar` library, ready to be loaded by tools like **JPype**.
* **Toolchain Diagnostics**: `check_toolchain()` utility to verify all necessary compilers and tools are installed.
* **Venv-Aware**: Can be pointed to a specific Python virtual environment to find the correct interpreter and includes.
* **Cross-Platform**: Natively handles MSVC on Windows and GCC/Clang on Linux/macOS.

## Requirements

Before use, ensure the necessary compilers and libraries are installed and available in your system's PATH. You can verify your setup by running `builder.check_toolchain()`.

* **Python**: 3.7+
* **For C++ Modules**: `pip install pybind11`
* **For Rust Modules**: `pip install maturin`
* **C++ Toolchain**:
    * Windows: Visual Studio Build Tools (for `cl.exe` and `vcvars64.bat`)
    * Linux/macOS: `g++` or `clang++`
* **Java Toolchain**: Java JDK (for `javac` and `jar`)
* **Rust Toolchain**: `rustc` and `cargo` (via rustup.rs)

## How to Use

### 1. Initialization

Import the class and create an instance. It's recommended to run the toolchain check.

```python
from builder_parallel import UniversalBuilder

# Initialize with parallel execution enabled (default)
builder = UniversalBuilder(
    verbose=True, 
    cache_enabled=True
)

# Check if all compilers are ready
builder.check_toolchain()
2. Building Executables (The "Output" Workflow)This is the default mode. The builder compiles the code into a standalone program and runs it.Python# Build and run a C++ program
builder.build_from_file('my_program.cpp')

# Build and run a multi-file Java program
builder.build_from_file(['MainApp.java', 'Utils.java'])

# Build and run a Rust program
builder.build_from_file('hello.rs', optimization='release')

# Run a Python script (using the configured interpreter)
builder.build_from_file('my_script.py')
3. Building Modules (The "Input" Workflow)This is the most powerful feature. By adding a flag, you tell the builder to create a library for Python to import.Python# --- C++ with PyBind11 ---
# Compiles 'my_module.cpp' into 'my_module.pyd' or 'my_module.so'
# This only *builds* the module, it does not run it.
builder.build_from_file(
    'my_module.cpp', 
    pybind=True, 
    module_name='my_module'
)
# Now in another Python script:
# import my_module
# my_module.do_fast_thing()

# --- Rust with PyO3/Maturin ---
# Compiles the Cargo project in the same directory as 'lib.rs'
# This requires a valid Cargo.toml file.
builder.build_from_file('src/lib.rs', pyo3=True)

# --- Java with JAR ---
# Compiles Java files into a 'MyLibrary.jar' file
# Ready to be loaded by JPype.
builder.build_from_file(
    ['MyLibrary.java', 'Helper.java'], 
    jar=True, 
    jar_name='MyLibrary.jar'
)
4. Parallel Mixed BuildsUse build_and_run_mixed to compile executables from different languages concurrently.Python# This will compile main.cpp, data_processor.java, and logger.rs
# at the same time using a thread pool.
builder.build_and_run_mixed([
    'cpp/main.cpp',
    'java/data_processor.java',
    'rust/logger.rs'
])
5. Managing the CachePython# Clear all cached builds
builder.clear_cache()

# See cache statistics
stats = builder.get_cache_stats()
print(stats)
Public API ReferenceMethodDescriptionbuild_from_file(...)Main router. Detects language and builds an executable or module based on **kwargs.build_and_run_mixed(...)Builds and runs executables from multiple languages, either in sequence or parallel.check_toolchain()Checks for all required compilers (g++, cl, javac, rustc, maturin, etc.).clear_cache()Deletes the cache directory and index.get_cache_stats()Returns a dictionary with statistics on cached items.get_python_info()Returns info on the configured Python interpreter.get_parallel_info()Returns info on the parallel execution settings.
