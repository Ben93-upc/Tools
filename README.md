A Smart Orchestrator for Polyglot Development**

It is a Python class that solves this problem. It acts as a unified "control panel" for compiling and running code across these different languages. By abstracting away the underlying commands, it provides a single, simple, and intelligent interface (`build_from_file`) for all build tasks.

Its power lies in three key areas:

1.  **Smart Caching:** It hashes source files and skips recompilation if nothing has changed. This is critical for rapid iteration, saving immense amounts of time that would otherwise be spent waiting for compilers.
2.  **Parallel Execution:** The `build_and_run_mixed` method can compile C++, Java, and Rust projects *concurrently*, significantly speeding up full project builds by utilizing all available CPU cores.
3.  **Dual-Purpose Philosophy:** The builder is uniquely intelligent because it understands *why* you are building.
    * By default, it creates standalone **executables** (an "output" of your workflow).
    * But by adding a simple flag (e.g., `pybind=True`, `pyo3=True`, or `jar=True`), it switches modes to build **importable modules** (an "input" for your Python code).

This dual-mode philosophy is its greatest strength. A Python developer can write a high-performance C++ or Rust function and, with a single command (`builder.build_from_file('lib.rs', pyo3=True)`), compile it into a Python-native module, ready for import. It handles all the complexity of PyBind11 and Maturin automatically.

This tool is ideal for rapid prototyping, creating high-performance Python extensions, and managing complex polyglot projects. The `UniversalBuilder` removes the DevOps burden from the developer, allowing them to focus on writing code, not on managing compilers. It streamlines the polyglot workflow, making it fast, intelligent, and seamless.
