import cv2
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QComboBox, QLineEdit, QPushButton,
    QSpinBox, QListWidget, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor

from roi_extractor import ROIExtractor
from template_manager import TemplateManager

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
        
        self.template_manager = TemplateManager()
        self.roi_extractor = ROIExtractor(self.template_manager)
        
        self.current_image = None
        self.setup_ui()
        
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
        
        # Adicionar painéis ao layout principal
        layout.addWidget(left_panel)
        layout.addWidget(scroll_area, stretch=1)
        
        self.setLayout(layout)
        
    def setup_template_group(self):
        """Configura o grupo de controles do template"""
        group = QGroupBox("Template")
        layout = QVBoxLayout()
        
        # Tipo de documento
        doc_layout = QHBoxLayout()
        doc_layout.addWidget(QLabel("Tipo:"))
        self.doc_type = QComboBox()
        self.doc_type.currentTextChanged.connect(self.update_templates)
        doc_layout.addWidget(self.doc_type)
        
        # Nome do template
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nome:"))
        self.template_name = QLineEdit()
        name_layout.addWidget(self.template_name)
        
        layout.addLayout(doc_layout)
        layout.addLayout(name_layout)
        
        # Botões
        btn_layout = QHBoxLayout()
        
        new_btn = QPushButton("Novo")
        new_btn.clicked.connect(self.new_template)
        
        save_btn = QPushButton("Salvar")
        save_btn.clicked.connect(self.save_template)
        
        btn_layout.addWidget(new_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
        group.setLayout(layout)
        return group
        
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
        self.roi_list.clear()
        for name in sorted(self.regions.keys()):
            self.roi_list.addItem(name)

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