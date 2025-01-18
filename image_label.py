import sys
from pathlib import Path
import cv2
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QFileDialog, QStatusBar,
    QTabWidget, QScrollArea, QLineEdit, QGroupBox, QCheckBox,
    QSpinBox, QToolBar, QMessageBox, QDockWidget, QListWidget
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QSettings
from PySide6.QtGui import QImage, QPixmap, QIcon, QAction
import json

class ImageLabel(QLabel):
    """Widget personalizado para exibir e interagir com a imagem"""
    mousePressed = Signal(float, float)  # Sinais para eventos do mouse
    mouseMoved = Signal(float, float)
    mouseReleased = Signal(float, float)
    
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.scale_factor = 1.0
        
    def mousePressEvent(self, event):
        pos = event.position()
        self.mousePressed.emit(pos.x() / self.scale_factor, 
                             pos.y() / self.scale_factor)
        
    def mouseMoveEvent(self, event):
        pos = event.position()
        self.mouseMoved.emit(pos.x() / self.scale_factor, 
                           pos.y() / self.scale_factor)
        
    def mouseReleaseEvent(self, event):
        pos = event.position()
        self.mouseReleased.emit(pos.x() / self.scale_factor, 
                              pos.y() / self.scale_factor)

class TemplateEditor(QWidget):
    """Widget para edição de templates"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.template_manager = TemplateManager()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Grupo de seleção de template
        template_group = QGroupBox("Template")
        template_layout = QVBoxLayout()
        
        # Tipo de documento
        doc_type_layout = QHBoxLayout()
        self.doc_type_combo = QComboBox()
        self.doc_type_combo.currentTextChanged.connect(self.update_templates)
        doc_type_layout.addWidget(QLabel("Tipo de Documento:"))
        doc_type_layout.addWidget(self.doc_type_combo)
        
        # Nome do template
        template_name_layout = QHBoxLayout()
        self.template_combo = QComboBox()
        self.template_combo.currentTextChanged.connect(self.load_template)
        template_name_layout.addWidget(QLabel("Template:"))
        template_name_layout.addWidget(self.template_combo)
        
        template_layout.addLayout(doc_type_layout)
        template_layout.addLayout(template_name_layout)
        template_group.setLayout(template_layout)
        
        # Lista de ROIs
        roi_group = QGroupBox("Regiões de Interesse")
        roi_layout = QVBoxLayout()
        self.roi_list = QListWidget()
        self.roi_list.itemClicked.connect(self.select_roi)
        roi_layout.addWidget(self.roi_list)
        
        # Botões de ROI
        roi_buttons = QHBoxLayout()
        self.add_roi_btn = QPushButton("Adicionar ROI")
        self.delete_roi_btn = QPushButton("Remover ROI")
        self.add_roi_btn.clicked.connect(self.add_roi)
        self.delete_roi_btn.clicked.connect(self.delete_roi)
        roi_buttons.addWidget(self.add_roi_btn)
        roi_buttons.addWidget(self.delete_roi_btn)
        roi_layout.addLayout(roi_buttons)
        roi_group.setLayout(roi_layout)
        
        # Propriedades da ROI
        prop_group = QGroupBox("Propriedades")
        prop_layout = QVBoxLayout()
        
        # Nome
        name_layout = QHBoxLayout()
        self.roi_name = QLineEdit()
        name_layout.addWidget(QLabel("Nome:"))
        name_layout.addWidget(self.roi_name)
        
        # Tipo
        type_layout = QHBoxLayout()
        self.roi_type = QComboBox()
        self.roi_type.addItems(["text", "cpf", "number", "currency", "date"])
        type_layout.addWidget(QLabel("Tipo:"))
        type_layout.addWidget(self.roi_type)
        
        # Coordenadas
        coords_layout = QHBoxLayout()
        self.x_spin = QSpinBox()
        self.y_spin = QSpinBox()
        self.w_spin = QSpinBox()
        self.h_spin = QSpinBox()
        coords_layout.addWidget(QLabel("X:"))
        coords_layout.addWidget(self.x_spin)
        coords_layout.addWidget(QLabel("Y:"))
        coords_layout.addWidget(self.y_spin)
        coords_layout.addWidget(QLabel("W:"))
        coords_layout.addWidget(self.w_spin)
        coords_layout.addWidget(QLabel("H:"))
        coords_layout.addWidget(self.h_spin)
        
        prop_layout.addLayout(name_layout)
        prop_layout.addLayout(type_layout)
        prop_layout.addLayout(coords_layout)
        prop_group.setLayout(prop_layout)
        
        # Adiciona todos os grupos ao layout principal
        layout.addWidget(template_group)
        layout.addWidget(roi_group)
        layout.addWidget(prop_group)
        layout.addStretch()
        
        self.setLayout(layout)
        self.load_doc_types()
        
    def load_doc_types(self):
        """Carrega os tipos de documento disponíveis"""
        doc_types = self.template_manager.get_doc_types()
        self.doc_type_combo.clear()
        self.doc_type_combo.addItems(doc_types)
        
    def update_templates(self, doc_type):
        """Atualiza a lista de templates disponíveis"""
        templates = self.template_manager.get_templates(doc_type)
        self.template_combo.clear()
        self.template_combo.addItems(templates)
        
    def load_template(self, template_name):
        """Carrega um template específico"""
        if not template_name:
            return
            
        doc_type = self.doc_type_combo.currentText()
        template = self.template_manager.get_template(doc_type, template_name)
        if template:
            self.update_roi_list(template["regions"])
            
    def update_roi_list(self, regions):
        """Atualiza a lista de ROIs"""
        self.roi_list.clear()
        for name in regions:
            self.roi_list.addItem(name)
            
    def select_roi(self, item):
        """Seleciona uma ROI para edição"""
        name = item.text()
        doc_type = self.doc_type_combo.currentText()
        template_name = self.template_combo.currentText()
        template = self.template_manager.get_template(doc_type, template_name)
        
        if template and name in template["regions"]:
            region = template["regions"][name]
            self.roi_name.setText(name)
            self.roi_type.setCurrentText(region["expected_type"])
            x1, y1, x2, y2 = region["coords"]
            self.x_spin.setValue(x1)
            self.y_spin.setValue(y1)
            self.w_spin.setValue(x2 - x1)
            self.h_spin.setValue(y2 - y1)

class DocumentProcessor(QWidget):
    """Widget para processamento de documentos"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Diretórios
        dir_group = QGroupBox("Diretórios")
        dir_layout = QVBoxLayout()
        
        # Diretório de entrada
        input_layout = QHBoxLayout()
        self.input_dir = QLineEdit()
        self.input_dir.setPlaceholderText("Selecione o diretório de entrada")
        self.input_browse = QPushButton("...")
        self.input_browse.clicked.connect(self.browse_input)
        input_layout.addWidget(QLabel("Entrada:"))
        input_layout.addWidget(self.input_dir)
        input_layout.addWidget(self.input_browse)
        
        # Diretório de saída
        output_layout = QHBoxLayout()
        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("Selecione o diretório de saída")
        self.output_browse = QPushButton("...")
        self.output_browse.clicked.connect(self.browse_output)
        output_layout.addWidget(QLabel("Saída:"))
        output_layout.addWidget(self.output_dir)
        output_layout.addWidget(self.output_browse)
        
        dir_layout.addLayout(input_layout)
        dir_layout.addLayout(output_layout)
        dir_group.setLayout(dir_layout)
        
        # Opções de processamento
        options_group = QGroupBox("Opções")
        options_layout = QVBoxLayout()
        
        self.consolidate_check = QCheckBox("Consolidar resultados em um único arquivo")
        self.show_preview_check = QCheckBox("Mostrar prévia do processamento")
        
        options_layout.addWidget(self.consolidate_check)
        options_layout.addWidget(self.show_preview_check)
        options_group.setLayout(options_layout)
        
        # Botões
        button_layout = QHBoxLayout()
        self.process_btn = QPushButton("Processar")
        self.process_btn.clicked.connect(self.process_documents)
        self.cancel_btn = QPushButton("Cancelar")
        button_layout.addWidget(self.process_btn)
        button_layout.addWidget(self.cancel_btn)
        
        # Preview
        preview_group = QGroupBox("Prévia")
        preview_layout = QVBoxLayout()
        self.preview_label = ImageLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.preview_label)
        preview_group.setLayout(preview_layout)
        
        # Adiciona todos os grupos ao layout principal
        layout.addWidget(dir_group)
        layout.addWidget(options_group)
        layout.addLayout(button_layout)
        layout.addWidget(preview_group)
        
        self.setLayout(layout)
        
    def browse_input(self):
        """Abre diálogo para selecionar diretório de entrada"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Selecionar Diretório de Entrada")
        if dir_path:
            self.input_dir.setText(dir_path)
            
    def browse_output(self):
        """Abre diálogo para selecionar diretório de saída"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Selecionar Diretório de Saída")
        if dir_path:
            self.output_dir.setText(dir_path)
            
    def process_documents(self):
        """Inicia o processamento dos documentos"""
        input_dir = self.input_dir.text()
        output_dir = self.output_dir.text()
        
        if not input_dir or not output_dir:
            QMessageBox.warning(
                self, 
                "Erro", 
                "Selecione os diretórios de entrada e saída"
            )
            return
            
        # Implementar processamento aqui
        pass

class MainWindow(QMainWindow):
    """Janela principal da aplicação"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Extração de Documentos")
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        # Configuração básica da janela
        self.setMinimumSize(1200, 800)
        
        # Criar barra de ferramentas
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Ações da barra de ferramentas
        new_template_action = QAction(QIcon("icons/new.png"), "Novo Template", self)
        save_template_action = QAction(QIcon("icons/save.png"), "Salvar Template", self)
        toolbar.addAction(new_template_action)
        toolbar.addAction(save_template_action)
        
        # Widget central com abas
        tab_widget = QTabWidget()
        
        # Aba de Edição de Template
        self.template_editor = TemplateEditor()
        tab_widget.addTab(self.template_editor, "Editor de Templates")
        
        # Aba de Processamento
        self.processor = DocumentProcessor()
        tab_widget.addTab(self.processor, "Processamento")
        
        self.setCentralWidget(tab_widget)
        
        # Barra de status
        self.statusBar().showMessage("Pronto")
        
    def load_settings(self):
        """Carrega as configurações salvas"""
        settings = QSettings("MyCompany", "DocumentExtractor")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
    def closeEvent(self, event):
        """Salva as configurações ao fechar"""
        settings = QSettings("MyCompany", "DocumentExtractor")
        settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Estilo moderno e consistente
    
    # Configurar estilo da aplicação
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f0f0f0;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #cccccc;
            border-radius: 5px;
            margin-top: 1ex;
            padding: 10px;
        }
        QPushButton {
            background-color: #0078d4;
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #106ebe;
        }
        QPushButton:pressed {
            background-color: #005a9e;
        }
        QLineEdit {
            padding: 5px;
            border: 1px solid #cccccc;
            border-radius: 3px;
        }
        QComboBox {
            padding: 5px;
            border: 1px solid #cccccc;
            border-radius: 3px;
        }
        QListWidget {
            border: 1px solid #cccccc;
            border-radius: 3px;
        }
        QStatusBar {
            background-color: #f8f8f8;
        }
    """)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())