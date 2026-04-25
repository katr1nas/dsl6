"""
sql_token.py — Token types and Token dataclass for the Mini SQL lexer/parser.

Each TokenType is paired with a compiled regular expression that the lexer
uses to identify that category of token. Using regex here fulfils the lab
requirement: "use regular expressions to identify the type of the token."
"""

import re
from dataclasses import dataclass
from enum import Enum, auto


# ── keyword set ──────────────────────────────────────────────────────────────
SQL_KEYWORDS: frozenset[str] = frozenset({
    "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "NULL", "AS", "DISTINCT",
    "ORDER", "BY", "LIMIT", "OFFSET", "JOIN", "ON", "INNER", "LEFT", "RIGHT",
    "OUTER", "CREATE", "TABLE", "DROP", "DELETE", "UPDATE", "SET", "INSERT",
    "INTO", "VALUES", "GROUP", "HAVING", "ASC", "DESC",
})


# ── token types ───────────────────────────────────────────────────────────────
class TokenType(Enum):
    # Literals
    INTEGER    = auto()
    FLOAT      = auto()
    STRING     = auto()
    # Identifiers / keywords
    KEYWORD    = auto()
    IDENTIFIER = auto()
    # Arithmetic operators
    PLUS       = auto()
    MINUS      = auto()
    STAR       = auto()
    SLASH      = auto()
    PERCENT    = auto()
    # Comparison operators
    EQ         = auto()   # =
    NEQ        = auto()   # <> or !=
    LT         = auto()   # <
    GT         = auto()   # >
    LTE        = auto()   # <=
    GTE        = auto()   # >=
    # Punctuation
    COMMA      = auto()
    SEMICOLON  = auto()
    LPAREN     = auto()
    RPAREN     = auto()
    DOT        = auto()
    # Special
    EOF        = auto()
    UNKNOWN    = auto()


# ── regex patterns (used by Lexer for token identification) ──────────────────
# Order matters: longer / more specific patterns must come first.
TOKEN_PATTERNS: list[tuple[TokenType, re.Pattern]] = [
    # Floats before integers to match the decimal point
    (TokenType.FLOAT,      re.compile(r'\d+\.\d+([eE][+-]?\d+)?')),
    (TokenType.INTEGER,    re.compile(r'\d+')),
    # String literals: single-quoted, allow \' escape inside
    (TokenType.STRING,     re.compile(r"'(?:[^'\\]|\\.)*'")),
    # Two-character comparison operators (before single-char)
    (TokenType.LTE,        re.compile(r'<=')),
    (TokenType.GTE,        re.compile(r'>=')),
    (TokenType.NEQ,        re.compile(r'<>|!=')),
    # Single-character operators / punctuation
    (TokenType.LT,         re.compile(r'<')),
    (TokenType.GT,         re.compile(r'>')),
    (TokenType.EQ,         re.compile(r'=')),
    (TokenType.PLUS,       re.compile(r'\+')),
    (TokenType.MINUS,      re.compile(r'-')),
    (TokenType.STAR,       re.compile(r'\*')),
    (TokenType.SLASH,      re.compile(r'/')),
    (TokenType.PERCENT,    re.compile(r'%')),
    (TokenType.COMMA,      re.compile(r',')),
    (TokenType.SEMICOLON,  re.compile(r';')),
    (TokenType.LPAREN,     re.compile(r'\(')),
    (TokenType.RPAREN,     re.compile(r'\)')),
    (TokenType.DOT,        re.compile(r'\.')),
    # Words: checked against SQL_KEYWORDS after matching
    (TokenType.IDENTIFIER, re.compile(r'[A-Za-z_][A-Za-z0-9_]*')),
]


# ── token dataclass ───────────────────────────────────────────────────────────
@dataclass
class Token:
    type:  TokenType
    value: str
    line:  int = 1

    def __repr__(self) -> str:
        return f"Token({self.type.name:<12} {self.value!r:<22} line={self.line})"
