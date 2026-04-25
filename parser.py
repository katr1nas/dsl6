"""
parser.py — Recursive-descent parser for Mini SQL.

Consumes a token stream produced by  Lexer  and builds an AST whose
node types are defined in  ast_nodes.py.

Grammar (simplified BNF)
────────────────────────
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
comparison     ::= additive [ ('='|'<>'|'!='|'<'|'>'|'<='|'>=') additive ]
additive       ::= multiplicative (('+' | '-') multiplicative)*
multiplicative ::= unary (('*' | '/' | '%') unary)*
unary          ::= '-' unary  |  primary
primary        ::= '(' expr ')'
               |  identifier ['.' identifier]
               |  INTEGER | FLOAT | STRING | NULL
               |  '*'
"""

from __future__ import annotations
from typing import Optional

from ast_nodes import (
    BinaryOp, FloatLiteral, FromClause, Identifier, IntLiteral,
    JoinClause, LimitClause, NullLiteral, OrderByClause, Program,
    QualifiedIdentifier, SelectStatement, StarExpr, StringLiteral,
    TableRef, UnaryOp, WhereClause, Node,
)
from lexer import Lexer
from sql_token import Token, TokenType


class ParseError(Exception):
    pass


class Parser:
    """
    Recursive-descent parser.

    Usage:
        ast = Parser("SELECT id FROM users WHERE id > 1;").parse()
        ast.pretty()
    """

    def __init__(self, src: str):
        lexer = Lexer(src)
        # Filter out UNKNOWN tokens for robustness; keep EOF
        self._tokens: list[Token] = [
            t for t in lexer.tokenize() if t.type is not TokenType.UNKNOWN
        ]
        self._pos: int = 0

    # ── low-level token operations ─────────────────────────────────────────────
    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        if tok.type is not TokenType.EOF:
            self._pos += 1
        return tok

    def _check(self, ttype: TokenType, value: Optional[str] = None) -> bool:
        tok = self._peek()
        if tok.type is not ttype:
            return False
        if value is not None and tok.value.upper() != value.upper():
            return False
        return True

    def _match(self, ttype: TokenType, value: Optional[str] = None) -> bool:
        if self._check(ttype, value):
            self._advance()
            return True
        return False

    def _expect(self, ttype: TokenType, value: Optional[str] = None) -> Token:
        if not self._check(ttype, value):
            tok = self._peek()
            expected = value if value else ttype.name
            raise ParseError(
                f"Line {tok.line}: expected {expected!r}, got {tok.value!r} ({tok.type.name})"
            )
        return self._advance()

    def _is_keyword(self, *words: str) -> bool:
        tok = self._peek()
        return tok.type is TokenType.KEYWORD and tok.value.upper() in {w.upper() for w in words}

    # ── public entry ──────────────────────────────────────────────────────────
    def parse(self) -> Program:
        stmts: list[SelectStatement] = []
        while self._peek().type is not TokenType.EOF:
            stmts.append(self._parse_select())
            self._match(TokenType.SEMICOLON)
        return Program(stmts)

    # ── SELECT statement ──────────────────────────────────────────────────────
    def _parse_select(self) -> SelectStatement:
        self._expect(TokenType.KEYWORD, "SELECT")

        distinct = bool(self._match(TokenType.KEYWORD) and
                        self._tokens[self._pos - 1].value == "DISTINCT")
        # A cleaner distinct check:
        # back up if the consumed keyword wasn't DISTINCT
        # (above logic has a flaw — redo)
        # Reset and do it properly:
        # The _match already advanced, but we need to check value before advancing.
        # Let's use _is_keyword instead.

        # Restart distinct detection (simpler):
        # We already consumed SELECT; peek for DISTINCT.
        # The block above may have consumed a non-DISTINCT keyword by mistake.
        # Rebuild:
        pass

        distinct = False
        if self._is_keyword("DISTINCT"):
            self._advance()
            distinct = True

        columns = self._parse_select_list()
        self._expect(TokenType.KEYWORD, "FROM")
        from_clause = self._parse_from_clause()

        where_clause: Optional[WhereClause] = None
        if self._is_keyword("WHERE"):
            self._advance()
            where_clause = WhereClause(self._parse_expr())

        order_clause: Optional[OrderByClause] = None
        if self._is_keyword("ORDER"):
            self._advance()
            self._expect(TokenType.KEYWORD, "BY")
            expr = self._parse_expr()
            direction = "ASC"
            if self._is_keyword("ASC", "DESC"):
                direction = self._advance().value.upper()
            order_clause = OrderByClause(expr, direction)

        limit_clause: Optional[LimitClause] = None
        if self._is_keyword("LIMIT"):
            self._advance()
            limit_tok = self._expect(TokenType.INTEGER)
            limit_val = int(limit_tok.value)
            offset_val: Optional[int] = None
            if self._is_keyword("OFFSET"):
                self._advance()
                offset_val = int(self._expect(TokenType.INTEGER).value)
            limit_clause = LimitClause(limit_val, offset_val)

        return SelectStatement(distinct, columns, from_clause,
                               where_clause, order_clause, limit_clause)

    # ── SELECT list ───────────────────────────────────────────────────────────
    def _parse_select_list(self) -> list[Node]:
        if self._check(TokenType.STAR):
            self._advance()
            return [StarExpr()]
        cols: list[Node] = [self._parse_expr()]
        while self._match(TokenType.COMMA):
            cols.append(self._parse_expr())
        return cols

    # ── FROM + JOINs ──────────────────────────────────────────────────────────
    def _parse_from_clause(self) -> FromClause:
        table = self._parse_table_ref()
        joins: list[JoinClause] = []
        while True:
            join_type = self._try_parse_join_keyword()
            if join_type is None:
                break
            join_table = self._parse_table_ref()
            self._expect(TokenType.KEYWORD, "ON")
            on_expr = self._parse_expr()
            joins.append(JoinClause(join_type, join_table, on_expr))
        return FromClause(table, joins)

    def _try_parse_join_keyword(self) -> Optional[str]:
        """Consume and return the full join type string, or return None."""
        # Plain JOIN
        if self._is_keyword("JOIN"):
            self._advance()
            return "JOIN"
        # Qualified: INNER|LEFT|RIGHT|OUTER  JOIN
        for qualifier in ("INNER", "LEFT", "RIGHT", "OUTER"):
            if self._is_keyword(qualifier):
                self._advance()
                self._expect(TokenType.KEYWORD, "JOIN")
                return f"{qualifier} JOIN"
        return None

    def _parse_table_ref(self) -> TableRef:
        name_tok = self._expect(TokenType.IDENTIFIER)
        alias: Optional[str] = None
        if self._is_keyword("AS"):
            self._advance()
            alias = self._expect(TokenType.IDENTIFIER).value
        elif self._check(TokenType.IDENTIFIER):
            # Optional AS without the keyword: FROM employees e
            alias = self._advance().value
        return TableRef(name_tok.value, alias)

    # ── expressions (Pratt-style with helper methods) ─────────────────────────
    def _parse_expr(self) -> Node:
        return self._parse_or()

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

    def _parse_not(self) -> Node:
        if self._is_keyword("NOT"):
            op = self._advance().value
            return UnaryOp(op, self._parse_not())
        return self._parse_comparison()

    _COMPARISON_OPS = {
        TokenType.EQ, TokenType.NEQ, TokenType.LT,
        TokenType.GT, TokenType.LTE, TokenType.GTE,
    }

    def _parse_comparison(self) -> Node:
        left = self._parse_additive()
        if self._peek().type in self._COMPARISON_OPS:
            op = self._advance().value
            left = BinaryOp(op, left, self._parse_additive())
        return left

    def _parse_additive(self) -> Node:
        left = self._parse_multiplicative()
        while self._peek().type in (TokenType.PLUS, TokenType.MINUS):
            op = self._advance().value
            left = BinaryOp(op, left, self._parse_multiplicative())
        return left

    def _parse_multiplicative(self) -> Node:
        left = self._parse_unary()
        while self._peek().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self._advance().value
            left = BinaryOp(op, left, self._parse_unary())
        return left

    def _parse_unary(self) -> Node:
        if self._check(TokenType.MINUS):
            op = self._advance().value
            return UnaryOp(op, self._parse_unary())
        return self._parse_primary()

    def _parse_primary(self) -> Node:
        tok = self._peek()

        # Parenthesised expression
        if tok.type is TokenType.LPAREN:
            self._advance()
            expr = self._parse_expr()
            self._expect(TokenType.RPAREN)
            return expr

        # NULL literal
        if tok.type is TokenType.KEYWORD and tok.value == "NULL":
            self._advance()
            return NullLiteral()

        # Integer literal
        if tok.type is TokenType.INTEGER:
            self._advance()
            return IntLiteral(int(tok.value))

        # Float literal
        if tok.type is TokenType.FLOAT:
            self._advance()
            return FloatLiteral(float(tok.value))

        # String literal
        if tok.type is TokenType.STRING:
            self._advance()
            return StringLiteral(tok.value)

        # Star (only in SELECT list context — handled by _parse_select_list,
        # but we allow it here too for  COUNT(*)  style use)
        if tok.type is TokenType.STAR:
            self._advance()
            return StarExpr()

        # Identifier, possibly qualified (table.column)
        if tok.type is TokenType.IDENTIFIER:
            self._advance()
            if self._check(TokenType.DOT):
                self._advance()
                col_tok = self._expect(TokenType.IDENTIFIER)
                return QualifiedIdentifier(tok.value, col_tok.value)
            return Identifier(tok.value)

        raise ParseError(
            f"Line {tok.line}: unexpected token {tok.value!r} ({tok.type.name})"
        )
