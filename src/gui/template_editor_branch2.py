"""
Integração completa do sistema de templates e extração de documentos.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
import pytesseract
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


from template_manager import TemplateManager
class Template:
    """Classe que representa um template de documento."""
    
    def __init__(self, name: str, doc_type: str):
        self.name = name
        self.doc_type = doc_type
        self.fields = []
        self.created_at = datetime.now()
        self.modified_at = datetime.now()
        
    def add_field(self, field_data: Dict):
        """Adiciona um novo campo ao template."""
        self.fields.append(field_data)
        self.modified_at = datetime.now()
        
    def remove_field(self, field_name: str):
        """Remove um campo do template."""
        self.fields = [f for f in self.fields if f['name'] != field_name]
        self.modified_at = datetime.now()
        
    def to_dict(self) -> Dict:
        """Converte o template para dicionário."""
        return {
            'name': self.name,
            'doc_type': self.doc_type,
            'fields': self.fields,
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat()
        }

class ImageViewer(QLabel):
    """Widget para visualização e edição de ROIs na imagem."""
    
    roi_selected = Signal(dict)  # Emite dados da ROI selecionada
    roi_moved = Signal(str, tuple)  # Emite nome da ROI e novas coordenadas
    
    def __init__(self):
        super().__init__()
        self.image = None
        self.scale_factor = 1.0
        self.current_roi = None
        self.dragging = False
        self.resize_mode = False
        self.fields = []
        
        self.setMinimumSize(800, 600)
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        
    def set_image(self, image):
        """Define a imagem atual."""
        if isinstance(image, np.ndarray):
            height, width = image.shape[:2]
            bytes_per_line = 3 * width
            q_img = QImage(image.data, width, height, bytes_per_line, 
                          QImage.Format_RGB888).rgbSwapped()
            self.image = QPixmap.fromImage(q_img)
            self.update_view()
            
    def update_view(self):
        """Atualiza a visualização."""
        if self.image:
            scaled = self.image.scaled(self.size(), Qt.KeepAspectRatio, 
                                     Qt.SmoothTransformation)
            self.setPixmap(scaled)
            self.scale_factor = scaled.width() / self.image.width()
            
    def set_fields(self, fields: List[Dict]):
        """Atualiza a lista de campos/ROIs."""
        self.fields = fields
        self.update()
        
    def paintEvent(self, event):
        """Desenha as ROIs sobre a imagem."""
        super().paintEvent(event)
        if not self.pixmap():
            return
            
        painter = QPainter(self)
        painter.begin(self)
        
        for field in self.fields:
            color = QColor(*field.get('color', (255, 0, 0)))
            x, y, w, h = self.scale_coords(field['coords'])
            
            # Desenhar retângulo
            pen = QPen(color, 2)
            if field == self.current_roi:
                pen.setWidth(3)
            painter.setPen(pen)
            painter.drawRect(x, y, w, h)
            
            # Desenhar nome
            painter.drawText(x, y-5, field['name'])
            
            # Desenhar alças de redimensionamento se em modo resize
            if field == self.current_roi and self.resize_mode:
                self.draw_resize_handles(painter, x, y, w, h)
                
        painter.end()
        
    def draw_resize_handles(self, painter, x, y, w, h):
        """Desenha alças de redimensionamento."""
        handle_size = 6
        handles = [
            (x, y),             # Top-left
            (x + w, y),         # Top-right
            (x, y + h),         # Bottom-left
            (x + w, y + h)      # Bottom-right
        ]
        
        painter.setBrush(QBrush(Qt.white))
        for hx, hy in handles:
            painter.drawRect(
                int(hx - handle_size/2),
                int(hy - handle_size/2),
                handle_size,
                handle_size
            )
            
    def scale_coords(self, coords):
        """Escala coordenadas para o tamanho atual da visualização."""
        x, y, w, h = coords
        return (
            int(x * self.scale_factor),
            int(y * self.scale_factor),
            int(w * self.scale_factor),
            int(h * self.scale_factor)
        )
        
    def unscale_coords(self, coords):
        """Converte coordenadas da visualização para coordenadas da imagem."""
        x, y, w, h = coords
        return (
            int(x / self.scale_factor),
            int(y / self.scale_factor),
            int(w / self.scale_factor),
            int(h / self.scale_factor)
        )

class FieldDialog(QDialog):
    """Diálogo para adicionar/editar campos do template."""
    
    def __init__(self, parent=None, field_data=None):
        super().__init__(parent)
        self.field_data = field_data
        self.setup_ui()
        if field_data:
            self.load_field_data()
            
    def setup_ui(self):
        """Configura a interface do diálogo."""
        self.setWindowTitle("Campo do Template")
        layout = QVBoxLayout()
        
        # Nome do campo
        name_layout = QHBoxLayout()
        self.name_edit = QLineEdit()
        name_layout.addWidget(QLabel("Nome:"))
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Tipo do campo
        type_layout = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(['text', 'cpf', 'date', 'currency', 'number'])
        type_layout.addWidget(QLabel("Tipo:"))
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
        # Coordenadas
        coords_group = QGroupBox("Coordenadas")
        coords_layout = QGridLayout()
        
        self.x_spin = QSpinBox()
        self.y_spin = QSpinBox()
        self.w_spin = QSpinBox()
        self.h_spin = QSpinBox()
        
        for spin in [self.x_spin, self.y_spin, self.w_spin, self.h_spin]:
            spin.setRange(0, 9999)
            
        coords_layout.addWidget(QLabel("X:"), 0, 0)
        coords_layout.addWidget(self.x_spin, 0, 1)
        coords_layout.addWidget(QLabel("Y:"), 1, 0)
        coords_layout.addWidget(self.y_spin, 1, 1)
        coords_layout.addWidget(QLabel("Largura:"), 2, 0)
        coords_layout.addWidget(self.w_spin, 2, 1)
        coords_layout.addWidget(QLabel("Altura:"), 3, 0)
        coords_layout.addWidget(self.h_spin, 3, 1)
        
        coords_group.setLayout(coords_layout)
        layout.addWidget(coords_group)
        
        # Botões
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
    def load_field_data(self):
        """Carrega dados do campo para edição."""
        if self.field_data:
            self.name_edit.setText(self.field_data['name'])
            self.type_combo.setCurrentText(self.field_data['type'])
            x, y, w, h = self.field_data['coords']
            self.x_spin.setValue(x)
            self.y_spin.setValue(y)
            self.w_spin.setValue(w)
            self.h_spin.setValue(h)
            
    def get_field_data(self) -> Dict:
        """Retorna os dados do campo."""
        return {
            'name': self.name_edit.text(),
            'type': self.type_combo.currentText(),
            'coords': (
                self.x_spin.value(),
                self.y_spin.value(),
                self.w_spin.value(),
                self.h_spin.value()
            ),
            'color': (  # Cor aleatória para visualização
                np.random.randint(0, 255),
                np.random.randint(0, 255),
                np.random.randint(0, 255)
            )
        }

class TemplateEditor(QWidget):
    """Widget principal para edição de templates."""
    
    template_saved = Signal()  # Emitido quando um template é salvo
    
    def __init__(self):
        super().__init__()
        self.template_manager = TemplateManager()
        self.current_template = None
        self.fields_list = []
        self.setup_ui()
        
    def setup_ui(self):
        """Configura a interface do editor."""
        layout = QHBoxLayout()
        
        # Painel esquerdo
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # Grupo Template
        template_group = QGroupBox("Template")
        template_layout = QVBoxLayout()
        
        # Tipo de documento
        doc_type_layout = QHBoxLayout()
        self.doc_type_combo = QComboBox()
        doc_type_layout.addWidget(QLabel("Tipo:"))
        doc_type_layout.addWidget(self.doc_type_combo)
        
        # Nome do template
        name_layout = QHBoxLayout()
        self.template_name = QLineEdit()
        name_layout.addWidget(QLabel("Nome:"))
        name_layout.addWidget(self.template_name)
        
        template_layout.addLayout(doc_type_layout)
        template_layout.addLayout(name_layout)
        template_group.setLayout(template_layout)
        
        # Grupo Campos
        fields_group = QGroupBox("Campos")
        fields_layout = QVBoxLayout()
        
        self.fields_list_widget = QListWidget()
        fields_layout.addWidget(self.fields_list_widget)
        
        field_buttons = QHBoxLayout()
        add_field_btn = QPushButton("+")
        del_field_btn = QPushButton("-")
        test_field_btn = QPushButton("Testar")
        
        field_buttons.addWidget(add_field_btn)
        field_buttons.addWidget(del_field_btn)
        field_buttons.addWidget(test_field_btn)
        fields_layout.addLayout(field_buttons)
        
        fields_group.setLayout(fields_layout)
        
        # Propriedades
        props_group = QGroupBox("Propriedades")
        props_layout = QVBoxLayout()
        self.props_widget = QWidget()
        props_layout.addWidget(self.props_widget)
        props_group.setLayout(props_layout)
        
        # Adicionar grupos ao painel esquerdo
        left_layout.addWidget(template_group)
        left_layout.addWidget(fields_group)
        left_layout.addWidget(props_group)
        left_panel.setLayout(left_layout)
        
        # Painel direito (visualização)
        self.image_viewer = ImageViewer()
        
        # Layout principal
        layout.addWidget(left_panel, stretch=1)
        layout.addWidget(self.image_viewer, stretch=2)
        
        self.setLayout(layout)
        
        # Conectar sinais
        add_field_btn.clicked.connect(self.add_field)
        del_field_btn.clicked.connect(self.remove_field)
        test_field_btn.clicked.connect(self.test_field)
        self.fields_list_widget.itemClicked.connect(self.on_field_selected)
        self.doc_type_combo.currentTextChanged.connect(self.update_templates)
        
        # Carregar tipos de documento
        self.load_doc_types()
        
    def load_doc_types(self):
        """Carrega tipos de documento disponíveis."""
        doc_types = self.template_manager.get_doc_types()
        self.doc_type_combo.clear()
        self.doc_type_combo.addItems(doc_types)
        
    def add_field(self):
        """Adiciona um novo campo ao template."""
        dialog = FieldDialog(self)
        if dialog.exec_():
            field_data = dialog.get_field_data()
            self.fields_list.append(field_data)
            self.fields_list_widget.addItem(field_data['name'])
            self.image_viewer.set_fields(self.fields_list)
            
    def remove_field(self):
        """Remove o campo selecionado."""
        current_item = self.fields_list_widget.currentItem()
        if current_item:
            row = self.fields_list_widget.row(current_item)
            self.fields_list_widget.takeItem(row)
            self.fields_list.pop(row)
            self.image_viewer.set_fields(self.fields_list)
            
    def test_field(self):
        """Testa a extração do campo selecionado."""
        current_item = self.fields_list_widget.currentItem()
        if not current_item:
            return
            
        row = self.fields_list_widget.row(current_item)
        field = self.fields_list[row]
        
        # Extrair e mostrar resultado
        if hasattr(self, 'current_image'):
            roi = self.extract_roi(field['coords'])
            text = self.extract_text(roi, field['type'])
            QMessageBox.information(self,
                "Teste de Extração",
                f"Texto extraído para o campo '{field['name']}':\n{text}"
            )
            
    def extract_roi(self, coords):
        """Extrai uma região de interesse da imagem atual."""
        x, y, w, h = coords
        if hasattr(self, 'current_image'):
            return self.current_image[y:y+h, x:x+w]
        return None
        
    def extract_text(self, roi, field_type):
        """Extrai texto de uma ROI usando OCR."""
        if roi is None:
            return ""
            
        # Pré-processamento baseado no tipo
        processed = self.preprocess_roi(roi, field_type)
        
        # Configurar Tesseract baseado no tipo
        config = {
            'text': '--psm 6 --oem 3',
            'cpf': '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.-/',
            'date': '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789/',
            'currency': '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789,.',
            'number': '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.'
        }
        
        # Extrair texto
        try:
            text = pytesseract.image_to_string(
                processed,
                config=config.get(field_type, config['text'])
            )
            return self.post_process_text(text, field_type)
        except Exception as e:
            print(f"Erro na extração: {e}")
            return ""
            
    def preprocess_roi(self, roi, field_type):
        """Pré-processa ROI para melhorar OCR."""
        # Converter para escala de cinza
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi
            
        # Redimensionar para melhor OCR
        scale = 2
        enlarged = cv2.resize(
            gray, 
            None, 
            fx=scale, 
            fy=scale, 
            interpolation=cv2.INTER_CUBIC
        )
        
        # Remover ruído
        denoised = cv2.bilateralFilter(enlarged, 9, 75, 75)
        
        # Ajustes baseados no tipo
        if field_type in ['cpf', 'date', 'currency', 'number']:
            # Aumentar contraste para números
            denoised = cv2.convertScaleAbs(denoised, alpha=1.2, beta=0)
            
        return denoised
        
    def post_process_text(self, text, field_type):
        """Processa o texto extraído baseado no tipo."""
        text = text.strip()
        
        if not text:
            return ""
            
        if field_type == 'cpf':
            # Manter apenas números
            nums = ''.join(filter(str.isdigit, text))
            if len(nums) == 11:
                return f"{nums[:3]}.{nums[3:6]}.{nums[6:9]}-{nums[9:]}"
            return nums
            
        elif field_type == 'date':
            # Procurar padrão de data
            import re
            match = re.search(r'(\d{2})/(\d{2})/(\d{2,4})', text)
            if match:
                day, month, year = match.groups()
                if len(year) == 2:
                    year = '20' + year
                return f"{day}/{month}/{year}"
            return text
            
        elif field_type == 'currency':
            # Formatar valor monetário
            nums = ''.join(filter(lambda x: x.isdigit() or x in ',.', text))
            if ',' not in nums:
                nums = nums[:-2] + ',' + nums[-2:]
            return nums
            
        elif field_type == 'number':
            # Manter apenas números e pontos
            return ''.join(filter(lambda x: x.isdigit() or x == '.', text))
            
        return text
        
    def on_field_selected(self, item):
        """Manipula a seleção de um campo na lista."""
        row = self.fields_list_widget.row(item)
        field = self.fields_list[row]
        self.update_properties(field)
        self.image_viewer.current_roi = field
        self.image_viewer.update()
        
    def update_properties(self, field):
        """Atualiza o painel de propriedades com dados do campo."""
        # Criar novo widget de propriedades
        props = QWidget()
        layout = QFormLayout()
        
        # Nome
        name_edit = QLineEdit(field['name'])
        name_edit.textChanged.connect(
            lambda t: self.update_field_property(field, 'name', t)
        )
        layout.addRow("Nome:", name_edit)
        
        # Tipo
        type_combo = QComboBox()
        type_combo.addItems(['text', 'cpf', 'date', 'currency', 'number'])
        type_combo.setCurrentText(field['type'])
        type_combo.currentTextChanged.connect(
            lambda t: self.update_field_property(field, 'type', t)
        )
        layout.addRow("Tipo:", type_combo)
        
        # Coordenadas
        x, y, w, h = field['coords']
        
        x_spin = QSpinBox()
        x_spin.setRange(0, 9999)
        x_spin.setValue(x)
        x_spin.valueChanged.connect(
            lambda v: self.update_field_coords(field, 'x', v)
        )
        layout.addRow("X:", x_spin)
        
        y_spin = QSpinBox()
        y_spin.setRange(0, 9999)
        y_spin.setValue(y)
        y_spin.valueChanged.connect(
            lambda v: self.update_field_coords(field, 'y', v)
        )
        layout.addRow("Y:", y_spin)
        
        w_spin = QSpinBox()
        w_spin.setRange(1, 9999)
        w_spin.setValue(w)
        w_spin.valueChanged.connect(
            lambda v: self.update_field_coords(field, 'w', v)
        )
        layout.addRow("Largura:", w_spin)
        
        h_spin = QSpinBox()
        h_spin.setRange(1, 9999)
        h_spin.setValue(h)
        h_spin.valueChanged.connect(
            lambda v: self.update_field_coords(field, 'h', v)
        )
        layout.addRow("Altura:", h_spin)
        
        props.setLayout(layout)
        
        # Substituir widget atual
        old_layout = self.props_widget.layout()
        if old_layout:
            QWidget().setLayout(old_layout)
        self.props_widget.setLayout(layout)
        
    def update_field_property(self, field, prop, value):
        """Atualiza uma propriedade do campo."""
        field[prop] = value
        if prop == 'name':
            # Atualizar item na lista
            items = self.fields_list_widget.findItems(
                field['name'],
                Qt.MatchExactly
            )
            if items:
                items[0].setText(value)
                
    def update_field_coords(self, field, coord, value):
        """Atualiza coordenadas do campo."""
        x, y, w, h = field['coords']
        if coord == 'x':
            field['coords'] = (value, y, w, h)
        elif coord == 'y':
            field['coords'] = (x, value, w, h)
        elif coord == 'w':
            field['coords'] = (x, y, value, h)
        elif coord == 'h':
            field['coords'] = (x, y, w, value)
            
        self.image_viewer.update()