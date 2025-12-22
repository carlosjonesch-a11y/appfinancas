# 💰 Finanças Pessoais

Aplicativo de gestão financeira pessoal com leitura automática de cupons fiscais (OCR).

## ✨ Funcionalidades

- 📊 **Dashboard interativo** - Visualize suas finanças com gráficos
- 📸 **Leitura de cupons fiscais** - Escaneie NFCe/SAT com OCR
- 🤖 **Lançamento automático** - Importação direta dos itens do cupom
- ✏️ **Lançamento semi-automático** - Revise antes de salvar
- 🏷️ **Categorização inteligente** - Sugestão automática de categorias
- 👤 **Usuário único** - Foco em uso pessoal (sem login)
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

5. **Execute o aplicativo**
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
├── data/                  # Opcional (dev local); não versionado
├── models/
│   └── __init__.py       # Modelos de dados
├── pages/
│   ├── __init__.py
│   ├── dashboard.py      # Página do dashboard
│   ├── transacoes.py     # Página de transações
│   └── categorias.py     # Página de categorias
└── services/
    ├── __init__.py
    ├── database.py       # Serviço de banco de dados
    └── ocr.py            # Serviço de OCR
```

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
4. Em **App settings → Secrets**, cole:
   - `APP_NAME`, `DEBUG`
   - `STORAGE_BACKEND = "supabase"`
   - `SUPABASE_URL = "https://<seu-projeto>.supabase.co"`
   - `SUPABASE_ANON_KEY = "<anon_public_key>"`
5. Deploy.

Observações importantes:
- Com `STORAGE_BACKEND=supabase`, seus dados ficam persistidos no Supabase.
- Arquivos locais em `data/` não são persistentes no Streamlit Cloud.
- No modo Supabase, o app pede login (email/senha) e isola os dados por usuário via RLS.

## 🧪 Popular dados de exemplo (Supabase)

1. No Supabase, execute o SQL de setup do arquivo `supabase_setup.sql`.
2. Crie `.streamlit/secrets.toml` (não versionado) com:
   - `STORAGE_BACKEND = "supabase"`
   - `SUPABASE_URL = "https://<seu-projeto>.supabase.co"`
   - `SUPABASE_KEY = "<service_role_key>"`
3. Rode o script:
```bash
python scripts/popular_banco.py popular
```

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
