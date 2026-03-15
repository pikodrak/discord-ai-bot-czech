"""
Fix Python 3.9 compatibility by converting Python 3.10+ union syntax to Optional.

This script converts type hints like:
  str | None  ->  Optional[str]
  int | None  ->  Optional[int]
  dict[str, Any] | None  ->  Optional[dict[str, Any]]
"""

import re
import sys
from pathlib import Path

def fix_file(filepath: Path) -> tuple[bool, int]:
    """
    Fix union type syntax in a Python file.

    Args:
        filepath: Path to the Python file

    Returns:
        Tuple of (was_modified, num_changes)
    """
    content = filepath.read_text()
    original_content = content
    changes = 0

    # Check if file already imports Optional
    has_optional_import = 'from typing import' in content and 'Optional' in content

    # Pattern to match: type | None
    # Matches: str | None, int | None, dict[...] | None, etc.
    pattern = r'([A-Za-z_]\w*(?:\[[^\]]+\])?)\s*\|\s*None'

    # Find all matches
    matches = list(re.finditer(pattern, content))

    if matches:
        # Replace all occurrences
        content = re.sub(pattern, r'Optional[\1]', content)
        changes = len(matches)

        # Add Optional to imports if not present
        if not has_optional_import:
            # Find the typing import line
            typing_import_pattern = r'from typing import ([^\n]+)'
            typing_match = re.search(typing_import_pattern, content)

            if typing_match:
                # Add Optional to existing import
                imports = typing_match.group(1).strip()
                if not imports.endswith(','):
                    imports += ','
                imports += ' Optional'
                content = re.sub(
                    typing_import_pattern,
                    f'from typing import {imports}',
                    content,
                    count=1
                )
            else:
                # No typing import found, add one after other imports
                # Find the last import statement
                import_lines = []
                for line in content.split('\n'):
                    if line.startswith('import ') or line.startswith('from '):
                        import_lines.append(line)

                if import_lines:
                    last_import = import_lines[-1]
                    content = content.replace(
                        last_import,
                        f'{last_import}\nfrom typing import Optional',
                        1
                    )

    if content != original_content:
        filepath.write_text(content)
        return True, changes
    return False, 0


def main():
    """Fix all Python files in src/llm/."""
    project_root = Path(__file__).parent
    llm_dir = project_root / 'src' / 'llm'

    if not llm_dir.exists():
        print(f"Error: {llm_dir} not found")
        return 1

    print("Fixing Python 3.9 compatibility issues...")
    print("=" * 70)

    total_files = 0
    total_changes = 0
    modified_files = []

    for filepath in sorted(llm_dir.glob('*.py')):
        if filepath.name == '__pycache__':
            continue

        was_modified, changes = fix_file(filepath)
        if was_modified:
            total_files += 1
            total_changes += changes
            modified_files.append(filepath.name)
            print(f"✓ {filepath.name}: {changes} change(s)")
        else:
            print(f"  {filepath.name}: no changes needed")

    print("=" * 70)
    print(f"Modified {total_files} file(s), {total_changes} total change(s)")

    if modified_files:
        print("\nModified files:")
        for filename in modified_files:
            print(f"  - {filename}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
