"""
lexer.py — Mini SQL Lexer (Lab 3, enhanced for Lab 6).

The lexer now uses the TOKEN_PATTERNS list from sql_token.py so that every
token category is identified through a regular expression, satisfying the
lab requirement explicitly.
"""

from sql_token import SQL_KEYWORDS, TOKEN_PATTERNS, Token, TokenType


class LexerError(Exception):
    pass


class Lexer:
    """
    Tokenises a Mini SQL string into a flat stream of Token objects.

    Usage:
        lexer  = Lexer("SELECT * FROM users;")
        tokens = lexer.tokenize()     # → list[Token]

    Or consume one token at a time:
        tok = lexer.next_token()
    """

    def __init__(self, src: str):
        self.src  = src
        self.pos  = 0
        self.line = 1

    # ── public API ─────────────────────────────────────────────────────────────
    def tokenize(self) -> list[Token]:
        """Return all tokens (including the final EOF)."""
        tokens: list[Token] = []
        while True:
            tok = self.next_token()
            tokens.append(tok)
            if tok.type is TokenType.EOF:
                break
        return tokens

    def next_token(self) -> Token:
        self._skip_whitespace_and_comments()
        if self.pos >= len(self.src):
            return Token(TokenType.EOF, "", self.line)

        # Try each pattern in priority order
        for ttype, pattern in TOKEN_PATTERNS:
            m = pattern.match(self.src, self.pos)
            if m:
                value = m.group(0)
                line  = self.line
                self.pos += len(value)

                # Count newlines inside the matched text
                self.line += value.count("\n")

                # Keyword check for identifier matches
                if ttype is TokenType.IDENTIFIER:
                    if value.upper() in SQL_KEYWORDS:
                        ttype = TokenType.KEYWORD
                        value = value.upper()   # normalise to upper-case

                # Strip surrounding quotes and unescape for strings
                if ttype is TokenType.STRING:
                    value = value[1:-1].replace("\\'", "'")

                return Token(ttype, value, line)

        # Nothing matched → unknown character
        ch = self.src[self.pos]
        self.pos += 1
        return Token(TokenType.UNKNOWN, ch, self.line)

    # ── private helpers ────────────────────────────────────────────────────────
    def _skip_whitespace_and_comments(self) -> None:
        while self.pos < len(self.src):
            ch = self.src[self.pos]
            if ch in (" ", "\t", "\r"):
                self.pos += 1
            elif ch == "\n":
                self.pos += 1
                self.line += 1
            elif ch == "-" and self.pos + 1 < len(self.src) and self.src[self.pos + 1] == "-":
                # Line comment: skip to end of line
                while self.pos < len(self.src) and self.src[self.pos] != "\n":
                    self.pos += 1
            else:
                break
