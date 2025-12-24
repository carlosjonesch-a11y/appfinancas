# 🚀 Guia de Deploy no Streamlit Cloud

## Pré-requisitos

1. **Conta no Streamlit Cloud**: https://app.streamlit.io
2. **Repositório GitHub com o código**
3. **Projeto Supabase configurado** com as tabelas criadas
4. **Credenciais Supabase** (URL, ANON_KEY e SERVICE_ROLE_KEY)

## Passo 1: Preparar o Repositório GitHub

✅ Certifique-se de que o código está no GitHub:

```bash
git push origin main
```

Arquivos importantes que o Streamlit Cloud vai buscar:
- `app.py` - Arquivo principal
- `requirements.txt` - Dependências
- `.streamlit/config.toml` - Configuração
- `pages/` - Diretório com páginas

## Passo 2: Configurar Supabase (Importante!)

### 2.1 Executar o Setup SQL

No Supabase, vá para **SQL Editor** e execute:

```sql
-- Copie e cole todo o conteúdo de supabase_setup.sql
```

Isso criará todas as tabelas necessárias:
- `usuarios`
- `categorias`
- `contas`
- `transacoes`
- `transacoes_recorrentes`
- `orcamentos`
- `investimentos`
- `investimentos_saldos`
- `metas` (novo)
- `contas_pagaveis` (novo)

### 2.2 Habilitar Row Level Security (RLS)

O script `supabase_setup.sql` já cria as políticas RLS. Verifique se estão ativas:

No Supabase Console:
- **Authentication > Policies** - Confirme que as políticas estão criadas

## Passo 3: Deploy no Streamlit Cloud

### 3.1 Conectar GitHub

1. Acesse https://app.streamlit.io
2. Clique em **"New app"**
3. Selecione seu repositório
4. Configure:
   - **Repository**: `carlosjonesch-a11y/appfinancas`
   - **Branch**: `main`
   - **Main file path**: `app.py`

### 3.2 Configurar Secrets

Após criar o app, vá para **Settings (⚙️) > Secrets**

Copie o conteúdo abaixo e substitua pelos seus valores:

```toml
SUPABASE_URL = "https://seu-projeto.supabase.co"
SUPABASE_ANON_KEY = "sua-chave-anon-aqui"
SUPABASE_KEY = "sua-service-role-key-aqui"
STORAGE_BACKEND = "supabase"
APP_NAME = "💰 Finanças Pessoais"
```

### 3.3 Obter as Credenciais do Supabase

No **Supabase Dashboard**:

1. **Settings > API**
   - `Project URL` → `SUPABASE_URL`
   - `anon public` → `SUPABASE_ANON_KEY`
   - `service_role secret` → `SUPABASE_KEY`

2. **Copie exatamente como aparecem**

## Passo 4: Verificar o Deploy

Após salvar os secrets:

1. O Streamlit Cloud vai **fazer deploy automaticamente**
2. Você verá o status em tempo real
3. Quando terminar, terá um link como: `https://app-nome.streamlit.app`

## Solução de Problemas

### ❌ Erro: "Invalid API key"

**Solução**: Verifique que:
- `SUPABASE_URL` começa com `https://`
- Termina com `.supabase.co`
- Sem `/` no final
- `SUPABASE_ANON_KEY` começa com `eyJ`

### ❌ Erro: "Access denied" ou "RLS Policy"

**Solução**:
- Verifique se executou `supabase_setup.sql` completo
- Confirme que as policies RLS estão ativas
- Use `SUPABASE_ANON_KEY` (não SERVICE_ROLE no app em produção)

### ❌ Erro: "Module not found"

**Solução**:
- Verifique `requirements.txt`
- Certifique-se que está no repositório
- Faça `git push` após qualquer alteração

### ❌ App demora para carregar

**Solução**:
- Streamlit Cloud tem recursos limitados
- Primeira execução é mais lenta (cold start)
- Se persistir, considere upgrade da conta

## Dicas Importantes

1. **Secrets são privadas**: Nunca commit `secrets.toml`
2. **Logs**: Vá em **Manage app > Logs** para ver erros
3. **Redeploy**: Qualquer push em `main` redeploy automaticamente
4. **Limpar cache**: Settings > Reboot script (se necessário)
5. **Monitoramento**: Use `st.write()` para debug no app

## Estrutura do Projeto

```
app finanças/
├── app.py                    # Arquivo principal
├── config.py                 # Configurações
├── requirements.txt          # Dependências Python
├── supabase_setup.sql        # Setup do banco (IMPORTANTE!)
├── .streamlit/
│   ├── config.toml          # Configuração do Streamlit
│   └── secrets.toml.example # Exemplo de secrets
├── pages/                    # Páginas do app
│   ├── dashboard.py
│   ├── transacoes.py
│   ├── categorias.py
│   ├── metas_contas.py       # NOVO
│   ├── orcamentos.py
│   ├── cartao_credito.py
│   ├── investimentos.py
│   └── configuracoes.py
├── services/                 # Serviços
│   ├── database.py           # Banco de dados
│   ├── supabase_auth.py      # Autenticação
│   ├── ocr.py
│   └── ...
└── models/                   # Modelos de dados

```

## Próximos Passos

1. ✅ Fazer push do código (`git push origin main`)
2. ✅ Criar app no Streamlit Cloud
3. ✅ Executar `supabase_setup.sql` no Supabase
4. ✅ Configurar secrets no Streamlit Cloud
5. ✅ Acessar a URL do app
6. ✅ Criar sua conta (signup)
7. ✅ Começar a usar!

## Suporte

- **Documentação Streamlit**: https://docs.streamlit.io
- **Documentação Supabase**: https://supabase.com/docs
- **Community Forum**: https://discuss.streamlit.io

---

**Última atualização**: 23 de dezembro de 2025
