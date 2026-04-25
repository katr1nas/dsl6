# dsl6
# Lab Work No. 6 — Parser & Abstract Syntax Tree

**Course:** Formal Languages & Finite Automata  
**Author:** Serghei Barladean  
**Date:** May 2026

---

## Table of Contents

1. [Objectives](#objectives)
2. [Theoretical Background](#theoretical-background)
3. [Domain — Mini SQL Parser](#domain--mini-sql-parser)
4. [Grammar Specification](#grammar-specification)
5. [AST Node Definitions](#ast-node-definitions)
6. [Implementation](#implementation)
7. [Program Output](#program-output)
8. [Conclusions](#conclusions)

---

## Objectives

1. Understand what parsing is and how it is implemented programmatically.
2. Understand the Abstract Syntax Tree data structure and how it differs from a parse tree.
3. Extend the Mini SQL Lexer from Lab 3 with:
   - Explicit `TokenType` enum backed by **regular expressions** for token identification.
   - AST node data structures for the SQL domain.
   - A recursive-descent parser that transforms a token stream into an AST.

---

## Theoretical Background

### Parsing

**Parsing** (syntactic analysis) is the process of analysing a sequence of tokens to determine their grammatical structure with respect to a formal grammar. It is the second phase of a typical compiler/interpreter pipeline, immediately after lexical analysis:

```
Source text
    │
    ▼
┌─────────┐   token stream   ┌────────┐   AST    ┌────────────┐
│  LEXER  │ ──────────────▶  │ PARSER │ ──────▶  │ EVALUATOR  │
└─────────┘                  └────────┘          └────────────┘
```

Two broad families of parsers exist:

| Family | Strategy | Typical algorithm |
|--------|----------|-------------------|
| Top-down | Predict & match from root | Recursive descent, LL(k) |
| Bottom-up | Shift & reduce from leaves | LR(k), LALR, Earley |

This lab uses **recursive descent** — one function per grammar non-terminal, each calling others to handle sub-expressions. It is the most readable parsing technique and maps directly onto the BNF grammar.

### Parse Tree vs Abstract Syntax Tree

A **parse tree** (concrete syntax tree) mirrors the grammar exactly — every rule application, including parentheses and punctuation, appears as a node. An **AST** discards noise and retains only semantic content:

```
Input: (salary + bonus) * 1.2

Parse tree:                  AST:
expr                         BinaryOp('*')
└── multiplicative           ├── BinaryOp('+')
    ├── unary                │   ├── Identifier(salary)
    │   └── primary          │   └── Identifier(bonus)
    │       ├── '('          └── FloatLiteral(1.2)
    │       ├── expr
    │       │   └── additive
    │       │       ├── …
    │       └── ')'
    ├── '*'
    └── primary
        └── FLOAT(1.2)
```

The parentheses carry no meaning once operator precedence is encoded in the tree structure — so the AST omits them entirely.

### Operator Precedence via Grammar Levels

Precedence is enforced by the grammar hierarchy:

```
expr          (lowest — OR)
└── or_expr
    └── and_expr
        └── not_expr
            └── comparison
                └── additive     (+  -)
                    └── multiplicative  (*  /  %)
                        └── unary      (-)
                            └── primary  (lowest — atoms)
```

Each level can only call levels *below* it for its operands, so a `*` always binds more tightly than a `+`. No explicit precedence tables are needed.

---

## Domain — Mini SQL Parser

The parser handles a **Mini SQL** dialect — the same domain as the Lab 3 lexer. A program is a sequence of `SELECT` statements, each of which may include:

- `DISTINCT`
- Column list (`*` or expressions)
- `FROM table [alias]`
- `[INNER|LEFT|RIGHT|OUTER] JOIN … ON …`
- `WHERE` expression (AND, OR, NOT, comparisons, arithmetic)
- `ORDER BY … [ASC|DESC]`
- `LIMIT … [OFFSET …]`

---

## Grammar Specification

```
program        ::= statement (';' statement)* ';'?
statement      ::= select_stmt
select_stmt    ::= SELECT [DISTINCT] select_list
                   FROM table_ref
                   join_clause*
                   [WHERE expr]
                   [ORDER BY expr [ASC | DESC]]
                   [LIMIT integer [OFFSET integer]]
select_list    ::= '*'  |  expr (',' expr)*
table_ref      ::= identifier [AS? identifier]
join_clause    ::= [INNER|LEFT|RIGHT|OUTER] JOIN table_ref ON expr
expr           ::= or_expr
or_expr        ::= and_expr (OR and_expr)*
and_expr       ::= not_expr (AND not_expr)*
not_expr       ::= NOT not_expr  |  comparison
comparison     ::= additive [('='|'<>'|'!='|'<'|'>'|'<='|'>=') additive]
additive       ::= multiplicative (('+' | '-') multiplicative)*
multiplicative ::= unary (('*' | '/' | '%') unary)*
unary          ::= '-' unary  |  primary
primary        ::= '(' expr ')'
               |  identifier ['.' identifier]
               |  INTEGER | FLOAT | STRING | NULL | '*'
```

---

## AST Node Definitions

All nodes are Python `dataclass` objects that inherit from a common `Node` base and implement `pretty(indent)` for tree rendering.

### Expression Nodes

| Node | Fields | Example |
|------|--------|---------|
| `IntLiteral` | `value: int` | `42` |
| `FloatLiteral` | `value: float` | `3.14` |
| `StringLiteral` | `value: str` | `'Alice'` |
| `NullLiteral` | — | `NULL` |
| `StarExpr` | — | `*` |
| `Identifier` | `name: str` | `salary` |
| `QualifiedIdentifier` | `table, column: str` | `e.dept_id` |
| `BinaryOp` | `op, left, right` | `salary >= 50000` |
| `UnaryOp` | `op, operand` | `NOT active` |

### Structural Nodes

| Node | Fields |
|------|--------|
| `TableRef` | `name, alias?` |
| `JoinClause` | `join_type, table, on_expr` |
| `FromClause` | `table, joins[]` |
| `WhereClause` | `condition` |
| `OrderByClause` | `expr, direction` |
| `LimitClause` | `limit, offset?` |
| `SelectStatement` | `distinct, columns[], from_clause, where_clause?, order_clause?, limit_clause?` |
| `Program` | `statements[]` |

---

## Implementation

The project contains four source files:

```
sql_token.py    ← TokenType enum + TOKEN_PATTERNS (regex list) + Token dataclass
lexer.py        ← Lexer (from Lab 3, uses TOKEN_PATTERNS for identification)
ast_nodes.py    ← All AST node dataclasses
parser.py       ← Recursive-descent parser
main_parser.py  ← Demo runner
```

---

### `sql_token.py` — Token Types with Regex

Each `TokenType` is paired with a compiled regex in the `TOKEN_PATTERNS` list. The lexer iterates this list in order for every new token, so longer patterns (e.g. `<=`) are checked before shorter ones (`<`):

```python
TOKEN_PATTERNS: list[tuple[TokenType, re.Pattern]] = [
    (TokenType.FLOAT,   re.compile(r'\d+\.\d+([eE][+-]?\d+)?')),
    (TokenType.INTEGER, re.compile(r'\d+')),
    (TokenType.STRING,  re.compile(r"'(?:[^'\\]|\\.)*'")),
    (TokenType.LTE,     re.compile(r'<=')),
    (TokenType.GTE,     re.compile(r'>=')),
    (TokenType.NEQ,     re.compile(r'<>|!=')),
    # … single-char operators …
    (TokenType.IDENTIFIER, re.compile(r'[A-Za-z_][A-Za-z0-9_]*')),
]
```

After an `IDENTIFIER` match, the value is looked up in `SQL_KEYWORDS` to decide whether it becomes a `KEYWORD` token instead.

---

### `lexer.py` — Pattern-Driven Lexer

`next_token()` simply tries each pattern at `self.pos` using `pattern.match(src, pos)`. The first match wins:

```python
def next_token(self) -> Token:
    self._skip_whitespace_and_comments()
    if self.pos >= len(self.src):
        return Token(TokenType.EOF, "", self.line)

    for ttype, pattern in TOKEN_PATTERNS:
        m = pattern.match(self.src, self.pos)
        if m:
            value = m.group(0)
            self.pos += len(value)
            if ttype is TokenType.IDENTIFIER and value.upper() in SQL_KEYWORDS:
                ttype  = TokenType.KEYWORD
                value  = value.upper()
            if ttype is TokenType.STRING:
                value = value[1:-1].replace("\\'", "'")
            return Token(ttype, value, self.line)

    ch = self.src[self.pos]; self.pos += 1
    return Token(TokenType.UNKNOWN, ch, self.line)
```

---

### `ast_nodes.py` — Node Hierarchy

Every node implements `pretty(indent)` which returns an indented string. Compound nodes delegate to children:

```python
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
```

---

### `parser.py` — Recursive Descent

The parser stores the full token list and an integer cursor. Helper methods:

| Method | Purpose |
|--------|---------|
| `_peek()` | Look at current token without advancing |
| `_advance()` | Consume and return current token |
| `_check(type, value?)` | Test current token without consuming |
| `_match(type, value?)` | Consume if match, return bool |
| `_expect(type, value?)` | Consume or raise `ParseError` |
| `_is_keyword(*words)` | Check current token is a keyword in set |

**Expression parsing** uses the grammar hierarchy to enforce precedence without any explicit table. Each level calls the next-lower level for its operands:

```python
def _parse_or(self) -> Node:
    left = self._parse_and()
    while self._is_keyword("OR"):
        op = self._advance().value
        left = BinaryOp(op, left, self._parse_and())
    return left

def _parse_and(self) -> Node:
    left = self._parse_not()
    while self._is_keyword("AND"):
        op = self._advance().value
        left = BinaryOp(op, left, self._parse_not())
    return left
```

**Join parsing** consumes the optional qualifier and mandatory `JOIN` keyword as one unit:

```python
def _try_parse_join_keyword(self) -> Optional[str]:
    if self._is_keyword("JOIN"):
        self._advance(); return "JOIN"
    for qualifier in ("INNER", "LEFT", "RIGHT", "OUTER"):
        if self._is_keyword(qualifier):
            self._advance()
            self._expect(TokenType.KEYWORD, "JOIN")
            return f"{qualifier} JOIN"
    return None
```

---

## Program Output

### Test 1 — Basic SELECT with WHERE

```sql
SELECT * FROM employees WHERE dept_id = 10;
```

```
Program:
  [0]
    SelectStatement(distinct=False)
      columns:
        Star(*)
      FromClause:
        TableRef(employees)
      WhereClause:
        BinaryOp('=')
          left:
            Identifier(dept_id)
          right:
            IntLiteral(10)
```

---

### Test 2 — Arithmetic expression

```sql
SELECT name, salary * 1.1 FROM staff WHERE salary >= 50000.0;
```

```
Program:
  [0]
    SelectStatement(distinct=False)
      columns:
        Identifier(name)
        BinaryOp('*')
          left:
            Identifier(salary)
          right:
            FloatLiteral(1.1)
      FromClause:
        TableRef(staff)
      WhereClause:
        BinaryOp('>=')
          left:
            Identifier(salary)
          right:
            FloatLiteral(50000.0)
```

---

### Test 3 — JOIN with table alias and qualified column names

```sql
SELECT e.name FROM employees e JOIN departments d ON e.dept_id = d.id;
```

```
Program:
  [0]
    SelectStatement(distinct=False)
      columns:
        QualifiedIdentifier(e.name)
      FromClause:
        TableRef(employees AS e)
        JoinClause(JOIN)
          TableRef(departments AS d)
          ON:
            BinaryOp('=')
              left:
                QualifiedIdentifier(e.dept_id)
              right:
                QualifiedIdentifier(d.id)
```

---

### Test 4 — Compound WHERE with AND / OR / NOT

```sql
SELECT id, email FROM users
WHERE active <> 0 AND NOT role = 'admin' OR is_superuser = 1;
```

```
WhereClause:
  BinaryOp('OR')
    left:
      BinaryOp('AND')
        left:
          BinaryOp('<>')
            left:  Identifier(active)
            right: IntLiteral(0)
        right:
          UnaryOp('NOT')
            BinaryOp('=')
              left:  Identifier(role)
              right: StringLiteral('admin')
    right:
      BinaryOp('=')
        left:  Identifier(is_superuser)
        right: IntLiteral(1)
```

The tree shows correct precedence: `NOT` binds tighter than `AND`, and `AND` tighter than `OR`.

---

### Test 5 — ORDER BY + LIMIT + OFFSET

```sql
SELECT id, name FROM products ORDER BY price DESC LIMIT 10 OFFSET 20;
```

```
SelectStatement(distinct=False)
  columns:
    Identifier(id)
    Identifier(name)
  FromClause:
    TableRef(products)
  OrderByClause(DESC):
    Identifier(price)
  LimitClause(LIMIT 10  OFFSET 20)
```

---

### Test 6 — Parenthesised subexpression

```sql
SELECT (salary + bonus) * 1.2 FROM employees;
```

```
columns:
  BinaryOp('*')
    left:
      BinaryOp('+')
        left:  Identifier(salary)
        right: Identifier(bonus)
    right:
      FloatLiteral(1.2)
```

The parentheses are gone — their effect is encoded in the tree structure (`+` is a child of `*`).

---

## Conclusions

1. **The AST is cleaner than the parse tree.** Parentheses, semicolons, and keyword tokens like `SELECT` or `FROM` have no place in the AST — they were needed to parse the structure, but once that structure is in the tree, they carry no information. The result is a compact, semantics-only representation.

2. **Grammar levels enforce precedence automatically.** By structuring the recursive calls so that `OR` calls `AND`, `AND` calls `NOT`, `NOT` calls `comparison`, and so on, operator precedence emerges from the call stack without any explicit priority table. `NOT` always binds tighter than `AND`, which always binds tighter than `OR` — this is verified by Test 4.

3. **Regex patterns in TOKEN_PATTERNS make the lexer transparent.** Each token type is paired with a compiled regex right next to its enum value. This makes it easy to see at a glance what string patterns map to what types, and to add new token types without touching the scanning loop.

4. **Maximal munch is preserved by pattern ordering.** `<=`, `>=`, `<>`, `!=` must appear before `<`, `>`, `=`, `-` in `TOKEN_PATTERNS`. Because `re.Pattern.match` anchors at the current position and we pick the first hit, the order of the list is the tie-breaker — exactly the maximal-munch rule.

5. **Qualified identifiers (table.column) require one token of lookahead.** After scanning an identifier, the parser peeks at the next token: if it is a `.`, a qualified identifier is assembled from the two names. This is a common pattern in recursive descent — the grammar is technically LL(1) but one extra peek after the primary prevents any backtracking.

6. **The parser and the AST are fully decoupled.** `ast_nodes.py` knows nothing about tokens or the parser. This separation means the same AST could be produced by a different front-end (e.g. a JSON-to-AST converter), or the same parser could target a different AST shape without rewriting either component.
