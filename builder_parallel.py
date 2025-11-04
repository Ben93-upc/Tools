import os
import sys
import subprocess
import platform
import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Union
from contextlib import contextmanager
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import threading

try:
    import pybind11
    PYBIND11_AVAILABLE = True
except ImportError:
    PYBIND11_AVAILABLE = False

class UniversalBuilder:
    """
    Una classe per compilare ed eseguire C++, Java, Rust, Python e wrapper PyBind11 
    con supporto drag-and-drop, caching intelligente, profiling, multi-file e PARALLELIZZAZIONE NATIVA.
    
    Supporta compilazione simultanea di file con estensioni diverse:
    - C++: .cpp, .cc, .cxx
    - Java: .java
    - Rust: .rs
    - Python: .py
    - PyBind11: .cpp (con keyword speciale)
    
    VERSIONE: 2.3 - INTEGRAZIONE PyBind11
    """
    # Configurazione esplicita dei flag del compilatore
    MSVC_CPP_FLAGS = "/O2 /MD /std:c++14 /EHsc"
    # MODIFICATO: Flag specifici per PyBind11 (usa /LD per creare una DLL/pyd)
    MSVC_PYBIND_FLAGS = "/O2 /MD /std:c++14 /EHsc /LD" 
    GCC_CPP_FLAGS = "-O3 -Wall -std=c++14"
    # MODIFICATO: Flag specifici per PyBind11 (usa -shared e -fPIC per un .so)
    GCC_PYBIND_FLAGS = "-O3 -Wall -shared -std=c++14 -fPIC"

    # Mapping estensioni -> linguaggio
    EXTENSION_MAP = {
        '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp',
        '.java': 'java',
        '.rs': 'rust',
        '.py': 'python'
    }

    def __init__(self, verbose: bool = True, cache_enabled: bool = True, 
                 cache_dir: str = ".builder_cache", python_venv_path: Optional[str] = None,
                 parallel_enabled: bool = True, max_workers: Optional[int] = None):
        """
        Inizializza il builder.
        Args:
            verbose: Se True, stampa comandi e output dettagliati.
            cache_enabled: Se True, abilita il caching intelligente.
            cache_dir: Directory per i file cache.
            python_venv_path: Percorso al virtual environment Python.
            parallel_enabled: Se True, abilita la compilazione parallela.
            max_workers: Numero massimo di worker paralleli (None = auto-detect dal numero di CPU).
        """
        self.verbose = verbose
        self.system = platform.system()
        self.cache_enabled = cache_enabled
        self.cache_dir = Path(cache_dir)
        self.python_venv_path = python_venv_path
        self.parallel_enabled = parallel_enabled
        
        # Configura numero di worker paralleli
        if max_workers is None:
            self.max_workers = os.cpu_count() or 2
        else:
            self.max_workers = max_workers
        
        if self.verbose and self.parallel_enabled:
            print(f"⚙️  Parallelizzazione abilitata: {self.max_workers} worker")
        
        # Configura Python interpreter
        self._configure_python_interpreter()
        
        # Crea directory cache se non esiste
        if self.cache_enabled:
            self.cache_dir.mkdir(exist_ok=True)
            self._load_cache_index()
        else:
            self.cache_index = {}

    def _configure_python_interpreter(self):
        """Configura l'interprete Python da usare (default o venv)."""
        if self.python_venv_path:
            venv_path = Path(self.python_venv_path)
            
            if venv_path.is_dir():
                if self.system == "Windows":
                    python_exe = venv_path / "Scripts" / "python.exe"
                else:
                    python_exe = venv_path / "bin" / "python"
            else:
                python_exe = venv_path
            
            if python_exe.exists():
                self.python_interpreter = str(python_exe)
                if self.verbose:
                    print(f"✅ Python interpreter configurato: {self.python_interpreter}")
            else:
                if self.verbose:
                    print(f"⚠️  Python venv non trovato in {self.python_venv_path}, uso default")
                self.python_interpreter = sys.executable
        else:
            self.python_interpreter = sys.executable

    def _load_cache_index(self):
        """Carica l'indice cache da disco."""
        cache_index_file = self.cache_dir / "index.json"
        try:
            if cache_index_file.exists():
                with open(cache_index_file, 'r') as f:
                    self.cache_index = json.load(f)
            else:
                self.cache_index = {}
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Errore caricamento cache: {e}")
            self.cache_index = {}

    def _save_cache_index(self):
        """Salva l'indice cache su disco."""
        if not self.cache_enabled:
            return
        cache_index_file = self.cache_dir / "index.json"
        try:
            with open(cache_index_file, 'w') as f:
                json.dump(self.cache_index, f, indent=2)
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Errore salvataggio cache: {e}")

    def _compute_file_hash(self, file_path: Path) -> str:
        """Calcola hash SHA256 di un file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _compute_files_hash(self, file_paths: List[Path]) -> str:
        """Calcola hash combinato di più file."""
        combined_hash = hashlib.sha256()
        for file_path in sorted(file_paths):
            file_hash = self._compute_file_hash(file_path)
            combined_hash.update(file_hash.encode())
        return combined_hash.hexdigest()

    def _is_cached(self, file_paths: List[Path], exe_name: str) -> bool:
        """Verifica se i file sono in cache e validi."""
        if not self.cache_enabled:
            return False
        
        cache_key = str(sorted([str(f) for f in file_paths]))
        
        if cache_key not in self.cache_index:
            return False
        
        cache_info = self.cache_index[cache_key]
        current_hash = self._compute_files_hash(file_paths)
        
        if cache_info.get("hash") == current_hash:
            exe_path = Path(cache_info.get("exe_path", ""))
            if exe_path.exists():
                return True
        
        return False

    def _run_cached(self, exe_path: Path) -> Tuple[int, str, str]:
        """Esegue un eseguibile cached."""
        if self.verbose:
            print(f"⚡ Usando versione cached: {exe_path.name}")
        
        run_cmd = f"./{exe_path.name}" if self.system != "Windows" else f".\\{exe_path.name}"
        return self._run_command(run_cmd, cwd=exe_path.parent)

    def _update_cache(self, file_paths: List[Path], exe_path: Path):
        """Aggiorna l'indice cache."""
        if not self.cache_enabled:
            return
        
        cache_key = str(sorted([str(f) for f in file_paths]))
        current_hash = self._compute_files_hash(file_paths)
        
        self.cache_index[cache_key] = {
            "hash": current_hash,
            "exe_path": str(exe_path),
            "timestamp": datetime.now().isoformat(),
            "files": [str(f) for f in file_paths]
        }
        
        self._save_cache_index()

    @contextmanager
    def _work_in_directory(self, path: Path):
        """Context manager per cambiare temporaneamente la directory di lavoro."""
        original_dir = Path.cwd()
        try:
            os.chdir(path)
            yield
        finally:
            os.chdir(original_dir)

    def _run_command(self, cmd: str, cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        """Esegue un comando shell e restituisce (returncode, stdout, stderr)."""
        if self.verbose:
            print(f"▶️ Eseguo: {cmd}")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=cwd
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Timeout: il comando ha impiegato più di 5 minuti."
        except Exception as e:
            return 1, "", f"Errore imprevisto durante l'esecuzione: {str(e)}"

    def _get_py_include(self) -> str:
        """Ottiene il percorso di include di Python."""
        # MODIFICATO: Usa self.python_interpreter per coerenza con il venv
        return subprocess.check_output([
            self.python_interpreter, '-c',
            'import sysconfig; print(sysconfig.get_path("include"))'
        ]).decode().strip()
        
    def _get_pybind_include(self) -> str:
        """Ottiene i percorsi di include di PyBind11."""
        if not PYBIND11_AVAILABLE:
            raise ImportError("PyBind11 non è installato")
        # MODIFICATO: Usa self.python_interpreter per coerenza con il venv
        return subprocess.check_output([
            self.python_interpreter, '-m', 'pybind11', '--includes'
        ]).decode().strip()

    def _get_ext_suffix(self) -> str:
        """Ottiene il suffisso per le estensioni native (.pyd o .so)."""
        try:
            # MODIFICATO: Usa self.python_interpreter per coerenza con il venv
            return subprocess.check_output([
                self.python_interpreter, '-c',
                'import sysconfig; print(sysconfig.get_config_var("EXT_SUFFIX"))'
            ]).decode().strip()
        except subprocess.CalledProcessError:
            return ".pyd" if self.system == "Windows" else ".so"

    # ===== METODO PRINCIPALE CON PARALLELIZZAZIONE =====
    
    def build_and_run_mixed(self, file_paths: Union[str, List[str]], 
                            profile: bool = False, parallel: Optional[bool] = None) -> bool:
        """
        Compila ed esegue file di estensioni diverse in una singola chiamata.
        Supporta compilazione parallela dei linguaggi!
        
        Args:
            file_paths: Stringa o lista di file paths (possono essere estensioni diverse)
            profile: Se True, mostra profiling
            parallel: Se True, compila linguaggi in parallelo. None = usa configurazione predefinito
        
        Returns:
            True se tutto ha successo, False altrimenti
        """
        # Normalizza input a lista
        if isinstance(file_paths, str):
            file_paths = [file_paths]
        
        # Risolvi i path e verifica esistenza
        resolved_paths = [Path(f).resolve() for f in file_paths]
        
        for path in resolved_paths:
            if not path.exists():
                print(f"❌ File non trovato: {path}")
                return False
        
        # Raggruppa file per linguaggio
        files_by_lang = self._group_files_by_language(resolved_paths)
        
        print(f"\n📋 Compilazione multi-linguaggio")
        print(f"   File totali: {len(resolved_paths)}")
        print(f"   Linguaggi: {', '.join(files_by_lang.keys())}")
        
        # Decidi se usare parallelizzazione
        use_parallel = parallel if parallel is not None else self.parallel_enabled
        
        # NOTA: La compilazione PyBind11 non è supportata in 'mixed' 
        # perché richiede un flag esplicito (pybind=True) in build_from_file.
        # 'mixed' è pensato per eseguire eseguibili standard.
        
        if use_parallel and len(files_by_lang) > 1:
            print(f"   Modalità: 🚀 PARALLELA ({self.max_workers} worker)")
            print("="*60)
            return self._build_and_run_mixed_parallel(files_by_lang, profile)
        else:
            print(f"   Modalità: ⏳ SEQUENZIALE")
            print("="*60)
            return self._build_and_run_mixed_sequential(files_by_lang, profile)

    def _build_and_run_mixed_sequential(self, files_by_lang: Dict, profile: bool) -> bool:
        """Compila sequenzialmente."""
        results = {}
        
        for lang, files in files_by_lang.items():
            print(f"\n[{lang.upper()}] {len(files)} file")
            
            if lang == 'cpp':
                results[lang] = self.build_and_run_cpp(files, profile=profile)
            elif lang == 'java':
                results[lang] = self.build_and_run_java(files, profile=profile)
            elif lang == 'rust':
                results[lang] = self.build_and_run_rust(files[0], profile=profile)
            elif lang == 'python':
                results[lang] = self.build_and_run_python(files, profile=profile)
        
        return self._print_mixed_results(results)

    def _build_and_run_mixed_parallel(self, files_by_lang: Dict, profile: bool) -> bool:
        """Compila in parallelo usando ThreadPoolExecutor con mapping corretto."""
        
        print("\n🚀 Inizio compilazione parallela...\n")
        
        results = {}
        start_time = time.time()
        
        # Crea un mapping delle task
        tasks = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Sottometti tutti i task
            for lang, files in files_by_lang.items():
                print(f"📨 Sottomesso: [{lang.upper()}]")
                
                if lang == 'cpp':
                    future = executor.submit(self.build_and_run_cpp, files, None, profile)
                elif lang == 'java':
                    future = executor.submit(self.build_and_run_java, files, profile)
                elif lang == 'rust':
                    future = executor.submit(self.build_and_run_rust, files[0], None, 'release', profile)
                elif lang == 'python':
                    future = executor.submit(self.build_and_run_python, files, profile)
                
                tasks[lang] = future
            
            # FIXED: Mapping corretto di future -> linguaggio
            future_to_lang = {future: lang for lang, future in tasks.items()}
            
            # Raccogli i risultati man mano che completano
            print("\n⏳ In elaborazione...")
            for future in as_completed(tasks.values(), timeout=600):
                lang = future_to_lang[future]
                try:
                    result = future.result()
                    results[lang] = result
                    status = "✅" if result else "❌"
                    print(f"{status} Completato: [{lang.upper()}]")
                except Exception as e:
                    results[lang] = False
                    print(f"❌ Errore: [{lang.upper()}] - {e}")
        
        elapsed = time.time() - start_time
        
        print(f"\n⏱️  Tempo totale: {elapsed:.3f}s")
        
        return self._print_mixed_results(results)

    def _print_mixed_results(self, results: Dict) -> bool:
        """Stampa i risultati finali."""
        print("\n" + "="*60)
        print("📊 RISULTATI FINALI")
        print("="*60)
        
        all_success = True
        for lang, success in results.items():
            status = "✅ SUCCESSO" if success else "❌ FALLITO"
            print(f"{lang.upper()}: {status}")
            if not success:
                all_success = False
        
        return all_success

    def _group_files_by_language(self, file_paths: List[Path]) -> Dict[str, List[Path]]:
        """Raggruppa file per linguaggio basandosi sull'estensione."""
        groups = defaultdict(list)
        
        for file_path in file_paths:
            suffix = file_path.suffix.lower()
            lang = self.EXTENSION_MAP.get(suffix)
            
            if lang:
                groups[lang].append(file_path)
            else:
                print(f"⚠️  Estensione non riconosciuta: {suffix} ({file_path.name})")
        
        return dict(groups)

    # MODIFICATO: `build_from_file` ora accetta **kwargs per PyBind11
    def build_from_file(self, file_path: Union[str, List[str]], exe_name: Optional[str] = None, 
                        profile: bool = False, **kwargs) -> bool:
        """
        Metodo intelligente che rileva il tipo di file e chiama il builder appropriato.
        NUOVO: Supporta sia file singoli che liste di file dello stesso linguaggio.
        
        Args:
            file_path: Stringa (file singolo) o lista di file
            exe_name: Nome eseguibile opzionale
            profile: Se True, mostra profiling
            **kwargs: Argomenti aggiuntivi
                - pybind (bool): Se True, compila C++ come modulo PyBind11.
                - module_name (str): Nome del modulo PyBind11 (se pybind=True).
        
        Returns:
            True se successo, False altrimenti
        """
        # MIGLIORATO: Supporta sia stringa che lista di file
        if isinstance(file_path, list):
            if not file_path:
                print("❌ Lista di file vuota")
                return False
            main_file_path = Path(file_path[0]).resolve()
            files_to_compile = file_path
        else:
            main_file_path = Path(file_path).resolve()
            files_to_compile = str(file_path)
        
        if not main_file_path.exists():
            print(f"❌ File non trovato: {main_file_path}")
            return False
        
        suffix = main_file_path.suffix.lower()
        lang = self.EXTENSION_MAP.get(suffix)
        
        # Stampa info corretta per singolo o multi-file
        if isinstance(file_path, list):
            file_names = ", ".join([Path(f).name for f in file_path])
            print(f"📁 File rilevati: {file_names} ({lang})")
        else:
            print(f"📁 File rilevato: {main_file_path.name} ({lang})")
        
        # NUOVO: Logica di routing per PyBind11
        pybind_build = kwargs.get('pybind', False)
        
        if lang == 'cpp':
            if pybind_build:
                # È un build PyBind11. Compila solo.
                module_name = kwargs.get('module_name')
                # Il metodo restituisce un Path se ha successo, None se fallisce
                module_path = self.build_pybind_module(
                    files_to_compile, 
                    module_name=module_name, 
                    profile=profile
                )
                return module_path is not None
            else:
                # È un build C++ standard. Compila ed esegui.
                return self.build_and_run_cpp(files_to_compile, exe_name=exe_name, profile=profile)
        
        elif lang == 'java':
            return self.build_and_run_java(files_to_compile, profile=profile)
        
        elif lang == 'rust':
            optimization = kwargs.get('optimization', 'release')
            rust_file = files_to_compile[0] if isinstance(files_to_compile, list) else files_to_compile
            return self.build_and_run_rust(rust_file, exe_name=exe_name, 
                                           optimization=optimization, profile=profile)
        
        elif lang == 'python':
            return self.build_and_run_python(files_to_compile, profile=profile)
        
        else:
            print(f"❌ Tipo di file non supportato: {suffix}")
            return False

    # ===== METODI DI COMPILAZIONE C++ (MULTI-FILE) =====
    
    def build_and_run_cpp(self, src_files: Union[str, List[str]], exe_name: Optional[str] = None, 
                          profile: bool = False) -> bool:
        """Compila ed esegue uno o più file C++ (come ESEGUIBILE)."""
        
        if isinstance(src_files, str):
            src_files = [src_files]
        
        src_paths = [Path(f).resolve() for f in src_files]
        
        for src_path in src_paths:
            if not src_path.exists():
                print(f"❌ File sorgente non trovato: {src_path}")
                return False

        if exe_name is None:
            exe_name = src_paths[0].stem + (".exe" if self.system == "Windows" else "")
        
        exe_path = src_paths[0].parent / exe_name

        if self._is_cached(src_paths, exe_name):
            ret_code, stdout, stderr = self._run_cached(exe_path)
            if stdout: print(stdout.strip())
            return ret_code == 0

        with self._work_in_directory(src_paths[0].parent):
            file_names = ", ".join([p.name for p in src_paths])
            print(f"[C++] Compilazione: {file_names} → {exe_name}")
            
            if not self._compile_cpp_files(src_paths, exe_name):
                return False

            print(f"✅ Compilazione riuscita. Esecuzione di '{exe_name}'...")
            
            self._update_cache(src_paths, exe_path)
            
            run_cmd = f".\\{exe_name}" if self.system == "Windows" else f"./{exe_name}"
            ret_code, stdout, stderr = self._run_command(run_cmd)

            print("--- OUTPUT ESECUZIONE ---")
            if stdout: print(stdout.strip())
            if stderr: print(f"ERRORE ESECUZIONE:\n{stderr.strip()}")
            print("-------------------------")
            
            return ret_code == 0

    def _compile_cpp_files(self, src_paths: List[Path], exe_name: str) -> bool:
        """Compila i file C++ (metodo helper)."""
        build_cmd = self._get_cpp_build_command(src_paths, exe_name)
        if not build_cmd:
            return False
            
        ret_code, stdout, stderr = self._run_command(build_cmd)
        if stdout: print(stdout)

        if ret_code != 0:
            print(f"❌ Compilazione fallita.")
            if stderr: print(f"ERRORE:\n{stderr}")
            return False
        
        return True

    def _get_cpp_build_command(self, src_paths: List[Path], exe_name: str) -> Optional[str]:
        """Costruisce il comando di compilazione C++ per la piattaforma corrente."""
        src_files = " ".join([f'"{p.name}"' for p in src_paths])
        
        if self.system == "Windows":
            try:
                vcvars_path = self._find_vcvars64()
                return f'call "{vcvars_path}" && cl {self.MSVC_CPP_FLAGS} {src_files} /Fe"{exe_name}"'
            except FileNotFoundError as e:
                print(f"❌ {e}")
                return None
        else:
            return f'g++ {self.GCC_CPP_FLAGS} {src_files} -o "{exe_name}"'

    # ===== NUOVO: METODI DI COMPILAZIONE PYBIND11 =====
    
    def build_pybind_module(self, src_files: Union[str, List[str]], 
                            module_name: Optional[str] = None, 
                            profile: bool = False) -> Optional[Path]:
        """
        Compila uno o più file C++ in un modulo Python (.pyd/.so) usando PyBind11.
        Non esegue il file, ma ritorna il percorso del modulo compilato.
        
        Args:
            src_files: File sorgente C++ (o lista)
            module_name: Nome del modulo (es. 'mio_modulo'). Se None, usa il nome del primo file.
            profile: (Non usato per PyBind, ma mantenuto per coerenza)
            
        Returns:
            Path al modulo compilato se successo, None altrimenti.
        """
        if not PYBIND11_AVAILABLE:
            print("❌ Errore: PyBind11 non è installato nel venv/sistema.")
            print("   Esegui: pip install pybind11")
            return None

        if isinstance(src_files, str):
            src_files = [src_files]
        
        src_paths = [Path(f).resolve() for f in src_files]
        
        for src_path in src_paths:
            if not src_path.exists():
                print(f"❌ File sorgente non trovato: {src_path}")
                return None
        
        # Determina il nome del modulo
        if module_name is None:
            module_name = src_paths[0].stem
        
        # Determina il nome completo del file (es. 'mio_modulo.cp310-win_amd64.pyd')
        ext_suffix = self._get_ext_suffix()
        
        # Pulisci il nome (a volte .pyd o .so è già in ext_suffix, ma di solito no)
        # ext_suffix è tipo ".cp310-win_amd64.pyd" o ".cpython-310-x86_64-linux-gnu.so"
        if ext_suffix.startswith(f".{module_name}"):
             module_filename = ext_suffix[1:]
        else:
             module_filename = module_name + ext_suffix
        
        module_path = src_paths[0].parent / module_filename

        # Controlla la cache
        if self._is_cached(src_paths, module_filename):
            if self.verbose:
                print(f"⚡ Modulo PyBind11 [cache]: {module_path.name}")
            return module_path

        # Compila
        with self._work_in_directory(src_paths[0].parent):
            file_names = ", ".join([p.name for p in src_paths])
            print(f"[PyBind11] Compilazione: {file_names} → {module_filename}")
            
            build_cmd = self._get_pybind_build_command(src_paths, module_filename)
            if not build_cmd:
                return None

            ret_code, stdout, stderr = self._run_command(build_cmd)
            if stdout: print(stdout)

            if ret_code != 0:
                print(f"❌ Compilazione PyBind11 fallita.")
                if stderr: print(f"ERRORE:\n{stderr}")
                return None
            
            print(f"✅ Compilazione PyBind11 riuscita: {module_path.name}")
            print(f"   Puoi importarlo con: import {module_name}")
            
            # Aggiorna la cache
            self._update_cache(src_paths, module_path) 
            return module_path

    def _get_pybind_build_command(self, src_paths: List[Path], module_filename: str) -> Optional[str]:
        """Costruisce il comando di compilazione PyBind11."""
        try:
            # Percorso include Python (es. .../include/python3.10)
            py_include = self._get_py_include()
            # Stringa di flag include PyBind11 (es. "-I.../site-packages/pybind11/include")
            pb_includes_str = self._get_pybind_include()
        except Exception as e:
            print(f"❌ Errore nel trovare gli include di Python/PyBind11: {e}")
            return None

        src_files = " ".join([f'"{p.name}"' for p in src_paths])
        
        if self.system == "Windows":
            try:
                vcvars_path = self._find_vcvars64()
                # Converte i flag GCC (-I) in flag MSVC (/I)
                msvc_includes = f'/I"{py_include}" {pb_includes_str.replace("-I", "/I")}'
                
                # /Fe<file> specifica il nome output per una DLL quando /LD è usato
                return (f'call "{vcvars_path}" && cl {self.MSVC_PYBIND_FLAGS} {msvc_includes} '
                        f'{src_files} /Fe"{module_filename}"')
            except FileNotFoundError as e:
                print(f"❌ {e}")
                return None
        else:
            # GCC/Clang
            # pb_includes_str è già formattato correttamente (es. "-Ipath1 -Ipath2")
            include_flags = f'-I"{py_include}" {pb_includes_str}'
            
            return (f'g++ {self.GCC_PYBIND_FLAGS} {include_flags} '
                    f'{src_files} -o "{module_filename}"')

    # ===== METODI DI COMPILAZIONE JAVA (MULTI-FILE) =====
    
    def build_and_run_java(self, src_files: Union[str, List[str]], profile: bool = False) -> bool:
        """Compila ed esegue uno o più file sorgente Java."""
        
        if isinstance(src_files, str):
            src_files = [src_files]
        
        src_paths = [Path(f).resolve() for f in src_files]
        
        for src_path in src_paths:
            if not src_path.exists():
                print(f"❌ File sorgente non trovato: {src_path}")
                return False
        
        main_file = src_paths[0]
        classname = main_file.stem
        
        with self._work_in_directory(main_file.parent):
            file_names = ", ".join([p.name for p in src_paths])
            print(f"[Java] Compilazione: {file_names}")

            if not self._compile_java_files(src_paths):
                return False

            print("✅ Compilazione riuscita. Esecuzione...")

            ret_code, stdout, stderr = self._run_command(f"java {classname}")
            
            print("--- OUTPUT ESECUZIONE ---")
            if stdout: print(stdout.strip())
            if stderr: print(f"ERRORE ESECUZIONE:\n{stderr.strip()}")
            print("-------------------------")
            
            return ret_code == 0

    def _compile_java_files(self, src_paths: List[Path]) -> bool:
        """Compila i file Java (metodo helper)."""
        src_files = " ".join([f'"{p.name}"' for p in src_paths])
        ret_code, _, stderr = self._run_command(f"javac {src_files}")
        if ret_code != 0:
            print(f"❌ Compilazione fallita.")
            if stderr: print(f"ERRORE:\n{stderr}")
            return False
        return True

    # ===== METODI DI COMPILAZIONE RUST =====
    
    def build_and_run_rust(self, src_file: str, exe_name: Optional[str] = None, 
                           optimization: str = "release", profile: bool = False) -> bool:
        """Compila ed esegue un file sorgente Rust (.rs)."""
        src_path = Path(src_file).resolve()
        if not src_path.exists():
            print(f"❌ File sorgente non trovato: {src_path}")
            return False

        if exe_name is None:
            exe_name = src_path.stem
        
        exe_path = src_path.parent / exe_name

        with self._work_in_directory(src_path.parent):
            print(f"[Rust] Compilazione: {src_path.name} → {exe_name}")
            
            # FIXED: Corretto comando Rust per release
            if optimization == "release":
                opt_flags = "-C opt-level=3"
            else:
                opt_flags = ""
            
            build_cmd = f'rustc {opt_flags} "{src_path.name}" -o "{exe_name}"'
            
            ret_code, stdout, stderr = self._run_command(build_cmd)
            if stdout: print(stdout)

            if ret_code != 0:
                print(f"❌ Compilazione fallita.")
                if stderr: print(f"ERRORE:\n{stderr}")
                return False

            print(f"✅ Compilazione riuscita. Esecuzione di '{exe_name}'...")
            
            run_cmd = f"./{exe_name}"
            ret_code, stdout, stderr = self._run_command(run_cmd)

            print("--- OUTPUT ESECUZIONE ---")
            if stdout: print(stdout.strip())
            if stderr: print(f"ERRORE ESECUZIONE:\n{stderr.strip()}")
            print("-------------------------")
            
            return ret_code == 0

    def build_rust_project(self, project_dir: str = ".", 
                           optimization: str = "release", profile: bool = False) -> bool:
        """Compila un progetto Rust con Cargo."""
        project_path = Path(project_dir).resolve()
        if not (project_path / "Cargo.toml").exists():
            print(f"❌ Cargo.toml non trovato in: {project_path}")
            return False

        with self._work_in_directory(project_path):
            print(f"[Cargo] Compilazione progetto in: {project_path}")
            
            opt_flag = "--release" if optimization == "release" else ""
            build_cmd = f"cargo build {opt_flag}"
            
            ret_code, stdout, stderr = self._run_command(build_cmd)
            if stdout: print(stdout)
            
            if ret_code != 0:
                print("❌ Compilazione fallita.")
                if stderr: print(f"ERRORE:\n{stderr}")
                return False
            
            print("✅ Compilazione riuscita!")
            return True

    # ===== METODI PER PYTHON =====
    
    def build_and_run_python(self, py_files: Union[str, List[str]], profile: bool = False) -> bool:
        """Esegue uno o più script Python usando il Python interpreter configurato."""
        
        if isinstance(py_files, str):
            py_files = [py_files]
        
        py_paths = [Path(f).resolve() for f in py_files]
        
        for py_path in py_paths:
            if not py_path.exists():
                print(f"❌ File Python non trovato: {py_path}")
                return False
        
        main_file = py_paths[0]
        
        with self._work_in_directory(main_file.parent):
            file_names = ", ".join([p.name for p in py_paths])
            print(f"[Python] Esecuzione: {file_names}")
            print(f"   Interpreter: {self.python_interpreter}")
            
            run_cmd = f'"{self.python_interpreter}" "{main_file.name}"'
            ret_code, stdout, stderr = self._run_command(run_cmd)
            
            print("--- OUTPUT ESECUZIONE ---")
            if stdout: print(stdout.strip())
            if stderr: print(f"ERRORE ESECUZIONE:\n{stderr.strip()}")
            print("-------------------------")
            
            return ret_code == 0

    # ===== FUNZIONI DI UTILITÀ =====
    
    @staticmethod
    def _find_vcvars64() -> str:
        """Trova vcvars64.bat per Visual Studio."""
        base_paths = [
            Path("C:/Program Files/Microsoft Visual Studio"),
            Path("C:/Program Files (x86)/Microsoft Visual Studio")
        ]
        versions = ["2022", "2019", "2017"]
        editions = ["BuildTools", "Community", "Professional", "Enterprise"]

        for base in base_paths:
            for version in versions:
                for edition in editions:
                    candidate = base / version / edition / "VC/Auxiliary/Build/vcvars64.bat"
                    if candidate.exists():
                        return str(candidate)
        
        raise FileNotFoundError(
            "vcvars64.bat non trovato! Installa Visual Studio Build Tools o Community."
        )

    @staticmethod
    def check_toolchain():
        """Controlla la disponibilità degli strumenti di compilazione."""
        print("=== Controllo Toolchain ===")
        tools = {}
        
        tools['Python'] = f"✅ Disponibile (Versione: {sys.version.split()[0]})"
        
        # MODIFICATO: Controlla la variabile globale
        if PYBIND11_AVAILABLE:
            tools['PyBind11'] = "✅ Disponibile"
        else:
            tools['PyBind11'] = "❌ Non disponibile (esegui: pip install pybind11)"
            
        if platform.system() == "Windows":
            try:
                UniversalBuilder._find_vcvars64()
                tools['MSVC (C++)'] = "✅ Disponibile"
            except FileNotFoundError:
                tools['MSVC (C++)'] = "❌ Non disponibile (Installa Visual Studio Build Tools)"
        else:
            ret = subprocess.run("g++ --version", shell=True, 
                                 capture_output=True).returncode
            tools['g++ (C++)'] = "✅ Disponibile" if ret == 0 else "❌ Non disponibile"

        ret = subprocess.run("javac -version", shell=True, 
                             capture_output=True)
        if ret.returncode == 0:
            tools['Java'] = f"✅ Disponibile"
        else:
            tools['Java'] = "❌ Non disponibile (Installa un JDK)"

        ret = subprocess.run("rustc --version", shell=True, 
                             capture_output=True, text=True)
        if ret.returncode == 0:
            tools['Rust (rustc)'] = f"✅ Disponibile ({ret.stdout.strip()})"
        else:
            tools['Rust (rustc)'] = "❌ Non disponibile (vedi: https://rustup.rs)"
        
        ret = subprocess.run("cargo --version", shell=True, 
                             capture_output=True, text=True)
        if ret.returncode == 0:
            tools['Cargo'] = f"✅ Disponibile ({ret.stdout.strip()})"
        else:
            tools['Cargo'] = "❌ Non disponibile (vedi: https://rustup.rs)"

        for tool, status in tools.items():
            print(f"- {tool}: {status}")

    def clear_cache(self):
        """Pulisce la cache completamente."""
        if not self.cache_enabled:
            print("Cache non abilitata")
            return
        
        try:
            import shutil
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(exist_ok=True)
            self.cache_index = {}
            print(f"✅ Cache pulita: {self.cache_dir}")
        except Exception as e:
            print(f"❌ Errore pulizia cache: {e}")

    def get_cache_stats(self) -> Dict:
        """Ritorna statistiche sulla cache."""
        if not self.cache_enabled:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "cache_dir": str(self.cache_dir),
            "num_cached_builds": len(self.cache_index),
            "cache_size_mb": self._get_dir_size(self.cache_dir) / 1024 / 1024,
            "cached_files": self.cache_index
        }

    @staticmethod
    def _get_dir_size(path: Path) -> float:
        """Calcola la dimensione di una directory in bytes."""
        total = 0
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
        return total

    def get_python_info(self) -> Dict:
        """Ritorna informazioni sul Python interpreter configurato."""
        return {
            "interpreter": self.python_interpreter,
            "is_venv": self.python_venv_path is not None,
            "venv_path": self.python_venv_path
        }

    def get_parallel_info(self) -> Dict:
        """Ritorna informazioni sulla parallelizzazione."""
        return {
            "parallel_enabled": self.parallel_enabled,
            "max_workers": self.max_workers,
            "cpu_count": os.cpu_count(),
            "executor_type": "ThreadPoolExecutor"
        }


# --- Esempi d'uso ---
if __name__ == '__main__':
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     UniversalBuilder - Multi-Language Compiler           ║")
    print("║ CON PARALLELIZZAZIONE NATIVA (concurrent.futures)        ║")
    print("║     VERSIONE 2.3 - INTEGRAZIONE PyBind11                 ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    # Builder con parallelizzazione abilitata (default)
    builder = UniversalBuilder(
        verbose=True,
        cache_enabled=True,
        parallel_enabled=True
    )
    
    print("\n" + "="*60)
    print("VERIFICA TOOLCHAIN")
    print("="*60)
    builder.check_toolchain() # NUOVO: Esegui il check all'avvio
    
    print("\n" + "="*60)
    print("INFO PARALLELIZZAZIONE")
    print("="*60)
    
    parallel_info = builder.get_parallel_info()
    print(f"Parallelizzazione: {'🚀 ABILITATA' if parallel_info['parallel_enabled'] else '⏳ DISABILITATA'}")
    print(f"Worker disponibili: {parallel_info['max_workers']}")
    print(f"CPU del sistema: {parallel_info['cpu_count']}")
    print(f"Tipo executor: {parallel_info['executor_type']}")
    
    print("\n✅ Builder pronto!")
    print("Usa:")
    print("  --- Eseguibili ---")
    print("  - builder.build_from_file('file.cpp')")
    print("  - builder.build_from_file(['main.cpp', 'utils.cpp'])")
    print("  - builder.build_from_file('programma.java')")
    print("  - builder.build_from_file('script.rs')")
    print("  - builder.build_from_file('script.py')")
    print("\n  --- Moduli PyBind11 (NUOVO) ---")
    print("  - builder.build_from_file('mio_modulo.cpp', pybind=True)")
    print("  - builder.build_from_file('mio_modulo.cpp', pybind=True, module_name='custom_name')")
    print("  (Questo compila il modulo. Dovrai poi importarlo nel tuo script Python)")
