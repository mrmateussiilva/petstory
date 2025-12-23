# Documentação Completa - PetStory Art

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura do Sistema](#arquitetura-do-sistema)
3. [Funcionalidades Principais](#funcionalidades-principais)
4. [Fluxo de Processamento](#fluxo-de-processamento)
5. [Estrutura do Projeto](#estrutura-do-projeto)
6. [Serviços e Componentes](#serviços-e-componentes)
7. [Frontend](#frontend)
8. [API e Endpoints](#api-e-endpoints)
9. [Configuração e Deploy](#configuração-e-deploy)
10. [Tecnologias Utilizadas](#tecnologias-utilizadas)

---

## 🎯 Visão Geral

**PetStory Art** é uma plataforma SaaS que transforma fotos de pets em desenhos de colorir estilo "Bobbie Goods" (kawaii/doodle) utilizando inteligência artificial. O sistema processa múltiplas fotos do pet, gera arte personalizada, cria um kit digital completo (PDF, página web de homenagem) e envia tudo por e-mail ao usuário.

### Objetivo do Projeto

Criar uma experiência completa onde o usuário:
- Envia fotos do seu pet (1 a 10 fotos)
- Preenche informações sobre o pet (nome, data especial, história/biografia)
- Recebe automaticamente um kit digital contendo:
  - PDF com livro de colorir (capa, biografia, páginas de colorir, adesivos)
  - Página HTML de homenagem personalizada
  - Tudo enviado por e-mail

### Diferencial

- Processamento rápido (5-10 minutos)
- Estilo artístico único (Bobbie Goods - traço grosso, kawaii)
- Kit digital completo (não apenas imagens isoladas)
- Interface moderna e intuitiva
- 100% automatizado após o upload

---

## 🏗️ Arquitetura do Sistema

### Padrão Arquitetural

O projeto segue uma arquitetura em camadas com separação clara de responsabilidades:

```
┌─────────────────────────────────────────┐
│          Frontend (HTML/CSS/JS)         │
│  - Página inicial (landing)             │
│  - Formulário de criação                │
└──────────────┬──────────────────────────┘
               │ HTTP POST
┌──────────────▼──────────────────────────┐
│       FastAPI (Backend Principal)       │
│  - Recebe upload                         │
│  - Valida dados                          │
│  - Agenda tarefa em background           │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      Worker (Processamento)             │
│  1. Geração de arte (Gemini IA)         │
│  2. Criação do PDF                       │
│  3. Geração da página web                │
│  4. Envio de e-mail                      │
└─────────────────────────────────────────┘
```

### Padrões de Design

- **Strategy Pattern**: Interface abstrata `ImageGenerator` permite trocar o provedor de IA facilmente
- **Service Layer**: Serviços especializados (Email, PDF, Web, Gemini)
- **Background Tasks**: Processamento assíncrono usando FastAPI BackgroundTasks

---

## ✨ Funcionalidades Principais

### 1. Upload e Validação de Fotos

- Aceita múltiplas fotos (1 a 10 por pedido)
- Formatos suportados: JPEG, PNG, WebP
- Validação de tamanho (máx. 10MB por foto)
- Validação de tipo de conteúdo
- Armazenamento temporário organizado por usuário (baseado no e-mail)

### 2. Geração de Arte com IA (Gemini)

- Transforma fotos reais em desenho estilo "Bobbie Goods"
- Características do estilo:
  - Corpo arredondado e "gordinho" (estilo kawaii)
  - Olhos pequenos e simples (dois pontos pretos)
  - Traços grossos e negros (como marcador)
  - Fundo branco puro
  - Sem sombreamento ou gradações
  - Ideal para colorir
- Usa modelo Gemini 2.5 Flash Image ou Gemini 3 Pro Image Preview
- Rate limiting: delay de 2 segundos entre gerações para evitar limites da API

### 3. Geração de PDF (Kit Digital)

O PDF gerado contém:

#### Página 1: Capa
- Título: "Livro de Colorir do [Nome do Pet]"
- Primeira arte gerada como imagem de capa

#### Página 2: Biografia ("A História")
- Título: "Quem é [Nome do Pet]?"
- Data especial (se fornecida)
- Foto original em formato Polaroid
- Texto da biografia/história do pet

#### Páginas 3+: Páginas de Colorir
- Uma página para cada arte gerada
- Formato A4, ocupando toda a página
- Número da página ("Desenho #1", "Desenho #2", etc.)

#### Última Página: Adesivos
- Grid 3x3 (9 adesivos)
- Usa as artes geradas (repetindo se necessário)
- Cada adesivo é uma versão menor da arte

### 4. Geração de Página Web de Homenagem

- Página HTML standalone (não requer servidor)
- Design moderno com Tailwind CSS
- Gradientes e animações suaves
- Inclui:
  - Nome do pet
  - Data especial
  - Arte gerada (embutida como base64)
  - História/biografia do pet
- Pode ser aberta diretamente no navegador ou hospedada

### 5. Envio de E-mail

- E-mail HTML personalizado
- Anexos:
  - PDF do kit digital
  - Arquivo HTML da página de homenagem
- Configuração via SMTP (Gmail ou outro servidor)
- Modo simulação se SMTP não configurado (apenas logs)

### 6. Armazenamento Temporário

- Arquivos organizados por pedido único
- Estrutura de diretórios: `temp/[email-slug]/[nome-pet-slug]_[timestamp]/`
- Cada pedido tem seu próprio diretório único (mesmo e-mail pode ter múltiplos pedidos)
- Todos os arquivos de um pedido (fotos originais, artes geradas, PDF, HTML) são salvos no mesmo diretório
- Formato do diretório garante unicidade: email + nome do pet + timestamp (YYYYMMDD_HHMMSS)

---

## 🔄 Fluxo de Processamento

### Fluxo Completo

```
1. USUÁRIO PREENCHE FORMULÁRIO
   ↓
   - Nome do pet
   - Data especial (opcional)
   - História/biografia
   - E-mail
   - Fotos (1-10)

2. FRONTEND ENVIA PARA API
   ↓
   POST /api/upload
   - Valida campos obrigatórios
   - Valida fotos (tipo, tamanho, quantidade)
   - Salva fotos temporariamente
   - Retorna status 200 (sucesso)

3. BACKEND AGENDA TAREFA EM BACKGROUND
   ↓
   BackgroundTasks.add_task(process_pet_story)

4. WORKER PROCESSA (ASSÍNCRONO)
   ↓
   ┌─────────────────────────────────────┐
   │ Passo 1: Geração de Arte            │
   │ - Para cada foto:                   │
   │   - Chama Gemini API                │
   │   - Gera arte estilo Bobbie Goods   │
   │   - Salva arte em PNG               │
   │   - Delay de 2s entre gerações      │
   └─────────────────────────────────────┘
   ↓
   ┌─────────────────────────────────────┐
   │ Passo 2: Criação do PDF             │
   │ - Cria capa                         │
   │ - Adiciona página de biografia      │
   │ - Adiciona páginas de colorir       │
   │ - Adiciona página de adesivos       │
   │ - Salva PDF                         │
   └─────────────────────────────────────┘
   ↓
   ┌─────────────────────────────────────┐
   │ Passo 3: Geração da Página Web      │
   │ - Cria HTML com Tailwind CSS        │
   │ - Embuta arte como base64           │
   │ - Inclui nome, data, história       │
   │ - Salva HTML                        │
   └─────────────────────────────────────┘
   ↓
   ┌─────────────────────────────────────┐
   │ Passo 4: Envio de E-mail            │
   │ - Lê PDF e HTML                     │
   │ - Cria e-mail HTML                  │
   │ - Anexa PDF e HTML                  │
   │ - Envia via SMTP                    │
   └─────────────────────────────────────┘
   ↓

5. USUÁRIO RECEBE E-MAIL
   - Com PDF anexado
   - Com HTML anexado
   - Pronto para usar!
```

### Tratamento de Erros

- Se uma foto falhar na geração de arte, o processamento continua com as outras
- Erros são logados detalhadamente
- Se o e-mail falhar, o PDF ainda é gerado (erro é logado)
- Validações no início evitam erros comuns (tamanho, formato, etc.)

---

## 📁 Estrutura do Projeto

```
petStoryArt/
├── app/                          # Código Python principal
│   ├── __init__.py
│   ├── main.py                   # FastAPI app e endpoints
│   ├── worker.py                 # Worker de processamento
│   │
│   ├── core/                     # Configurações
│   │   ├── __init__.py
│   │   └── config.py             # Settings (Pydantic)
│   │
│   ├── interfaces/               # Interfaces/Abstrações
│   │   ├── __init__.py
│   │   └── image_generator.py    # Interface ImageGenerator
│   │
│   ├── services/                 # Serviços especializados
│   │   ├── __init__.py
│   │   ├── gemini_service.py     # Geração de arte (Gemini)
│   │   ├── pdf_service.py        # Geração de PDFs
│   │   ├── email_service.py      # Envio de e-mails (SMTP)
│   │   └── web_generator.py      # Geração de páginas HTML
│   │
│   └── utils/                    # Utilitários
│       ├── __init__.py
│       └── slug.py               # Conversão de e-mail para slug
│
├── frontend/                     # Interface do usuário
│   ├── index.html                # Landing page
│   └── criar.html                # Página de criação/upload
│
├── temp/                         # Arquivos temporários
│   └── [email-slug]/             # Por usuário (email)
│       └── [nome-pet]_[timestamp]/  # Por pedido único
│           ├── foto_1_[timestamp].jpg
│           ├── arte_[timestamp].png
│           ├── kit_digital_[timestamp].pdf
│           └── homenagem_[timestamp].html
│
├── fonts/                        # Fontes (se necessário)
│   └── PatrickHand-Regular.ttf
│
├── pyproject.toml                # Dependências (uv)
├── Dockerfile                    # Imagem Docker
├── README.md                     # README do projeto
└── docs.md                       # Esta documentação
```

---

## 🔧 Serviços e Componentes

### 1. GeminiService (`app/services/gemini_service.py`)

**Responsabilidade**: Gerar arte estilo Bobbie Goods a partir de fotos reais.

**Principais Métodos**:
- `generate(image_bytes, prompt) -> bytes`: Gera imagem a partir de bytes
- `generate_art(photo_path, output_dir) -> str`: Processa arquivo de foto e salva arte

**Características**:
- Usa Google Generative AI (Gemini)
- Prompt otimizado para estilo Bobbie Goods
- Suporta diferentes modelos (configurável)
- Conversão automática de formatos (RGB)
- Retorna PNG

### 2. PDFService (`app/services/pdf_service.py`)

**Responsabilidade**: Criar PDFs do kit digital completo.

**Principais Métodos**:
- `create_pdf_from_images(images, output_path) -> bytes`: Cria PDF simples de imagens
- `create_digital_kit(...) -> str`: Cria kit completo (capa, biografia, colorir, adesivos)
- `clean_text(text) -> str`: Remove emojis e caracteres especiais (compatibilidade FPDF)

**Características**:
- Usa FPDF2
- Formato A4 (210x297mm)
- Layout profissional e organizado
- Suporte a imagens (JPEG, PNG)
- Tratamento de texto (remoção de emojis para compatibilidade)

### 3. EmailService (`app/services/email_service.py`)

**Responsabilidade**: Enviar e-mails com anexos via SMTP.

**Principais Métodos**:
- `send_pdf(to_email, subject, pdf_bytes, pdf_filename) -> bool`: Envia PDF simples
- `send_pet_story_email(to_email, pet_name, pdf_bytes, html_content, pdf_filename) -> bool`: Envia kit completo

**Características**:
- Suporte a SMTP (Gmail, outros servidores)
- E-mails HTML formatados
- Múltiplos anexos
- Modo simulação se não configurado (logs apenas)
- Tratamento de erros de autenticação/envio

### 4. WebGenerator (`app/services/web_generator.py`)

**Responsabilidade**: Gerar página HTML de homenagem.

**Principais Métodos**:
- `generate_tribute_page(pet_name, pet_date, pet_story, art_image_path) -> str`: Gera HTML completo

**Características**:
- HTML standalone (sem dependências externas de imagens)
- Imagem embutida como base64
- Design moderno com Tailwind CSS
- Responsivo
- Gradientes e efeitos visuais

### 5. Worker (`app/worker.py`)

**Responsabilidade**: Orquestrar todo o fluxo de processamento.

**Função Principal**:
- `process_pet_story(nome_pet, pet_date, pet_story, email, photo_paths) -> dict`

**Fluxo**:
1. Inicializa serviços (Gemini, PDF, Web, Email)
2. Gera arte para cada foto
3. Cria PDF do kit digital
4. Gera página HTML de homenagem
5. Envia e-mail com anexos
6. Retorna resultado (sucesso ou erro)

**Tratamento de Erros**:
- Continua processamento mesmo se uma foto falhar
- Loga todos os erros
- Retorna status detalhado

### 6. Config (`app/core/config.py`)

**Responsabilidade**: Gerenciar configurações da aplicação.

**Principais Configurações**:
- API Keys (Gemini)
- SMTP (servidor, porta, usuário, senha)
- Diretório temporário
- CORS origins
- Modelo Gemini a usar
- Delay entre gerações (rate limiting)

**Características**:
- Usa Pydantic Settings
- Carrega de variáveis de ambiente (.env)
- Validação automática
- Type hints

---

## 🎨 Frontend

### Página Inicial (`frontend/index.html`)

**Propósito**: Landing page para atrair usuários e explicar o serviço.

**Funcionalidades**:
- Hero section com slider comparativo (antes/depois)
- Galeria de exemplos
- Seção "Como funciona" (3 passos)
- Depoimentos
- O que o usuário recebe
- FAQ
- CTA (Call to Action) para criar livro

**Design**:
- Estilo "caderno de desenho" (doodle style)
- Animações suaves
- Responsivo (mobile-first)
- Tailwind CSS
- Fontes: Patrick Hand (títulos), Fredoka (texto)

**Interatividade**:
- Slider comparativo (drag para comparar foto vs arte)
- Scroll reveal (animações ao rolar)
- Parallax effect nos elementos decorativos
- Smooth scroll para âncoras

### Página de Criação (`frontend/criar.html`)

**Propósito**: Formulário para o usuário enviar fotos e informações do pet.

**Campos do Formulário**:
1. **Nome do Pet** (obrigatório)
2. **Data Especial** (opcional, date picker)
3. **História/Biografia** (obrigatório, textarea, máx. 300 caracteres)
4. **E-mail** (obrigatório, validação de formato)
5. **Fotos** (obrigatório, 1-10 fotos, drag & drop ou click)

**Funcionalidades**:
- Drag & drop de fotos
- Preview de fotos selecionadas
- Validação de tamanho (máx. 10MB por foto)
- Contador de caracteres (biografia)
- Progress bar durante upload
- Mensagens de status (sucesso/erro)

**Validações Frontend**:
- Campos obrigatórios
- Formato de e-mail
- Quantidade de fotos (1-10)
- Tamanho de arquivo (10MB)
- Tipo de arquivo (imagens)

**Integração com Backend**:
- Fetch API para POST `/api/upload`
- FormData para envio multipart
- Tratamento de respostas (sucesso/erro)
- Reset do formulário após sucesso

---

## 🌐 API e Endpoints

### Base URL
- Desenvolvimento: `http://localhost:8000`
- Produção: Configurável via variável de ambiente

### Endpoints

#### 1. `GET /`
**Descrição**: Health check básico

**Resposta**:
```json
{
  "status": "ok",
  "service": "PetStory API",
  "version": "0.1.0"
}
```

#### 2. `GET /health`
**Descrição**: Health check para monitoramento

**Resposta**:
```json
{
  "status": "healthy"
}
```

#### 3. `POST /api/upload`
**Descrição**: Endpoint principal para upload de fotos e criação do kit digital

**Content-Type**: `multipart/form-data`

**Parâmetros (Form Data)**:
- `nome_pet` (string, obrigatório): Nome do pet
- `pet_date` (string, opcional): Data especial (formato: YYYY-MM-DD)
- `pet_story` (string, obrigatório): História/biografia do pet (máx. ~300 caracteres)
- `email` (string, obrigatório): E-mail do destinatário
- `fotos` (file[], obrigatório): Array de arquivos de imagem (1-10 fotos)

**Validações**:
- E-mail deve conter "@"
- Nome do pet não pode estar vazio
- História não pode estar vazia
- Mínimo 1 foto, máximo 10 fotos
- Tipo de arquivo: image/jpeg, image/jpg, image/png, image/webp
- Tamanho máximo: 10MB por foto

**Resposta de Sucesso (200)**:
```json
{
  "status": "success",
  "message": "História de [Nome] está sendo processada! Você receberá um e-mail em [email] quando estiver pronta.",
  "nome_pet": "Max",
  "email": "usuario@example.com",
  "fotos_count": 3
}
```

**Resposta de Erro (400/500)**:
```json
{
  "detail": "Mensagem de erro específica"
}
```

**Processamento**:
- Fotos são salvas temporariamente
- Tarefa é agendada em background
- Resposta imediata (não aguarda processamento)

### CORS

O backend está configurado para aceitar requisições do frontend hospedado separadamente (ex: GitHub Pages). Configure `CORS_ORIGINS` no `.env` com as URLs permitidas.

---

## ⚙️ Configuração e Deploy

### Variáveis de Ambiente (`.env`)

```env
# Obrigatório
GEMINI_API_KEY=sua_chave_gemini_aqui

# E-mail (SMTP)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=sua_senha_de_app
EMAIL_FROM=noreply@petstory.com
EMAIL_FROM_NAME=PetStory

# Aplicação
DEBUG=False
TEMP_DIR=temp
GEMINI_IMAGE_MODEL=gemini-2.5-flash-image

# CORS (separado por vírgula ou JSON array)
CORS_ORIGINS=https://seu-usuario.github.io,http://localhost:3000
```

### Desenvolvimento Local

1. **Instalar dependências**:
```bash
uv sync
```

2. **Configurar `.env`** (copiar de `.env.example` e preencher)

3. **Executar servidor**:
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. **Acessar documentação**:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Docker

**Build**:
```bash
docker build -t petstory-backend .
```

**Executar**:
```bash
docker run -p 8000:8000 --env-file .env petstory-backend
```

### Deploy em Produção

1. Configurar variáveis de ambiente no servidor/hospedagem
2. Build da imagem Docker (ou instalar dependências diretamente)
3. Executar servidor (recomendado usar gunicorn ou similar para produção)
4. Configurar proxy reverso (nginx) se necessário
5. Configurar CORS com URLs do frontend

### Notas de Produção

- Use gunicorn ou similar (não apenas uvicorn direto)
- Configure rate limiting se necessário
- Monitore uso da API Gemini (cotas)
- Limpe arquivos temporários periodicamente
- Configure logs adequados
- Use HTTPS em produção
- Configure backup do diretório `temp` se necessário

---

## 🛠️ Tecnologias Utilizadas

### Backend

- **Python 3.12+**: Linguagem principal
- **FastAPI**: Framework web assíncrono
- **uv**: Gerenciador de pacotes moderno (alternativa ao pip)
- **Google Generative AI (Gemini)**: Geração de imagens com IA
- **FPDF2**: Geração de PDFs
- **Pillow (PIL)**: Processamento de imagens
- **Pydantic Settings**: Gerenciamento de configurações
- **Python-multipart**: Suporte a upload de arquivos

### Frontend

- **HTML5**: Estrutura
- **CSS3**: Estilização (com Tailwind CSS)
- **JavaScript (Vanilla)**: Interatividade
- **Tailwind CSS**: Framework CSS utility-first (via CDN)
- **Font Awesome**: Ícones
- **Google Fonts**: Fontes (Patrick Hand, Fredoka, Poppins)

### Infraestrutura

- **Docker**: Containerização
- **SMTP**: Envio de e-mails (Gmail ou outro servidor)

### Padrões e Boas Práticas

- **Strategy Pattern**: Para geração de imagens
- **Service Layer**: Separação de responsabilidades
- **Background Tasks**: Processamento assíncrono
- **Type Hints**: Python com type hints
- **Logging**: Sistema de logs estruturado
- **Error Handling**: Tratamento robusto de erros

---

## 📝 Notas Adicionais

### Limitações Conhecidas

- Rate limiting da API Gemini: delay de 2 segundos entre gerações
- Tamanho máximo de arquivo: 10MB por foto
- Máximo de fotos: 10 por pedido
- FPDF tem limitações com emojis (por isso há função `clean_text`)
- Sem banco de dados: arquivos temporários apenas

### Melhorias Futuras Possíveis

- Banco de dados para histórico de pedidos
- Dashboard administrativo
- Suporte a mais estilos artísticos
- Compressão automática de imagens grandes
- Sistema de fila (Redis/RabbitMQ) para processamento
- API de status de processamento
- Webhooks para notificações
- Suporte a vídeos
- Integração com redes sociais
- Sistema de pagamento integrado
- Cache de artes geradas
- Suporte a múltiplos idiomas

### Segurança

- Validação rigorosa de tipos de arquivo
- Validação de tamanho de arquivo
- Sanitização de entradas do usuário
- CORS configurável
- Logs sem informações sensíveis
- Credenciais via variáveis de ambiente

---

## 📞 Suporte e Contribuição

Para dúvidas, problemas ou contribuições, consulte o README.md principal do projeto.

---

**Última atualização**: Dezembro 2024
**Versão**: 0.1.0

