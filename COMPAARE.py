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
            input_directory = input("\nDigite o caminho do diretório de entrada: ")
            output_directory = input("Digite o caminho do diretório de saída: ")
            append_option = input("\nDeseja consolidar os resultados em um único arquivo? (s/n): ").strip().lower()

            append = append_option == 's'
            
            # Criar extractor sem template específico
            extractor = DocumentROIExtractor()
            
            # O processo de seleção de template acontece dentro de process_directory
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