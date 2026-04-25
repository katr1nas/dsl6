"""
ast_nodes.py — Abstract Syntax Tree node definitions for the Mini SQL parser.

Every node is a plain Python dataclass.  The tree is printed with
the helper function  pretty_print(node)  which walks it recursively
and renders an indented, human-readable representation.

Node hierarchy
──────────────
Program
└── SelectStatement
    ├── distinct: bool
    ├── columns: list[Expr | StarExpr]
    ├── from_clause: FromClause
    │   ├── table: TableRef
    │   └── joins: list[JoinClause]
    ├── where_clause: WhereClause | None
    ├── order_clause: OrderByClause | None
    └── limit_clause: LimitClause | None

Expressions
    BinaryOp  (left op right)
    UnaryOp   (op operand)
    Identifier (name)
    QualifiedIdentifier (table.column)
    IntLiteral | FloatLiteral | StringLiteral | NullLiteral
    StarExpr   (* in SELECT list)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ── base ──────────────────────────────────────────────────────────────────────
class Node:
    """Base class for every AST node."""

    def pretty(self, indent: int = 0) -> str:
        """Return a nicely-indented string representation of this subtree."""
        raise NotImplementedError


def _ind(level: int) -> str:
    return "  " * level


# ── expressions ───────────────────────────────────────────────────────────────
@dataclass
class IntLiteral(Node):
    value: int

    def pretty(self, indent: int = 0) -> str:
        return f"{_ind(indent)}IntLiteral({self.value})"


@dataclass
class FloatLiteral(Node):
    value: float

    def pretty(self, indent: int = 0) -> str:
        return f"{_ind(indent)}FloatLiteral({self.value})"


@dataclass
class StringLiteral(Node):
    value: str

    def pretty(self, indent: int = 0) -> str:
        return f"{_ind(indent)}StringLiteral({self.value!r})"


@dataclass
class NullLiteral(Node):
    def pretty(self, indent: int = 0) -> str:
        return f"{_ind(indent)}NullLiteral"


@dataclass
class StarExpr(Node):
    """The bare  *  in  SELECT * …"""
    def pretty(self, indent: int = 0) -> str:
        return f"{_ind(indent)}Star(*)"


@dataclass
class Identifier(Node):
    name: str

    def pretty(self, indent: int = 0) -> str:
        return f"{_ind(indent)}Identifier({self.name})"


@dataclass
class QualifiedIdentifier(Node):
    """table.column  notation."""
    table: str
    column: str

    def pretty(self, indent: int = 0) -> str:
        return f"{_ind(indent)}QualifiedIdentifier({self.table}.{self.column})"


@dataclass
class BinaryOp(Node):
    op: str
    left: Node
    right: Node

    def pretty(self, indent: int = 0) -> str:
        lines = [f"{_ind(indent)}BinaryOp({self.op!r})"]
        lines.append(f"{_ind(indent+1)}left:")
        lines.append(self.left.pretty(indent + 2))
        lines.append(f"{_ind(indent+1)}right:")
        lines.append(self.right.pretty(indent + 2))
        return "\n".join(lines)


@dataclass
class UnaryOp(Node):
    op: str
    operand: Node

    def pretty(self, indent: int = 0) -> str:
        lines = [f"{_ind(indent)}UnaryOp({self.op!r})"]
        lines.append(self.operand.pretty(indent + 1))
        return "\n".join(lines)


# ── table / join references ───────────────────────────────────────────────────
@dataclass
class TableRef(Node):
    """A table name with an optional alias:  employees AS e  or just  employees."""
    name: str
    alias: Optional[str] = None

    def pretty(self, indent: int = 0) -> str:
        alias_str = f" AS {self.alias}" if self.alias else ""
        return f"{_ind(indent)}TableRef({self.name}{alias_str})"


@dataclass
class JoinClause(Node):
    join_type: str          # INNER, LEFT, RIGHT, OUTER, plain JOIN
    table: TableRef
    on_expr: Node

    def pretty(self, indent: int = 0) -> str:
        lines = [f"{_ind(indent)}JoinClause({self.join_type})"]
        lines.append(self.table.pretty(indent + 1))
        lines.append(f"{_ind(indent+1)}ON:")
        lines.append(self.on_expr.pretty(indent + 2))
        return "\n".join(lines)


# ── clauses ───────────────────────────────────────────────────────────────────
@dataclass
class FromClause(Node):
    table: TableRef
    joins: list[JoinClause] = field(default_factory=list)

    def pretty(self, indent: int = 0) -> str:
        lines = [f"{_ind(indent)}FromClause:"]
        lines.append(self.table.pretty(indent + 1))
        for j in self.joins:
            lines.append(j.pretty(indent + 1))
        return "\n".join(lines)


@dataclass
class WhereClause(Node):
    condition: Node

    def pretty(self, indent: int = 0) -> str:
        lines = [f"{_ind(indent)}WhereClause:"]
        lines.append(self.condition.pretty(indent + 1))
        return "\n".join(lines)


@dataclass
class OrderByClause(Node):
    expr: Node
    direction: str = "ASC"      # ASC | DESC

    def pretty(self, indent: int = 0) -> str:
        lines = [f"{_ind(indent)}OrderByClause({self.direction}):"]
        lines.append(self.expr.pretty(indent + 1))
        return "\n".join(lines)


@dataclass
class LimitClause(Node):
    limit: int
    offset: Optional[int] = None

    def pretty(self, indent: int = 0) -> str:
        off = f"  OFFSET {self.offset}" if self.offset is not None else ""
        return f"{_ind(indent)}LimitClause(LIMIT {self.limit}{off})"


# ── top-level statement ───────────────────────────────────────────────────────
@dataclass
class SelectStatement(Node):
    distinct: bool
    columns: list[Node]
    from_clause: FromClause
    where_clause: Optional[WhereClause]
    order_clause: Optional[OrderByClause]
    limit_clause: Optional[LimitClause]

    def pretty(self, indent: int = 0) -> str:
        lines = [f"{_ind(indent)}SelectStatement(distinct={self.distinct})"]
        lines.append(f"{_ind(indent+1)}columns:")
        for col in self.columns:
            lines.append(col.pretty(indent + 2))
        lines.append(self.from_clause.pretty(indent + 1))
        if self.where_clause:
            lines.append(self.where_clause.pretty(indent + 1))
        if self.order_clause:
            lines.append(self.order_clause.pretty(indent + 1))
        if self.limit_clause:
            lines.append(self.limit_clause.pretty(indent + 1))
        return "\n".join(lines)


@dataclass
class Program(Node):
    """Root node — a list of SQL statements."""
    statements: list[SelectStatement]

    def pretty(self, indent: int = 0) -> str:
        lines = [f"{_ind(indent)}Program:"]
        for i, stmt in enumerate(self.statements):
            lines.append(f"{_ind(indent+1)}[{i}]")
            lines.append(stmt.pretty(indent + 2))
        return "\n".join(lines)


# ── pretty-print helper ───────────────────────────────────────────────────────
def pretty_print(node: Node) -> None:
    print(node.pretty())
