# Verilog / SystemVerilog Recursive Descent Parser with Error Recovery
from typing import List, Optional, Tuple, Dict, Any
from .tokenizer import Token, TokenType, tokenize
from .ast_nodes import (
    ASTNode, ModuleNode, PortNode, ParamNode, SignalDeclNode,
    AssignNode, AlwaysNode, SensitivityItemNode, InitialNode,
    BlockNode, IfNode, CaseNode, CaseItemNode, ProceduralAssignNode,
    BinaryOpNode, UnaryOpNode, TernaryOpNode, IdentifierNode,
    NumberNode, BitSelectNode, ConcatNode, ReplicateNode,
    InstanceNode, SystemTaskNode, DelayNode, AssertNode, DesignAST
)

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.errors = []
        self.warnings = []

    def current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]

    def peek(self, offset: int = 1) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]

    def advance(self) -> Token:
        tok = self.current()
        if self.pos < len(self.tokens):
            self.pos += 1
        return tok

    def match(self, val: str, type_: Optional[str] = None) -> bool:
        tok = self.current()
        if type_ and tok.type != type_:
            return False
        return tok.value == val

    def consume(self, expected_val: Optional[str] = None, expected_type: Optional[str] = None) -> Token:
        tok = self.current()
        if expected_val and tok.value != expected_val:
            self.error(f"Expected '{expected_val}', found '{tok.value}'")
        elif expected_type and tok.type != expected_type:
            self.error(f"Expected token type '{expected_type}', found '{tok.type}'")
        return self.advance()

    def error(self, msg: str):
        tok = self.current()
        self.errors.append({
            "line": tok.line,
            "col": tok.col,
            "message": msg,
            "token": tok.value
        })

    def warn(self, msg: str):
        tok = self.current()
        self.warnings.append({
            "line": tok.line,
            "col": tok.col,
            "message": msg
        })

    def synchronize(self, sync_tokens: List[str]):
        """Skip tokens until a synchronization token is found."""
        while self.current().type != TokenType.EOF:
            if self.current().value in sync_tokens:
                if self.current().value == ";":
                    self.advance()
                return
            self.advance()

    def parse_number(self, tok: Token) -> NumberNode:
        val_str = tok.value.replace("_", "")
        width = None
        is_signed = False
        val = 0
        try:
            if "'" in val_str:
                parts = val_str.split("'", 1)
                if parts[0]:
                    width = int(parts[0])
                base_part = parts[1]
                if base_part.startswith("s") or base_part.startswith("S"):
                    is_signed = True
                    base_part = base_part[1:]
                base = base_part[0].lower()
                num_digits = base_part[1:]
                if base == 'b':
                    num_digits = num_digits.replace("x", "0").replace("z", "0").replace("?", "0")
                    val = int(num_digits, 2) if num_digits else 0
                elif base == 'h':
                    num_digits = num_digits.replace("x", "0").replace("z", "0").replace("?", "0")
                    val = int(num_digits, 16) if num_digits else 0
                elif base == 'o':
                    val = int(num_digits, 8) if num_digits else 0
                elif base == 'd':
                    val = int(num_digits, 10) if num_digits else 0
            else:
                val = int(val_str)
        except Exception:
            val = 0
        return NumberNode(tok.value, val, width, is_signed, tok.line, tok.col)

    def parse_primary_expression(self) -> ASTNode:
        tok = self.current()

        # System tasks ($time, etc.)
        if tok.type == TokenType.SYSTEM_TASK:
            self.advance()
            return SystemTaskNode(tok.value, [], tok.line, tok.col)

        # Numbers
        if tok.type == TokenType.NUMBER:
            self.advance()
            return self.parse_number(tok)

        # Strings
        if tok.type == TokenType.STRING:
            self.advance()
            return IdentifierNode(tok.value, tok.line, tok.col)

        # Delay #5
        if tok.value == "#":
            self.advance()
            num = self.advance()
            return DelayNode(num.value, tok.line, tok.col)

        # Identifiers (or bit selects / array indexing)
        if tok.type == TokenType.IDENTIFIER or (tok.type == TokenType.KEYWORD and tok.value in ("signed", "unsigned")):
            name = tok.value
            self.advance()
            node = IdentifierNode(name, tok.line, tok.col)

            # Check for bit selects [msb:lsb] or [idx]
            while self.match("["):
                self.advance()
                msb = self.parse_expression()
                lsb = None
                if self.match(":"):
                    self.advance()
                    lsb = self.parse_expression()
                elif self.match("+:") or self.match("-:"):
                    # SystemVerilog indexed part-select
                    self.advance()
                    lsb = self.parse_expression()
                self.consume("]")
                node = BitSelectNode(node, msb, lsb, tok.line, tok.col)
            return node

        # Parenthesized expression
        if self.match("("):
            self.advance()
            expr = self.parse_expression()
            self.consume(")")
            return expr

        # Concatenation or Replication: {a, b} or {4{a}}
        if self.match("{"):
            start_tok = self.advance()
            first = self.parse_expression()
            # If followed by '{', it's a replication: {count {expr}}
            if self.match("{"):
                self.advance()
                rep_expr = self.parse_expression()
                self.consume("}")
                self.consume("}")
                return ReplicateNode(first, rep_expr, start_tok.line, start_tok.col)
            elements = [first]
            while self.match(","):
                self.advance()
                elements.append(self.parse_expression())
            self.consume("}")
            return ConcatNode(elements, start_tok.line, start_tok.col)

        # Unary operators (~, !, +, -, &, |, ^)
        if tok.value in ("~", "!", "+", "-", "&", "|", "^", "~&", "~|", "~^", "^~"):
            self.advance()
            sub = self.parse_unary_expression()
            return UnaryOpNode(tok.value, sub, tok.line, tok.col)

        # Fallback
        self.error(f"Unexpected token in expression: '{tok.value}'")
        self.advance()
        return IdentifierNode("error", tok.line, tok.col)

    def parse_unary_expression(self) -> ASTNode:
        tok = self.current()
        if tok.value in ("~", "!", "+", "-", "&", "|", "^", "~&", "~|", "~^", "^~"):
            self.advance()
            sub = self.parse_unary_expression()
            return UnaryOpNode(tok.value, sub, tok.line, tok.col)
        return self.parse_primary_expression()

    def parse_multiplicative(self) -> ASTNode:
        expr = self.parse_unary_expression()
        while self.current().value in ("*", "/", "%"):
            op = self.advance().value
            right = self.parse_unary_expression()
            expr = BinaryOpNode(op, expr, right, expr.line, expr.col)
        return expr

    def parse_additive(self) -> ASTNode:
        expr = self.parse_multiplicative()
        while self.current().value in ("+", "-"):
            op = self.advance().value
            right = self.parse_multiplicative()
            expr = BinaryOpNode(op, expr, right, expr.line, expr.col)
        return expr

    def parse_shift(self) -> ASTNode:
        expr = self.parse_additive()
        while self.current().value in ("<<", ">>", "<<<", ">>>"):
            op = self.advance().value
            right = self.parse_additive()
            expr = BinaryOpNode(op, expr, right, expr.line, expr.col)
        return expr

    def parse_relational(self) -> ASTNode:
        expr = self.parse_shift()
        while self.current().value in ("<", "<=", ">", ">="):
            op = self.advance().value
            right = self.parse_shift()
            expr = BinaryOpNode(op, expr, right, expr.line, expr.col)
        return expr

    def parse_equality(self) -> ASTNode:
        expr = self.parse_relational()
        while self.current().value in ("==", "!=", "===", "!=="):
            op = self.advance().value
            right = self.parse_relational()
            expr = BinaryOpNode(op, expr, right, expr.line, expr.col)
        return expr

    def parse_bitwise_and(self) -> ASTNode:
        expr = self.parse_equality()
        while self.current().value in ("&", "~&"):
            op = self.advance().value
            right = self.parse_equality()
            expr = BinaryOpNode(op, expr, right, expr.line, expr.col)
        return expr

    def parse_bitwise_xor(self) -> ASTNode:
        expr = self.parse_bitwise_and()
        while self.current().value in ("^", "^~", "~^"):
            op = self.advance().value
            right = self.parse_bitwise_and()
            expr = BinaryOpNode(op, expr, right, expr.line, expr.col)
        return expr

    def parse_bitwise_or(self) -> ASTNode:
        expr = self.parse_bitwise_xor()
        while self.current().value in ("|", "~|"):
            op = self.advance().value
            right = self.parse_bitwise_xor()
            expr = BinaryOpNode(op, expr, right, expr.line, expr.col)
        return expr

    def parse_logical_and(self) -> ASTNode:
        expr = self.parse_bitwise_or()
        while self.current().value == "&&":
            op = self.advance().value
            right = self.parse_bitwise_or()
            expr = BinaryOpNode(op, expr, right, expr.line, expr.col)
        return expr

    def parse_logical_or(self) -> ASTNode:
        expr = self.parse_logical_and()
        while self.current().value == "||":
            op = self.advance().value
            right = self.parse_logical_and()
            expr = BinaryOpNode(op, expr, right, expr.line, expr.col)
        return expr

    def parse_ternary(self) -> ASTNode:
        expr = self.parse_logical_or()
        if self.match("?"):
            self.advance()
            true_e = self.parse_expression()
            self.consume(":")
            false_e = self.parse_ternary()
            expr = TernaryOpNode(expr, true_e, false_e, expr.line, expr.col)
        return expr

    def parse_expression(self) -> ASTNode:
        return self.parse_ternary()

    def parse_range(self) -> Tuple[Optional[ASTNode], Optional[ASTNode]]:
        if self.match("["):
            self.advance()
            msb = self.parse_expression()
            lsb = None
            if self.match(":"):
                self.advance()
                lsb = self.parse_expression()
            self.consume("]")
            return msb, lsb
        return None, None

    def parse_statement(self) -> ASTNode:
        tok = self.current()

        # begin ... end
        if tok.value == "begin":
            start_tok = self.advance()
            block_name = None
            if self.match(":"):
                self.advance()
                block_name = self.consume(expected_type=TokenType.IDENTIFIER).value
            stmts = []
            while not self.match("end") and self.current().type != TokenType.EOF:
                stmt = self.parse_statement()
                if stmt:
                    stmts.append(stmt)
            self.consume("end")
            return BlockNode(stmts, block_name, start_tok.line, start_tok.col)

        # if-else
        if tok.value == "if":
            start_tok = self.advance()
            self.consume("(")
            cond = self.parse_expression()
            self.consume(")")
            then_b = self.parse_statement()
            else_b = None
            if self.match("else"):
                self.advance()
                else_b = self.parse_statement()
            return IfNode(cond, then_b, else_b, start_tok.line, start_tok.col)

        # case, casez, casex
        if tok.value in ("case", "casez", "casex"):
            case_type = tok.value
            start_tok = self.advance()
            self.consume("(")
            case_expr = self.parse_expression()
            self.consume(")")
            items = []
            while not self.match("endcase") and self.current().type != TokenType.EOF:
                if self.match("default"):
                    def_tok = self.advance()
                    if self.match(":"):
                        self.advance()
                    def_stmt = self.parse_statement()
                    items.append(CaseItemNode([], def_stmt, is_default=True, line=def_tok.line, col=def_tok.col))
                else:
                    conds = [self.parse_expression()]
                    while self.match(","):
                        self.advance()
                        conds.append(self.parse_expression())
                    self.consume(":")
                    stmt = self.parse_statement()
                    items.append(CaseItemNode(conds, stmt, is_default=False, line=conds[0].line, col=conds[0].col))
            self.consume("endcase")
            return CaseNode(case_expr, items, case_type, start_tok.line, start_tok.col)

        # for loop
        if tok.value == "for":
            start_tok = self.advance()
            self.consume("(")
            init_stmt = self.parse_statement()
            cond_expr = self.parse_expression()
            self.consume(";")
            step_stmt = self.parse_statement()
            self.consume(")")
            body = self.parse_statement()
            return BlockNode([init_stmt, body], f"for_loop_L{start_tok.line}", start_tok.line, start_tok.col)

        # System task ($display, $finish, $monitor, etc.)
        if tok.type == TokenType.SYSTEM_TASK:
            start_tok = self.advance()
            args = []
            if self.match("("):
                self.advance()
                while not self.match(")") and self.current().type != TokenType.EOF:
                    args.append(self.parse_expression())
                    if self.match(","):
                        self.advance()
                self.consume(")")
            if self.match(";"):
                self.advance()
            return SystemTaskNode(start_tok.value, args, start_tok.line, start_tok.col)

        # Delay #10;
        if tok.value == "#":
            self.advance()
            delay_tok = self.advance()
            if self.match(";"):
                self.advance()
            return DelayNode(delay_tok.value, tok.line, tok.col)

        # Assert statement (SystemVerilog)
        if tok.value == "assert":
            start_tok = self.advance()
            self.consume("(")
            cond = self.parse_expression()
            self.consume(")")
            else_action = None
            if self.match("else"):
                self.advance()
                else_action = self.parse_statement()
            elif self.match(";"):
                self.advance()
            return AssertNode(cond, else_action, start_tok.line, start_tok.col)

        # Null statement
        if tok.value == ";":
            self.advance()
            return None

        # Procedural assignment: lhs <= rhs; or lhs = rhs;
        lhs = self.parse_primary_expression()
        is_non_blocking = False
        if self.match("<="):
            is_non_blocking = True
            self.advance()
        elif self.match("="):
            is_non_blocking = False
            self.advance()
        elif self.match(";"):
            self.advance()
            return lhs
        else:
            self.error(f"Expected assignment operator <= or =, got '{self.current().value}'")
            self.synchronize([";", "end", "endcase"])
            return None

        rhs = self.parse_expression()
        if self.match(";"):
            self.advance()
        return ProceduralAssignNode(lhs, rhs, is_non_blocking, lhs.line, lhs.col)

    def parse_always(self) -> AlwaysNode:
        start_tok = self.advance() # 'always', 'always_comb', 'always_ff', etc.
        always_type = start_tok.value
        sensitivity = []

        if self.match("@"):
            self.advance()
            self.consume("(")
            if self.match("*"):
                self.advance()
                sensitivity.append(SensitivityItemNode(None, "*", start_tok.line, start_tok.col))
            else:
                while not self.match(")") and self.current().type != TokenType.EOF:
                    edge = None
                    if self.current().value in ("posedge", "negedge"):
                        edge = self.advance().value
                    sig_tok = self.consume(expected_type=TokenType.IDENTIFIER)
                    sensitivity.append(SensitivityItemNode(edge, sig_tok.value, sig_tok.line, sig_tok.col))
                    if self.match("or") or self.match(","):
                        self.advance()
            self.consume(")")
        elif always_type in ("always_comb", "always_latch"):
            sensitivity.append(SensitivityItemNode(None, "*", start_tok.line, start_tok.col))

        body = self.parse_statement()
        return AlwaysNode(sensitivity, body, always_type, start_tok.line, start_tok.col)

    def parse_module(self) -> Optional[ModuleNode]:
        start_tok = self.consume("module")
        mod_name = self.consume(expected_type=TokenType.IDENTIFIER).value
        params = []
        ports = []
        items = []

        # ANSI Parameters: #(parameter WIDTH = 8, parameter DEPTH = 16)
        if self.match("#"):
            self.advance()
            self.consume("(")
            while not self.match(")") and self.current().type != TokenType.EOF:
                if self.match("parameter") or self.match("localparam"):
                    self.advance()
                p_name = self.consume(expected_type=TokenType.IDENTIFIER).value
                p_val = None
                if self.match("="):
                    self.advance()
                    p_val = self.parse_expression()
                params.append(ParamNode(p_name, p_val, start_tok.line, start_tok.col))
                if self.match(","):
                    self.advance()
            self.consume(")")

        # Port list (ANSI or non-ANSI)
        if self.match("("):
            self.advance()
            while not self.match(")") and self.current().type != TokenType.EOF:
                # Check for ANSI port declaration: input/output/inout [msb:lsb] wire/reg/logic name
                direction = None
                if self.current().value in ("input", "output", "inout"):
                    direction = self.advance().value

                dtype = "wire"
                if self.current().value in ("wire", "reg", "logic", "integer"):
                    dtype = self.advance().value

                msb, lsb = self.parse_range()

                if self.current().value in ("wire", "reg", "logic"):
                    dtype = self.advance().value

                p_name_tok = self.consume(expected_type=TokenType.IDENTIFIER)
                ports.append(PortNode(direction or "inout", p_name_tok.value, msb, lsb, dtype, p_name_tok.line, p_name_tok.col))

                if self.match(","):
                    self.advance()
                elif not self.match(")"):
                    self.error(f"Expected ',' or ')' after port declaration '{p_name_tok.value}', found '{self.current().value}'")
            self.consume(")")

        self.consume(";")

        # Module Body Items
        while not self.match("endmodule") and self.current().type != TokenType.EOF:
            tok = self.current()

            # Ignore directives
            if tok.type == TokenType.DIRECTIVE:
                self.advance()
                continue

            # Parameters declared inside body
            if tok.value in ("parameter", "localparam"):
                self.advance()
                while not self.match(";") and self.current().type != TokenType.EOF:
                    p_name = self.consume(expected_type=TokenType.IDENTIFIER).value
                    p_val = None
                    if self.match("="):
                        self.advance()
                        p_val = self.parse_expression()
                    params.append(ParamNode(p_name, p_val, tok.line, tok.col))
                    if self.match(","):
                        self.advance()
                self.consume(";")
                continue

            # Port declarations (non-ANSI style: input [7:0] a, b;)
            if tok.value in ("input", "output", "inout"):
                direction = self.advance().value
                dtype = "wire"
                if self.current().value in ("wire", "reg", "logic"):
                    dtype = self.advance().value
                msb, lsb = self.parse_range()
                if self.current().value in ("wire", "reg", "logic"):
                    dtype = self.advance().value

                while not self.match(";") and self.current().type != TokenType.EOF:
                    name_tok = self.consume(expected_type=TokenType.IDENTIFIER)
                    # Update existing port if present or add
                    found = False
                    for p in ports:
                        if p.name == name_tok.value:
                            p.direction = direction
                            p.width_msb = msb
                            p.width_lsb = lsb
                            p.data_type = dtype
                            found = True
                            break
                    if not found:
                        ports.append(PortNode(direction, name_tok.value, msb, lsb, dtype, name_tok.line, name_tok.col))
                    if self.match(","):
                        self.advance()
                self.consume(";")
                continue

            # Signal declarations: wire, reg, logic, integer
            if tok.value in ("wire", "reg", "logic", "integer", "genvar"):
                decl_type = self.advance().value
                msb, lsb = self.parse_range()
                while not self.match(";") and self.current().type != TokenType.EOF:
                    name_tok = self.consume(expected_type=TokenType.IDENTIFIER)
                    # Check for memory array [0:15]
                    arr_msb, arr_lsb = self.parse_range()
                    init_v = None
                    if self.match("="):
                        self.advance()
                        init_v = self.parse_expression()
                    items.append(SignalDeclNode(decl_type, name_tok.value, msb, lsb, arr_msb, init_v, name_tok.line, name_tok.col))
                    if self.match(","):
                        self.advance()
                self.consume(";")
                continue

            # Continuous assignment: assign a = b;
            if tok.value == "assign":
                self.advance()
                lhs = self.parse_primary_expression()
                self.consume("=")
                rhs = self.parse_expression()
                self.consume(";")
                items.append(AssignNode(lhs, rhs, tok.line, tok.col))
                continue

            # Procedural block: always, always_comb, always_ff, always_latch
            if tok.value in ("always", "always_comb", "always_ff", "always_latch"):
                items.append(self.parse_always())
                continue

            # Initial block (testbenches & ROM initialization)
            if tok.value == "initial":
                self.advance()
                body = self.parse_statement()
                items.append(InitialNode(body, tok.line, tok.col))
                continue

            # Module instantiation: submodule_name inst_name (.a(a), .b(b));
            if tok.type == TokenType.IDENTIFIER:
                # Could be instance or function/task
                inst_mod = self.advance().value
                inst_name = ""
                if self.current().type == TokenType.IDENTIFIER:
                    inst_name = self.advance().value

                port_map = {}
                if self.match("("):
                    self.advance()
                    while not self.match(")") and self.current().type != TokenType.EOF:
                        if self.match("."):
                            self.advance()
                            p_formal = self.consume(expected_type=TokenType.IDENTIFIER).value
                            self.consume("(")
                            p_actual = self.parse_expression() if not self.match(")") else None
                            self.consume(")")
                            port_map[p_formal] = p_actual
                        else:
                            # Positional port
                            p_actual = self.parse_expression()
                            port_map[f"port_{len(port_map)}"] = p_actual
                        if self.match(","):
                            self.advance()
                    self.consume(")")
                if self.match(";"):
                    self.advance()
                items.append(InstanceNode(inst_mod, inst_name, port_map, line=tok.line, col=tok.col))
                continue

            # Generate block
            if tok.value == "generate":
                self.advance()
                while not self.match("endgenerate") and not self.match("endmodule") and self.current().type != TokenType.EOF:
                    # Parse generate items
                    self.advance()
                if self.match("endgenerate"):
                    self.advance()
                continue

            # Unknown or unexpected token inside module - advance to recover
            self.warn(f"Ignored token inside module: '{tok.value}'")
            self.advance()

        self.consume("endmodule")
        return ModuleNode(mod_name, ports, items, params, start_tok.line, start_tok.col)

    def parse(self) -> DesignAST:
        modules = []
        while self.current().type != TokenType.EOF:
            tok = self.current()
            if tok.value == "module":
                mod = self.parse_module()
                if mod:
                    modules.append(mod)
            elif tok.type == TokenType.DIRECTIVE:
                self.advance()
            else:
                self.advance()
        return DesignAST(modules, self.errors, self.warnings)

def parse_verilog(code: str) -> DesignAST:
    tokens = tokenize(code)
    parser = Parser(tokens)
    return parser.parse()
