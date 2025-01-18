import cv2
import numpy as np
import os
import pytesseract
from pathlib import Path
import matplotlib.pyplot as plt
import json
import csv
import re

def manage_templates():
    template_manager = TemplateManager()
    extractor = DocumentROIExtractor(template_manager)
    
    while True:
        print("\n=== Gerenciamento de Templates ===")
        print("1. Criar novo template")
        print("2. Editar template existente")
        print("3. Visualizar templates")
        print("4. Excluir template")
        print("5. Sair")
        
        try:
            choice = input("\nEscolha uma opção: ").strip()
            
            if choice == "1":
                doc_type = input("Tipo de documento (ex: nota_de_empenho): ").strip()
                if not doc_type:
                    print("Tipo de documento não pode ser vazio!")
                    continue
                    
                template_name = input("Nome do template: ").strip()
                if not template_name:
                    print("Nome do template não pode ser vazio!")
                    continue
                
                # Iniciar processo interativo de definição de regiões
                print("\nAjuste as regiões interativamente...")
                
                # Selecionar imagem para calibração
                image_path = input("\nCaminho da imagem para calibração: ").strip()
                if not os.path.exists(image_path):
                    print("Erro: Arquivo não encontrado.")
                    continue
                
                img = cv2.imread(image_path)
                if img is None:
                    print("Erro ao carregar a imagem.")
                    continue

                try:
                    standardized_img = extractor.standardize_image(img)
                    # Passa o doc_type e template_name para o ajuste interativo
                    regions = extractor.interactive_roi_adjustment(
                        standardized_img, 
                        doc_type=doc_type, 
                        template_name=template_name
                    )
                    print(f"\nTemplate '{template_name}' criado com sucesso!")
                except Exception as e:
                    print(f"Erro ao ajustar regiões interativas: {e}")
                
            elif choice == "2":
                if template_manager.list_templates():
                    doc_type = input("\nTipo de documento: ").strip()
                    template_name = input("Nome do template: ").strip()
                    
                    # Verificar se o template existe
                    if doc_type in template_manager.templates and \
                       template_name in template_manager.templates[doc_type]:
                        
                        # Selecionar imagem para edição
                        image_path = input("\nCaminho da imagem para calibração: ").strip()
                        if not os.path.exists(image_path):
                            print("Erro: Arquivo não encontrado.")
                            continue
                        
                        img = cv2.imread(image_path)
                        if img is None:
                            print("Erro ao carregar a imagem.")
                            continue

                        try:
                            standardized_img = extractor.standardize_image(img)
                            # Passa o doc_type e template_name para edição
                            regions = extractor.interactive_roi_adjustment(
                                standardized_img, 
                                doc_type=doc_type, 
                                template_name=template_name
                            )
                            print(f"\nTemplate '{template_name}' atualizado com sucesso!")
                        except Exception as e:
                            print(f"Erro ao ajustar regiões interativas: {e}")
                    else:
                        print(f"Erro: Template '{template_name}' não encontrado.")
                
            elif choice == "3":
                if not template_manager.list_templates():
                    print("Nenhum template disponível.")
                input("\nPressione Enter para continuar...")
                
            elif choice == "4":
                if template_manager.list_templates():
                    doc_type = input("\nTipo de documento: ").strip()
                    template_name = input("Nome do template: ").strip()
                    if not template_manager.delete_template(doc_type, template_name):
                        print(f"Erro: Template '{template_name}' não encontrado.")
                    else:
                        print(f"Template '{template_name}' excluído com sucesso!")
                
            elif choice == "5":
                print("\nVoltando ao menu principal...")
                break
                
            else:
                print("\nOpção inválida! Por favor, escolha uma opção entre 1 e 5.")
                
        except Exception as e:
            print(f"\nErro inesperado: {e}")
            print("Por favor, tente novamente.")


class DocumentROIExtractor:
    def __init__(self, template_manager=None):
        """
        Inicializa o extrator com um gerenciador de templates opcional
        """
        self.template_manager = template_manager or TemplateManager()
        self.current_doc_type = None
        self.current_template_name = None
        
        self.target_width = 1654
        self.target_height = 2339
    
        self.tesseract_config = {
            "text": "--psm 6 --oem 3",
            "cpf": "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.-/",
            "number": "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.",
            "currency": "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789,.",
            "date": "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789/"
        }
            
        # Regiões padrão como fallback
        self.default_regions = {
            "PERITO": {
                "coords": (350, 310, 800, 340),  # Ajustei para suas coordenadas originais
                "color": (0, 0, 255),
                "expected_type": "text"
            },
            "CPF": {
                "coords": (350, 340, 500, 370),  # Ajustei para suas coordenadas originais
                "color": (0, 255, 0),
                "expected_type": "cpf"
            },
            "PROCESSO": {
                "coords": (500, 340, 700, 370),  # Ajustei para suas coordenadas originais 
                "color": (0, 255, 255),
                "expected_type": "number"
            },
            "VALOR": {
                "coords": (900, 310, 1050, 340),
                "color": (255, 0, 0),
                "expected_type": "currency"
            },
            "DATA": {
                "coords": (900, 280, 1050, 310),
                "color": (255, 165, 0),
                "expected_type": "date"
            }
        }
            
       
    def load_template_regions(self, doc_type, template_name):
        """Carrega as regiões de um template específico"""
        templates = self.template_manager.get_template(doc_type)
        if templates and template_name in templates:
            self.regions = templates[template_name]["regions"]
            return True
        return False

    def extract_text_from_roi(self, roi, expected_type):
        """Extrai texto de uma ROI usando OCR com múltiplas tentativas"""
     #   print(f"Chama a função extract_text_from_roi")
        try:
            # Lista para armazenar resultados de diferentes tentativas
            results = []
            
            # Primeira tentativa: imagem original pré-processada
            processed_roi = self.preprocess_roi(roi, expected_type)
            text1 = pytesseract.image_to_string(
                processed_roi,
                lang='por',  # Usar ambos os modelos
                config=self.tesseract_config[expected_type]
            ).strip()
            results.append(text1)
            
            # Segunda tentativa: inverter cores
            inverted_roi = cv2.bitwise_not(processed_roi)
            text2 = pytesseract.image_to_string(
                inverted_roi,
                lang='por',
                config=self.tesseract_config[expected_type]
            ).strip()
            results.append(text2)
            
            # Terceira tentativa: aumentar contraste
            contrasted = cv2.convertScaleAbs(processed_roi, alpha=1.5, beta=0)
            text3 = pytesseract.image_to_string(
                contrasted,
                lang='por',
                config=self.tesseract_config[expected_type]
            ).strip()
            results.append(text3)
            
            # Escolher o melhor resultado
            best_text = self.choose_best_result(results, expected_type)
            
            # Pós-processamento específico por tipo
            cleaned_text = self.post_process_text(best_text, expected_type)
            
            return cleaned_text
            
        except Exception as e:
            print(f"Erro na extração de texto: {e}")
            return ""

    def choose_best_result(self, results, expected_type):
        """Escolhe o melhor resultado entre várias tentativas"""
       # print(f"Chamada a função choose_best_result")
        # Remover resultados vazios
        valid_results = [r for r in results if r.strip()]
        if not valid_results:
            return ""
            
        if expected_type == "cpf":
            # Escolher o que tem mais números
            return max(valid_results, key=lambda x: len([c for c in x if c.isdigit()]))
            
        elif expected_type == "date":
            # Escolher o que mais se parece com uma data
            for result in valid_results:
                if re.search(r'\d{2}/\d{2}/\d{2,4}', result):
                    return result
            return valid_results[0]
            
        elif expected_type in ["number", "currency"]:
            # Escolher o que tem mais números
            return max(valid_results, key=lambda x: len([c for c in x if c.isdigit()]))
            
        # Para texto, escolher o mais longo que não seja só números
        text_results = [r for r in valid_results if not r.replace('.','').replace(',','').isdigit()]
        if text_results:
            return max(text_results, key=len)
        return valid_results[0]

    def post_process_text(self, text, expected_type):
        """Limpa e formata o texto extraído"""
       # print(f"Texto extraído: {text}")
        if not text:
            return ""
            
        # Remover caracteres indesejados
        text = re.sub(r'[^\w\s./,-]', '', text)
        
        if expected_type == "cpf":
            # Manter apenas números e formatação de CPF
            nums = ''.join(filter(str.isdigit, text))
            if len(nums) == 11:
                return f"{nums[:3]}.{nums[3:6]}.{nums[6:9]}-{nums[9:]}"
            return nums
            
        elif expected_type == "date":
            # Tentar formatar como data
            match = re.search(r'(\d{2})/(\d{2})/(\d{2,4})', text)
            if match:
                day, month, year = match.groups()
                if len(year) == 2:
                    year = '20' + year
                return f"{day}/{month}/{year}"
            return text
            
        elif expected_type == "currency":
            # Formatar valor monetário
            nums = ''.join(filter(lambda x: x.isdigit() or x in ',.', text))
            if ',' not in nums:
                nums = nums[:-2] + ',' + nums[-2:]
            return nums
            
        elif expected_type == "number":
            # Manter apenas números e pontos
            return ''.join(filter(lambda x: x.isdigit() or x == '.', text))
            
        # Para texto normal, apenas limpar espaços extras
        return ' '.join(text.split())

    def validate_field(self, text, expected_type):
        """Valida se o texto extraído corresponde ao tipo esperado"""
      #  print(f"Validando texto: {text} como tipo: {expected_type}")
        if not text:
            return False
            
        if expected_type == "cpf":
            # Valida CPF/CNPJ - deve ter 11 ou 14 dígitos
            nums = ''.join(filter(str.isdigit, text))
            return len(nums) in [11, 14]
            
        elif expected_type == "date":
            # Valida data - deve ter formato DD/MM/YY ou DD/MM/YYYY
            import re
            pattern = r'\d{2}/\d{2}/(\d{2}|\d{4})'
            return bool(re.search(pattern, text))
            
        elif expected_type == "currency":
            # Valida moeda - deve ter números e vírgula
            import re
            pattern = r'\d+,\d{2}'
            return bool(re.search(pattern, text))
            
        elif expected_type == "number":
            # Valida número - deve ter pelo menos um dígito
            return any(char.isdigit() for char in text)
            
        # Para tipo "text", qualquer string não vazia é válida
        return bool(text.strip())

    def standardize_image(self, image):
        """
        Padroniza o tamanho da imagem para as dimensões desejadas e melhora a qualidade.
        """
        try:
            # Verificar se a imagem foi carregada corretamente
            if image is None:
                raise ValueError("A imagem fornecida é nula ou inválida.")
            
            # Verificar se a imagem já está em escala de cinza
            if len(image.shape) == 3:  # Se tem 3 canais (BGR)
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:  # Se já está em escala de cinza
                gray = image
            
            # Redimensionar para o tamanho padrão usando interpolação cúbica para manter qualidade
            resized = cv2.resize(
                gray, 
                (self.target_width, self.target_height), 
                interpolation=cv2.INTER_CUBIC
            )
            
            # Converter de volta para o formato BGR para compatibilidade com funções de visualização ou processamento
            standardized = cv2.cvtColor(resized, cv2.COLOR_GRAY2BGR)
            
            return standardized
        except cv2.error as cv_error:
            print(f"Erro do OpenCV na padronização da imagem: {cv_error}")
            return image
        except Exception as e:
            print(f"Erro inesperado na padronização da imagem: {e}")
            return image

        
    def preprocess_roi(self, roi, expected_type):
        """Pré-processamento avançado para cada tipo de ROI"""
        try:
            # Verificar o número de canais da imagem
            if len(roi.shape) == 3:  # Se a imagem tem 3 canais (BGR)
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            else:  # Se já está em escala de cinza
                gray = roi
            
            # Aumentar resolução (pode ajudar em textos pequenos)
            scale_factor = 8
            enlarged = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, 
                                interpolation=cv2.INTER_CUBIC)
            
            # Remover ruído com filtro bilateral (preserva bordas)
            denoised = cv2.bilateralFilter(enlarged, 9, 75, 75)
            
            # Salvar imagem intermediária para debug
            debug_path = f"debug_roi_{expected_type}.png"
            cv2.imwrite(debug_path, denoised)
            
            return denoised
            
        except Exception as e:
            print(f"Erro no pré-processamento: {e}")
            return roi

    def validate_roi_position(self, image):
        """Função para validar visualmente a posição das ROIs na imagem padronizada"""
       # print("chamada a função validate_roi_position")
        debug_img = image.copy()
        
        # Adicionar grid de referência
        grid_color = (128, 128, 128)
        for x in range(0, self.target_width, 100):
            cv2.line(debug_img, (x, 0), (x, self.target_height), grid_color, 1)
            if x % 500 == 0:
                cv2.putText(debug_img, str(x), (x, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, grid_color, 2)
        
        for y in range(0, self.target_height, 100):
            cv2.line(debug_img, (0, y), (self.target_width, y), grid_color, 1)
            if y % 500 == 0:
                cv2.putText(debug_img, str(y), (10, y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, grid_color, 2)
        
        # Desenhando ROIs
        for name, region in self.regions.items():
            x1, y1, x2, y2 = region["coords"]
            cv2.rectangle(debug_img, (x1, y1), (x2, y2), region["color"], 2)
            cv2.putText(debug_img, f"{name}", (x1, y1-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, region["color"], 2)
        
        return debug_img

    def process_directory(self, input_dir, output_dir, append=True, doc_type=None):
        try:
            input_path = Path(input_dir)
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Define the consolidated CSV file path
            consolidated_csv_path = output_path / "resultados_consolidados.csv"
            field_order = ['PERITO', 'CPF', 'PROCESSO', 'VALOR', 'DATA']

            if append:
                if not consolidated_csv_path.exists():
                    with open(consolidated_csv_path, 'w', encoding='utf-8', newline='') as f:
                        writer = csv.writer(f, delimiter=';')
                        writer.writerow(field_order)
                    print(f"Arquivo consolidado criado: {consolidated_csv_path}")

            # Process each image
            image_files = list(input_path.glob("*.png")) + list(input_path.glob("*.jpg"))

            if not image_files:
                print(f"Sem imagens em {input_dir}.")
                return None

            print(f"Processando {len(image_files)} imagens de {input_dir}...")
            
            # Adicionar barra de progresso
            for i, img_path in enumerate(sorted(image_files)):
                print(f"\nProcessando [{i+1}/{len(image_files)}]: {img_path.name}")
                try:
                    # Process each image using the document type
                    results = self.process_image(img_path, output_path, doc_type=doc_type)
                    if results:
                        if append:
                            self.save_results(
                                results,
                                consolidated_csv_path.parent,
                                consolidated_csv_path.name,
                                field_order,
                                append=True
                            )
                            # Mostrar os resultados extraídos
                            print("Resultados extraídos:")
                            for field, value in results.items():
                                print(f"  {field}: {value}")
                    print(f"Processamento concluído: {img_path.name}")
                except Exception as e:
                    print(f"Erro ao processar {img_path}: {e}")

            if append:
                print(f"\nResultados consolidados salvos em: {consolidated_csv_path}")
                return consolidated_csv_path
            else:
                print(f"\nResultados individuais salvos em: {output_path}")
                return output_path
                
        except Exception as e:
            print(f"Erro ao processar diretório: {e}")
            return None

    def process_image(self, image_path, output_dir, doc_type=None):
        """Processes a single image using the specified document type."""
        try:
            # Load the image
            img = cv2.imread(str(image_path))
            if img is None:
                raise ValueError(f"Não foi possível ler a imagem: {image_path}")

            # Standardize the image
            print("Normalizando imagem...")
            standardized_img = self.standardize_image(img)

            results = {}
            # Processamento direto usando as regiões definidas
            for name, region in self.regions.items():
                try:
                    # Debug de extração
                    print(f"Extraindo {name}...")
                    roi = self.extract_roi(standardized_img, region["coords"])
                    
                    # Debug de pré-processamento
                    print(f"Pré-processando {name}...")
                    processed_roi = self.preprocess_roi(roi, region["expected_type"])
                    
                    # Debug de OCR
                    print(f"Aplicando OCR em {name}...")
                    text = self.extract_text_from_roi(processed_roi, region["expected_type"])
                    results[name] = text.strip()
                    print(f"{name}: {text.strip()}")
                    
                except Exception as e:
                    print(f"Erro ao processar {name}: {e}")
                    results[name] = ""

            return results
        except Exception as e:
            print(f"Erro ao processar {image_path}: {e}")
            return None


    def save_results(self, results, output_dir, file_name="ocr_results.csv", field_order=None, append=True):
        """
        Saves OCR results to a CSV file.
        
        Args:
            results (dict): Dictionary containing OCR results.
            output_dir (str or Path): Directory to save the results.
            file_name (str): Name of the CSV file. Default is "ocr_results.csv".
            field_order (list): List of fields to include in the CSV. Default is standard fields.
            append (bool): Whether to append to an existing file. If False, overwrites the file.
            
        Returns:
            Path: Path to the saved CSV file, or None if an error occurs.
        """
        try:
            # Ensure output directory exists
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Default field order
            if field_order is None:
                field_order = ['PERITO', 'CPF', 'PROCESSO', 'VALOR', 'DATA']

            # Path to the CSV file
            csv_path = output_dir / file_name

            # Determine write mode
            mode = 'a' if append else 'w'
            write_header = not csv_path.exists() or not append

            # Open and write to the CSV file
            with open(csv_path, mode, encoding='utf-8', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                if write_header:  # Write header only if needed
                    writer.writerow(field_order)
                
                # Ensure all fields are included, even if missing in results
                row = [results.get(field, '') for field in field_order]
                writer.writerow(row)

            print(f"Results saved in: {csv_path} (Append={append})")
            return csv_path
        except Exception as e:
            print(f"Error saving results to {output_dir}/{file_name}: {e}")
            return None



    def debug_roi(self, image, region_name):
        """Método para debug de uma ROI específica"""
       # print(f"chamada a função debug_roi")
        if region_name not in self.regions:
            print(f"Região {region_name} não encontrada")
            return
            
        region = self.regions[region_name]
        roi = self.extract_roi(image, region["coords"])
        
        plt.figure(figsize=(10, 5))
        plt.subplot(121)
        plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        x1, y1, x2, y2 = region["coords"]
        plt.gca().add_patch(plt.Rectangle((x1, y1), x2-x1, y2-y1, 
                                        fill=False, color='red', linewidth=2))
        plt.title("Imagem Original com ROI")
        
        plt.subplot(122)
        plt.imshow(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
        plt.title(f"ROI Extraída: {region_name}")
        plt.show()
        
    def extract_roi(self, image, coords):
        """Extrai uma ROI específica da imagem"""
        #print(f"chamada a função extract_roi")
        try:
            x1, y1, x2, y2 = coords
            # Garantir que as coordenadas estão dentro dos limites da imagem
            height, width = image.shape[:2]
            x1 = max(0, min(x1, width))
            x2 = max(0, min(x2, width))
            y1 = max(0, min(y1, height))
            y2 = max(0, min(y2, height))
            
            # Verificar se a região é válida
            if x1 >= x2 or y1 >= y2:
                raise ValueError(f"Coordenadas inválidas: ({x1}, {y1}, {x2}, {y2})")
                
            # Extrair a região
            roi = image[y1:y2, x1:x2]
            
            # Verificar se a ROI não está vazia
            if roi.size == 0:
                raise ValueError("ROI extraída está vazia")
                
            return roi
        except Exception as e:
            print(f"Erro ao extrair ROI {coords}: {e}")
            # Retornar uma pequena imagem preta em caso de erro
            return np.zeros((10, 10, 3), dtype=np.uint8)
    
    def validate_result(self, text, expected_type):
        """Valida o resultado do OCR baseado no tipo esperado"""
      #  print(f"Chamada a função validate_result")
        if not text:
            return False, "Texto vazio"
            
        if expected_type == "cpf":
            # Remover caracteres não numéricos
            nums = ''.join(filter(str.isdigit, text))
            return len(nums) in [11, 14], nums  # 11 para CPF, 14 para CNPJ
            
        elif expected_type == "date":
            # Verificar se tem formato de data
            import re
            pattern = r'\d{2}/\d{2}/\d{2}'
            match = re.search(pattern, text)
            return bool(match), match.group(0) if match else text
            
        elif expected_type == "currency":
            # Verificar se tem formato de valor monetário
            import re
            pattern = r'\d+,\d{2}'
            match = re.search(pattern, text)
            return bool(match), match.group(0) if match else text
            
        elif expected_type == "number":
            # Verificar se tem números
            has_numbers = any(char.isdigit() for char in text)
            return has_numbers, text
            
        return True, text
            
 
    def interactive_roi_adjustment(self, image):
        """Permite ajuste interativo das ROIs com alternância entre mover e redimensionar"""
        window_name = "ROI Adjustment"
        current_roi = None
        editing_roi = None  # ROI em modo de edição (com alças para redimensionamento)
        drag_start = None
        last_click_time = 0  # Para detectar duplo clique
        last_click_roi = None  # Para identificar em qual ROI foi o duplo clique

        def handle_double_click(x, y, clicked_roi):
            """Gerencia o duplo clique em uma ROI"""
            nonlocal editing_roi
            if editing_roi == clicked_roi:
                editing_roi = None
                print(f"Modo de movimentação ativado para todas as ROIs")
            else:
                editing_roi = clicked_roi
                print(f"Modo de redimensionamento ativado para: {editing_roi}")

        def find_clicked_roi(x, y):
            """Encontra qual ROI foi clicada"""
            for name, region in self.regions.items():
                x1, y1, x2, y2 = region["coords"]
                margin = 5
                if (x1-margin) <= x <= (x2+margin) and (y1-margin) <= y <= (y2+margin):
                    return name
            return None

        def mouse_callback(event, x, y, flags, param):
            """Callback de mouse para interação com a janela"""
            nonlocal current_roi, drag_start, last_click_time, last_click_roi, editing_roi

            if event == cv2.EVENT_LBUTTONDOWN:
                clicked_roi = find_clicked_roi(x, y)
                
                current_time = cv2.getTickCount() / cv2.getTickFrequency()
                if clicked_roi == last_click_roi and (current_time - last_click_time) < 0.3:
                    handle_double_click(x, y, clicked_roi)
                    last_click_time = 0
                else:
                    last_click_roi = clicked_roi
                    last_click_time = current_time

                    if clicked_roi:
                        current_roi = clicked_roi
                        if editing_roi == clicked_roi:
                            x1, y1, x2, y2 = self.regions[clicked_roi]["coords"]
                            edge_size = 10
                            if (abs(x - x1) < edge_size and abs(y - y1) < edge_size):
                                drag_start = "topleft"
                            elif (abs(x - x2) < edge_size and abs(y - y1) < edge_size):
                                drag_start = "topright"
                            elif (abs(x - x1) < edge_size and abs(y - y2) < edge_size):
                                drag_start = "bottomleft"
                            elif (abs(x - x2) < edge_size and abs(y - y2) < edge_size):
                                drag_start = "bottomright"
                        else:
                            x1, y1, x2, y2 = self.regions[clicked_roi]["coords"]
                            drag_start = (x - x1, y - y1)

            elif event == cv2.EVENT_MOUSEMOVE and flags == cv2.EVENT_FLAG_LBUTTON:
                if current_roi and drag_start:
                    x1, y1, x2, y2 = self.regions[current_roi]["coords"]
                    
                    if editing_roi == current_roi:
                        min_size = 20
                        if isinstance(drag_start, str):
                            if drag_start == "topleft":
                                x1 = min(x, x2 - min_size)
                                y1 = min(y, y2 - min_size)
                            elif drag_start == "topright":
                                x2 = max(x, x1 + min_size)
                                y1 = min(y, y2 - min_size)
                            elif drag_start == "bottomleft":
                                x1 = min(x, x2 - min_size)
                                y2 = max(y, y1 + min_size)
                            elif drag_start == "bottomright":
                                x2 = max(x, x1 + min_size)
                                y2 = max(y, y1 + min_size)
                    else:
                        width = x2 - x1
                        height = y2 - y1
                        new_x1 = x - drag_start[0]
                        new_y1 = y - drag_start[1]
                        new_x2 = new_x1 + width
                        new_y2 = new_y1 + height

                        if new_x1 < 0:
                            new_x1 = 0
                            new_x2 = width
                        if new_y1 < 0:
                            new_y1 = 0
                            new_y2 = height
                        if new_x2 > self.target_width:
                            new_x2 = self.target_width
                            new_x1 = new_x2 - width
                        if new_y2 > self.target_height:
                            new_y2 = self.target_height
                            new_y1 = new_y2 - height

                        x1, y1, x2, y2 = new_x1, new_y1, new_x2, new_y2

                    x1 = max(0, min(x1, self.target_width))
                    y1 = max(0, min(y1, self.target_height))
                    x2 = max(0, min(x2, self.target_width))
                    y2 = max(0, min(y2, self.target_height))
                    
                    self.regions[current_roi]["coords"] = (int(x1), int(y1), int(x2), int(y2))

            elif event == cv2.EVENT_LBUTTONUP:
                current_roi = None
                drag_start = None

        def draw_regions(img):
            """Desenha as ROIs e alças de redimensionamento quando apropriado"""
            for name, region in self.regions.items():
                x1, y1, x2, y2 = region["coords"]
                color = region["color"]
                
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                cv2.putText(img, f"{name}", (x1, y1-5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                
                if name == editing_roi:
                    handle_size = 5
                    cv2.rectangle(img, (x1-handle_size, y1-handle_size), 
                                (x1+handle_size, y1+handle_size), color, -1)
                    cv2.rectangle(img, (x2-handle_size, y1-handle_size),
                                (x2+handle_size, y1+handle_size), color, -1)
                    cv2.rectangle(img, (x1-handle_size, y2-handle_size),
                                (x1+handle_size, y2+handle_size), color, -1)
                    cv2.rectangle(img, (x2-handle_size, y2-handle_size),
                                (x2+handle_size, y2+handle_size), color, -1)

        def add_new_roi():
            """Adiciona uma nova ROI"""
            print("\nAdicionando nova ROI")
            name = input("Nome da ROI: ").strip().upper()
            if not name:
                print("Nome inválido!")
                return
            
            if name in self.regions:
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
            
            # Criar ROI com coordenadas padrão no centro da imagem
            center_x = self.target_width // 2
            center_y = self.target_height // 2
            width = 200
            height = 30
            
            color = (
                np.random.randint(0, 255),
                np.random.randint(0, 255),
                np.random.randint(0, 255)
            )
            
            self.regions[name] = {
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

        def save_template():
            """Salva o template atual"""
            try:
                # Salvar no gerenciador de templates
                self.template_manager.create_template(self.current_doc_type, self.current_template_name, self.regions)
                print(f"\nTemplate '{self.current_template_name}' salvo com sucesso!")
                
                # Salvar também em arquivo de texto para referência
                with open('roi_coordinates.txt', 'w') as f:
                    f.write(f"Documento: {self.current_doc_type}\n")
                    f.write(f"Template: {self.current_template_name}\n\n")
                    for name, region in self.regions.items():
                        f.write(f"{name}: {region['coords']}\n")
                print("Coordenadas salvas em 'roi_coordinates.txt'")
                
            except Exception as e:
                print(f"Erro ao salvar template: {e}")

        # Configuração da janela
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO)
        cv2.resizeWindow(window_name, 1200, 800)
        cv2.setMouseCallback(window_name, mouse_callback)

        print("\nInstruções:")
        print("- Clique e arraste os retângulos para movê-los")
        print("- Dê um duplo clique em um retângulo para ativar o modo de redimensionamento")
        print("- No modo de redimensionamento, arraste os quadradinhos nos cantos")
        print("- Dê outro duplo clique para voltar ao modo de movimento")
        print("- Pressione 'a' para adicionar uma nova ROI")
        print("- Pressione 's' para salvar as coordenadas atuais")
        print("- Pressione 'q' quando terminar o ajuste")

        while True:
            debug_img = image.copy()
            # Adicionar grid de referência
            grid_color = (128, 128, 128)
            for x in range(0, self.target_width, 100):
                cv2.line(debug_img, (x, 0), (x, self.target_height), grid_color, 1)
                if x % 500 == 0:
                    cv2.putText(debug_img, str(x), (x, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, grid_color, 2)
            
            for y in range(0, self.target_height, 100):
                cv2.line(debug_img, (0, y), (self.target_width, y), grid_color, 1)
                if y % 500 == 0:
                    cv2.putText(debug_img, str(y), (10, y), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, grid_color, 2)

            draw_regions(debug_img)
            cv2.imshow(window_name, debug_img)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\nCoordenadas finais salvas:")
                for name, region in self.regions.items():
                    print(f"{name}: {region['coords']}")
                break
            
            elif key == ord('s'):
          
          
                print("\nCoordenadas atuais:")
                for name, region in self.regions.items():
                    print(f"{name}: {region['coords']}")
                with open('roi_coordinates.txt', 'w') as f:
                    for name, region in self.regions.items():
                        f.write(f"{name}: {region['coords']}\n")
            
            
            
                print("\nCoordenadas salvas em 'roi_coordinates.txt'")
            elif key == ord('a'):
                add_new_roi()

        cv2.destroyAllWindows()
        return self.regions



    def select_template(self, doc_type=None, template_name=None):
        """
        Seleciona um template existente ou cria um novo.
        Retorna (doc_type, template_name) selecionados.
        """
        if not doc_type:
            print("\nTemplates disponíveis:")
            self.template_manager.list_templates()
            doc_type = input("\nDigite o tipo de documento: ").strip()
        
        if not template_name:
            if doc_type in self.template_manager.templates:
                print(f"\nTemplates para {doc_type}:")
                for name in self.template_manager.templates[doc_type].keys():
                    print(f"- {name}")
                template_name = input("\nDigite o nome do template: ").strip()
            else:
                print(f"\nNenhum template encontrado para {doc_type}")
                template_name = input("Digite um nome para o novo template: ").strip()
        
        self.current_doc_type = doc_type
        self.current_template_name = template_name
        
        if (doc_type in self.template_manager.templates and 
            template_name in self.template_manager.templates[doc_type]):
            self.regions = self.template_manager.templates[doc_type][template_name]["regions"]
            print(f"\nTemplate '{template_name}' carregado com sucesso!")
        else:
            self.regions = self.default_regions.copy()
            print("\nUsando configuração padrão de regiões...")
        
        return doc_type, template_name
    
    def evaluate_template_match(self, image, template):
        """Avalia se o template corresponde bem à imagem"""
       # print(f"chamada a função evaluate_template_match")
        try:
            success_count = 0
            total_fields = len(template["regions"])
            
            for name, region in template["regions"].items():
                try:
                    # Extrair ROI
                    roi = self.extract_roi(image, region["coords"])
                    
                    # Extrair texto
                    text = self.extract_text_from_roi(roi, region["expected_type"])
                    
                    # Validar o texto extraído
                    if self.validate_field(text, region["expected_type"]):
                        success_count += 1
                        
                except Exception as e:
                    print(f"Erro ao avaliar região {name}: {e}")
                    continue
            
            # Calcular confiança (proporção de campos válidos)
            confidence = success_count / total_fields if total_fields > 0 else 0
            return confidence
            
        except Exception as e:
            print(f"Erro na avaliação do template: {e}")
            return 0

 
class TemplateManager:
    def __init__(self):
        self.templates_file = "document_templates.json"
        self.templates = self.load_templates()

    def create_template(self, doc_type, template_name, regions):
        """Creates a new template for a document type."""
        if doc_type not in self.templates:
            self.templates[doc_type] = {}

        # Garantir que cada região tenha todas as informações necessárias
        processed_regions = {}
        for name, region in regions.items():
            processed_regions[name] = {
                "coords": region["coords"],
                "color": region["color"],
                "expected_type": region["expected_type"]
            }

        self.templates[doc_type][template_name] = {
            "name": template_name,
            "regions": processed_regions,
            "confidence_threshold": 0.6
        }
        self.save_templates()
    def load_template_regions(self, doc_type, template_name):
        """
        Carrega as regiões de um template específico para self.regions
        
        Args:
            doc_type (str): Tipo do documento
            template_name (str): Nome do template
        
        Returns:
            bool: True se carregou com sucesso, False caso contrário
        """
        try:
            if not hasattr(self, 'template_manager'):
                print("Template manager não inicializado")
                return False
                
            templates = self.template_manager.templates
            if doc_type not in templates or template_name not in templates[doc_type]:
                print(f"Template {template_name} para documento tipo {doc_type} não encontrado")
                return False
                
            template = templates[doc_type][template_name]
            self.regions = template["regions"]
            print(f"Regiões do template {template_name} carregadas com sucesso")
            return True
            
        except Exception as e:
            print(f"Erro ao carregar regiões do template: {e}")
            return False

    def save_template_regions(self, doc_type, template_name):
        """
        Salva as regiões atuais no template especificado
        
        Args:
            doc_type (str): Tipo do documento
            template_name (str): Nome do template
        
        Returns:
            bool: True se salvou com sucesso, False caso contrário
        """
        try:
            if not hasattr(self, 'template_manager'):
                print("Template manager não inicializado")
                return False
                
            templates = self.template_manager.templates
            if doc_type not in templates or template_name not in templates[doc_type]:
                print(f"Template {template_name} para documento tipo {doc_type} não encontrado")
                return False
                
            templates[doc_type][template_name]["regions"] = self.regions
            self.template_manager.save_templates()
            print(f"Regiões salvas no template {template_name} com sucesso")
            return True
            
        except Exception as e:
            print(f"Erro ao salvar regiões no template: {e}")
            return False

    def load_templates(self):
        try:
            if os.path.exists(self.templates_file):
                with open(self.templates_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Erro ao carregar templates: {e}")
            return {}

    def list_templates(self):
        """Lists all available templates."""
        if not self.templates:
            print("\nNenhum template encontrado.")
            return False

        print("\n=== Templates Disponíveis ===")
        for doc_type, templates in self.templates.items():
            print(f"Tipo de Documento: {doc_type}")
            for template_name in templates:
                print(f"  - {template_name}")
        return True

    def save_templates(self):
        """Saves templates to a file."""
        try:
            with open(self.templates_file, 'w') as f:
                json.dump(self.templates, f, indent=4)
            print("Templates salvos com sucesso!")
        except Exception as e:
            print(f"Erro ao salvar templates: {e}")

    def delete_template(self, doc_type, template_name):
        """Deletes a template."""
        if doc_type in self.templates and template_name in self.templates[doc_type]:
            del self.templates[doc_type][template_name]
            if not self.templates[doc_type]:
                del self.templates[doc_type]
            self.save_templates()
            return True
        return False

    def get_template(self, doc_type):
        """Retrieves the template for a specific document type."""
        if doc_type in self.templates:
            return self.templates[doc_type]
        print(f"Nenhum template encontrado para o tipo de documento: {doc_type}")
        return None




if __name__ == "__main__":
    while True:
        print("\n=== Sistema de Extração de Documentos ===")
        print("1. Processar documentos")
        print("2. Gerenciar templates")
        print("3. Sair")

        choice = input("\nEscolha uma opção: ")

        if choice == "1":
            # Processar documentos
            input_directory = input("\nDigite o caminho do diretório de entrada: ")
            output_directory = input("Digite o caminho do diretório de saída: ")
            append_option = input("\nDeseja consolidar os resultados em um único arquivo? (s/n): ").strip().lower()

            append = append_option == 's'
            
                        # Criar extractor sem template específico
            extractor = DocumentROIExtractor()

            template_manager = TemplateManager()
            
            if not template_manager.list_templates():
                print("\nNenhum template disponível. Crie pelo menos um antes de processar documentos.")
                continue
            
            doc_type = input("\nDigite o tipo de documento a ser processado: ").strip()
            
            # Verificar se o tipo de documento está nos templates
            if doc_type not in template_manager.templates:
                print(f"\nTipo de documento '{doc_type}' não encontrado nos templates. Por favor, crie-o antes de continuar.")
                continue
            
            if os.path.exists(input_directory):
                extractor.process_directory(input_directory, output_directory, append=append)
            else:
                print("Diretório de entrada não encontrado.")

        elif choice == "2":
            manage_templates()

        elif choice == "3":
            print("\nEncerrando o programa...")
            break

        else:
            print("Opção inválida!")