"""
main_parser.py — Demo for Lab 6: Parser & AST
"""

from lexer import Lexer
from parser import Parser
from ast_nodes import pretty_print

DIVIDER = "─" * 64


EXAMPLES = [
    # ── 1 ──────────────────────────────────────────────────────────────────
    (
        "Basic SELECT with WHERE",
        "SELECT * FROM employees WHERE dept_id = 10;"
    ),
    # ── 2 ──────────────────────────────────────────────────────────────────
    (
        "Arithmetic expression + column alias",
        "SELECT name, salary * 1.1 FROM staff WHERE salary >= 50000.0;"
    ),
    # ── 3 ──────────────────────────────────────────────────────────────────
    (
        "JOIN with table alias and qualified column names",
        "SELECT e.name FROM employees e JOIN departments d ON e.dept_id = d.id;"
    ),
    # ── 4 ──────────────────────────────────────────────────────────────────
    (
        "Compound WHERE with AND / OR / NOT",
        "SELECT id, email FROM users WHERE active <> 0 AND NOT role = 'admin' OR is_superuser = 1;"
    ),
    # ── 5 ──────────────────────────────────────────────────────────────────
    (
        "ORDER BY + LIMIT + OFFSET",
        "SELECT id, name FROM products ORDER BY price DESC LIMIT 10 OFFSET 20;"
    ),
    # ── 6 ──────────────────────────────────────────────────────────────────
    (
        "Subexpression with parentheses",
        "SELECT (salary + bonus) * 1.2 FROM employees;"
    ),
]


def demo_tokens(sql: str) -> None:
    """Print the raw token stream produced by the lexer."""
    tokens = Lexer(sql).tokenize()
    print("  Token stream:")
    for tok in tokens:
        print(f"    {tok}")


def demo_ast(sql: str) -> None:
    """Parse the SQL and pretty-print the resulting AST."""
    ast = Parser(sql).parse()
    print("  AST:")
    for line in ast.pretty().splitlines():
        print(f"    {line}")


def main() -> None:
    print("\n" + "=" * 64)
    print("  LAB 6 — Parser & Abstract Syntax Tree")
    print("  Course: Formal Languages & Finite Automata")
    print("=" * 64)

    for title, sql in EXAMPLES:
        print(f"\n{DIVIDER}")
        print(f"  Test: {title}")
        print(f"  SQL : {sql}")
        print(DIVIDER)
        demo_tokens(sql)
        print()
        demo_ast(sql)


if __name__ == "__main__":
    main()
