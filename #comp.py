import cv2
import numpy as np
import os
import pytesseract
from pathlib import Path
import matplotlib.pyplot as plt
import json
import csv
import re
import tqdm

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
        self.regions = self.default_regions.copy()

    def select_template(self, doc_type=None, template_name=None):
        """
        Seleciona um template existente ou prepara para criar um novo.
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

    def interactive_roi_adjustment(self, image, doc_type=None, template_name=None):
        """
        Permite ajuste interativo das ROIs com alternância entre mover e redimensionar.
        Integrado com o sistema de templates.
        
        Args:
            image: Imagem a ser processada
            doc_type: Tipo do documento (opcional)
            template_name: Nome do template (opcional)
            
        Returns:
            dict: Dicionário com as regiões ajustadas
        """
        adjuster = ROIAdjuster(self, image, doc_type, template_name)
        return adjuster.run()


    def process_directory(self, input_dir, output_dir, append=True, doc_type=None, template_name=None):
        """
        Processa um diretório de imagens usando um template específico
        """
        try:
            # Selecionar template se não especificado
            if not doc_type or not template_name:
                doc_type, template_name = self.select_template(doc_type, template_name)
            
            if not doc_type or not template_name:
                print("Template não selecionado. Abortando processamento.")
                return None
                
            input_path = Path(input_dir)
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            consolidated_csv_path = output_path / "resultados_consolidados.csv"
            field_order = ['PERITO', 'CPF', 'PROCESSO', 'VALOR', 'DATA']

            if append:
                if not consolidated_csv_path.exists():
                    with open(consolidated_csv_path, 'w', encoding='utf-8', newline='') as f:
                        writer = csv.writer(f, delimiter=';')
                        writer.writerow(field_order)
                    print(f"Arquivo consolidado criado: {consolidated_csv_path}")

            image_files = list(input_path.glob("*.png")) + list(input_path.glob("*.jpg"))

            if not image_files:
                print(f"Sem imagens em {input_dir}.")
                return None

            print(f"Processando {len(image_files)} imagens de {input_dir}...")
            
            for i, img_path in enumerate(sorted(image_files)):
                print(f"\nProcessando [{i+1}/{len(image_files)}]: {img_path.name}")
                try:
                    results = self.process_image(img_path, output_path)
                    if results:
                        if append:
                            self.save_results(
                                results,
                                consolidated_csv_path.parent,
                                consolidated_csv_path.name,
                                field_order,
                                append=True
                            )
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

    # [Manter todos os outros métodos da classe DocumentROIExtractor como estão]