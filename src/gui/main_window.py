from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QToolBar, QStatusBar,
    QMessageBox, QFileDialog
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import QSettings, Qt

from .template_editor import TemplateEditor
from .document_processor import DocumentProcessor

class MainWindow(QMainWindow):
    def __init__(self, settings: QSettings):
        super().__init__()
        self.settings = settings
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Configura a interface principal"""
        self.setWindowTitle("Sistema de Extração de Documentos")
        self.setMinimumSize(1200, 800)
              # Widget central com abas
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        

        # Criar abas principais
        self.template_editor = TemplateEditor()
        self.document_processor = DocumentProcessor()
        
        self.tab_widget.addTab(self.template_editor, "Editor de Templates")
        self.tab_widget.addTab(self.document_processor, "Processamento")
        
        # Barra de status
        self.statusBar().showMessage("Pronto")
        
        # Conectar sinais
        self.template_editor.template_saved.connect(
            lambda: self.statusBar().showMessage("Template salvo com sucesso", 3000))
        self.document_processor.processing_status.connect(
            self.statusBar().showMessage)
        # Barra de ferramentas
        
        self.setup_toolbar()
        
    def setup_toolbar(self):
        """Configura a barra de ferramentas"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Ações
        new_action = QAction("Novo Template", self)
        new_action.setIcon(QIcon("resources/icons/new.png"))
        new_action.setStatusTip("Criar novo template")
        new_action.triggered.connect(self.template_editor.new_template)
        
        save_action = QAction("Salvar Template", self)
        save_action.setIcon(QIcon("resources/icons/save.png"))
        save_action.setStatusTip("Salvar template atual")
        save_action.triggered.connect(self.template_editor.save_template)
        
        open_action = QAction("Abrir Imagem", self)
        open_action.setIcon(QIcon("resources/icons/open.png"))
        open_action.setStatusTip("Abrir imagem para calibração")
        open_action.triggered.connect(self.open_image)
        
        settings_action = QAction("Configurações", self)
        settings_action.setIcon(QIcon("resources/icons/settings.png"))
        settings_action.setStatusTip("Configurações do sistema")
        settings_action.triggered.connect(self.show_settings)
        
        # Adicionar ações à barra
        toolbar.addAction(new_action)
        toolbar.addAction(save_action)
        toolbar.addAction(open_action)
        toolbar.addSeparator()
        toolbar.addAction(settings_action)
        
    def load_settings(self):
        """Carrega configurações salvas"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)
            
    def save_settings(self):
        """Salva configurações atuais"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        
    def open_image(self):
        """Abre uma imagem para calibração"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir Imagem",
            "",
            "Imagens (*.png *.jpg *.jpeg)"
        )
        
        if file_name:
            current_tab = self.tab_widget.currentWidget()
            if isinstance(current_tab, TemplateEditor):
                current_tab.load_image(file_name)
            elif isinstance(current_tab, DocumentProcessor):
                current_tab.preview_image(file_name)
                
    def show_settings(self):
        """Mostra diálogo de configurações"""
        # TODO: Implementar diálogo de configurações
        QMessageBox.information(
            self,
            "Configurações",
            "Configurações do sistema serão implementadas em breve."
        )
        
    def closeEvent(self, event):
        """Evento de fechamento da janela"""
        self.save_settings()
        super().closeEvent(event)