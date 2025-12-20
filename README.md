# 💰 Finanças Pessoais

Aplicativo de gestão financeira pessoal com suporte a múltiplos usuários e leitura automática de cupons fiscais (OCR).

## ✨ Funcionalidades

- 📊 **Dashboard interativo** - Visualize suas finanças com gráficos
- 📸 **Leitura de cupons fiscais** - Escaneie NFCe/SAT com OCR
- 🤖 **Lançamento automático** - Importação direta dos itens do cupom
- ✏️ **Lançamento semi-automático** - Revise antes de salvar
- 🏷️ **Categorização inteligente** - Sugestão automática de categorias
- 👥 **Multi-usuário** - Cada pessoa tem seus próprios dados
- 📱 **Interface responsiva** - Funciona no celular e desktop

## 🚀 Instalação

### Pré-requisitos

- Python 3.9 ou superior
- pip (gerenciador de pacotes Python)

### Passos

1. **Clone ou baixe o projeto**

2. **Crie um ambiente virtual (recomendado)**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Instale as dependências**
```bash
pip install -r requirements.txt
```

4. **Configure as variáveis de ambiente**
```bash
# Copie o arquivo de exemplo
copy .env.example .env

# Edite o .env com suas configurações
```

5. **Configure o Supabase (opcional, mas recomendado)**
   - Crie uma conta gratuita em [supabase.com](https://supabase.com)
   - Crie um novo projeto
   - Execute o SQL de criação de tabelas (veja `models/__init__.py`)
   - Copie a URL e a chave anon para o arquivo `.env`

6. **Execute o aplicativo**
```bash
streamlit run app.py
```

## 📁 Estrutura do Projeto

```
app finanças/
├── app.py                 # Aplicativo principal
├── config.py              # Configurações
├── requirements.txt       # Dependências
├── .env.example          # Exemplo de variáveis de ambiente
├── .gitignore
├── README.md
├── data/                  # Dados locais (credenciais)
│   └── credentials.yaml
├── models/
│   └── __init__.py       # Modelos de dados e SQL
├── pages/
│   ├── __init__.py
│   ├── dashboard.py      # Página do dashboard
│   ├── transacoes.py     # Página de transações
│   └── categorias.py     # Página de categorias
└── services/
    ├── __init__.py
    ├── auth.py           # Serviço de autenticação
    ├── database.py       # Serviço de banco de dados
    └── ocr.py            # Serviço de OCR
```

## 🔧 Configuração do Supabase

1. Crie uma conta em [supabase.com](https://supabase.com)
2. Crie um novo projeto
3. Vá em **SQL Editor** e execute o script SQL em `models/__init__.py` (variável `SQL_CREATE_TABLES`)
4. Copie a **URL** e a **anon key** de **Settings > API**
5. Cole no arquivo `.env`

## 📸 Como usar o OCR

1. Vá em **➕ Nova Transação**
2. Clique na aba **📸 Escanear Cupom**
3. Faça upload da foto do cupom fiscal
4. Escolha o modo:
   - **Semi-automático**: Revise e edite os itens antes de salvar
   - **Automático**: Salva diretamente com categorização inteligente
5. Clique em **Processar Cupom**

### Dicas para melhor leitura

- Tire a foto com boa iluminação
- Mantenha o cupom reto e sem dobras
- Inclua todo o conteúdo na foto
- Prefira cupons térmicos legíveis

## 🛠️ Tecnologias

- **[Streamlit](https://streamlit.io/)** - Framework web
- **[EasyOCR](https://github.com/JaidedAI/EasyOCR)** - Reconhecimento de texto
- **[Supabase](https://supabase.com/)** - Banco de dados PostgreSQL
- **[Plotly](https://plotly.com/)** - Gráficos interativos
- **[Pandas](https://pandas.pydata.org/)** - Manipulação de dados

## 🚀 Deploy Gratuito

### Streamlit Cloud (Recomendado)

1. Suba o código para o GitHub
2. Acesse [share.streamlit.io](https://share.streamlit.io)
3. Clique em **New app** e selecione:
   - **Repository**: seu repositório
   - **Branch**: `main` (ou a branch que você usa)
   - **Main file path**: `app.py`
4. Em **App settings → Secrets**, cole as variáveis (veja o arquivo `.streamlit/secrets.toml.example`):
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `SECRET_KEY` (obrigatório para o cookie do login)
   - (opcional) `APP_NAME`, `DEBUG`
5. Deploy.

Observações importantes:
- O Streamlit Cloud não é armazenamento persistente. Arquivos locais (ex: `data/credentials.yaml`) podem ser perdidos se o app reiniciar.
- Para testes rápidos isso funciona; para produção, o ideal é mover autenticação/usuários para um backend (ex: Supabase Auth).
- **Não versionar** `data/credentials.yaml`: ele pode conter emails e hashes de senha. Ele já foi adicionado ao `.gitignore`.

### Render

1. Crie conta em [render.com](https://render.com)
2. Crie um novo Web Service
3. Conecte o repositório
4. Configure:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

## 📝 Próximas Funcionalidades (Roadmap)

- [ ] Orçamentos mensais por categoria
- [ ] Metas de economia
- [ ] Exportação para Excel/PDF
- [ ] Notificações e alertas
- [ ] Importação de extrato bancário
- [ ] Gráficos de tendência
- [ ] App mobile (PWA)

## 🤝 Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests.

## 📄 Licença

Este projeto é de uso livre para fins pessoais e educacionais.

---

Desenvolvido com ❤️ usando Python e Streamlit
