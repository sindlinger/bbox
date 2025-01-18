# Documentação Técnica - Sistema de Extração de Documentos

## Arquitetura do Sistema

### Estrutura de Diretórios
```
.
├── logs/                    # Logs do sistema
├── main.py                  # Ponto de entrada
├── resources/              # Recursos estáticos
│   └── icons/             # Ícones da interface
└── src/                   # Código fonte
    ├── data/             # Dados persistentes
    │   └── templates/    # Templates salvos
    ├── gui/             # Interface gráfica
    │   ├── document_processor.py
    │   ├── main_window.py
    │   └── template_editor.py
    └── roi_extractor.py  # Core do sistema
```

### Componentes Principais

1. **ROI Extractor**
   - Core do sistema de extração
   - Gerencia coordenadas e tipos de ROIs
   - Integra com Tesseract OCR
   - Pipeline de pré-processamento de imagens

2. **Template Manager**
   - Persistência de templates
   - Validação e versionamento
   - Cache e otimização

3. **GUI**
   - Interface principal (MainWindow)
   - Editor de templates
   - Processador de documentos
   - Visualizador de resultados

## Fluxo de Dados

1. **Criação de Template**
   ```
   Interface → ROI Definition → Template Validation → Storage
   ```

2. **Processamento de Documentos**
   ```
   Input Images → Template Loading → ROI Extraction → OCR → Results
   ```

3. **Gerenciamento de Dados**
   ```
   Templates ↔ JSON Storage ↔ Runtime Cache ↔ Processing Queue
   ```

## Desenvolvimento

### Setup do Ambiente
```bash
# Criar ambiente
python -m venv .venv

# Dependências de desenvolvimento
pip install -r requirements-dev.txt

# Hooks de pre-commit
pre-commit install
```

### Testes
```bash
# Unitários
pytest tests/unit

# Integração
pytest tests/integration

# Cobertura
pytest --cov=src tests/
```

### Convenções de Código
- PEP 8
- Type hints
- Docstrings (Google style)
- Commits semânticos

## Roadmap e Próximos Passos

### 1. Detecção Automática de Templates
#### Objetivo
Implementar sistema inteligente para seleção automática de templates quando o atual falha.

#### Implementação Proposta
1. **Sistema de Pontuação**
   ```python
   class TemplateScoring:
       def evaluate_match(self, image, template):
           scores = {
               'roi_match': self._evaluate_roi_positions(),
               'ocr_confidence': self._evaluate_ocr_results(),
               'structural_similarity': self._evaluate_structure()
           }
           return weighted_average(scores)
   ```

2. **Fallback Automático**
   ```python
   class SmartTemplateSelector:
       def select_best_template(self, image, doc_type):
           templates = self.load_templates(doc_type)
           scores = [(t, self.score_template(image, t)) for t in templates]
           return max(scores, key=lambda x: x[1])
   ```

3. **Métricas de Qualidade**
   - Taxa de sucesso OCR
   - Consistência estrutural
   - Validação de dados extraídos

### 2. Sistema de Anotação para Machine Learning

#### Objetivos
- Criar sistema de anotação para treinar modelos
- Integrar com frameworks de ML
- Automatizar detecção de ROIs

#### Implementação Proposta

1. **Estrutura de Dados**
```python
class DocumentAnnotation:
    def __init__(self):
        self.rois = []
        self.labels = {}
        self.metadata = {}
        
    def export_yolo(self):
        """Exporta anotações no formato YOLO"""
        
    def export_coco(self):
        """Exporta anotações no formato COCO"""
```

2. **Pipeline de ML**
```python
class MLPipeline:
    def prepare_dataset(self):
        """Prepara dados para treinamento"""
        
    def train_model(self):
        """Treina modelo de detecção"""
        
    def evaluate_model(self):
        """Avalia performance do modelo"""
```

3. **Interface de Anotação**
- Ferramentas de marcação
- Atalhos de teclado
- Validação em tempo real
- Export para diferentes formatos

### Melhorias de Curto Prazo

1. **Performance**
   - Cache de templates
   - Processamento paralelo
   - Otimização de imagens

2. **Interface**
   - Previews em tempo real
   - Undo/Redo
   - Temas personalizáveis

3. **Validação**
   - Regras por tipo de dado
   - Expressões regulares
   - Validação cruzada

### Melhorias de Longo Prazo

1. **Automação**
   - Detecção automática de layouts
   - Sugestão de ROIs
   - Auto-correção de alinhamento

2. **Integração**
   - APIs REST
   - Plugins de terceiros
   - Sistemas de storage

3. **Machine Learning**
   - Transfer learning
   - Few-shot learning
   - Active learning

## Contribuição

### Processo
1. Fork do repositório
2. Criar branch feature/fix
3. Desenvolver com testes
4. Pull Request

### Guidelines
- Documentar mudanças
- Seguir estilo do código
- Incluir testes
- Atualizar documentação

## Manutenção

### Logs
- Rotação automática
- Níveis de verbosidade
- Métricas de uso

### Backup
- Templates
- Configurações
- Dados de treinamento

### Monitoramento
- Status do sistema
- Uso de recursos
- Erros e exceções