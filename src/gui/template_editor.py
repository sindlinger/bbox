import cv2
import numpy as np
import json
import os
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QComboBox, QLineEdit, QPushButton,
    QSpinBox, QListWidget, QListWidgetItem, QScrollArea, QMessageBox, QInputDialog, QDialogButtonBox, QGridLayout, QDialog
)

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor

from roi_extractor import ROIExtractor
from gui.template_manager import TemplateManager

class ImageViewer(QLabel):
    """Widget personalizado para visualizar e editar ROIs"""
    
    roi_selected = Signal(str)  # Emite nome da ROI selecionada
    roi_moved = Signal(str, QPoint)  # Emite nome da ROI e nova posição
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        self.setAlignment(Qt.AlignCenter)
        
        self.image = None
        self.scale_factor = 1.0
        self.regions = {}
        self.selected_roi = None
        self.dragging = False
        self.drag_start = None
        self.template_modified = False
        self.fields_list = []  # Lista para campos do template
        self.setMouseTracking(True)
        
    def load_image(self, image):
        """Carrega uma nova imagem"""
        self.image = image
        self.update_view()
        
    def set_regions(self, regions):
        """Atualiza as regiões de interesse"""
        self.regions = regions
        self.update()
        
    def update_view(self):
        """Atualiza a visualização"""
        if self.image is None:
            return
            
        height, width = self.image.shape[:2]
        bytes_per_line = 3 * width
        
        q_img = QImage(
            self.image.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888
        ).rgbSwapped()
        
        scaled_img = q_img.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self.setPixmap(QPixmap.fromImage(scaled_img))
        self.scale_factor = scaled_img.width() / width
        
    def paintEvent(self, event):
        """Desenha as ROIs sobre a imagem"""
        super().paintEvent(event)
        
        if not self.pixmap():
            return
            
        painter = QPainter(self)
        painter.begin(self)
        
        for name, region in self.regions.items():
            # Obter coordenadas e ajustar para escala
            x1, y1, x2, y2 = region["coords"]
            x1 = int(x1 * self.scale_factor)
            y1 = int(y1 * self.scale_factor)
            x2 = int(x2 * self.scale_factor)
            y2 = int(y2 * self.scale_factor)
            
            # Configurar estilo
            color = QColor(*region["color"])
            pen = QPen(color, 2)
            if name == self.selected_roi:
                pen.setWidth(3)
            painter.setPen(pen)
            
            # Desenhar retângulo
            painter.drawRect(x1, y1, x2-x1, y2-y1)
            
            # Desenhar label
            painter.drawText(x1, y1-5, name)
            
        painter.end()
        
    def mousePressEvent(self, event):
        """Processa clique do mouse"""
        if event.button() == Qt.LeftButton:
            pos = event.position()
            x, y = pos.x(), pos.y()
            
            # Encontrar ROI clicada
            for name, region in self.regions.items():
                x1, y1, x2, y2 = region["coords"]
                x1 = int(x1 * self.scale_factor)
                y1 = int(y1 * self.scale_factor)
                x2 = int(x2 * self.scale_factor)
                y2 = int(y2 * self.scale_factor)
                
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self.selected_roi = name
                    self.dragging = True
                    self.drag_start = (x - x1, y - y1)
                    self.roi_selected.emit(name)
                    self.update()
                    break
                    
    def mouseMoveEvent(self, event):
        """Processa movimento do mouse"""
        if self.dragging and self.selected_roi:
            pos = event.position()
            x, y = int(pos.x()), int(pos.y())
            
            # Calcular nova posição
            region = self.regions[self.selected_roi]
            x1, y1, x2, y2 = region["coords"]
            width = x2 - x1
            height = y2 - y1
            
            new_x = (x - self.drag_start[0]) / self.scale_factor
            new_y = (y - self.drag_start[1]) / self.scale_factor
            
            # Emitir sinal de movimento
            self.roi_moved.emit(self.selected_roi, QPoint(new_x, new_y))
            self.update()
            
    def mouseReleaseEvent(self, event):
        """Processa liberação do botão do mouse"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.drag_start = None

class TemplateEditor(QWidget):
    """Widget principal para edição de templates"""
    
    template_saved = Signal()  # Emitido quando um template é salvo
    
    def __init__(self):
        super().__init__()
        self.template_modified = False
        self.selected_roi = None
        
        self.roi_list = QListWidget()  # Lista visual de ROIs
        self.fields_list = []          # Lista de metadados dos campos
        self.fields_list_widget = QListWidget()  # Adicionando a definição de fields_list_widget
        self.regions = {}   

        # Inicializar gerenciadores
        self.template_manager = TemplateManager()
        self.roi_extractor = ROIExtractor(self.template_manager)
        
        # Conectar sinais
        self.roi_list.itemClicked.connect(self.select_roi)
        self.fields_list_widget.itemClicked.connect(self.on_field_selected)
            
        
        self.setup_ui()
        
        # Inicializar estado
        self.init_state()
        
    def setup_ui(self):
        """Configura a interface do editor"""
        layout = QHBoxLayout()
        
        # Painel esquerdo (controles)
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # Grupo de template
        template_group = self.setup_template_group()
        left_layout.addWidget(template_group)
        
        # Grupo de ROIs
        roi_group = self.setup_roi_group()
        left_layout.addWidget(roi_group)
        
        # Grupo de propriedades
        prop_group = self.setup_properties_group()
        left_layout.addWidget(prop_group)
        
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(400)
        
        # Visualizador de imagem
        self.image_viewer = ImageViewer()
        self.image_viewer.roi_selected.connect(self.select_roi)
        self.image_viewer.roi_moved.connect(self.move_roi)
        
        # Scroll area para a imagem
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.image_viewer)
        scroll_area.setWidgetResizable(True)
        
        # Botão de confirmação da imagem
        confirm_btn = QPushButton("Confirmar Imagem")
        confirm_btn.clicked.connect(self.confirm_image)
        
        # Layout direito com scroll area e botão
        right_layout = QVBoxLayout()
        right_layout.addWidget(scroll_area)
        right_layout.addWidget(confirm_btn)
        
        # Adicionar painéis ao layout principal
        layout.addWidget(left_panel)
        layout.addLayout(right_layout, stretch=1)
        
        
        self.fields_list_widget = QListWidget()
        self.fields_list_widget.itemClicked.connect(self.on_field_selected)

        # Botões para gerenciar campos
        add_field_btn = QPushButton("Adicionar Campo")
        remove_field_btn = QPushButton("Remover Campo")
        add_field_btn.clicked.connect(self.add_field)
        remove_field_btn.clicked.connect(self.remove_field)
        
        self.setLayout(layout)
        
    def setup_template_group(self):
        """Configura o grupo de controles do template"""
        group = QGroupBox("Template")
        layout = QVBoxLayout()
        
        # Nome do template
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nome:"))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        
        # Tipo de documento
        doc_layout = QHBoxLayout()
        doc_layout.addWidget(QLabel("Tipo:"))
        self.doc_type = QComboBox()
        self.doc_type.addItems(["RG", "CPF", "CNH", "OUTROS"])
        self.doc_type.currentTextChanged.connect(self.update_templates)
        doc_layout.addWidget(self.doc_type)
        
        # Lista de templates
        self.template_list = QListWidget()
        self.template_list.currentItemChanged.connect(self.open_template)
        
        # Botões
        btn_layout = QHBoxLayout()
        
        new_btn = QPushButton("Novo")
        new_btn.clicked.connect(self.new_template)
        
        save_btn = QPushButton("Salvar")
        save_btn.clicked.connect(self.save_template)
        
        btn_layout.addWidget(new_btn)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(name_layout)
        layout.addLayout(doc_layout)
        layout.addWidget(self.template_list)
        
        return group
        
        
    
    def confirm_image(self):
        """Confirma a imagem selecionada e habilita a edição de ROIs"""
        if self.current_image is not None:
            self.enable_roi_editing(True)
            QMessageBox.information(self, "Sucesso", 
                                "Imagem confirmada. Você pode começar a adicionar ROIs.")
        else:
            QMessageBox.warning(self, "Aviso", 
                            "Por favor, selecione uma imagem primeiro.")    
    
    
    
    def setup_roi_group(self):
        """Configura o grupo de controles das ROIs"""
        group = QGroupBox("Regiões")
        layout = QVBoxLayout()
        
        # Lista de ROIs
        self.roi_list = QListWidget()
        
        self.roi_list.itemClicked.connect(
            lambda item: self.select_roi(item.text()))
        layout.addWidget(self.roi_list)
        
        # Botões
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Adicionar")
        add_btn.clicked.connect(self.add_roi)
        
        del_btn = QPushButton("Remover")
        del_btn.clicked.connect(self.delete_roi)

        test_btn = QPushButton("Testar OCR")
        test_btn.clicked.connect(self.test_roi_ocr)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(test_btn)
        layout.addLayout(btn_layout)
        
        group.setLayout(layout)
        return group


    def load_image(self, file_path):
        """Carrega uma nova imagem para edição"""
        try:
            image = cv2.imread(file_path)
            if image is None:
                raise ValueError("Não foi possível carregar a imagem")
                
            self.current_image = self.roi_extractor.standardize_image(image)
            self.image_viewer.load_image(self.current_image)
            
            # Desabilitar edição de ROIs até confirmação
            self.enable_roi_editing(False)
            
        except Exception as e:
            QMessageBox.critical(self, "Erro",
                            f"Erro ao carregar imagem: {str(e)}")

    # def init_state(self):
    #     """Inicializa o estado do editor"""
    #     # Inicializar listas
    #     self.fields_list = QListWidget()  # Adicionar esta linha
    #     self.roi_list = QListWidget()     # Adicionar esta linha
        
    #     # Desabilitar edição de ROIs inicialmente
    #     self.enable_roi_editing(False)
        
    #     # Atualizar templates
    #     self.update_templates(self.doc_type.currentText())



    def setup_properties_group(self):
        """Configura o grupo de propriedades da ROI"""
        group = QGroupBox("Propriedades da ROI")
        layout = QVBoxLayout()
        
        # Nome da ROI
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nome:"))
        self.roi_name = QLineEdit()
        self.roi_name.textChanged.connect(self.update_roi_properties)
        name_layout.addWidget(self.roi_name)
        
        # Tipo de dados
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Tipo:"))
        self.roi_type = QComboBox()
        self.roi_type.addItems(["text", "cpf", "number", "currency", "date"])
        self.roi_type.currentTextChanged.connect(self.update_roi_properties)
        type_layout.addWidget(self.roi_type)
        
        # Coordenadas
        coords_layout = QHBoxLayout()
        coords_layout.addWidget(QLabel("X:"))
        self.roi_x = QSpinBox()
        self.roi_x.setRange(0, 9999)
        self.roi_x.valueChanged.connect(self.update_roi_coords)
        
        coords_layout.addWidget(QLabel("Y:"))
        self.roi_y = QSpinBox()
        self.roi_y.setRange(0, 9999)
        self.roi_y.valueChanged.connect(self.update_roi_coords)
        
        coords_layout.addWidget(QLabel("W:"))
        self.roi_w = QSpinBox()
        self.roi_w.setRange(1, 9999)
        self.roi_w.valueChanged.connect(self.update_roi_coords)
        
        coords_layout.addWidget(QLabel("H:"))
        self.roi_h = QSpinBox()
        self.roi_h.setRange(1, 9999)
        self.roi_h.valueChanged.connect(self.update_roi_coords)
        
        coords_layout.addWidget(self.roi_x)
        coords_layout.addWidget(self.roi_y)
        coords_layout.addWidget(self.roi_w)
        coords_layout.addWidget(self.roi_h)

        # Botões de ajuste rápido
        adjust_layout = QHBoxLayout()
        
        expand_btn = QPushButton("+")
        expand_btn.setToolTip("Expandir ROI")
        expand_btn.clicked.connect(lambda: self.adjust_roi_size(1.1))
        
        shrink_btn = QPushButton("-")
        shrink_btn.setToolTip("Reduzir ROI")
        shrink_btn.clicked.connect(lambda: self.adjust_roi_size(0.9))
        
        adjust_layout.addWidget(expand_btn)
        adjust_layout.addWidget(shrink_btn)
        
        layout.addLayout(name_layout)
        layout.addLayout(type_layout)
        layout.addLayout(coords_layout)
        layout.addLayout(adjust_layout)
        
        group.setLayout(layout)
        return group

    def adjust_roi_size(self, factor):
        """Ajusta o tamanho da ROI selecionada"""
        if not self.selected_roi:
            return
            
        region = self.regions[self.selected_roi]
        x1, y1, x2, y2 = region["coords"]
        
        # Calcular centro
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        # Calcular nova largura e altura
        width = (x2 - x1) * factor
        height = (y2 - y1) * factor
        
        # Calcular novas coordenadas
        new_x1 = center_x - width/2
        new_y1 = center_y - height/2
        new_x2 = center_x + width/2
        new_y2 = center_y + height/2
        
        # Atualizar coordenadas
        region["coords"] = (int(new_x1), int(new_y1), int(new_x2), int(new_y2))
        self.update_roi_display()
    
    
    def setup_side_panel(self):
        """Configura o painel lateral"""
        layout = QVBoxLayout()
        
        # Lista de campos
        self.fields_list = QListWidget()
        self.fields_list.currentItemChanged.connect(self.field_selected)
        
        # Controles de coordenadas
        coords_layout = QVBoxLayout()
        
        # X
        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("X:"))
        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 9999)
        self.x_spin.valueChanged.connect(self.update_roi_from_inputs)
        x_layout.addWidget(self.x_spin)
        
        # Y
        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Y:"))
        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 9999)
        self.y_spin.valueChanged.connect(self.update_roi_from_inputs)
        y_layout.addWidget(self.y_spin)
        
        # Width
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("Width:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 9999)
        self.width_spin.valueChanged.connect(self.update_roi_from_inputs)
        width_layout.addWidget(self.width_spin)
        
        # Height
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Height:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 9999)
        self.height_spin.valueChanged.connect(self.update_roi_from_inputs)
        height_layout.addWidget(self.height_spin)
        
        coords_layout.addLayout(x_layout)
        coords_layout.addLayout(y_layout)
        coords_layout.addLayout(width_layout)
        coords_layout.addLayout(height_layout)
        
        layout.addWidget(self.fields_list)
        layout.addLayout(coords_layout)
        
        return layout

    def init_state(self):
        """Inicializa o estado do editor"""
        self.selected_roi = None
        self.template_modified = False
        self.regions = {}
        self.current_image = None
        
        # Popula o combo de tipos de documento
        self.doc_type.addItems(["RG", "CPF", "CNH", "OUTROS"])  # Ajuste conforme necessário
        
        # Atualiza as listas
        self.update_templates()
  
    def sync_roi_fields(self):
        """Sincroniza as duas listas com as regiões atuais"""
        try:
            # Limpar ambas as listas
            self.roi_list.clear()
            self.fields_list.clear()
            self.fields_list_widget.clear()
            
            # Adicionar campos/ROIs baseados nas regiões
            for name, region in self.regions.items():
                # Adicionar à lista de ROIs (visual)
                self.roi_list.addItem(name)
                
                # Criar item para lista de campos (metadados)
                field_item = QListWidgetItem(name)
                field_data = {
                    'id': name,
                    'name': name,
                    'type': region['expected_type'],
                    'bbox': {
                        'x': region['coords'][0],
                        'y': region['coords'][1],
                        'width': region['coords'][2] - region['coords'][0],
                        'height': region['coords'][3] - region['coords'][1]
                    }
                }
                
                # Adicionar aos campos
                field_item.setData(Qt.UserRole, field_data)
                self.fields_list_widget.addItem(field_item)
                self.fields_list.append(field_data)
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", 
                            f"Erro ao sincronizar campos: {str(e)}")

    def field_selected(self, current, previous):
        """Manipula a seleção de um campo na lista"""
        if current:
            field_data = current.data(Qt.UserRole)
            if field_data and 'bbox' in field_data:
                self.update_coordinate_inputs(field_data['bbox'])

    # Aqui vão todas as funções que implementamos anteriormente
    
    def enable_roi_editing(self, enabled=True):
        """Habilita ou desabilita a edição de ROIs"""
        # Habilitar/desabilitar controles de ROI
        self.roi_name.setEnabled(enabled)
        self.roi_type.setEnabled(enabled)
        self.roi_x.setEnabled(enabled)
        self.roi_y.setEnabled(enabled)
        self.roi_w.setEnabled(enabled)
        self.roi_h.setEnabled(enabled)
        
    def update_roi_from_inputs(self):
        """Atualiza a ROI baseado nos valores dos campos de entrada"""
        try:
            current_item = self.fields_list.currentItem()
            if not current_item:
                return
                
            field_data = current_item.data(Qt.UserRole)
            if not field_data:
                return
                
            # Atualiza as coordenadas
            field_data['bbox'] = {
                'x': self.x_spin.value(),
                'y': self.y_spin.value(),
                'width': self.width_spin.value(),
                'height': self.height_spin.value()
            }
            
            # Atualiza o item na lista
            current_item.setData(Qt.UserRole, field_data)
            
            # Atualiza o visualizador
            self.image_viewer.update_roi(field_data['id'], field_data['bbox'])
            
            # Marca como modificado
            self.template_modified = True
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", 
                            f"Erro ao atualizar ROI: {str(e)}")
                    
                    
    def update_coordinate_inputs(self, bbox):
        """
        Atualiza os campos de entrada de coordenadas com os valores da bbox
        
        Args:
            bbox: Dicionário com as coordenadas {x, y, width, height}
        """
        try:
            self.x_spin.setValue(bbox['x'])
            self.y_spin.setValue(bbox['y'])
            self.width_spin.setValue(bbox['width'])
            self.height_spin.setValue(bbox['height'])
        except Exception as e:
            QMessageBox.critical(self, "Erro", 
                            f"Erro ao atualizar coordenadas: {str(e)}")
            
            
    def update_templates(self):
        
        """Atualiza a lista de templates com base no tipo de documento selecionado"""
        try:
            # Limpa a lista atual de templates
            self.template_list.clear()
            
            # Obtém o tipo de documento selecionado
            doc_type = self.doc_type.currentText()
            
            # Define o diretório base dos templates
            template_dir = os.path.join("templates", doc_type)
            
            # Verifica se o diretório existe
            if not os.path.exists(template_dir):
                os.makedirs(template_dir)
                
            # Lista todos os arquivos .json no diretório
            template_files = [f for f in os.listdir(template_dir) 
                            if f.endswith('.json')]
            
            # Adiciona os templates à lista
            for template_file in template_files:
                template_name = os.path.splitext(template_file)[0]
                self.template_list.addItem(template_name)
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", 
                            f"Erro ao atualizar templates: {str(e)}")


    def update_coordinate_inputs(self, bbox):
        """
        Atualiza os campos de entrada de coordenadas com os valores da bbox
        
        Args:
            bbox: Dicionário com as coordenadas {x, y, width, height}
        """
        try:
            self.x_spin.setValue(bbox['x'])
            self.y_spin.setValue(bbox['y'])
            self.width_spin.setValue(bbox['width'])
            self.height_spin.setValue(bbox['height'])
        except Exception as e:
            QMessageBox.critical(self, "Erro", 
                            f"Erro ao atualizar coordenadas: {str(e)}")

    def move_roi(self, roi_id, new_position):
        """Atualiza a posição de uma ROI quando ela é movida na interface"""
        try:
            # Atualizar a região
            if roi_id in self.regions:
                region = self.regions[roi_id]
                old_coords = region["coords"]
                width = old_coords[2] - old_coords[0]
                height = old_coords[3] - old_coords[1]
                
                # Calcular novas coordenadas
                new_x = int(new_position.x())
                new_y = int(new_position.y())
                new_coords = (new_x, new_y, new_x + width, new_y + height)
                
                # Atualizar região
                region["coords"] = new_coords
                
                # Atualizar campos
                self.update_field_coordinates(roi_id, new_coords)
                
                # Atualizar interface
                self.update_roi_display()
                self.template_modified = True
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", 
                            f"Erro ao mover ROI: {str(e)}")

    def update_field_coordinates(self, roi_id, coords):
        """Atualiza as coordenadas nos campos"""
        for i in range(self.fields_list_widget.count()):
            item = self.fields_list_widget.item(i)
            field_data = item.data(Qt.UserRole)
            if field_data['id'] == roi_id:
                field_data['bbox'] = {
                    'x': coords[0],
                    'y': coords[1],
                    'width': coords[2] - coords[0],
                    'height': coords[3] - coords[1]
                }
                item.setData(Qt.UserRole, field_data)
                break
        
    def new_template(self):
        """Cria um novo template"""
        try:
            # Solicita o nome do novo template
            name, ok = QInputDialog.getText(self, 'Novo Template', 
                                        'Nome do template:')
            
            if ok and name:
                # Verifica se já existe um template com esse nome
                doc_type = self.doc_type.currentText()
                template_path = os.path.join("templates", doc_type, 
                                        f"{name}.json")
                
                if os.path.exists(template_path):
                    QMessageBox.warning(self, "Aviso", 
                                    "Já existe um template com este nome!")
                    return
                
                # Cria um novo template vazio
                template_data = {
                    "name": name,
                    "doc_type": doc_type,
                    "fields": [],
                    "created_at": datetime.now().isoformat(),
                    "modified_at": datetime.now().isoformat()
                }
                
                # Salva o novo template
                os.makedirs(os.path.dirname(template_path), exist_ok=True)
                with open(template_path, 'w', encoding='utf-8') as f:
                    json.dump(template_data, f, indent=4)
                
                # Atualiza a lista de templates
                self.update_templates()
                
                # Seleciona o novo template
                items = self.template_list.findItems(name, Qt.MatchExactly)
                if items:
                    self.template_list.setCurrentItem(items[0])
                    
        except Exception as e:
            QMessageBox.critical(self, "Erro", 
                            f"Erro ao criar novo template: {str(e)}")

    def open_template(self):
        """Abre um template existente"""
        try:
            # Obtém o item selecionado
            current_item = self.template_list.currentItem()
            if not current_item:
                return
                
            template_name = current_item.text()
            doc_type = self.doc_type.currentText()
            
            # Carrega o arquivo do template
            template_path = os.path.join("templates", doc_type, 
                                    f"{template_name}.json")
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
                
            # Atualiza a interface com os dados do template
            self.name_edit.setText(template_data["name"])
            
            # Limpa e preenche a lista de campos
            self.fields_list.clear()
            for field in template_data["fields"]:
                item = QListWidgetItem()
                item.setText(field["name"])
                item.setData(Qt.UserRole, field)
                self.fields_list.addItem(item)
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", 
                            f"Erro ao abrir template: {str(e)}")

    def save_template(self):
        """Salva o template atual"""
        try:
            # Verifica se há um template selecionado
            current_item = self.template_list.currentItem()
            if not current_item:
                QMessageBox.warning(self, "Aviso", 
                                "Nenhum template selecionado!")
                return
                
            template_name = current_item.text()
            doc_type = self.doc_type.currentText()
            
            # Coleta os dados atuais do template
            template_data = {
                "name": self.name_edit.text(),
                "doc_type": doc_type,
                "fields": [],
                "modified_at": datetime.now().isoformat()
            }
            
            # Coleta todos os campos
            for i in range(self.fields_list.count()):
                item = self.fields_list.item(i)
                field_data = item.data(Qt.UserRole)
                template_data["fields"].append(field_data)
                
            # Salva o template
            template_path = os.path.join("templates", doc_type, 
                                    f"{template_name}.json")
            
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=4)
                
            # Emite o sinal de template salvo
            self.template_saved.emit()
            
            QMessageBox.information(self, "Sucesso", 
                                "Template salvo com sucesso!")
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", 
                            f"Erro ao salvar template: {str(e)}")
        
    def keyPressEvent(self, event):
        """Processa eventos de teclado"""
        if not self.selected_roi:
            return
            
        step = 1
        if event.modifiers() & Qt.ShiftModifier:
            step = 10
            
        region = self.regions[self.selected_roi]
        x1, y1, x2, y2 = region["coords"]
        
        if event.key() == Qt.Key_Left:
            x1 -= step
            x2 -= step
        elif event.key() == Qt.Key_Right:
            x1 += step
            x2 += step
        elif event.key() == Qt.Key_Up:
            y1 -= step
            y2 -= step
        elif event.key() == Qt.Key_Down:
            y1 += step
            y2 += step
        elif event.key() == Qt.Key_Delete:
            self.delete_roi()
            return
            
        region["coords"] = (x1, y1, x2, y2)
        self.update_roi_display()

    def test_roi_ocr(self):
        """Testa o OCR na ROI selecionada"""
        if not self.selected_roi or not self.current_image:
            return
            
        region = self.regions[self.selected_roi]
        roi = self.roi_extractor.extract_roi(
            self.current_image, 
            region["coords"]
        )
        
        text = self.roi_extractor.extract_text(
            roi, 
            region["expected_type"]
        )
        
        QMessageBox.information(
            self,
            "Resultado OCR",
            f"Texto extraído: {text}"
        )

    def add_roi(self):
        """Adiciona uma nova ROI"""
        name, ok = QInputDialog.getText(
            self, 
            "Nova ROI",
            "Nome da ROI:"
        )
        
        if ok and name:
            if name in self.regions:
                QMessageBox.warning(
                    self,
                    "Erro",
                    "Já existe uma ROI com este nome!"
                )
                return
                
            # Criar ROI no centro da imagem
            center_x = self.image_viewer.width() // 2
            center_y = self.image_viewer.height() // 2
            width = 200
            height = 50
            
            self.regions[name] = {
                "coords": (
                    center_x - width//2,
                    center_y - height//2,
                    center_x + width//2,
                    center_y + height//2
                ),
                "color": (np.random.randint(0, 255), 
                         np.random.randint(0, 255),
                         np.random.randint(0, 255)),
                "expected_type": "text"
            }
            
            self.update_roi_list()
            self.select_roi(name)

    def delete_roi(self):
        """Remove a ROI selecionada"""
        if self.selected_roi:
            reply = QMessageBox.question(
                self,
                "Confirmar Exclusão",
                f"Deseja realmente excluir a ROI '{self.selected_roi}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                del self.regions[self.selected_roi]
                self.selected_roi = None
                self.update_roi_list()
                self.update_roi_display()

    def update_roi_coords(self):
        """Atualiza as coordenadas da ROI a partir dos spinboxes"""
        if not self.selected_roi:
            return
            
        region = self.regions[self.selected_roi]
        x = self.roi_x.value()
        y = self.roi_y.value()
        w = self.roi_w.value()
        h = self.roi_h.value()
        
        region["coords"] = (x, y, x + w, y + h)
        self.update_roi_display()

    def update_roi_properties(self):
        """Atualiza as propriedades da ROI"""
        if not self.selected_roi:
            return
            
        region = self.regions[self.selected_roi]
        region["expected_type"] = self.roi_type.currentText()
        
        new_name = self.roi_name.text()
        if new_name and new_name != self.selected_roi:
            if new_name in self.regions:
                QMessageBox.warning(
                    self,
                    "Erro",
                    "Já existe uma ROI com este nome!"
                )
                self.roi_name.setText(self.selected_roi)
                return
                
            self.regions[new_name] = region
            del self.regions[self.selected_roi]
            self.selected_roi = new_name
            self.update_roi_list()
            

    def update_roi_list(self):
        """Atualiza a lista de ROIs"""
        self.sync_roi_fields()
        

    def update_roi_display(self):
        """Atualiza a exibição das ROIs"""
        self.image_viewer.set_regions(self.regions)
        if self.selected_roi:
            region = self.regions[self.selected_roi]
            x1, y1, x2, y2 = region["coords"]
            self.roi_x.setValue(x1)
            self.roi_y.setValue(y1)
            self.roi_w.setValue(x2 - x1)
            self.roi_h.setValue(y2 - y1)
            self.roi_type.setCurrentText(region["expected_type"])

    def select_roi(self, name):
        """Seleciona uma ROI para edição"""
        if name in self.regions:
            self.selected_roi = name
            self.roi_name.setText(name)
            self.update_roi_display()
            
    def load_image(self, file_path):
        """Carrega uma nova imagem para edição"""
        try:
            image = cv2.imread(file_path)
            if image is None:
                raise ValueError("Não foi possível carregar a imagem")
                
            self.current_image = self.roi_extractor.standardize_image(image)
            self.image_viewer.load_image(self.current_image)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao carregar imagem: {str(e)}"
            )
            
    def add_field(self):
        """Adiciona um novo campo ao template"""
        dialog = FieldDialog(self)
        if dialog.exec_():
            field_data = dialog.get_field_data()
            self.fields_list.append(field_data)
            self.fields_list_widget.addItem(field_data['name'])
            self.update_template()

    def remove_field(self):
        """Remove o campo selecionado"""
        current_item = self.fields_list_widget.currentItem()
        if current_item:
            row = self.fields_list_widget.row(current_item)
            self.fields_list_widget.takeItem(row)
            self.fields_list.pop(row)
            self.update_template()

    def on_field_selected(self, item):
        """Manipula a seleção de um campo"""
        row = self.fields_list_widget.row(item)
        field_data = self.fields_list[row]
        # Atualizar interface com dados do campo selecionado

    def update_template(self):
        """Atualiza o template com os campos atuais"""
        if hasattr(self, 'current_template') and self.current_template:
            self.current_template['fields'] = self.fields_list
            self.template_modified = True
    
    
class FieldDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Campo Nome
        self.name_edit = QLineEdit()
        layout.addWidget(QLabel("Nome do Campo:"))
        layout.addWidget(self.name_edit)

        # Tipo de Campo
        self.type_combo = QComboBox()
        self.type_combo.addItems(['text', 'number', 'date', 'cpf', 'currency'])
        layout.addWidget(QLabel("Tipo:"))
        layout.addWidget(self.type_combo)

        # Coordenadas
        coord_layout = QGridLayout()
        self.x_spin = QSpinBox()
        self.y_spin = QSpinBox()
        self.width_spin = QSpinBox()
        self.height_spin = QSpinBox()
        coord_layout.addWidget(QLabel("X:"), 0, 0)
        coord_layout.addWidget(self.x_spin, 0, 1)
        coord_layout.addWidget(QLabel("Y:"), 1, 0)
        coord_layout.addWidget(self.y_spin, 1, 1)
        coord_layout.addWidget(QLabel("Largura:"), 2, 0)
        coord_layout.addWidget(self.width_spin, 2, 1)
        coord_layout.addWidget(QLabel("Altura:"), 3, 0)
        coord_layout.addWidget(self.height_spin, 3, 1)
        layout.addLayout(coord_layout)

        # Botões
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_field_data(self):
        """Retorna os dados do campo"""
        return {
            'name': self.name_edit.text(),
            'type': self.type_combo.currentText(),
            'coords': (
                self.x_spin.value(),
                self.y_spin.value(),
                self.width_spin.value(),
                self.height_spin.value()
            )
        }