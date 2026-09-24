# AST Node definitions for Verilog / SystemVerilog
from typing import List, Optional, Any, Dict

class ASTNode:
    def __init__(self, line: int = 1, col: int = 1):
        self.line = line
        self.col = col

    def to_dict(self) -> Dict[str, Any]:
        res = {"type": self.__class__.__name__, "line": self.line, "col": self.col}
        for k, v in self.__dict__.items():
            if k.startswith("_"):
                continue
            if isinstance(v, ASTNode):
                res[k] = v.to_dict()
            elif isinstance(v, list):
                res[k] = [elem.to_dict() if isinstance(elem, ASTNode) else elem for elem in v]
            elif isinstance(v, dict):
                res[k] = {dk: dv.to_dict() if isinstance(dv, ASTNode) else dv for dk, dv in v.items()}
            else:
                res[k] = v
        return res

class ModuleNode(ASTNode):
    def __init__(self, name: str, ports: List['PortNode'], items: List[ASTNode], parameters: List['ParamNode'] = None, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.name = name
        self.ports = ports or []
        self.items = items or []
        self.parameters = parameters or []

class PortNode(ASTNode):
    def __init__(self, direction: str, name: str, width_msb: Optional[ASTNode] = None, width_lsb: Optional[ASTNode] = None, data_type: str = "wire", line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.direction = direction # 'input', 'output', 'inout'
        self.name = name
        self.width_msb = width_msb
        self.width_lsb = width_lsb
        self.data_type = data_type # 'wire', 'reg', 'logic'

class ParamNode(ASTNode):
    def __init__(self, name: str, value: Any, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.name = name
        self.value = value

class SignalDeclNode(ASTNode):
    def __init__(self, decl_type: str, name: str, width_msb: Optional[ASTNode] = None, width_lsb: Optional[ASTNode] = None, array_size: Optional[ASTNode] = None, init_value: Optional[ASTNode] = None, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.decl_type = decl_type # 'wire', 'reg', 'logic', 'integer'
        self.name = name
        self.width_msb = width_msb
        self.width_lsb = width_lsb
        self.array_size = array_size # e.g. for memory: reg [7:0] mem [0:15]
        self.init_value = init_value

class AssignNode(ASTNode):
    def __init__(self, lhs: ASTNode, rhs: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.lhs = lhs
        self.rhs = rhs

class AlwaysNode(ASTNode):
    def __init__(self, sensitivity: List['SensitivityItemNode'], body: ASTNode, always_type: str = "always", line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.sensitivity = sensitivity # e.g. [('posedge', 'clk'), ('negedge', 'rst_n')] or ['*']
        self.body = body
        self.always_type = always_type # 'always', 'always_comb', 'always_ff', 'always_latch'

class SensitivityItemNode(ASTNode):
    def __init__(self, edge: Optional[str], signal: str, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.edge = edge # 'posedge', 'negedge', None
        self.signal = signal

class InitialNode(ASTNode):
    def __init__(self, body: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.body = body

class BlockNode(ASTNode):
    def __init__(self, statements: List[ASTNode], name: Optional[str] = None, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.statements = statements or []
        self.name = name

class IfNode(ASTNode):
    def __init__(self, condition: ASTNode, then_branch: ASTNode, else_branch: Optional[ASTNode] = None, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch

class CaseItemNode(ASTNode):
    def __init__(self, conditions: List[ASTNode], body: ASTNode, is_default: bool = False, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.conditions = conditions # List of condition expressions, empty if default
        self.body = body
        self.is_default = is_default

class CaseNode(ASTNode):
    def __init__(self, expr: ASTNode, items: List[CaseItemNode], case_type: str = "case", line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.expr = expr
        self.items = items or []
        self.case_type = case_type # 'case', 'casez', 'casex'

class ProceduralAssignNode(ASTNode):
    def __init__(self, lhs: ASTNode, rhs: ASTNode, is_non_blocking: bool = False, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.lhs = lhs
        self.rhs = rhs
        self.is_non_blocking = is_non_blocking # True for <=, False for =

class BinaryOpNode(ASTNode):
    def __init__(self, op: str, left: ASTNode, right: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.op = op
        self.left = left
        self.right = right

class UnaryOpNode(ASTNode):
    def __init__(self, op: str, expr: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.op = op
        self.expr = expr

class TernaryOpNode(ASTNode):
    def __init__(self, condition: ASTNode, true_expr: ASTNode, false_expr: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.condition = condition
        self.true_expr = true_expr
        self.false_expr = false_expr

class IdentifierNode(ASTNode):
    def __init__(self, name: str, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.name = name

class NumberNode(ASTNode):
    def __init__(self, raw: str, value: int, width: Optional[int] = None, is_signed: bool = False, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.raw = raw
        self.value = value
        self.width = width
        self.is_signed = is_signed

class BitSelectNode(ASTNode):
    def __init__(self, target: ASTNode, msb: ASTNode, lsb: Optional[ASTNode] = None, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.target = target
        self.msb = msb
        self.lsb = lsb # If None, it is a single bit select [idx], otherwise slice [msb:lsb]

class ConcatNode(ASTNode):
    def __init__(self, elements: List[ASTNode], line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.elements = elements

class ReplicateNode(ASTNode):
    def __init__(self, count: ASTNode, expr: ASTNode, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.count = count
        self.expr = expr

class InstanceNode(ASTNode):
    def __init__(self, module_name: str, instance_name: str, port_map: Dict[str, ASTNode], param_map: Dict[str, ASTNode] = None, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.module_name = module_name
        self.instance_name = instance_name
        self.port_map = port_map or {}
        self.param_map = param_map or {}

class SystemTaskNode(ASTNode):
    def __init__(self, task_name: str, args: List[Any], line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.task_name = task_name
        self.args = args

class DelayNode(ASTNode):
    def __init__(self, delay_val: Any, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.delay_val = delay_val

class AssertNode(ASTNode):
    def __init__(self, condition: ASTNode, else_action: Optional[ASTNode] = None, line: int = 1, col: int = 1):
        super().__init__(line, col)
        self.condition = condition
        self.else_action = else_action

class DesignAST(ASTNode):
    def __init__(self, modules: List[ModuleNode], syntax_errors: List[Dict[str, Any]] = None, warnings: List[Dict[str, Any]] = None):
        super().__init__(1, 1)
        self.modules = modules or []
        self.syntax_errors = syntax_errors or []
        self.errors = self.syntax_errors
        self.warnings = warnings or []
