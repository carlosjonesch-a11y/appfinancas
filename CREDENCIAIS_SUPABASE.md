# 📚 Guia: Obter Credenciais do Supabase

## Passo 1: Acesse o Supabase
```
https://app.supabase.com
```

## Passo 2: Selecione seu projeto
- Procure pelo nome do projeto na lista

## Passo 3: Vá em Settings
- Clique no ícone de **engrenagem (⚙️)** no canto inferior esquerdo
- Ou vá em **Project Settings** no menu

## Passo 4: Clique em "API"
- No menu lateral, procure por **"API"** ou **"API Settings"**

## Passo 5: Copie as Credenciais

Você verá uma tabela com:

```
Project URL:            https://xxxxxxxxxxxxx.supabase.co
Anon public:           eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Service role secret:   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Copiar cada uma:

1. **SUPABASE_URL**
   - Copie: `Project URL` inteiro
   - Exemplo: `https://seu-projeto.supabase.co`

2. **SUPABASE_ANON_KEY** ⭐ (Essa é a que estava dando erro!)
   - Copie: `anon public`
   - Começa com: `eyJ`
   - Tem dois pontos `.`
   - Exemplo: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3Mi...`

3. **SUPABASE_KEY**
   - Copie: `service_role secret`
   - Igual ao anterior (começa com `eyJ`)

## Passo 6: Cole no arquivo

Abra: `c:\vscode\app finanças\.streamlit\secrets.toml`

```toml
SUPABASE_URL = "https://seu-projeto.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3Mi..."
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3Mi..."
STORAGE_BACKEND = "supabase"
```

## Passo 7: Salve e Teste

- Salve o arquivo (Ctrl+S)
- O Streamlit vai recarregar automaticamente
- Se tudo certo, você vê a página de login

---

## ⚠️ Erros Comuns

### ❌ "Invalid API key"
- Você copiou a chave errada
- Use a **ANON (public)**, não a service role para teste
- Certifique-se que começa com `eyJ`

### ❌ "Access denied" ou "RLS Policy"
- Verifique se executou o `supabase_setup.sql` no Supabase
- As políticas RLS precisam estar criadas

### ❌ Arquivo não é lido
- Certifique-se que o arquivo é: `.streamlit/secrets.toml`
- Não use `.example`
- Sem espaços no nome

---

## 🆘 Precisa de Ajuda?

Se mesmo assim não funcionar:
1. Verifique se copiar os caracteres especiais (não é formatação)
2. Não use aspas ou espaços extras
3. Teste o URL no navegador: `https://seu-projeto.supabase.co` (deve abrir)

