import cv2
import numpy as np



class ROIAdjuster:
    def __init__(self, extractor, image, doc_type=None, template_name=None):
        """
        Inicializa o ajustador de ROIs
        
        Args:
            extractor: Instância do DocumentROIExtractor
            image: Imagem a ser processada
            doc_type: Tipo do documento (opcional)
            template_name: Nome do template (opcional)
        """
        self.extractor = extractor
        self.image = image
        self.window_name = None
        self.current_roi = None
        self.editing_roi = None
        self.drag_start = None
        self.last_click_time = 0
        self.last_click_roi = None
        
        # Inicializa template e configurações
        self._setup_template(doc_type, template_name)
        
    def _setup_template(self, doc_type, template_name):
        """Configura o template e inicializa as variáveis relacionadas"""
        doc_type, template_name = self.extractor.select_template(doc_type, template_name)
        self.window_name = f"ROI Adjustment - {doc_type} - {template_name}"
        
    def handle_double_click(self, x, y, clicked_roi):
        """Gerencia o duplo clique em uma ROI"""
        if self.editing_roi == clicked_roi:
            self.editing_roi = None
            print(f"Modo de movimentação ativado para todas as ROIs")
        else:
            self.editing_roi = clicked_roi
            print(f"Modo de redimensionamento ativado para: {self.editing_roi}")

    def find_clicked_roi(self, x, y):
        """Encontra qual ROI foi clicada"""
        for name, region in self.extractor.regions.items():
            x1, y1, x2, y2 = region["coords"]
            margin = 5
            if (x1-margin) <= x <= (x2+margin) and (y1-margin) <= y <= (y2+margin):
                return name
        return None

    def handle_mouse_down(self, x, y):
        """Processa o evento de clique do mouse"""
        clicked_roi = self.find_clicked_roi(x, y)
        
        current_time = cv2.getTickCount() / cv2.getTickFrequency()
        if clicked_roi == self.last_click_roi and (current_time - self.last_click_time) < 0.3:
            self.handle_double_click(x, y, clicked_roi)
            self.last_click_time = 0
        else:
            self.last_click_roi = clicked_roi
            self.last_click_time = current_time

            if clicked_roi:
                self.current_roi = clicked_roi
                if self.editing_roi == clicked_roi:
                    self.setup_resize_handles(x, y, clicked_roi)
                else:
                    self.setup_move_handles(x, y, clicked_roi)

    def setup_resize_handles(self, x, y, roi_name):
        """Configura as alças de redimensionamento"""
        x1, y1, x2, y2 = self.extractor.regions[roi_name]["coords"]
        edge_size = 10
        if (abs(x - x1) < edge_size and abs(y - y1) < edge_size):
            self.drag_start = "topleft"
        elif (abs(x - x2) < edge_size and abs(y - y1) < edge_size):
            self.drag_start = "topright"
        elif (abs(x - x1) < edge_size and abs(y - y2) < edge_size):
            self.drag_start = "bottomleft"
        elif (abs(x - x2) < edge_size and abs(y - y2) < edge_size):
            self.drag_start = "bottomright"

    def setup_move_handles(self, x, y, roi_name):
        """Configura as alças de movimento"""
        x1, y1, x2, y2 = self.extractor.regions[roi_name]["coords"]
        self.drag_start = (x - x1, y - y1)

    def handle_mouse_move(self, x, y):
        """Processa o movimento do mouse durante o arrasto"""
        if not (self.current_roi and self.drag_start):
            return

        x1, y1, x2, y2 = self.extractor.regions[self.current_roi]["coords"]
        
        if self.editing_roi == self.current_roi:
            self.handle_resize(x, y, x1, y1, x2, y2)
        else:
            self.handle_move(x, y, x1, y1, x2, y2)

    def handle_resize(self, x, y, x1, y1, x2, y2):
        """Processa o redimensionamento de uma ROI"""
        min_size = 20
        if isinstance(self.drag_start, str):
            if self.drag_start == "topleft":
                x1 = min(x, x2 - min_size)
                y1 = min(y, y2 - min_size)
            elif self.drag_start == "topright":
                x2 = max(x, x1 + min_size)
                y1 = min(y, y2 - min_size)
            elif self.drag_start == "bottomleft":
                x1 = min(x, x2 - min_size)
                y2 = max(y, y1 + min_size)
            elif self.drag_start == "bottomright":
                x2 = max(x, x1 + min_size)
                y2 = max(y, y1 + min_size)
        
        self.update_roi_coords(x1, y1, x2, y2)

    def handle_move(self, x, y, x1, y1, x2, y2):
        """Processa o movimento de uma ROI"""
        width = x2 - x1
        height = y2 - y1
        new_x1 = x - self.drag_start[0]
        new_y1 = y - self.drag_start[1]
        new_x2 = new_x1 + width
        new_y2 = new_y1 + height

        if new_x1 < 0:
            new_x1 = 0
            new_x2 = width
        if new_y1 < 0:
            new_y1 = 0
            new_y2 = height
        if new_x2 > self.extractor.target_width:
            new_x2 = self.extractor.target_width
            new_x1 = new_x2 - width
        if new_y2 > self.extractor.target_height:
            new_y2 = self.extractor.target_height
            new_y1 = new_y2 - height

        self.update_roi_coords(new_x1, new_y1, new_x2, new_y2)

    def update_roi_coords(self, x1, y1, x2, y2):
        """Atualiza as coordenadas de uma ROI com limites seguros"""
        x1 = max(0, min(x1, self.extractor.target_width))
        y1 = max(0, min(y1, self.extractor.target_height))
        x2 = max(0, min(x2, self.extractor.target_width))
        y2 = max(0, min(y2, self.extractor.target_height))
        
        self.extractor.regions[self.current_roi]["coords"] = (int(x1), int(y1), int(x2), int(y2))

    def handle_mouse_up(self):
        """Processa o evento de soltar o botão do mouse"""
        self.current_roi = None
        self.drag_start = None

    def draw_regions(self, img):
        """Desenha as ROIs e alças de redimensionamento"""
        for name, region in self.extractor.regions.items():
            x1, y1, x2, y2 = region["coords"]
            color = region["color"]
            
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            cv2.putText(img, f"{name}", (x1, y1-5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            if name == self.editing_roi:
                self.draw_resize_handles(img, x1, y1, x2, y2, color)

    def draw_resize_handles(self, img, x1, y1, x2, y2, color):
        """Desenha as alças de redimensionamento para uma ROI"""
        handle_size = 5
        cv2.rectangle(img, (x1-handle_size, y1-handle_size), 
                     (x1+handle_size, y1+handle_size), color, -1)
        cv2.rectangle(img, (x2-handle_size, y1-handle_size),
                     (x2+handle_size, y1+handle_size), color, -1)
        cv2.rectangle(img, (x1-handle_size, y2-handle_size),
                     (x1+handle_size, y2+handle_size), color, -1)
        cv2.rectangle(img, (x2-handle_size, y2-handle_size),
                     (x2+handle_size, y2+handle_size), color, -1)

    def add_new_roi(self):
        """Adiciona uma nova ROI"""
        print("\nAdicionando nova ROI")
        name = input("Nome da ROI: ").strip().upper()
        if not name:
            print("Nome inválido!")
            return
        
        if name in self.extractor.regions:
            print("ROI com este nome já existe!")
            return
            
        print("\nTipos disponíveis:")
        print("1. text")
        print("2. cpf")
        print("3. number")
        print("4. currency")
        print("5. date")
        
        type_choice = input("Escolha o tipo (1-5): ").strip()
        type_map = {
            "1": "text",
            "2": "cpf",
            "3": "number",
            "4": "currency",
            "5": "date"
        }
        
        if type_choice not in type_map:
            print("Tipo inválido!")
            return
            
        expected_type = type_map[type_choice]
        
        center_x = self.extractor.target_width // 2
        center_y = self.extractor.target_height // 2
        width = 200
        height = 30
        
        color = (
            np.random.randint(0, 255),
            np.random.randint(0, 255),
            np.random.randint(0, 255)
        )
        
        self.extractor.regions[name] = {
            "coords": (
                center_x - width//2,
                center_y - height//2,
                center_x + width//2,
                center_y + height//2
            ),
            "color": color,
            "expected_type": expected_type
        }
        
        print(f"\nROI '{name}' adicionada! Use o mouse para ajustar sua posição.")

    def save_template(self):
        """Salva o template atual"""
        try:
            self.extractor.template_manager.create_template(
                self.extractor.current_doc_type, 
                self.extractor.current_template_name, 
                self.extractor.regions
            )
            print(f"\nTemplate '{self.extractor.current_template_name}' salvo com sucesso!")
            
            with open('roi_coordinates.txt', 'w') as f:
                f.write(f"Documento: {self.extractor.current_doc_type}\n")
                f.write(f"Template: {self.extractor.current_template_name}\n\n")
                for name, region in self.extractor.regions.items():
                    f.write(f"{name}: {region['coords']}\n")
            print("Coordenadas salvas em 'roi_coordinates.txt'")
            
        except Exception as e:
            print(f"Erro ao salvar template: {e}")

    def draw_grid(self, img):
        """Desenha o grid de referência na imagem"""
        grid_color = (128, 128, 128)
        
        for x in range(0, self.extractor.target_width, 100):
            cv2.line(img, (x, 0), (x, self.extractor.target_height), grid_color, 1)
            if x % 500 == 0:
                cv2.putText(img, str(x), (x, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, grid_color, 2)
        
        for y in range(0, self.extractor.target_height, 100):
            cv2.line(img, (0, y), (self.extractor.target_width, y), grid_color, 1)
            if y % 500 == 0:
                cv2.putText(img, str(y), (10, y), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, grid_color, 2)

    def mouse_callback(self, event, x, y, flags, param):
        """Callback para eventos do mouse"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.handle_mouse_down(x, y)
        elif event == cv2.EVENT_MOUSEMOVE and flags == cv2.EVENT_FLAG_LBUTTON:
            self.handle_mouse_move(x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self.handle_mouse_up()

    def run(self):
        """Executa o ajuste interativo das ROIs"""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO)
        cv2.resizeWindow(self.window_name, 1200, 800)
        cv2.setMouseCallback(self.window_name, lambda e, x, y, f, p: self.mouse_callback(e, x, y, f, p))

        print("\nInstruções:")
        print("- Clique e arraste os retângulos para movê-los")
        print("- Dê um duplo clique em um retângulo para ativar o modo de redimensionamento")
        print("- No modo de redimensionamento, arraste os quadradinhos nos cantos")
        print("- Dê outro duplo clique para voltar ao modo de movimento")
        print("- Pressione 'a' para adicionar uma nova ROI")
        print("- Pressione 's' para salvar o template")
        print("- Pressione 'q' quando terminar o ajuste")

        while True:
            debug_img = self.image.copy()
            self.draw_grid(debug_img)
            self.draw_regions(debug_img)
            cv2.imshow(self.window_name, debug_img)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\nCoordenadas finais:")
                for name, region in self.extractor.regions.items():
                    print(f"{name}: {region['coords']}")
                break
            
            elif key == ord('s'):
                self.save_template()
            
            elif key == ord('a'):
                self.add_new_roi()

        cv2.destroyAllWindows()
        return self.extractor.regions