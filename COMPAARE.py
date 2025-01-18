import os
import json
import uuid
from datetime import datetime
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QListWidget, QListWidgetItem, 
    QPushButton, QSpinBox, QMessageBox, QInputDialog
)
from .image_viewer import ImageViewer

class TemplateEditor(QWidget):
    # Sinais
    template_saved = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.template_modified = False

        self.setup_ui()
        
    def setup_ui(self):
        """Configura a interface do editor de templates"""
        layout = QVBoxLayout()
        
        # Grupo de template
        template_group = self.setup_template_group()
        layout.addWidget(template_group)
        
        # Área principal
        main_area = QHBoxLayout()
        
        # Visualizador de imagem
        self.image_viewer = ImageViewer()
        self.image_viewer.roi_moved.connect(self.move_roi)
        main_area.addWidget(self.image_viewer)
        
        # Painel lateral
        side_panel = self.setup_side_panel()
        main_area.addLayout(side_panel)
        
        layout.addLayout(main_area)
        self.setLayout(layout)
        
    def setup_template_group(self):
        """Configura o grupo de controles do template"""
        group = QWidget()
        layout = QHBoxLayout()
        
        # Tipo de documento
        doc_type_label = QLabel("Tipo de Documento:")
        self.doc_type = QComboBox()
        self.doc_type.addItems(["Tipo1", "Tipo2", "Tipo3"])  # Adicione seus tipos
        self.doc_type.currentTextChanged.connect(self.update_templates)
        
        # Lista de templates
        self.template_list = QListWidget()
        self.template_list.currentItemChanged.connect(self.open_template)
        
        # Botões
        new_btn = QPushButton("Novo")
        new_btn.clicked.connect(self.new_template)
        
        save_btn = QPushButton("Salvar")
        save_btn.clicked.connect(self.save_template)
        
        layout.addWidget(doc_type_label)
        layout.addWidget(self.doc_type)
        layout.addWidget(self.template_list)
        layout.addWidget(new_btn)
        layout.addWidget(save_btn)
        
        group.setLayout(layout)
        return group
        
    def update_templates(self):
        """Atualiza a lista de templates com base no tipo de documento selecionado"""
        try:
            self.template_list.clear()
            doc_type = self.doc_type.currentText()
            template_dir = os.path.join("templates", doc_type)
            
            if not os.path.exists(template_dir):
                os.makedirs(template_dir)
                
            template_files = [f for f in os.listdir(template_dir) 
                            if f.endswith('.json')]
            
            for template_file in template_files:
                template_name = os.path.splitext(template_file)[0]
                self.template_list.addItem(template_name)
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", 
                               f"Erro ao atualizar templates: {str(e)}")

    def move_roi(self, roi_id, new_position):
        """Atualiza a posição de uma ROI quando ela é movida na interface"""
        try:
            current_item = self.fields_list.currentItem()
            if not current_item:
                return
                
            field_data = current_item.data(Qt.UserRole)
            if not field_data:
                return
                
            field_data['bbox']['x'] = new_position[0]
            field_data['bbox']['y'] = new_position[1]
            
            current_item.setData(Qt.UserRole, field_data)
            self.update_coordinate_inputs(field_data['bbox'])
            self.template_modified = True
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", 
                               f"Erro ao mover ROI: {str(e)}")

    # [Adicione aqui as outras funções que implementamos anteriormente]
    # new_template()
    # open_template()
    # save_template()
    # update_coordinate_inputs()
    # add_roi()
    # remove_roi()
    # update_roi_from_inputs()