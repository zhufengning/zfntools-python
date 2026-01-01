
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, 
    QLabel, QComboBox, QCheckBox, QSplitter, QLineEdit, QMessageBox,
    QGroupBox, QApplication
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat

from plugin_system import PluginType, WidgetPlugin

try:
    from keystone import *
    HAS_KEYSTONE = True
except ImportError:
    HAS_KEYSTONE = False

TOOL_NAME = "ASM to HEX Converter"
TOOL_DESCRIPTION = "Convert Assembly code to Hex machine code using Keystone Engine"

class AsmHighlighter(QSyntaxHighlighter):
    """Simple syntax highlighter for Assembly"""
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
        import re
        for pattern, format in self.highlighting_rules:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                self.setFormat(match.start(), match.end() - match.start(), format)

class ToolWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.ks = None
        self.last_bytes = None
        self.setup_ui()
        
        if HAS_KEYSTONE:
            self.init_keystone()
        else:
            self.append_output("Error: Keystone Engine not installed. Please run 'uv add keystone-engine'")

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # --- Top Controls ---
        top_layout = QHBoxLayout()
        
        # Architecture
        self.combo_arch = QComboBox()
        self.combo_arch.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.combo_arch.addItems(["x86", "ARM", "ARM64", "MIPS", "PPC", "SPARC", "SystemZ", "Hexagon"])
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
        
        # Options
        self.chk_0x = QCheckBox("0x prefix")
        self.chk_line_mode = QCheckBox("Line Mode") # Renamed from Verbose
        self.chk_line_mode.setToolTip("Assemble line-by-line. \nDisable this to support jumps/labels (Block Mode).")
        self.chk_line_mode.setChecked(False) # Default to Block Mode for better compatibility
        
        self.chk_auto = QCheckBox("Auto Assemble")
        self.chk_auto.setToolTip("Automatically assemble when text changes.\nIn Block Mode, output only updates on successful assembly.")
        self.chk_auto.stateChanged.connect(self.on_asm_changed)
        
        top_layout.addWidget(self.chk_0x)
        top_layout.addWidget(self.chk_line_mode)
        top_layout.addWidget(self.chk_auto)
        
        layout.addLayout(top_layout)
        
        # --- Main Splitter ---
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Assembly Input
        input_group = QGroupBox("Assembly")
        input_layout = QVBoxLayout(input_group)
        self.txt_asm = QTextEdit()
        self.txt_asm.setFont(QFont("Consolas", 10))
        self.highlighter = AsmHighlighter(self.txt_asm.document())
        self.txt_asm.setPlaceholderText("nop\nret")
        self.txt_asm.textChanged.connect(self.on_asm_changed)
        input_layout.addWidget(self.txt_asm)
        
        # Right: Hex Output
        output_group = QGroupBox("Hex Output")
        output_layout = QVBoxLayout(output_group)
        self.txt_hex = QTextEdit()
        self.txt_hex.setFont(QFont("Consolas", 10))
        self.txt_hex.setReadOnly(True)
        output_layout.addWidget(self.txt_hex)
        
        splitter.addWidget(input_group)
        splitter.addWidget(output_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter, 1)
        
        # --- Bottom Controls ---
        bottom_layout = QHBoxLayout()
        
        bottom_layout.addWidget(QLabel("Offset:"))
        self.txt_offset = QLineEdit("0x0")
        self.txt_offset.setFixedWidth(100)
        bottom_layout.addWidget(self.txt_offset)
        
        bottom_layout.addStretch()
        
        # Copy Buttons
        copy_layout = QHBoxLayout()
        copy_layout.setSpacing(5)
        
        copy_layout.addWidget(QLabel("Copy:"))

        self.btn_copy_hex = QPushButton("Hex")
        self.btn_copy_c = QPushButton("C Array")
        self.btn_copy_lit = QPushButton("\\x..")
        
        for btn in [self.btn_copy_hex, self.btn_copy_c, self.btn_copy_lit]:
            btn.setStyleSheet("padding: 5px 10px;")
            copy_layout.addWidget(btn)
            
        self.btn_copy_hex.clicked.connect(self.copy_hex_string)
        self.btn_copy_c.clicked.connect(self.copy_c_array)
        self.btn_copy_lit.clicked.connect(self.copy_literal)
        
        bottom_layout.addLayout(copy_layout)
        bottom_layout.addSpacing(10)

        self.btn_assemble = QPushButton("Assemble")
        self.btn_assemble.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; 
                color: white; 
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:pressed { background-color: #3d8b40; }
        """)
        self.btn_assemble.clicked.connect(self.assemble)
        
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_all)
        
        bottom_layout.addWidget(self.btn_assemble)
        bottom_layout.addWidget(self.btn_clear)
        
        layout.addLayout(bottom_layout)
        
        # Status Bar
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("color: gray;")
        layout.addWidget(self.lbl_status)
        
        # Initial setup
        self.update_mode_options()

    def update_mode_options(self):
        arch = self.combo_arch.currentText()
        self.combo_mode.clear()
        
        if arch == "x86":
            self.combo_mode.addItems(["16-bit", "32-bit", "64-bit"])
            self.combo_mode.setCurrentText("64-bit")
        elif arch == "ARM":
            self.combo_mode.addItems(["ARM", "THUMB", "ARM + V8", "THUMB + V8"])
        elif arch == "ARM64":
            self.combo_mode.addItems(["Little Endian"])
        elif arch == "MIPS":
            self.combo_mode.addItems(["MIPS32", "MIPS64"])
        else:
            self.combo_mode.addItems(["Default"])

    def init_keystone(self):
        if not HAS_KEYSTONE: return
        
        # Map UI selection to Keystone constants
        arch_map = {
            "x86": KS_ARCH_X86,
            "ARM": KS_ARCH_ARM,
            "ARM64": KS_ARCH_ARM64,
            "MIPS": KS_ARCH_MIPS,
            "PPC": KS_ARCH_PPC,
            "SPARC": KS_ARCH_SPARC,
            "SystemZ": KS_ARCH_SYSTEMZ,
            "Hexagon": KS_ARCH_HEXAGON
        }
        
        mode_map = {
            "16-bit": KS_MODE_16,
            "32-bit": KS_MODE_32,
            "64-bit": KS_MODE_64,
            "ARM": KS_MODE_ARM,
            "THUMB": KS_MODE_THUMB,
            "ARM + V8": KS_MODE_ARM | KS_MODE_V8,
            "THUMB + V8": KS_MODE_THUMB | KS_MODE_V8,
            "Little Endian": KS_MODE_LITTLE_ENDIAN,
            "MIPS32": KS_MODE_MIPS32,
            "MIPS64": KS_MODE_MIPS64,
            "Default": 0
        }
        
        try:
            arch = arch_map.get(self.combo_arch.currentText(), KS_ARCH_X86)
            mode_text = self.combo_mode.currentText()
            mode = mode_map.get(mode_text, KS_MODE_32)
            
            # Special handling for MIPS/ARM endianness if needed, for now simple default
            if mode_text == "Default" and self.combo_arch.currentText() == "ARM64":
                 # KS_MODE_LITTLE_ENDIAN is 0, so it matches default but let's be explicit
                 mode = KS_MODE_LITTLE_ENDIAN
            
            self.ks = Ks(arch, mode)
            self.lbl_status.setText(f"Initialized: {self.combo_arch.currentText()} {mode_text}")
        except Exception as e:
            self.lbl_status.setText(f"Initialization Error: {e}")
            self.ks = None

    def on_asm_changed(self):
        if self.chk_auto.isChecked():
            self.assemble(is_auto=True)

    def assemble(self, is_auto=False):
        if not HAS_KEYSTONE:
            if not is_auto:
                QMessageBox.critical(self, "Error", "Keystone Engine not installed")
            return
            
        # Re-initialize to capture current settings
        self.init_keystone()
        if not self.ks: return
        
        code = self.txt_asm.toPlainText()
        if not code.strip():
            return
            
        # Get Offset
        offset = 0
        try:
            offset_str = self.txt_offset.text().strip()
            if offset_str.startswith("0x"):
                offset = int(offset_str, 16)
            else:
                offset = int(offset_str)
        except ValueError:
            pass # Default to 0
            
        try:
            encoding, count = self.ks.asm(code, offset)
            self.last_bytes = encoding
            self.show_output(encoding, offset)
            
            # Heuristic check for partial assembly failure
            # (Keystone Python binding swallows errors if partial assembly is successful, so we compare counts)
            expected = self.count_expected_instructions(code)
            
            # Allow some flexibility, but if count < expected, it's suspicious
            if count < expected:
                self.lbl_status.setText(f"Partial success: {count}/{expected} instructions")
                self.lbl_status.setStyleSheet("color: #e6a23c; font-weight: bold;") # Warning color
                
            else:
                self.lbl_status.setText(f"Assembled {count} instructions successfully")
                self.lbl_status.setStyleSheet("color: gray;")
                
        except KsError as e:
            # Smart Update Logic for Auto Mode
            if is_auto:
                if self.chk_line_mode.isChecked():
                    # Line Mode: Always update to show partial results/errors
                    pass 
                else:
                    # Block Mode: Only update if successful. 
                    # If error, do NOT update output text, but maybe update status?
                    self.lbl_status.setText(f"Waiting for valid syntax... ({e})")
                    return

            # If Block Assembly failed, check if we are in Line Mode.
            # If so, we might want to run line-by-line anyway to show WHICH line failed.
            if self.chk_line_mode.isChecked():
                 self.show_output(None, offset) # Force line-by-line assembly in show_output
                 self.lbl_status.setText("Block assembly failed, showing line errors")
            else:
                 self.txt_hex.setText(f"ERROR: {e}")
                 self.lbl_status.setText("Assembly failed")

    def show_output(self, encoding, start_offset):
        self.txt_hex.clear()
        
        is_line_mode = self.chk_line_mode.isChecked()
        use_0x = self.chk_0x.isChecked()
        
        # If Line Mode is on, OR if encoding is None (which means block failed but we want line debug),
        # use line-by-line
        if is_line_mode:
            self.assemble_line_by_line(start_offset, use_0x)
        else:
            if encoding is None: return # Should not happen if logic is correct
            
            # Block Mode: Dump nicely formatted hex
            # Address: B0 B1 B2 ...
            hex_lines = []
            chunk_size = 16
            for i in range(0, len(encoding), chunk_size):
                chunk = encoding[i:i+chunk_size]
                
                # Bytes part
                hex_bytes = " ".join([f"{b:02X}" for b in chunk])
                if use_0x: 
                     # If 0x prefix is requested, add it to each byte? Or just start?
                     # The original request logic was simple string, here let's be nice.
                     # But 'chk_0x' usually means 0xAA 0xBB.
                     hex_bytes = " ".join([f"0x{b:02X}" for b in chunk])
                
                addr = start_offset + i
                hex_lines.append(f"{addr:08X}: {hex_bytes}")
            
            self.txt_hex.setText("\n".join(hex_lines))

    def assemble_line_by_line(self, start_offset, use_0x):
        lines = self.txt_asm.toPlainText().split('\n')
        current_offset = start_offset
        
        output_text = ""
        
        for line in lines:
            line_stripped = line.strip()
            # Skip empty or comment-only lines (Keystone handles comments usually, but let's be safe)
            if not line_stripped or line_stripped.startswith(';') or line_stripped.startswith('//'):
                # Just print the line (maybe as comment)
                if line_stripped:
                     output_text += f"                  ; {line_stripped}\n"
                continue
                
            try:
                # Assemble single line
                # Note: Labels might break this line-by-line approach if defined on previous lines.
                # But for simple conversion it's okay. 
                # Ideally we pass full context, but Keystone is stateless regarding labels across asm() calls usually?
                # Actually Keystone supports labels within the code block passed to asm().
                # So splitting invalidates labels.
                
                # If we want exact screenshot look, we must accept that we can't easily do it 
                # without an assembler that returns instruction map. Keystone doesn't easily returned map.
                
                # Compromise: specific per-line assembly, ignoring cross-line labels for display purposes?
                # Or just assemble everything and dump bytes.
                
                # Let's try to assemble line by line. If it fails, we fallback to full block.
                encoding, count = self.ks.asm(line, current_offset)
                
                # Format: Address: Bytes   ; Instruction
                hex_bytes = "".join([f"{b:02X}" for b in encoding])
                if use_0x: hex_bytes = "0x" + hex_bytes
                
                addr_str = f"{current_offset:08X}:"
                row = f"{addr_str} {hex_bytes:<16} ; {line_stripped}"
                output_text += row + "\n"
                
                current_offset += len(encoding)
            except KsError as e:
                # This line failed, maybe it depends on label?
                output_text += f"ERROR: {line_stripped} ({e})\n"
        
        self.txt_hex.setText(output_text)

    def append_output(self, text):
        self.txt_hex.append(text)

    def clear_all(self):
        self.txt_asm.clear()
        self.txt_hex.clear()
        self.lbl_status.setText("Ready")


    def copy_hex_string(self):
        if not self.last_bytes: return
        text = "".join([f"{b:02X}" for b in self.last_bytes])
        QApplication.clipboard().setText(text)
        self.lbl_status.setText("Copied Hex String")

    def copy_c_array(self):
        if not self.last_bytes: return
        text = ", ".join([f"0x{b:02X}" for b in self.last_bytes])
        text = f"{{ {text} }};"
        QApplication.clipboard().setText(text)
        self.lbl_status.setText("Copied C Array")

    def copy_literal(self):
        if not self.last_bytes: return
        text = "".join([f"\\x{b:02X}" for b in self.last_bytes])
        text = f'"{text}"'
        QApplication.clipboard().setText(text)
        self.lbl_status.setText("Copied String Literal")

    def count_expected_instructions(self, code):
        """Heuristic to count expected instructions in code to detect skips"""
        lines = code.split('\n')
        count = 0
        for line in lines:
            line = line.strip()
            if not line: continue
            if line.startswith(';') or line.startswith('//') or line.startswith('#'): continue
            if line.endswith(':'): continue # Label definition
            count += 1
        return count


class AsmConverterPlugin(WidgetPlugin):
    def get_name(self) -> str:
        return TOOL_NAME
    
    def get_description(self) -> str:
        return TOOL_DESCRIPTION
    
    def get_type(self) -> PluginType:
        return PluginType.WIDGET
    
    def create_widget(self) -> QWidget:
        return ToolWidget()
