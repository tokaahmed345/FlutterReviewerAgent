import os
import re
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# ── API Key (Groq) ─────────────────────────────────────────────────────────────
load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=API_KEY)
MODEL = "llama-3.3-70b-versatile"

# ── Terminal Colors ────────────────────────────────────────────────────────────
class Color:
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    MAGENTA = "\033[95m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RESET   = "\033[0m"

def c(text, color): return f"{color}{text}{Color.RESET}"
def dim(text):      return c(text, Color.DIM)

def print_banner():
    print(f"""
{Color.CYAN}{Color.BOLD}
 ╔══════════════════════════════════════════╗
 ║   🔍  Flutter Code Reviewer Agent        ║
 ║   Auto-review & fix your Flutter code    ║
 ║   Powered by Groq 🚀                     ║
 ╚══════════════════════════════════════════╝
{Color.RESET}""")

# ── Call Groq API ──────────────────────────────────────────────────────────────
def call_groq(system_prompt: str, user_message: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ]
    )
    return response.choices[0].message.content

# ── Read dart files ────────────────────────────────────────────────────────────
def read_dart_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""

def get_all_dart_files(project_path: Path) -> list[Path]:
    """Get all dart files in lib/ folder."""
    lib = project_path / "lib"
    if not lib.exists():
        return []
    return [f for f in lib.rglob("*.dart") if ".g.dart" not in f.name]

def pick_files(project_path: Path, query: str) -> list[Path]:
    """
    Return files to review based on user input:
    - 'all'        → all dart files
    - 'auth'       → files with 'auth' in path
    - specific path → that file only
    """
    all_files = get_all_dart_files(project_path)

    if query.strip().lower() == "all":
        return all_files

    # Search by keyword in path
    matched = [f for f in all_files if query.lower() in str(f).lower()]
    if matched:
        return matched

    # Try exact path
    exact = project_path / query
    if exact.exists():
        return [exact]

    return []

# ── Extract fixed code from AI reply ──────────────────────────────────────────
def extract_fixed_files(reply: str) -> list[tuple[str, str]]:
    """Return list of (filepath, code) from AI reply."""
    results = []
    filenames = re.findall(r"📁 File: ([\w\/\\.]+)", reply)
    code_blocks = re.findall(r"```dart\n(.*?)```", reply, re.DOTALL)

    for i, code in enumerate(code_blocks):
        path = filenames[i] if i < len(filenames) else None
        if path:
            results.append((path, code))
    return results

# ── Auto-detect Flutter project ───────────────────────────────────────────────
def is_real_flutter_project(path: Path) -> bool:
    blocked = ["Pub", "Cache", "pub-cache", ".pub-cache", "pub.dev", "hosted"]
    for part in path.parts:
        if part in blocked:
            return False
    return (path / "lib").exists() and (path / "pubspec.yaml").exists()

def find_flutter_project() -> Path | None:
    cwd = Path.cwd()
    if is_real_flutter_project(cwd):
        return cwd
    for parent in list(cwd.parents)[:3]:
        if is_real_flutter_project(parent):
            return parent
    return None

def resolve_project_path() -> Path | None:
    auto = find_flutter_project()
    if auto:
        print(f"\n  {c('🔍 Flutter project detected:', Color.CYAN)} {c(str(auto), Color.BOLD)}")
        confirm = input(f"  {c('Use this project? (y/n):', Color.GREEN)} ").strip().lower()
        if confirm == "y":
            return auto

    path_input = input(f"\n  {c('📂 Enter Flutter project path:', Color.GREEN)} ").strip()
    if path_input:
        manual = Path(path_input).resolve()
        if manual.exists() and (manual / "pubspec.yaml").exists():
            return manual
        print(c("❌ Not a valid Flutter project.", Color.RED))
    return None

# ── Review a set of files ──────────────────────────────────────────────────────
def review_files(files: list[Path], project_path: Path, project_name: str):
    # Build context from selected files
    context = ""
    for f in files:
        rel = str(f.relative_to(project_path))
        content = read_dart_file(f)
        context += f"\n📁 File: {rel}\n```dart\n{content[:3000]}\n```\n"

    system_prompt = (
        f"You are a Senior Flutter/Dart Security Expert and Code Reviewer for project: {project_name}\n\n"
        "You have deep knowledge of mobile security, Flutter best practices, and secure coding.\n"
        "Your job is to detect ALL issues across 4 areas:\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔒 SECURITY CHECKLIST (check every single one):\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "1. HARDCODED SECRETS — any API keys, tokens, passwords written directly in code → HIGH RISK\n"
        "2. INSECURE STORAGE — SharedPreferences used for: password, token, email, userId, apiKey → HIGH RISK\n"
        "   FIX: use flutter_secure_storage for ALL sensitive data\n"
        "   CORRECT USAGE:\n"
        "     import 'package:flutter_secure_storage/flutter_secure_storage.dart';\n"
        "     final _storage = const FlutterSecureStorage();\n"
        "     await _storage.write(key: 'password', value: hashedPassword);\n"
        "     await _storage.write(key: 'email', value: email);\n"
        "3. WEAK HASHING — using hashCode, md5, or no hashing for passwords → HIGH RISK\n"
        "   FIX: use sha256 from crypto package:\n"
        "     import 'package:crypto/crypto.dart';\n"
        "     import 'dart:convert';\n"
        "     final hashed = sha256.convert(utf8.encode(password)).toString();\n"
        "4. INSECURE NETWORK — http:// instead of https:// → HIGH RISK\n"
        "5. SENSITIVE DATA IN LOGS — print() or log() with passwords/tokens → MEDIUM RISK\n"
        "6. MISSING INPUT VALIDATION — no checks on user input before API calls → MEDIUM RISK\n"
        "7. API KEYS IN CODE — use flutter_dotenv instead → HIGH RISK\n"
        "   FIX: import 'package:flutter_dotenv/flutter_dotenv.dart';\n"
        "        final apiKey = dotenv.env['API_KEY'];\n"
        "8. UNENCRYPTED DATA — sensitive data sent without encryption → HIGH RISK\n"
        "9. MISSING AUTH CHECKS — accessing data without checking if user is logged in → HIGH RISK\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🐛 BUGS & CODE QUALITY:\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "- Missing imports, wrong types, null safety issues, logic errors\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ PERFORMANCE:\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "- Missing const, heavy UI operations, memory leaks, unnecessary rebuilds\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏗️ ARCHITECTURE:\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "- Mixed layers, wrong MVVM structure, missing abstractions\n\n"

        "FORMAT your review EXACTLY like this:\n"
        "🔒 SECURITY:\n- [file] vulnerability + risk level (HIGH/MEDIUM/LOW)\n\n"
        "🐛 BUGS:\n- [file] issue\n\n"
        "⚡ PERFORMANCE:\n- [file] issue\n\n"
        "🏗️ ARCHITECTURE:\n- [file] issue\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "CRITICAL RULES (never break these):\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "- Always write 📁 File: lib/path/file.dart before each fixed file\n"
        "- Wrap every fixed file in ```dart blocks\n"
        "- Always include ALL imports — never skip any\n"

        "--- DIO RULES ---\n"
        "- Never use DioOptions — it does NOT exist. Use Options from dio:\n"
        "  CORRECT: Options headers = Options(headers: {'Authorization': 'Bearer $token'});\n"
        "  CORRECT: dio.get('url', options: Options(headers: {...}));\n"
        "  WRONG:   DioOptions(...) — this class does not exist\n"
        "- Never use DioError or DioErrorType — use DioException and DioExceptionType\n"
        "- DioExceptionType values: connectionTimeout, receiveTimeout, sendTimeout, badResponse, cancel, unknown\n"
        "- DioException.message is nullable — always use: e.message ?? 'Unknown error'\n"
        "- CRITICAL: Never call DioException(type, message) — positional args don't exist\n"
        "- CRITICAL: Never rethrow DioException — always throw ServerFailure(e.message ?? 'Unknown error')\n"

        "--- FAILURE CLASS RULES ---\n"
        "- Failure and ServerFailure must be defined in ONE place only: lib/core/failures.dart\n"
        "- Never redefine Failure or ServerFailure inside test files or feature files\n"
        "- Import failures like this: import 'package:PROJECT_NAME/core/failures.dart';\n"
        "- Correct Failure class:\n"
        "    abstract class Failure {\n"
        "      final String message;\n"
        "      const Failure(this.message);\n"
        "    }\n"
        "- Correct ServerFailure class:\n"
        "    class ServerFailure extends Failure {\n"
        "      const ServerFailure(super.message);\n"
        "    }\n"
        "- CRITICAL: ServerFailure(variable) must NOT have const — only ServerFailure('literal') can have const\n"
        "  CORRECT: throw ServerFailure(e.message ?? 'error');      ← no const\n"
        "  CORRECT: throw const ServerFailure('User ID required');   ← const ok with literal\n"
        "  WRONG:   throw const ServerFailure(variable);             ← NEVER do this\n"

        "--- IMPORT RULES ---\n"
        "- Never use package:filename.dart format — always use package:project_name/path/file.dart\n"
        "  CORRECT: import 'package:ai_study_agent/core/failures.dart';\n"
        "  WRONG:   import 'package:failures.dart';\n"
        "  WRONG:   import 'package:auth_manager.dart';\n"
        "- Never use package:convert/convert.dart — use dart:convert (built-in)\n"
        "- Never use package:secure_storage — use package:flutter_secure_storage/flutter_secure_storage.dart\n"
        "- Never use package:dio/failures.dart — failures.dart is a project file, not a dio file\n"

        "--- FILE RULES ---\n"
        "- Only fix the files that were reviewed — do NOT create new files unless absolutely necessary\n"
        "- If Failure class is needed, create lib/core/failures.dart and import it everywhere\n"
        "- Never invent packages — only use real Flutter packages\n"
        "- If user writes in Arabic, reply in Arabic (keep code in English)\n"
        "- Fixed code must NOT repeat the same issues found in review\n"
    )

    user_message = (
        f"Please review these files and list all issues and improvements:\n{context}"
    )

    print(f"  {dim('🔍 Reviewing files...')}", end="\r", flush=True)

    try:
        reply = call_groq(system_prompt, user_message)
        print(f"\r{c('🔍 Review Results:', Color.CYAN)}\n")
        for line in reply.split("\n"):
            if line.strip():
                print(f"  {line}")
        print()
        return reply, system_prompt, user_message

    except Exception as e:
        print(c(f"❌ Error: {e}", Color.RED))
        return None, system_prompt, user_message

# ── Auto-install packages ─────────────────────────────────────────────────────
def auto_install_packages(code: str, project_path: Path):
    """Scan code for package imports and auto-install any missing ones."""
    package_map = {
        "flutter_secure_storage":        "flutter_secure_storage",
        "FlutterSecureStorage":          "flutter_secure_storage",
        "package:crypto":                "crypto",
        "sha256":                        "crypto",
        "Hmac":                          "crypto",
        "package:encrypt":               "encrypt",
        "package:local_auth":            "local_auth",
        "flutter_dotenv":                "flutter_dotenv",
        "package:flutter_dotenv":        "flutter_dotenv",
        "package:dotenv":                "flutter_dotenv",
        "package:dio/":                  "dio",
        "package:dartz/":                "dartz",
        "package:get_it/":               "get_it",
        "package:flutter_bloc/":         "flutter_bloc",
        "package:go_router/":            "go_router",
        "package:provider/":             "provider",
        "package:shared_preferences/":   "shared_preferences",
        "package:hive/":                 "hive",
        "package:sqflite/":              "sqflite",
        "package:image_picker/":         "image_picker",
        "package:cached_network_image/": "cached_network_image",
    }

    pubspec = project_path / "pubspec.yaml"
    pubspec_content = pubspec.read_text(encoding="utf-8") if pubspec.exists() else ""

    packages_to_add = []
    for search_key, pkg_name in package_map.items():
        if search_key in code and pkg_name not in pubspec_content:
            if pkg_name not in packages_to_add:
                packages_to_add.append(pkg_name)

    if not packages_to_add:
        return

    pkg_str = " ".join(packages_to_add)
    print(f"  {c(f'📦 Auto-installing packages: {pkg_str}', Color.CYAN)}")
    result = subprocess.run(
        f"flutter pub add {pkg_str}",
        shell=True, cwd=project_path,
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"  {c('✅ Packages installed!', Color.GREEN)}")
        subprocess.run("flutter pub get", shell=True, cwd=project_path,
                       capture_output=True, text=True)
    else:
        print(f"  {c('❌ Failed to install packages:', Color.RED)} {result.stderr[:200]}")

# ── Apply fixes ────────────────────────────────────────────────────────────────
def apply_fixes(files: list[Path], project_path: Path, system_prompt: str, review_reply: str, user_message: str):
    fix_message = (
        "Now fix ALL the issues you found above. Be smart about how you fix each issue:\n\n"
        "- If the issue is a MISSING IMPORT → add only the missing import line\n"
        "- If the issue is a DEPRECATED API (e.g. DioError→DioException) → replace only that line\n"
        "- If the issue is a LOGIC ERROR or WRONG IMPLEMENTATION → rewrite the full function\n"
        "- If the issue is WRONG ARCHITECTURE or MISSING CLASS → rewrite the full file\n"
        "- If the issue is a MISSING FIELD → add only that field\n\n"
        "For every file that needs changes:\n"
        "1. Write 📁 File: lib/path/file.dart\n"
        "2. Write the COMPLETE corrected file (not partial)\n"
        "3. Make sure the fixed code does NOT repeat the same issues\n"
        "4. Always include ALL imports at the top\n"
        "5. Never write 'same as before' or skip any file that has issues\n"
    )

    print(f"  {dim('🔧 Applying fixes...')}", end="\r", flush=True)

    try:
        full_user_message = (
            "Previous code reviewed:\n" + user_message + "\n\n"
            + "Review findings:\n" + review_reply + "\n\n"
            + fix_message
        )
        reply = call_groq(system_prompt, full_user_message)
        fixed_files = extract_fixed_files(reply)

        if not fixed_files:
            print(f"\r  {c('✅ No files needed fixing!', Color.GREEN)}")
            return

        # Install packages FIRST before saving files
        all_code = " ".join([code for _, code in fixed_files])
        auto_install_packages(code=all_code, project_path=project_path)

        # Then save files
        print(f"\r  {c(f'💾 Auto-saving {len(fixed_files)} fixed file(s)...', Color.CYAN)}")
        for filepath, code in fixed_files:
            full_path = project_path / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(code, encoding="utf-8")
            print(f"  {c('✅ Fixed:', Color.GREEN)} {c(filepath, Color.BOLD)}")

        print(f"  {c('🎉 All fixes applied!', Color.GREEN)}\n")

        # Run dart analyze after fixes
        print(f"  {dim('🔍 Running dart analyze...')}")
        result = subprocess.run(
            "dart analyze", shell=True, cwd=project_path,
            capture_output=True, text=True
        )
        output = result.stdout + result.stderr
        if "No issues found" in output:
            print(f"  {c('✅ No issues found!', Color.GREEN)}")
        else:
            for line in output.strip().split("\n")[:10]:
                print(f"  {c(line, Color.YELLOW)}")

    except Exception as e:
        print(c(f"❌ Error: {e}", Color.RED))

# ── Main ───────────────────────────────────────────────────────────────────────
def run_reviewer(project_path: Path):
    project_name = project_path.name
    all_files = get_all_dart_files(project_path)

    print(f"\n{c('🚀 Flutter Reviewer ready!', Color.GREEN)}")
    print(f"  {dim('Commands: type file name / feature name / all — then type fix to apply fixes')}\n")

    while True:
        try:
            query = input(f"{c('Review', Color.MAGENTA)} ❯ ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{c('👋 Goodbye!', Color.CYAN)}")
            break

        if not query:
            continue
        if query.lower() in ["exit", "quit"]:
            print(c("👋 Goodbye!", Color.CYAN))
            break

        # List all files
        if query.lower() == "list":
            print(f"\n  {c('📂 Dart files in project:', Color.CYAN)}")
            for f in all_files:
                print(f"    {dim(str(f.relative_to(project_path)))}")
            print()
            continue

        # Pick files and review
        files = pick_files(project_path, query)
        if not files:
            print(f"  {c('❌ No files found for:', Color.RED)} {query}")
            print(f"  {dim('Try: all / auth / login / list')}")
            continue

        print(f"\n  {c(f'📂 Reviewing {len(files)} file(s):', Color.CYAN)}")
        for f in files:
            print(f"    {dim(str(f.relative_to(project_path)))}")
        print()

        review_reply, system_prompt, user_message = review_files(files, project_path, project_name)

        if review_reply:
            # Auto-install packages found in the reviewed files first
            all_code = "".join([read_dart_file(f) for f in files])
            auto_install_packages(code=all_code, project_path=project_path)

            # ── ✅ التعديل: اسأل المستخدم قبل الفيكس ──────────────────────────
            has_issues = any(x in review_reply for x in ["🐛", "🔒", "⚡", "🏗️", "issue", "error", "missing", "vulnerability"])
            if has_issues:
                fix_confirm = input(f"\n  {c('🔧 Issues found! Apply fixes? (y/n):', Color.YELLOW)} ").strip().lower()
                if fix_confirm == "y":
                    apply_fixes(files, project_path, system_prompt, review_reply, user_message)
                else:
                    print(f"  {c('⏭️  Fixes skipped.', Color.DIM)}\n")
            else:
                print(f"  {c('✅ No issues found! Code looks good.', Color.GREEN)}")

# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print_banner()
    project_path = resolve_project_path()
    if project_path is None:
        print(c("❌ No Flutter project selected. Exiting.", Color.RED))
    else:
        run_reviewer(project_path)