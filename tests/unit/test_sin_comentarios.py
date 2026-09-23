from __future__ import annotations

import ast
import io
import re
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCANNED_DIRECTORIES = ("src", "tests", "migrations")
TOOLING_DIRECTIVE = re.compile(
    r"#\s*(?:"
    r"type:\s*ignore(?:\[[a-z0-9_,\s-]+\])?"
    r"|noqa(?::\s*[A-Z0-9]+(?:\s*,\s*[A-Z0-9]+)*)?"
    r"|pragma:\s*no cover"
    r")"
)


def _python_files() -> list[Path]:
    return sorted(
        path
        for directory in SCANNED_DIRECTORIES
        for path in (ROOT / directory).rglob("*.py")
        if "__pycache__" not in path.parts
    )


def _relative(path: Path, line: int) -> str:
    return f"{path.relative_to(ROOT).as_posix()}:{line}"


def _comment_offenders(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    return [
        _relative(path, token.start[0])
        for token in tokens
        if token.type == tokenize.COMMENT and not TOOLING_DIRECTIVE.fullmatch(token.string)
    ]


def _docstring_offenders(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    documentable = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    return [
        _relative(path, node.body[0].lineno)
        for node in ast.walk(tree)
        if isinstance(node, documentable) and ast.get_docstring(node, clean=False) is not None
    ]


def test_el_codigo_no_tiene_comentarios() -> None:
    offenders = [line for path in _python_files() for line in _comment_offenders(path)]
    assert offenders == []


def test_el_codigo_no_tiene_docstrings() -> None:
    offenders = [line for path in _python_files() for line in _docstring_offenders(path)]
    assert offenders == []
