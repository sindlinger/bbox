import json
from pathlib import Path
import shutil
import logging
from datetime import datetime

class TemplateManager:
    """
    Gerencia o armazenamento e manipulação de templates de documentos.
    Cada template contém informações sobre as regiões de interesse (ROIs)
    e suas configurações.
    """
    
    def __init__(self, templates_dir=None):
        """
        Inicializa o gerenciador de templates.
        
        Args:
            templates_dir: Diretório para armazenar os templates. Se None,
                         usa o diretório padrão data/templates/
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent / "data" / "templates"
        
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.templates_file = self.templates_dir / "document_templates.json"
        self.templates = self.load_templates()
        
        # Configurar logging
        self.setup_logging()
        
    def setup_logging(self):
        """Configura o sistema de logging"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Criar handler para arquivo
        log_file = self.templates_dir / "template_manager.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Formato do log
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)

    def load_templates(self):
        """
        Carrega os templates do arquivo JSON.
        
        Returns:
            dict: Dicionário com os templates carregados
        """
        try:
            if self.templates_file.exists():
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Erro ao carregar templates: {e}")
            return {}

    def save_templates(self):
        """Salva os templates no arquivo JSON"""
        try:
            # Criar backup antes de salvar
            if self.templates_file.exists():
                backup_name = f"document_templates_backup_{datetime.now():%Y%m%d_%H%M%S}.json"
                shutil.copy2(self.templates_file, self.templates_dir / backup_name)
            
            # Salvar templates atualizados
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(self.templates, f, indent=4, ensure_ascii=False)
            
            self.logger.info("Templates salvos com sucesso")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar templates: {e}")
            return False

    def get_doc_types(self):
        """Retorna lista de tipos de documentos disponíveis"""
        return sorted(self.templates.keys())

    def get_templates(self, doc_type):
        """
        Retorna lista de templates para um tipo de documento
        
        Args:
            doc_type: Tipo do documento
            
        Returns:
            list: Lista de nomes dos templates
        """
        if doc_type in self.templates:
            return sorted(self.templates[doc_type].keys())
        return []

    def get_template(self, doc_type, template_name):
        """
        Retorna um template específico
        
        Args:
            doc_type: Tipo do documento
            template_name: Nome do template
            
        Returns:
            dict: Template encontrado ou None
        """
        if doc_type in self.templates and template_name in self.templates[doc_type]:
            return self.templates[doc_type][template_name]
        return None

    def create_template(self, doc_type, template_name, regions):
        """
        Cria ou atualiza um template
        
        Args:
            doc_type: Tipo do documento
            template_name: Nome do template
            regions: Dicionário com as regiões do template
        """
        try:
            if doc_type not in self.templates:
                self.templates[doc_type] = {}

            self.templates[doc_type][template_name] = {
                "name": template_name,
                "regions": regions,
                "created": datetime.now().isoformat(),
                "modified": datetime.now().isoformat()
            }
            
            self.save_templates()
            self.logger.info(f"Template {template_name} criado/atualizado com sucesso")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao criar template: {e}")
            return False

    def delete_template(self, doc_type, template_name):
        """
        Remove um template
        
        Args:
            doc_type: Tipo do documento
            template_name: Nome do template
        """
        try:
            if doc_type in self.templates and template_name in self.templates[doc_type]:
                del self.templates[doc_type][template_name]
                
                # Remover tipo de documento se não tiver mais templates
                if not self.templates[doc_type]:
                    del self.templates[doc_type]
                
                self.save_templates()
                self.logger.info(f"Template {template_name} removido com sucesso")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Erro ao deletar template: {e}")
            return False

    def validate_template(self, doc_type, template_name):
        """
        Valida um template
        
        Args:
            doc_type: Tipo do documento
            template_name: Nome do template
            
        Returns:
            tuple: (válido, lista de erros)
        """
        errors = []
        template = self.get_template(doc_type, template_name)
        
        if not template:
            return False, ["Template não encontrado"]
            
        # Validar regiões
        if "regions" not in template:
            errors.append("Template não contém regiões")
        else:
            for name, region in template["regions"].items():
                if "coords" not in region:
                    errors.append(f"Região {name} não tem coordenadas")
                if "expected_type" not in region:
                    errors.append(f"Região {name} não tem tipo definido")
                    
        return len(errors) == 0, errors