# Integração com Mercado Pago

Este documento explica como configurar e usar a integração com Mercado Pago para processar pagamentos de R$ 47,00.

## 📋 Configuração

### 1. Obter Credenciais do Mercado Pago

1. Acesse [Mercado Pago Developers](https://www.mercadopago.com.br/developers)
2. Crie uma conta ou faça login
3. Vá em **Suas integrações** → **Criar aplicação**
4. Copie o **Access Token** (Token de produção ou Token de teste)

### 2. Configurar Variáveis de Ambiente

Adicione as seguintes variáveis no seu arquivo `.env`:

```env
# Mercado Pago
MERCADOPAGO_ACCESS_TOKEN=seu_access_token_aqui
MERCADOPAGO_PUBLIC_KEY=seu_public_key_aqui  # Opcional, para frontend
MERCADOPAGO_PRODUCT_PRICE=47.0  # Preço em reais (padrão: 47.0)
MERCADOPAGO_WEBHOOK_SECRET=seu_webhook_secret  # Opcional

# URL base da API (para webhooks e redirects)
API_BASE_URL=https://seu-dominio.com  # ou http://localhost:8000 para desenvolvimento
```

### 3. Configurar Webhook (Produção)

1. No painel do Mercado Pago, vá em **Webhooks**
2. Configure a URL: `https://seu-dominio.com/api/payment/webhook`
3. Selecione os eventos: **Pagamentos** → **Pagamento aprovado**

## 🔄 Fluxo de Pagamento

### 1. Criar Preferência de Pagamento

**Endpoint:** `POST /api/payment/create`

**Body (form-data):**
```
email: cliente@email.com
pet_name: Spike
```

**Resposta:**
```json
{
  "status": "success",
  "checkout_url": "https://www.mercadopago.com.br/checkout/v1/redirect?pref_id=...",
  "preference_id": "1234567890"
}
```

### 2. Redirecionar para Checkout

O frontend deve redirecionar o usuário para `checkout_url` retornado.

### 3. Após o Pagamento

O Mercado Pago redireciona para:
- **Sucesso:** `/api/payment/success?email=...&pet_name=...&payment_id=...`
- **Falha:** `/api/payment/failure`
- **Pendente:** `/api/payment/pending`

### 4. Webhook (Notificação)

O Mercado Pago também envia uma notificação para `/api/payment/webhook` quando o status do pagamento muda.

### 5. Upload de Fotos

Após pagamento aprovado, o usuário pode fazer upload:

**Endpoint:** `POST /api/upload`

**Body (form-data):**
```
nome_pet: Spike
pet_date: 23 de dezembro de 2024
pet_story: História do pet...
email: cliente@email.com
fotos: [arquivos]
payment_id: 1234567890  # Opcional, para verificação adicional
```

**Validação:**
- O sistema verifica se há um pagamento aprovado para o email + nome do pet
- Se `payment_id` for fornecido, verifica diretamente no Mercado Pago
- Se não houver pagamento aprovado, retorna erro 402 (Payment Required)

## 🔧 Endpoints Disponíveis

### `POST /api/payment/create`
Cria uma preferência de pagamento no Mercado Pago.

**Parâmetros:**
- `email` (obrigatório): Email do cliente
- `pet_name` (obrigatório): Nome do pet

**Resposta:**
- `checkout_url`: URL para redirecionar o usuário
- `preference_id`: ID da preferência criada

### `POST /api/payment/webhook`
Recebe notificações do Mercado Pago sobre mudanças no status do pagamento.

**Uso:** Configurado automaticamente no Mercado Pago.

### `GET /api/payment/success`
Página de sucesso após pagamento aprovado.

**Parâmetros (query string):**
- `email`: Email do cliente
- `pet_name`: Nome do pet
- `payment_id` (opcional): ID do pagamento
- `status` (opcional): Status do pagamento

### `GET /api/payment/failure`
Página de falha após pagamento rejeitado.

### `GET /api/payment/pending`
Página de pagamento pendente.

## 🧪 Testando em Sandbox

Para testar sem usar dinheiro real:

1. Use o **Token de teste** do Mercado Pago
2. Configure `MERCADOPAGO_ACCESS_TOKEN` com o token de teste
3. O sistema retornará `sandbox_init_point` no lugar de `init_point`
4. Use os [cartões de teste do Mercado Pago](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro/additional-content/test-cards)

### Cartões de Teste

- **Aprovado:** `5031 4332 1540 6351` (CVV: 123, Vencimento: 11/25)
- **Rejeitado:** `5031 4332 1540 6351` (CVV: 123, Vencimento: 11/25) - usar valor que cause rejeição

## 📝 Exemplo de Uso no Frontend

```javascript
// 1. Criar pagamento
const formData = new FormData();
formData.append('email', 'cliente@email.com');
formData.append('pet_name', 'Spike');

const response = await fetch('/api/payment/create', {
  method: 'POST',
  body: formData
});

const { checkout_url } = await response.json();

// 2. Redirecionar para checkout
window.location.href = checkout_url;

// 3. Após retornar do Mercado Pago (na página de sucesso)
// O usuário pode fazer upload das fotos
```

## ⚠️ Importante

1. **Armazenamento de Pagamentos:** Atualmente usa armazenamento em memória (para MVP). Em produção, substitua por um banco de dados.

2. **Validação de Webhook:** Para produção, implemente validação do webhook usando `MERCADOPAGO_WEBHOOK_SECRET`.

3. **URL Base:** Configure `API_BASE_URL` corretamente para que os webhooks funcionem.

4. **Timeout de Pagamento:** Os pagamentos expiram em 24 horas. Após isso, o usuário precisa criar um novo pagamento.

5. **Limpeza:** O sistema limpa automaticamente pagamentos com mais de 7 dias.

## 🐛 Troubleshooting

### Erro: "Payment service not configured"
- Verifique se `MERCADOPAGO_ACCESS_TOKEN` está configurado no `.env`

### Erro: "Pagamento não verificado"
- O pagamento pode não ter sido aprovado ainda
- Verifique o status no painel do Mercado Pago
- Aguarde alguns segundos após o pagamento (webhook pode demorar)

### Webhook não está sendo chamado
- Verifique se a URL está acessível publicamente (não funciona com localhost)
- Use um serviço como [ngrok](https://ngrok.com/) para testar localmente
- Verifique os logs do Mercado Pago no painel

## 📚 Referências

- [Documentação Mercado Pago](https://www.mercadopago.com.br/developers/pt/docs)
- [SDK Python](https://github.com/mercadopago/sdk-python)

