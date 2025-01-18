# Sistema de Extração de Documentos - Guia do Usuário

## Primeiros Passos

### Iniciando o Programa
1. Execute o programa através do arquivo principal:
   ```bash
   python main.py
   ```
2. A interface principal será aberta com duas abas principais:
   - "Editor de Templates"
   - "Processamento"

## Editor de Templates

### Interface Principal do Editor
![Interface do Editor]
- **Painel Esquerdo**: Controles e propriedades
- **Área Central**: Visualização do documento
- **Barra de Ferramentas Superior**: Ações principais

### Criar Novo Template
1. Na barra de ferramentas, clique no botão "Novo Template"
2. No painel esquerdo:
   - Digite o tipo de documento (ex: "nota_fiscal")
   - Digite um nome para o template (ex: "modelo_padrao")
3. Clique em "Carregar Imagem" para selecionar um documento exemplo

### Adicionar Regiões de Interesse (ROIs)
1. No painel "Regiões", clique no botão "+"
2. Na janela que abrir:
   - Digite um nome para a região (ex: "CNPJ")
   - Selecione o tipo de dado:
     * "text" - Para texto geral
     * "cpf" - Para CPF/CNPJ
     * "date" - Para datas
     * "currency" - Para valores monetários
     * "number" - Para números em geral

### Ajustar ROIs na Imagem
1. **Mover ROI**:
   - Clique na região colorida e arraste
   - Use as setas do teclado para ajuste fino
   - Shift + setas para movimentos maiores

2. **Redimensionar ROI**:
   - Dê duplo clique na região para ativar o modo de redimensionamento
   - Aparecem quadrados nos cantos da região
   - Arraste os quadrados para redimensionar
   - Dê duplo clique novamente para sair do modo de redimensionamento

3. **Ajuste Preciso**:
   No painel "Propriedades":
   - X: Posição horizontal
   - Y: Posição vertical
   - W: Largura
   - H: Altura

### Testar Extração
1. Com uma ROI selecionada, clique em "Testar OCR"
2. Uma janela mostrará o texto extraído daquela região
3. Ajuste a posição/tamanho se necessário

### Salvar Template
1. Clique no botão "Salvar" na barra de ferramentas
2. O template será salvo e estará disponível para uso

## Processamento de Documentos

### Interface de Processamento
![Interface de Processamento]
- **Diretórios**: Seleção de entrada/saída
- **Template**: Seleção do template a usar
- **Opções**: Configurações de processamento
- **Preview**: Visualização do documento atual

### Configurar Processamento
1. **Selecionar Diretórios**:
   - Clique em "..." ao lado de "Entrada" para selecionar a pasta com as imagens
   - Clique em "..." ao lado de "Saída" para definir onde salvar os resultados

2. **Escolher Template**:
   - Selecione o tipo de documento no primeiro combo box
   - Selecione o template específico no segundo combo box

3. **Configurar Opções**:
   - "Consolidar resultados": Gera um único arquivo CSV com todos os resultados
   - "Mostrar preview": Exibe cada documento durante o processamento
   - "Salvar debug": Salva imagens intermediárias para verificação

### Iniciar Processamento
1. Clique em "Iniciar Processamento"
2. A barra de progresso mostrará o andamento
3. O status atual aparece abaixo da barra
4. Para interromper, clique em "Parar"

### Resultados
Os resultados serão salvos no diretório de saída:
1. Se "Consolidar resultados" estiver marcado:
   - `resultados_consolidados.csv`: Todas as extrações

2. Para cada documento processado:
   - `nome_do_documento_resultados.json`: Dados extraídos
   - `nome_do_documento_debug.png`: Imagem com ROIs marcadas (se debug ativado)

## Dicas de Uso

### Criação de Templates
1. **Escolha uma boa imagem exemplo**:
   - Documento bem digitalizado
   - Texto legível
   - Sem rotação ou distorção

2. **Defina ROIs com margem**:
   - Deixe um pequeno espaço ao redor do texto
   - Evite incluir bordas ou linhas
   - Verifique se o texto está totalmente contido

3. **Teste diferentes documentos**:
   - Use o botão "Carregar Imagem" para testar outras amostras
   - Verifique se as ROIs funcionam em diferentes casos

### Processamento em Lote
1. **Organize os documentos**:
   - Separe por tipo
   - Verifique a qualidade das digitalizações
   - Remova páginas em branco

2. **Monitore o processamento**:
   - Observe o preview quando disponível
   - Verifique a taxa de sucesso
   - Ajuste o template se necessário

## Solução de Problemas

### Problemas de Extração
1. **Texto não reconhecido**:
   - Verifique se a ROI está bem posicionada
   - Aumente a margem ao redor do texto
   - Verifique se o tipo de dado está correto

2. **Texto incorreto**:
   - Verifique a qualidade da imagem
   - Teste diferentes tipos de dados
   - Ajuste o tamanho da ROI

3. **Processamento lento**:
   - Reduza o número de ROIs
   - Desative o preview se não necessário
   - Verifique o tamanho das imagens

### Verificação de Resultados
1. Abra o arquivo CSV consolidado
2. Verifique os arquivos JSON individuais
3. Compare com as imagens de debug
4. Consulte os logs em caso de erro

## Suporte Adicional
- Consulte a documentação técnica para detalhes avançados
- Verifique os logs em `logs/roi_extractor.log`
- Reporte problemas no repositório do projeto