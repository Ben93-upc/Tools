# UniversalBuilder - README Completo

## 🚀 Panoramica

**UniversalBuilder** è uno script python che consente la compilazione di codice in **C++, Java, Rust, Python** direttamente da Jupyter Notebook, VS Code o script Python, è integrato del wrapper pybind11.

### ✨ Caratteristiche Principali

- 🎯 **Multi-linguaggio**: C++, Java, Rust, Python.
- 🚀 **Parallelizzazione nativa**: Compila **C++, Java, Rust, Python**
- 💾 **Caching intelligente**: Hash-based, salta ricompilazione
- 📊 **Profiling integrato**: Misura tempo compilazione/esecuzione
- 🎨 **Drag-and-drop Jupyter**: Trascinare file e funziona
- 📁 **Multi-file**: Raggruppa automaticamente file dello stesso linguaggio
- 🐍 **Virtual Environment**: Supporto Python venv nativo
- 🔄 **Riconoscimento automatico**: Detected estensione file automaticamente

### 📦 Caso d'uso ideale

Per usare **molteplici linguaggi** (Python, C++, Rust, Java), compilare e testare tutto **da un unico notebook e/o script Python**.

```python
# Una sola linea per compilare 4 linguaggi!
builder.build_and_run_mixed([
    'algorithm.cpp',
    'DataProcessor.java',
    'optimizer.rs',
    'analysis.py'
])
```

---

## 🔧 Installazione

### Prerequisiti

```bash
# Python 3.7+
python --version
pybind11

# Uno o più compilatori:

# C++ (Linux/macOS)
g++ --version

# C++ (Windows)
# Installa: Visual Studio Build Tools o Community Edition
# https://visualstudio.microsoft.com/downloads/

# Java
javac -version

# Rust
rustc --version
```

### Setup

1. **Scarica il file**
```bash
# Copia builder-parallel.py nella tua directory
cp builder-parallel.py ./
```

2. **Importa il modulo**
```python
from builder_parallel import UniversalBuilder

# Verifica disponibilità compilatori
UniversalBuilder.check_toolchain()
```

3. **Compila i file**
```python
builder = UniversalBuilder()
builder.build_and_run_mixed(['main.cpp', 'Main.java'])
```

---

## 💡 Utilizzo Dettagliato

### 1. Configurazione Base

```python
# Setup minimalista (usa defaults)
builder = UniversalBuilder()

# Setup completo
builder = UniversalBuilder(
    verbose=True,                  # Stampa dettagli
    cache_enabled=True,            # Abilita caching
    cache_dir=".builder_cache",    # Dove salvare cache
    python_venv_path='.venv',      # Path al virtual environment
    parallel_enabled=True,         # Abilita parallelizzazione
    max_workers=None               # Auto-detect CPU (8 se 8 core)
)
```

### 2. Compilare C++ Multi-file

```python
# File singolo
builder.build_and_run_cpp('main.cpp')

# Multi-file
builder.build_and_run_cpp([
    'src/main.cpp',
    'src/algorithms.cpp',
    'src/utils.cc',      # Estensioni diverse supportate
    'src/io.cxx'
])

# Con nome eseguibile personalizzato
builder.build_and_run_cpp(['main.cpp', 'utils.cpp'], exe_name='myapp')

# Con profiling (misura tempo)
builder.build_and_run_cpp(['main.cpp'], profile=True)


### 3. Compilare Java Multi-file

```python
# File singolo
builder.build_and_run_java('HelloWorld.java')

# Multi-file
builder.build_and_run_java([
    'Main.java',
    'Database.java',
    'Utils.java'
])

# Con profiling
builder.build_and_run_java(['Main.java', 'Utils.java'], profile=True)

# ⚠️ NOTA: Nome classe deve corrispondere al nome file
#    File: HelloWorld.java → public class HelloWorld { ... }
```

### 4. Compilare Rust

```python
# Release (veloce, ma lento da compilare)
builder.build_and_run_rust('main.rs', optimization='release')

# Debug (veloce da compilare)
builder.build_and_run_rust('main.rs', optimization='debug')

# Con nome personalizzato
builder.build_and_run_rust('main.rs', exe_name='myprogram', optimization='release')

# Con profiling
builder.build_and_run_rust('main.rs', optimization='release', profile=True)
```

### 5. Eseguire Python

```python
# Script singolo
builder.build_and_run_python('script.py')

# Script singolo (usa il venv configurato!)
builder.build_and_run_python('script.py')

# Con profiling
builder.build_and_run_python('script.py', profile=True)

# Script che accede a package nel venv
builder = UniversalBuilder(python_venv_path='.venv')
builder.build_and_run_python('script.py')
```

### 6. Compilazione MIXED

```python
# Una sola chiamata per TUTTI i linguaggi
builder.build_and_run_mixed([
    # C++ multi-file
    'main.cpp',
    'utils.cpp',
    'io.cc',
    
    # Java
    'Main.java',
    'Utils.java',
    
    # Rust
    'optimizer.rs',
    
    # Python
    'analysis.py'
])

```

### 7. Drag-and-Drop (Riconoscimento Automatico)

```python
# Il builder rileva automaticamente il linguaggio!
builder.build_from_file('script.py')       # Esegue con Python
builder.build_from_file('main.cpp')        # Compila con C++
builder.build_from_file('Main.java')       # Compila con Java
builder.build_from_file('main.rs')         # Compila con Rust

```
---

## 📚 API Completa

### Metodi Principali

```python
# 1. BUILD MISTO
builder.build_and_run_mixed(
    file_paths: Union[str, List[str]],
    profile: bool = False,
    parallel: Optional[bool] = None
) -> bool

# 2. C++ MULTI-FILE
builder.build_and_run_cpp(
    src_files: Union[str, List[str]],
    exe_name: Optional[str] = None,
    profile: bool = False
) -> bool

# 3. JAVA MULTI-FILE
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

# 6. DRAG-AND-DROP (AUTO-DETECTION)
builder.build_from_file(
    file_path: str,
    exe_name: Optional[str] = None,
    profile: bool = False,
    **kwargs
) -> bool

# 7. UTILITY
UniversalBuilder.check_toolchain()          # Verifica compilatori
builder.get_parallel_info()                 # Info parallelizzazione
builder.get_python_info()                   # Info Python
builder.get_cache_stats()                   # Info cache
builder.clear_cache()                       # Pulisci cache
```
---

## ⚙️ Configurazione Avanzata

### Setup con Virtual Environment

```bash
# Crea venv
python -m venv .venv

# Attiva (Linux/macOS)
source .venv/bin/activate

# Attiva (Windows)
.venv\Scripts\activate

# Crea builder che usa questo venv
builder = UniversalBuilder(python_venv_path='.venv')

```

### Configurazione Parallelizzazione

```python
import os

# Auto-detect (default)
builder = UniversalBuilder(max_workers=None)
# Usa os.cpu_count() (es. 8 se 8 core)

# Limita a N worker
builder = UniversalBuilder(max_workers=2)

# Disabilita parallelizzazione
builder = UniversalBuilder(parallel_enabled=False)

# Per singola chiamata
builder.build_and_run_mixed(files, parallel=True)   # Forza parallelo
builder.build_and_run_mixed(files, parallel=False)  # Forza sequenziale
```

### Configurazione Cache

```python
# Cache abilitata (default)
builder = UniversalBuilder(cache_enabled=True)

# Cache disabilitata
builder = UniversalBuilder(cache_enabled=False)

# Cache directory personalizzata
builder = UniversalBuilder(cache_dir="/tmp/my_cache")

# Visualizza statistiche
stats = builder.get_cache_stats()
print(f"Cache builds: {stats['num_cached_builds']}")
print(f"Cache size: {stats['cache_size_mb']:.2f} MB")

# Pulisci cache
builder.clear_cache()
```

---

## 🎁 Checklist di Setup

```
[ ] Python 3.7+ installato
[ ] g++ o MSVC installato (per C++)
[ ] javac installato (per Java)
[ ] rustc installato (per Rust)
[ ] builder-parallel.py nella directory
[ ] Creato venv (opzionale ma consigliato)
[ ] Check toolchain: UniversalBuilder.check_toolchain()
[ ] Primo build: builder.build_from_file('test.cpp')

---

### Debug:

```python
# Attiva verbose mode
builder = UniversalBuilder(verbose=True)

# Vedi tutti i comandi che esegue
# Vedi stderr dettagliato
# Vedi output profiling
```

### Comuni Cause di Errore:

1. ❌ File non trovato → Usa path assoluto
2. ❌ Compilatore mancante → Installa tramite gestore pacchetti
3. ❌ Java nome classe diverso → Leggi regole Java
4. ❌ Python module missing → Installa nel venv
5. ❌ Rust lento → Compila in debug durante sviluppo

---

## 🙏 Crediti

Costruito con:
- Python standard library
- GCC/Clang/MSVC
- Java compiler
- Rust compiler
- PyBind11
- concurrent.futures

---

**Versione:** 2.0  
**Data:** Novembre 2025  
**Autore:** UniversalBuilder Project  
**Status:** Production Ready ✅

---

## 🚀 Ready to Build?

```python
from builder_parallel import UniversalBuilder

builder = UniversalBuilder(verbose=True)
UniversalBuilder.check_toolchain()

# Compila quello che vuoi!
builder.build_and_run_mixed(['main.cpp', 'Main.java', 'calc.rs'])
```
