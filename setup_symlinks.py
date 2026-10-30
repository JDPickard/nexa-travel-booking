#!/usr/bin/env python3
"""
setup_symlinks.py
 Cross-platform symlink setup for shared AI guardrails, GitHub Copilot config, agents, and skills.
    """

import platform
import subprocess
import filecmp
from pathlib import Path

# Mapping: source folder in the AI guardrails submodule -> target location in the repo
SYMLINK_MAP = [
    # GitHub Copilot specific configurations
    (".github/demo-ai-guardrails/.github/instructions", ".github/instructions", True),
    (".github/demo-ai-guardrails/.github/agents", ".github/agents", True),
    (".github/demo-ai-guardrails/.github/skills", ".github/skills", True),

    # Claude Code skills
    (".github/demo-ai-guardrails/.github/skills", ".claude/skills", True),
]

def create_symlink(
    source_rel: str,
    target_rel: str,
    project_root: Path,
    merge_directory: bool = False,
):
    project_root = project_root.resolve()
    source = (project_root / source_rel).resolve()
    target = project_root / target_rel

    if not source.exists():
        print(f"⚠️  Skipping: Source '{source_rel}' does not exist in submodule.")
        return

    # Keep target folders real so repo-specific entries can coexist with shared links.
    if source.is_dir() and (merge_directory or (target.is_dir() and not target.is_symlink())):
        if target.is_symlink():
            if target.resolve() != source:
                print(f"⚠️  Target '{target_rel}' links somewhere else. Skipping to preserve it.")
                return
            target.unlink()
        elif target.exists() and not target.is_dir():
            print(f"⚠️  Target '{target_rel}' conflicts with the source. Skipping to avoid overwriting.")
            return

        target.mkdir(parents=True, exist_ok=True)
        for child_source in source.iterdir():
            child_target = target / child_source.name
            if child_source.name == ".DS_Store":
                if child_target.is_symlink() and child_target.resolve() == child_source.resolve():
                    child_target.unlink()
                continue
            create_symlink(
                child_source.relative_to(project_root).as_posix(),
                child_target.relative_to(project_root).as_posix(),
                project_root,
            )
        return

    # Ensure parent folder exists (e.g., creates .github/ if missing)
    target.parent.mkdir(parents=True, exist_ok=True)

    # Replace existing links and identical files, but preserve conflicting local content.
    if target.is_symlink():
        target.unlink()
    elif target.exists():
        if target.is_dir() or not source.is_file() or not target.is_file():
            print(f"⚠️  Target '{target_rel}' conflicts with the source. Skipping to avoid overwriting.")
            return
        if not filecmp.cmp(source, target, shallow=False):
            print(f"⚠️  Target '{target_rel}' differs from the source. Skipping to preserve local content.")
            return
        target.unlink()

    is_dir = source.is_dir()

    try:
        # Native symlink attempt
        target.symlink_to(source, target_is_directory=is_dir)
        print(f"✅ Linked: {target_rel} -> {source_rel}")

    except OSError as e:
        if platform.system() == "Windows":
            print(f"❌ Failed to create symlink for '{target_rel}': {e}")
            print("   👉 Enable 'Developer Mode' in Windows Settings (Privacy & Security -> For developers).")
        else:
            print(f"❌ Error linking {target_rel}: {e}")

def enable_git_hooks(project_root: Path):
    hooks_dir = project_root / ".github" / ".githooks"
    hook_names = ("post-checkout", "pre-commit")
    hook_paths = [hooks_dir / hook_name for hook_name in hook_names]

    for hook_path in hook_paths:
        if not hook_path.is_file():
            raise FileNotFoundError(f"Git hook not found: {hook_path}")
        if platform.system() != "Windows":
            hook_path.chmod(hook_path.stat().st_mode | 0o111)

    subprocess.run(
        ["git", "config", "--local", "core.hooksPath", ".github/.githooks"],
        cwd=project_root,
        check=True,
    )
    print("✅ Enabled repository Git hooks from .github/.githooks.")

def main():
    project_root = Path(__file__).parent.resolve()
    print(f"🔧 Setting up GitHub Copilot & AI symlinks in: {project_root}\n")

    print("Preparing shared demo AI guardrails submodule...")
    subprocess.run(
        ["git", "submodule", "update", "--init", "--recursive", "--", ".github/demo-ai-guardrails"],
        cwd=project_root,
        check=True,
    )

    for source_rel, target_rel, merge_directory in SYMLINK_MAP:
        create_symlink(source_rel, target_rel, project_root, merge_directory)

    enable_git_hooks(project_root)

    print("\n🎉 GitHub Copilot environment setup complete.")

if __name__ == "__main__":
    main()