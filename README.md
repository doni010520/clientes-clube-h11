# 🔄 Cashbarber → Supabase Sync

Sistema automatizado de sincronização de assinantes do painel Cashbarber para banco de dados Supabase.

## 📋 Visão Geral

Este projeto automatiza:
1. **Login** no painel administrativo do Cashbarber
2. **Navegação** até o relatório "Quantidade de assinantes"
3. **Extração** de dados da tabela (Cliente, Plano, Status)
4. **Sincronização** com banco Supabase usando fuzzy matching
5. **Atualização** de tipo de plano e status para cada cliente

## 🏗️ Arquitetura
```
┌─────────────────┐
│   Cashbarber    │
│     Painel      │
└────────┬────────┘
         │ Selenium
         ↓
┌─────────────────┐
│   Web Scraper   │
│  (extrator.py)  │
└────────┬────────┘
         │ BeautifulSoup
         ↓
┌─────────────────┐
│  Fuzzy Matcher  │
│ (integration.py)│
└────────┬────────┘
         │ Supabase Client
         ↓
┌─────────────────┐
│    Supabase     │
│    Database     │
└─────────────────┘
```

## 🚀 Deploy no Easypanel

### 1. Configure Variáveis de Ambiente

No Easypanel, vá em **Settings > Environment Variables** e adicione:
```env
CASHBARBER_EMAIL=seu@email.com
CASHBARBER_PASSWORD=suasenha
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SERVICE_KEY=sua_service_key
SUPABASE_TABLE_NAME=clientes
COLUMN_NOME=nome
COLUMN_PLANO=plano
COLUMN_STATUS=status_plano
COLUMN_TIMESTAMP=ultimo_contato
```

### 2. Configure Cron Job
```yaml
Schedule: 0 6 * * *
Command: python /app/main.py --email ${CASHBARBER_EMAIL} --password ${CASHBARBER_PASSWORD}
```

## 📊 Mapeamento de Campos

| Cashbarber | Supabase (`public.clientes`) |
|------------|------------------------------|
| Cliente    | `nome` (usado para matching) |
| Plano      | `plano` (atualizado)         |
| Status     | `status_plano` (atualizado)  |
| Timestamp  | `ultimo_contato` (atualizado)|

**Outros campos NÃO são alterados**: telefone, email, cpf, endereco, ia_on_off, etc.

## 🔍 Fuzzy Matching

A aplicação encontra clientes mesmo com variações:
```
Cashbarber: "João Silva"
Supabase:   "Joao da Silva"
Match: ✅ 87% similaridade
```

## ⚙️ Uso Local (Teste)
```bash
# Instalar dependências
pip install -r requirements.txt

# Teste dry-run
python main.py --email seu@email.com --password senha --dry-run

# Executar sincronização
python main.py --email seu@email.com --password senha
```

## 📖 Documentação

- **START_HERE.md** - Comece por aqui
- **SEU_SETUP.md** - Guia personalizado
- **EASYPANEL_GUIDE.md** - Deploy detalhado

## 🔐 Segurança

- Nunca commite credenciais no código
- Use variáveis de ambiente
- Service Role Key do Supabase (não anon key)

## 📝 Licença

MIT License
