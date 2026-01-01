
import sys
import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, 
    QLabel, QComboBox, QCheckBox, QSplitter, QLineEdit, QMessageBox,
    QGroupBox, QApplication
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat, QAction

from plugin_system import PluginType, WidgetPlugin

try:
    from capstone import *
    HAS_CAPSTONE = True
except ImportError:
    HAS_CAPSTONE = False

TOOL_NAME = "HEX to ASM Converter"
TOOL_DESCRIPTION = "Disassemble Hex machine code to Assembly using Capstone Engine"

class AsmHighlighter(QSyntaxHighlighter):
    """Simple syntax highlighter for Assembly (Reused from Assembler)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569cd6")) # VSCode Light Blue
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            "mov", "add", "sub", "mul", "div", "ret", "nop", "call", "jmp",
            "push", "pop", "xor", "or", "and", "inc", "dec", "cmp", "test",
            "lea", "int", "syscall", "b", "bl", "bx", "beq", "bne", "cbnz", "cbz"
        ]
        for word in keywords:
            self.highlighting_rules.append((f"\\b{word}\\b", keyword_format))

        # Registers
        register_format = QTextCharFormat()
        register_format.setForeground(QColor("#ce9178")) # VSCode Light Orange
        registers = [
            "rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rsp", "rbp",
            "eax", "ebx", "ecx", "edx", "esi", "edi", "esp", "ebp",
            "ax", "bx", "cx", "dx",
            "r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7", "x0", "x1", "x2", "x3", "x4"
        ]
        for reg in registers:
            self.highlighting_rules.append((f"\\b{reg}\\b", register_format))
            
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#b5cea8")) # VSCode Light Green
        self.highlighting_rules.append(("\\b0x[0-9a-fA-F]+\\b", number_format))
        self.highlighting_rules.append(("\\b[0-9]+\\b", number_format))
        
        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955")) # VSCode Greenish Grey
        self.highlighting_rules.append((";.*", comment_format))
        self.highlighting_rules.append(("//.*", comment_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                self.setFormat(match.start(), match.end() - match.start(), format)

class ToolWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.md = None
        self.setup_ui()
        
        if HAS_CAPSTONE:
            self.init_capstone()
        else:
            self.append_output("Error: Capstone Engine not installed. Please run 'uv add capstone'")

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # --- Top Controls ---
        top_layout = QHBoxLayout()
        
        # Architecture
        self.combo_arch = QComboBox()
        self.combo_arch.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.combo_arch.addItems(["x86", "ARM", "ARM64", "MIPS", "PPC", "SPARC", "SystemZ", "XCore"])
        self.combo_arch.setCurrentText("x86")
        self.combo_arch.currentIndexChanged.connect(self.update_mode_options)
        top_layout.addWidget(QLabel("Arch:"))
        top_layout.addWidget(self.combo_arch)
        
        # Mode
        self.combo_mode = QComboBox()
        self.combo_mode.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        # Initial modes for x86
        self.combo_mode.addItems(["32-bit", "64-bit"]) 
        top_layout.addWidget(QLabel("Mode:"))
        top_layout.addWidget(self.combo_mode)
        
        top_layout.addStretch()
        
        self.chk_auto = QCheckBox("Auto Disassemble")
        self.chk_auto.setChecked(True)
        self.chk_auto.stateChanged.connect(self.on_hex_changed)
        top_layout.addWidget(self.chk_auto)
        
        layout.addLayout(top_layout)
        
        # --- Main Splitter ---
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Hex Input
        input_group = QGroupBox("Hex Input")
        input_layout = QVBoxLayout(input_group)
        self.txt_hex = QTextEdit()
        self.txt_hex.setFont(QFont("Consolas", 10))
        self.txt_hex.setPlaceholderText("90 C3\n55 48 89 E5")
        self.txt_hex.textChanged.connect(self.on_hex_changed)
        input_layout.addWidget(self.txt_hex)
        
        # Right: Assembly Output
        output_group = QGroupBox("Assembly Output")
        output_layout = QVBoxLayout(output_group)
        self.txt_asm = QTextEdit()
        self.txt_asm.setFont(QFont("Consolas", 10))
        self.txt_asm.setReadOnly(True)
        self.highlighter = AsmHighlighter(self.txt_asm.document())
        output_layout.addWidget(self.txt_asm)
        
        splitter.addWidget(input_group)
        splitter.addWidget(output_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter, 1)
        
        # --- Bottom Controls ---
        bottom_layout = QHBoxLayout()
        
        bottom_layout.addWidget(QLabel("Offset:"))
        self.txt_offset = QLineEdit("0x1000")
        self.txt_offset.setFixedWidth(100)
        self.txt_offset.textChanged.connect(self.on_hex_changed) # Update on offset change too
        bottom_layout.addWidget(self.txt_offset)
        
        bottom_layout.addStretch()
        
        self.btn_disasm = QPushButton("Disassemble")
        self.btn_disasm.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; 
                color: white; 
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #1976D2; }
            QPushButton:pressed { background-color: #0D47A1; }
        """)
        self.btn_disasm.clicked.connect(self.disassemble)
        
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_all)
        
        bottom_layout.addWidget(self.btn_disasm)
        bottom_layout.addWidget(self.btn_clear)
        
        layout.addLayout(bottom_layout)
        
        # Status Bar
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("color: gray;")
        layout.addWidget(self.lbl_status)
        
        self.update_mode_options()

    def update_mode_options(self):
        arch = self.combo_arch.currentText()
        self.combo_mode.clear()
        
        if arch == "x86":
            self.combo_mode.addItems(["16-bit", "32-bit", "64-bit"])
            self.combo_mode.setCurrentText("64-bit")
        elif arch == "ARM":
            self.combo_mode.addItems(["ARM", "THUMB", "Cortex-M"])
        elif arch == "ARM64":
            self.combo_mode.addItems(["ARM64"])
        elif arch == "MIPS":
            self.combo_mode.addItems(["MIPS32", "MIPS64", "MIPS32R6"])
        elif arch == "PPC":
            self.combo_mode.addItems(["32-bit", "64-bit"])
        else:
            self.combo_mode.addItems(["Default"])
            
        # Re-init when mode changes
        self.init_capstone()
        if self.txt_hex.toPlainText():
            self.disassemble()

    def init_capstone(self):
        if not HAS_CAPSTONE: return
        
        arch_map = {
            "x86": CS_ARCH_X86,
            "ARM": CS_ARCH_ARM,
            "ARM64": CS_ARCH_ARM64,
            "MIPS": CS_ARCH_MIPS,
            "PPC": CS_ARCH_PPC,
            "SPARC": CS_ARCH_SPARC,
            "SystemZ": CS_ARCH_SYSZ,
            "XCore": CS_ARCH_XCORE
        }
        
        mode_map = {
            "16-bit": CS_MODE_16,
            "32-bit": CS_MODE_32,
            "64-bit": CS_MODE_64,
            "ARM": CS_MODE_ARM,
            "THUMB": CS_MODE_THUMB,
            "Cortex-M": CS_MODE_THUMB | CS_MODE_MCLASS, # Example approximation
            "ARM64": CS_MODE_ARM, # CS_MODE_ARM is 0, usually correct for ARM64 base
            "MIPS32": CS_MODE_MIPS32,
            "MIPS64": CS_MODE_MIPS64,
            "Default": 0
        }
        
        try:
            arch = arch_map.get(self.combo_arch.currentText(), CS_ARCH_X86)
            mode_text = self.combo_mode.currentText()
            mode = mode_map.get(mode_text, CS_MODE_64)
            
            # Additional endianness logic could be added
            
            self.md = Cs(arch, mode)
            self.lbl_status.setText(f"Initialized: {self.combo_arch.currentText()} {mode_text}")
        except Exception as e:
            self.lbl_status.setText(f"Initialization Error: {e}")
            self.md = None

    def on_hex_changed(self):
        if self.chk_auto.isChecked():
            self.disassemble()

    def clean_hex(self, hex_str):
        # Remove common delimiters: 0x, \x, space, comma, brackets, C-style comments
        # First remove comments
        hex_str = re.sub(r'//.*', '', hex_str)
        hex_str = re.sub(r'/\*.*?\*/', '', hex_str, flags=re.DOTALL)
        
        # Replace non-hex characters with empty string (keeping some separators might be useful, 
        # but pure replacement is easiest for flexible input)
        # Actually we want to parse it somewhat intelligently.
        # "0x90, 0x90" -> "9090"
        # "90 90" -> "9090"
        
        # Simple approach: find all hex-like logic
        # But user might have weird formatting.
        # Let's clean standard trash first.
        
        cleaned = hex_str.replace("0x", "").replace("\\x", "").replace(",", "").replace("{", "").replace("}", "").replace(";", "")
        # Remove whitespace
        cleaned = "".join(cleaned.split())
        return cleaned

    def disassemble(self):
        if not HAS_CAPSTONE or not self.md:
            return
            
        hex_str = self.txt_hex.toPlainText()
        if not hex_str.strip():
            self.txt_asm.clear()
            return
            
        cleaned_hex = self.clean_hex(hex_str)
        
        try:
            code = bytes.fromhex(cleaned_hex)
        except ValueError:
            self.lbl_status.setText("Invalid Hex Input")
            return
            
        # Get Offset
        offset = 0x1000
        try:
            offset_str = self.txt_offset.text().strip()
            if offset_str.startswith("0x"):
                offset = int(offset_str, 16)
            else:
                offset = int(offset_str)
        except ValueError:
            pass 
            
        output = []
        try:
            for i in self.md.disasm(code, offset):
                # Format: Address: Mnemonic Op_str
                # e.g. 0x1000: mov rax, 1
                addr = f"0x{i.address:x}"
                bytes_str = "".join([f"{b:02x}" for b in i.bytes])
                # Maybe show bytes too? "Address:  Bytes   Mnemonic Op_str"
                line = f"{addr}:  {i.mnemonic:<6} {i.op_str}"
                # line = f"{addr}:  {bytes_str:<16}  {i.mnemonic:<6} {i.op_str}" # Bytes might be clutter
                output.append(line)
            
            if not output:
                self.lbl_status.setText("No valid instructions found")
            else:
                self.lbl_status.setText(f"Disassembled {len(output)} instructions")
                
            self.txt_asm.setText("\n".join(output))
        except Exception as e:
            self.lbl_status.setText(f"Disassembly Error: {e}")

    def append_output(self, text):
        self.txt_asm.append(text)

    def clear_all(self):
        self.txt_hex.clear()
        self.txt_asm.clear()
        self.lbl_status.setText("Ready")


class DisassemblerPlugin(WidgetPlugin):
    def get_name(self) -> str:
        return TOOL_NAME
    
    def get_description(self) -> str:
        return TOOL_DESCRIPTION
    
    def get_type(self) -> PluginType:
        return PluginType.WIDGET
    
    def create_widget(self) -> QWidget:
        return ToolWidget()
