from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QProgressBar,
    QFileDialog, QMessageBox, QScrollArea, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QImage, QPixmap
import cv2
from pathlib import Path
import time

from roi_extractor import ROIExtractor
from template_manager import TemplateManager

class ProcessingWorker(QThread):
    """Thread worker para processamento em background"""
    
    progress = Signal(int)  # Progresso atual (0-100)
    status = Signal(str)    # Mensagem de status
    finished = Signal(bool) # True se sucesso, False se erro
    
    def __init__(self, extractor, input_dir, output_dir, template):
        super().__init__()
        self.extractor = extractor
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.template = template
        self.running = True
        
    def run(self):
        """Executa o processamento"""
        try:
            input_path = Path(self.input_dir)
            output_path = Path(self.output_dir)
            
            # Listar arquivos
            image_files = list(input_path.glob("*.png"))
            image_files.extend(input_path.glob("*.jpg"))
            
            if not image_files:
                raise ValueError("Nenhuma imagem encontrada")
                
            # Criar diretório de saída
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Processar cada imagem
            for i, img_path in enumerate(image_files):
                if not self.running:
                    break
                    
                self.status.emit(f"Processando {img_path.name}...")
                progress = int((i + 1) * 100 / len(image_files))
                self.progress.emit(progress)
                
                results = self.extractor.process_image(
                    str(img_path),
                    self.template
                )
                
                if results:
                    output_file = output_path / f"{img_path.stem}_results.json"
                    json.dump(results, output_file.open('w'), indent=4)
                    
                time.sleep(0.1)  # Prevenir UI freezing
                
            self.status.emit("Processamento concluído")
            self.finished.emit(True)
            
        except Exception as e:
            self.status.emit(f"Erro: {str(e)}")
            self.finished.emit(False)
            
    def stop(self):
        """Para o processamento"""
        self.running = False

class DocumentProcessor(QWidget):
    """Widget para processamento em lote de documentos"""
    
    processing_status = Signal(str)  # Emite mensagens de status
    
    def __init__(self):
        super().__init__()
        
        self.template_manager = TemplateManager()
        self.roi_extractor = ROIExtractor(self.template_manager)
        self.worker = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Configura a interface do processador"""
        layout = QVBoxLayout()
        
        # Grupo de diretórios
        dir_group = self.setup_directory_group()
        layout.addWidget(dir_group)
        
        # Grupo de template
        template_group = self.setup_template_group()
        layout.addWidget(template_group)
        
        # Grupo de opções
        options_group = self.setup_options_group()
        layout.addWidget(options_group)
        
        # Área de preview
        preview_group = self.setup_preview_group()
        layout.addWidget(preview_group)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Status
        self.status_label = QLabel("Pronto")
        layout.addWidget(self.status_label)
        
        # Botões
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Iniciar Processamento")
        self.start_btn.clicked.connect(self.start_processing)
        
        self.stop_btn = QPushButton("Parar")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def setup_directory_group(self):
        """Configura o grupo de seleção de diretórios"""
        group = QGroupBox("Diretórios")
        layout = QVBoxLayout()
        
        # Diretório de entrada
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Entrada:"))
        self.input_dir = QLineEdit()
        self.input_dir.setPlaceholderText("Selecione o diretório com as imagens")
        input_browse = QPushButton("...")
        input_browse.clicked.connect(self.browse_input)
        input_layout.addWidget(self.input_dir)
        input_layout.addWidget(input_browse)
        
        # Diretório de saída
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Saída:"))
        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("Selecione o diretório para os resultados")
        output_browse = QPushButton("...")
        output_browse.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_dir)
        output_layout.addWidget(output_browse)
        
        layout.addLayout(input_layout)
        layout.addLayout(output_layout)
        group.setLayout(layout)
        return group
        
    def setup_template_group(self):
        """Configura o grupo de seleção de template"""
        group = QGroupBox("Template")
        layout = QVBoxLayout()
        
        # Tipo de documento
        doc_layout = QHBoxLayout()
        doc_layout.addWidget(QLabel("Tipo:"))
        self.doc_type = QComboBox()
        self.doc_type.currentTextChanged.connect(self.update_templates)
        doc_layout.addWidget(self.doc_type)
        
        # Template
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("Template:"))
        self.template_name = QComboBox()
        template_layout.addWidget(self.template_name)
        
        layout.addLayout(doc_layout)
        layout.addLayout(template_layout)
        
        # Carregar tipos de documento
        self.load_doc_types()
        
        group.setLayout(layout)
        return group
        
    def setup_options_group(self):
        """Configura o grupo de opções de processamento"""
        group = QGroupBox("Opções")
        layout = QVBoxLayout()
        
        # Opções de processamento
        self.show_preview = QCheckBox("Mostrar preview durante processamento")
        self.save_debug = QCheckBox("Salvar imagens de debug")
        self.consolidate = QCheckBox("Consolidar resultados em um arquivo")
        
        layout.addWidget(self.show_preview)
        layout.addWidget(self.save_debug)
        layout.addWidget(self.consolidate)
        
        group.setLayout(layout)
        return group
        
    def setup_preview_group(self):
        """Configura o grupo de preview"""
        group = QGroupBox("Preview")
        layout = QVBoxLayout()
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(400, 300)
        
        # Scroll area para a preview
        scroll = QScrollArea()
        scroll.setWidget(self.preview_label)
        scroll.setWidgetResizable(True)
        
        layout.addWidget(scroll)
        group.setLayout(layout)
        return group
        
    def load_doc_types(self):
        """Carrega os tipos de documento disponíveis"""
        self.doc_type.clear()
        doc_types = self.template_manager.get_doc_types()
        self.doc_type.addItems(doc_types)
        
    def update_templates(self, doc_type):
        """Atualiza a lista de templates disponíveis"""
        self.template_name.clear()
        templates = self.template_manager.get_templates(doc_type)
        self.template_name.addItems(templates)
        
    def browse_input(self):
        """Abre diálogo para selecionar diretório de entrada"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Selecionar Diretório de Entrada"
        )
        if dir_path:
            self.input_dir.setText(dir_path)
        
    def browse_output(self):
        """Abre diálogo para selecionar diretório de saída"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Selecionar Diretório de Saída"
        )
        if dir_path:
            self.output_dir.setText(dir_path)
            
    def start_processing(self):
        """Inicia o processamento em lote"""
        # Validar entradas
        input_dir = self.input_dir.text()
        output_dir = self.output_dir.text()
        doc_type = self.doc_type.currentText()
        template_name = self.template_name.currentText()
        
        if not all([input_dir, output_dir, doc_type, template_name]):
            QMessageBox.warning(
                self,
                "Erro",
                "Preencha todos os campos necessários!"
            )
            return
            
        # Obter template
        template = self.template_manager.get_template(doc_type, template_name)
        if not template:
            QMessageBox.warning(
                self,
                "Erro",
                "Template não encontrado!"
            )
            return
            
        # Criar e iniciar worker
        self.worker = ProcessingWorker(
            self.roi_extractor,
            input_dir,
            output_dir,
            template
        )
        
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.status.connect(self.processing_status.emit)
        self.worker.finished.connect(self.processing_finished)
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        self.worker.start()
        
    def stop_processing(self):
        """Para o processamento atual"""
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.processing_finished(False)
            
    def processing_finished(self, success):
        """Chamado quando o processamento termina"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            self.progress_bar.setValue(100)
            QMessageBox.information(
                self,
                "Sucesso",
                "Processamento concluído com sucesso!"
            )
        else:
            QMessageBox.warning(
                self,
                "Aviso",
                "Processamento interrompido"
            )
            
    def preview_image(self, image_path):
        """Mostra uma imagem no preview"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Não foi possível carregar a imagem")
                
            # Converter BGR para RGB
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Criar QImage
            height, width, channel = image.shape
            bytes_per_line = 3 * width
            q_image = QImage(
                image.data,
                width,
                height,
                bytes_per_line,
                QImage.Format_RGB888
            )
            
            # Redimensionar mantendo proporção
            pixmap = QPixmap.fromImage(q_image)
            pixmap = pixmap.scaled(
                self.preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.preview_label.setPixmap(pixmap)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao carregar preview: {str(e)}"
            )