import cv2
import numpy as np
from pathlib import Path
import pytesseract
import logging
from datetime import datetime

class ROIExtractor:
    """
    Classe responsável pela extração e processamento de ROIs (Regiões de Interesse)
    em imagens de documentos.
    """
    
    def __init__(self, template_manager=None):
        """
        Inicializa o extrator de ROIs
        
        Args:
            template_manager: Instância do TemplateManager (opcional)
        """
        self.template_manager = template_manager
        self.current_doc_type = None
        self.current_template_name = None
        
        # Dimensões padrão para padronização de imagens
        self.target_width = 1654
        self.target_height = 2339
        
        # Configurações do OCR para diferentes tipos de campos
        self.tesseract_config = {
            "text": "--psm 6 --oem 3",
            "cpf": "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.-/",
            "number": "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.",
            "currency": "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789,.",
            "date": "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789/"
        }
        
        # Configurar logging
        self.setup_logging()
        
    def setup_logging(self):
        """Configura o sistema de logging"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Handler para arquivo
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / "roi_extractor.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Formato do log
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)

    def standardize_image(self, image):
        """
        Padroniza o tamanho e qualidade da imagem
        
        Args:
            image: Imagem OpenCV
            
        Returns:
            Imagem padronizada
        """
        try:
            if image is None:
                raise ValueError("Imagem inválida")
            
            # Converter para escala de cinza se necessário
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Redimensionar
            resized = cv2.resize(
                gray, 
                (self.target_width, self.target_height), 
                interpolation=cv2.INTER_CUBIC
            )
            
            # Converter de volta para BGR
            standardized = cv2.cvtColor(resized, cv2.COLOR_GRAY2BGR)
            
            return standardized
        except Exception as e:
            self.logger.error(f"Erro ao padronizar imagem: {e}")
            return image

    def extract_roi(self, image, coords):
        """
        Extrai uma ROI da imagem
        
        Args:
            image: Imagem OpenCV
            coords: Tupla (x1, y1, x2, y2) com coordenadas da ROI
            
        Returns:
            Imagem da ROI extraída
        """
        try:
            x1, y1, x2, y2 = coords
            
            # Garantir coordenadas dentro dos limites
            height, width = image.shape[:2]
            x1 = max(0, min(x1, width))
            x2 = max(0, min(x2, width))
            y1 = max(0, min(y1, height))
            y2 = max(0, min(y2, height))
            
            # Verificar se região é válida
            if x1 >= x2 or y1 >= y2:
                raise ValueError(f"Coordenadas inválidas: ({x1}, {y1}, {x2}, {y2})")
                
            # Extrair região
            roi = image[y1:y2, x1:x2]
            
            if roi.size == 0:
                raise ValueError("ROI extraída está vazia")
                
            return roi
            
        except Exception as e:
            self.logger.error(f"Erro ao extrair ROI {coords}: {e}")
            # Retornar uma pequena imagem preta em caso de erro
            return np.zeros((10, 10, 3), dtype=np.uint8)

    def preprocess_roi(self, roi, expected_type):
        """
        Pré-processa uma ROI para melhorar o reconhecimento de texto
        
        Args:
            roi: Imagem da ROI
            expected_type: Tipo esperado do dado ('text', 'cpf', etc)
            
        Returns:
            ROI pré-processada
        """
        try:
            # Converter para escala de cinza se necessário
            if len(roi.shape) == 3:
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            else:
                gray = roi
            
            # Aumentar resolução
            scale_factor = 8
            enlarged = cv2.resize(gray, None, 
                                fx=scale_factor, 
                                fy=scale_factor, 
                                interpolation=cv2.INTER_CUBIC)
            
            # Remover ruído mantendo bordas
            denoised = cv2.bilateralFilter(enlarged, 9, 75, 75)
            
            # Ajustes específicos por tipo
            if expected_type in ['cpf', 'number', 'currency', 'date']:
                # Aumentar contraste para números
                denoised = cv2.convertScaleAbs(denoised, alpha=1.5, beta=0)
            
            return denoised
            
        except Exception as e:
            self.logger.error(f"Erro no pré-processamento: {e}")
            return roi

    def extract_text(self, roi, expected_type):
        """
        Extrai texto de uma ROI usando OCR
        
        Args:
            roi: Imagem da ROI
            expected_type: Tipo esperado do dado
            
        Returns:
            Texto extraído e processado
        """
        try:
            # Lista para armazenar resultados de diferentes tentativas
            results = []
            
            # Primeira tentativa: imagem pré-processada
            processed_roi = self.preprocess_roi(roi, expected_type)
            text1 = pytesseract.image_to_string(
                processed_roi,
                lang='por',
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
            
            # Escolher melhor resultado e pós-processar
            best_text = self.choose_best_result(results, expected_type)
            cleaned_text = self.post_process_text(best_text, expected_type)
            
            return cleaned_text
            
        except Exception as e:
            self.logger.error(f"Erro na extração de texto: {e}")
            return ""

    def choose_best_result(self, results, expected_type):
        """
        Escolhe o melhor resultado entre várias tentativas de OCR
        
        Args:
            results: Lista de textos extraídos
            expected_type: Tipo esperado do dado
            
        Returns:
            Melhor texto encontrado
        """
        # Remover resultados vazios
        valid_results = [r for r in results if r.strip()]
        if not valid_results:
            return ""
            
        if expected_type == "cpf":
            # Escolher o que tem mais números
            return max(valid_results, 
                      key=lambda x: len([c for c in x if c.isdigit()]))
            
        elif expected_type == "date":
            # Escolher o que mais se parece com uma data
            import re
            for result in valid_results:
                if re.search(r'\d{2}/\d{2}/\d{2,4}', result):
                    return result
            return valid_results[0]
            
        elif expected_type in ["number", "currency"]:
            # Escolher o que tem mais números
            return max(valid_results, 
                      key=lambda x: len([c for c in x if c.isdigit()]))
            
        # Para texto, escolher o mais longo que não seja só números
        text_results = [r for r in valid_results 
                       if not r.replace('.','').replace(',','').isdigit()]
        if text_results:
            return max(text_results, key=len)
        return valid_results[0]

    def post_process_text(self, text, expected_type):
        """
        Limpa e formata o texto extraído
        
        Args:
            text: Texto extraído
            expected_type: Tipo esperado do dado
            
        Returns:
            Texto processado
        """
        if not text:
            return ""
            
        # Remover caracteres indesejados
        import re
        text = re.sub(r'[^\w\s./,-]', '', text)
        
        if expected_type == "cpf":
            # Formatar CPF
            nums = ''.join(filter(str.isdigit, text))
            if len(nums) == 11:
                return f"{nums[:3]}.{nums[3:6]}.{nums[6:9]}-{nums[9:]}"
            return nums
            
        elif expected_type == "date":
            # Formatar data
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

    def process_image(self, image_path, template_name=None):
        """
        Processa uma imagem usando um template específico
        
        Args:
            image_path: Caminho da imagem
            template_name: Nome do template a ser usado
            
        Returns:
            Dicionário com os resultados extraídos
        """
        try:
            # Carregar imagem
            img = cv2.imread(str(image_path))
            if img is None:
                raise ValueError(f"Não foi possível ler a imagem: {image_path}")

            # Padronizar imagem
            standardized_img = self.standardize_image(img)

            results = {}
            # Processar cada região definida no template
            for name, region in self.get_regions(template_name).items():
                try:
                    roi = self.extract_roi(standardized_img, region["coords"])
                    text = self.extract_text(roi, region["expected_type"])
                    results[name] = text.strip()
                    
                except Exception as e:
                    self.logger.error(f"Erro ao processar região {name}: {e}")
                    results[name] = ""

            return results
            
        except Exception as e:
            self.logger.error(f"Erro ao processar {image_path}: {e}")
            return None

    def get_regions(self, template_name=None):
        """
        Obtém as regiões de um template
        
        Args:
            template_name: Nome do template
            
        Returns:
            Dicionário com as regiões
        """
        if (template_name and self.template_manager and 
            template_name in self.template_manager.templates):
            return self.template_manager.templates[template_name]["regions"]
        return {}