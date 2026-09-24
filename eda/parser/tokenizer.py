# Verilog & SystemVerilog Tokenizer and Lexer
import re

class TokenType:
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    STRING = "STRING"
    OPERATOR = "OPERATOR"
    DELIMITER = "DELIMITER"
    SYSTEM_TASK = "SYSTEM_TASK"
    DIRECTIVE = "DIRECTIVE"
    EOF = "EOF"

KEYWORDS = {
    # Modules & ports
    "module", "endmodule", "input", "output", "inout", "parameter", "localparam", "defparam",
    # Data types
    "wire", "reg", "logic", "integer", "genvar", "signed", "unsigned", "real", "time",
    # Assignments & procedural
    "assign", "always", "always_comb", "always_ff", "always_latch", "initial", "final",
    "begin", "end", "fork", "join",
    # Control flow
    "if", "else", "case", "casez", "casex", "endcase", "default",
    "for", "while", "repeat", "forever",
    # Events & timing
    "posedge", "negedge", "or",
    # Generate
    "generate", "endgenerate",
    # Tasks & functions
    "function", "endfunction", "task", "endtask",
    # SystemVerilog extensions
    "typedef", "struct", "enum", "union", "package", "endpackage", "import",
    "assert", "property", "endproperty", "sequence", "endsequence",
    "interface", "endinterface"
}

OPERATORS = [
    # 3-char operators
    "<<<", ">>>", "===", "!==", "^~", "~^",
    # 2-char operators
    "<=", ">=", "==", "!=", "&&", "||", "<<", ">>", "++", "--",
    "+=", "-=", "*=", "/=", "&=", "|=", "^=",
    # 1-char operators
    "+", "-", "*", "/", "%", "&", "|", "^", "~", "!", "<", ">", "?", ":"
]

DELIMITERS = {";", ",", "(", ")", "[", "]", "{", "}", ".", "@", "#"}

class Token:
    def __init__(self, type_, value, line, col):
        self.type = type_
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)}, L{self.line}:C{self.col})"

class LexerError(Exception):
    def __init__(self, message, line, col):
        super().__init__(f"Lexer error at line {line}, col {col}: {message}")
        self.line = line
        self.col = col

def tokenize(code: str):
    tokens = []
    lines = code.split("\n")
    i = 0
    line_num = 1
    col_num = 1
    n = len(code)

    while i < n:
        c = code[i]

        # Whitespace
        if c == "\n":
            line_num += 1
            col_num = 1
            i += 1
            continue
        elif c in " \t\r":
            col_num += 1
            i += 1
            continue

        # Line comment //
        if c == "/" and i + 1 < n and code[i + 1] == "/":
            while i < n and code[i] != "\n":
                i += 1
            continue

        # Block comment /* ... */
        if c == "/" and i + 1 < n and code[i + 1] == "*":
            start_l, start_c = line_num, col_num
            i += 2
            col_num += 2
            closed = False
            while i + 1 < n:
                if code[i] == "\n":
                    line_num += 1
                    col_num = 1
                else:
                    col_num += 1
                if code[i] == "*" and code[i + 1] == "/":
                    i += 2
                    col_num += 1
                    closed = True
                    break
                i += 1
            if not closed:
                i = n
            continue

        # Compiler directives `timescale, `define, etc.
        if c == "`":
            start_col = col_num
            val = "`"
            i += 1
            col_num += 1
            while i < n and (code[i].isalnum() or code[i] == "_"):
                val += code[i]
                i += 1
                col_num += 1
            tokens.append(Token(TokenType.DIRECTIVE, val, line_num, start_col))
            continue

        # System tasks ($display, $finish, $monitor, etc.)
        if c == "$":
            start_col = col_num
            val = "$"
            i += 1
            col_num += 1
            while i < n and (code[i].isalnum() or code[i] == "_"):
                val += code[i]
                i += 1
                col_num += 1
            tokens.append(Token(TokenType.SYSTEM_TASK, val, line_num, start_col))
            continue

        # Strings "..."
        if c == '"':
            start_col = col_num
            val = '"'
            i += 1
            col_num += 1
            while i < n and code[i] != '"':
                if code[i] == "\\" and i + 1 < n:
                    val += code[i:i+2]
                    i += 2
                    col_num += 2
                else:
                    if code[i] == "\n":
                        line_num += 1
                        col_num = 1
                    else:
                        col_num += 1
                    val += code[i]
                    i += 1
            if i < n and code[i] == '"':
                val += '"'
                i += 1
                col_num += 1
            tokens.append(Token(TokenType.STRING, val, line_num, start_col))
            continue

        # Identifiers & Keywords
        if c.isalpha() or c == "_":
            start_col = col_num
            val = ""
            while i < n and (code[i].isalnum() or code[i] in "_$"):
                val += code[i]
                i += 1
                col_num += 1
            if val in KEYWORDS:
                tokens.append(Token(TokenType.KEYWORD, val, line_num, start_col))
            else:
                tokens.append(Token(TokenType.IDENTIFIER, val, line_num, start_col))
            continue

        # Verilog Numbers: e.g. 8'b1010_0001, 16'hFF, 32'd1000, 10, 'b1, '0, '1
        if c.isdigit() or (c == "'" and i + 1 < n and code[i+1] in "bBdDhHoO01"):
            start_col = col_num
            val = ""
            # Gather digits or base specifier
            while i < n and (code[i].isalnum() or code[i] in "_'?"):
                val += code[i]
                i += 1
                col_num += 1
            tokens.append(Token(TokenType.NUMBER, val, line_num, start_col))
            continue

        # Multi-char operators
        op_matched = None
        for op in OPERATORS:
            if code.startswith(op, i):
                op_matched = op
                break
        if op_matched:
            tokens.append(Token(TokenType.OPERATOR, op_matched, line_num, col_num))
            i += len(op_matched)
            col_num += len(op_matched)
            continue

        # Delimiters
        if c in DELIMITERS:
            tokens.append(Token(TokenType.DELIMITER, c, line_num, col_num))
            i += 1
            col_num += 1
            continue

        # Unknown character - treat as delimiter or advance
        tokens.append(Token(TokenType.DELIMITER, c, line_num, col_num))
        i += 1
        col_num += 1

    tokens.append(Token(TokenType.EOF, "", line_num, col_num))
    return tokens
