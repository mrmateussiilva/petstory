# Testes - PetStory Art

Este diretório contém os testes automatizados para os serviços principais do sistema.

## 📁 Estrutura

```
tests/
├── __init__.py
├── conftest.py              # Fixtures compartilhadas
├── test_web_generator.py    # Testes do gerador de páginas HTML
├── test_pdf_service.py      # Testes do gerador de PDF
└── test_gemini_service.py   # Testes do serviço de IA (Gemini)
```

## 🚀 Como Executar

### Instalar dependências de desenvolvimento

```bash
uv sync
```

### Executar todos os testes

```bash
pytest
```

### Executar testes específicos

```bash
# Testes de um serviço específico
pytest tests/test_web_generator.py
pytest tests/test_pdf_service.py
pytest tests/test_gemini_service.py

# Teste específico
pytest tests/test_web_generator.py::TestWebGenerator::test_generate_tribute_page_success
```

### Executar com cobertura

```bash
pytest --cov=app --cov-report=html
```

Isso gera um relatório HTML em `htmlcov/index.html` mostrando a cobertura de código.

### Executar em modo verbose

```bash
pytest -v
```

## 📋 O que é testado

### 1. WebGenerator (`test_web_generator.py`)
- ✅ Inicialização com template padrão e customizado
- ✅ Geração de página HTML com todos os dados
- ✅ Tratamento de imagem faltando
- ✅ Suporte a PNG e JPEG
- ✅ Proteção contra KeyError com chaves CSS/JS no template
- ✅ Caracteres especiais no conteúdo

### 2. PDFService (`test_pdf_service.py`)
- ✅ Criação de PDF a partir de imagens
- ✅ Geração do kit digital completo (capa, biografia, páginas de colorir, adesivos)
- ✅ Limpeza de texto (remoção de emojis, preservação de acentos)
- ✅ Tratamento de erros (imagens faltando, lista vazia)
- ✅ Validação de estrutura do PDF

### 3. GeminiGenerator (`test_gemini_service.py`)
- ✅ Inicialização com API key
- ✅ Geração de imagem (mocked - não usa API real)
- ✅ Conversão de formatos de imagem (RGBA → RGB)
- ✅ Tratamento de erros da API
- ✅ Salvamento de arte em disco
- ✅ Validação do prompt de estilo

## 🔧 Fixtures Disponíveis

As fixtures em `conftest.py` podem ser usadas em qualquer teste:

- `temp_dir`: Diretório temporário para arquivos de teste
- `sample_image_bytes`: Imagem PNG de exemplo (bytes)
- `sample_image_path`: Caminho para imagem PNG de exemplo
- `sample_art_image_bytes`: Arte de exemplo (bytes)
- `sample_art_image_path`: Caminho para arte de exemplo
- `multiple_art_images`: Lista de 3 artes de exemplo
- `sample_pet_data`: Dados de exemplo (nome, data, história)

## ⚠️ Notas Importantes

### Testes do GeminiService
Os testes do `GeminiGenerator` usam **mocks** da API do Gemini para não consumir créditos da API durante os testes. Isso significa que:
- ✅ Os testes são rápidos
- ✅ Não dependem de conexão com internet
- ✅ Não gastam créditos da API
- ⚠️ Não testam a integração real com a API do Gemini

Para testar a integração real, você precisaria:
1. Ter uma API key válida configurada
2. Criar testes de integração separados (marcados com `@pytest.mark.integration`)
3. Executar manualmente quando necessário

### Testes de Integração
Atualmente, os testes são principalmente **testes unitários**. Para testar o fluxo completo:
- Use os testes manuais descritos na documentação principal
- Ou crie testes de integração que executem o worker completo

## 📊 Cobertura de Código

Execute com cobertura para ver quais partes do código estão sendo testadas:

```bash
pytest --cov=app.services --cov-report=term-missing
```

Isso mostra:
- Porcentagem de cobertura por arquivo
- Linhas que não foram executadas

## 🐛 Debugging

Para debugar um teste específico:

```bash
# Executar com output detalhado
pytest -v -s tests/test_web_generator.py::TestWebGenerator::test_generate_tribute_page_success

# Executar com pdb (debugger)
pytest --pdb tests/test_web_generator.py
```

## 🔄 Adicionando Novos Testes

1. Crie um novo arquivo `test_<servico>.py` ou adicione ao arquivo existente
2. Use as fixtures de `conftest.py` quando possível
3. Siga o padrão de nomenclatura: `test_<funcionalidade>`
4. Use mocks para dependências externas (APIs, arquivos, etc.)
5. Execute `pytest` para verificar se tudo está funcionando

## 📝 Exemplo de Teste

```python
def test_my_feature(sample_image_path, sample_pet_data):
    """Test description."""
    # Arrange
    service = MyService()
    
    # Act
    result = service.do_something(sample_image_path)
    
    # Assert
    assert result is not None
    assert len(result) > 0
```

