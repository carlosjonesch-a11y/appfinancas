"""
Serviço de leitura de QR Code de cupons fiscais (NFCe/SAT)
Extrai dados diretamente da URL da nota fiscal
Usa OpenCV para leitura de QR Code (mais compatível com Windows)
"""
import re
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime

# OpenCV para leitura de QR Code
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("⚠️ opencv-python não instalado. Execute: pip install opencv-python")

# PIL para manipulação de imagens
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Requests e BeautifulSoup para extrair dados da SEFAZ
try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️ requests/beautifulsoup4 não instalados")
    BeautifulSoup = None  # Evitar erro de type hint


@dataclass
class ItemNFCe:
    """Item extraído da NFCe"""
    codigo: str = ""
    descricao: str = ""
    quantidade: float = 1.0
    unidade: str = "UN"
    valor_unitario: float = 0.0
    valor_total: float = 0.0


@dataclass
class DadosNFCe:
    """Dados completos extraídos da NFCe via QR Code"""
    chave_acesso: str = ""
    numero: str = ""
    serie: str = ""
    data_emissao: Optional[datetime] = None
    
    # Emitente
    emitente_nome: str = ""
    emitente_cnpj: str = ""
    emitente_endereco: str = ""
    
    # Valores
    valor_produtos: float = 0.0
    valor_desconto: float = 0.0
    valor_total: float = 0.0
    
    # Forma de pagamento
    forma_pagamento: str = ""
    valor_pago: float = 0.0
    troco: float = 0.0
    
    # Itens
    itens: List[ItemNFCe] = field(default_factory=list)
    
    # Metadados
    url_consulta: str = ""
    estado: str = ""
    sucesso: bool = False
    erro: str = ""


class QRCodeService:
    """Serviço para leitura de QR Code de NFCe usando OpenCV"""
    
    # Headers para simular navegador
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    def __init__(self):
        self.qr_detector = None
        if CV2_AVAILABLE:
            self.qr_detector = cv2.QRCodeDetector()
    
    @property
    def is_available(self) -> bool:
        """Verifica se o serviço está disponível"""
        return CV2_AVAILABLE and PIL_AVAILABLE
    
    def ler_qrcode(self, image_data) -> Optional[str]:
        """
        Lê QR Code da imagem e retorna a URL usando OpenCV
        
        Args:
            image_data: PIL Image, bytes, ou caminho do arquivo
            
        Returns:
            URL extraída do QR Code ou None
        """
        if not self.is_available or self.qr_detector is None:
            return None
        
        try:
            # Converter para array numpy para OpenCV
            if isinstance(image_data, bytes):
                # Converter bytes para numpy array
                nparr = np.frombuffer(image_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            elif isinstance(image_data, str):
                # Ler do caminho
                img = cv2.imread(image_data)
            elif PIL_AVAILABLE and isinstance(image_data, Image.Image):
                # Converter PIL Image para numpy array
                img = np.array(image_data.convert('RGB'))
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            else:
                return None
            
            if img is None:
                return None
            
            # Tentar decodificar QR Code diretamente
            url, _, _ = self.qr_detector.detectAndDecode(img)
            
            if url:
                return url
            
            # Se não encontrou, tentar com pré-processamento
            url = self._tentar_preprocessamento(img)
            if url:
                return url
            
            return None
            
        except Exception as e:
            print(f"Erro ao ler QR Code: {e}")
            return None
    
    def _tentar_preprocessamento(self, img) -> Optional[str]:
        """Tenta diferentes pré-processamentos para encontrar QR Code"""
        if not CV2_AVAILABLE or self.qr_detector is None:
            return None
        
        # Converter para escala de cinza
        if len(img.shape) == 3:
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            img_gray = img
        
        tentativas = []
        
        # Tentativa 1: Threshold adaptativo
        thresh1 = cv2.adaptiveThreshold(
            img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        tentativas.append(cv2.cvtColor(thresh1, cv2.COLOR_GRAY2BGR))
        
        # Tentativa 2: Otsu threshold
        _, thresh2 = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        tentativas.append(cv2.cvtColor(thresh2, cv2.COLOR_GRAY2BGR))
        
        # Tentativa 3: Aumentar contraste com CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(img_gray)
        tentativas.append(cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR))
        
        # Tentativa 4: Resize (aumentar 2x)
        scale = 2
        resized = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        tentativas.append(resized)
        
        # Tentativa 5: Blur + threshold
        blurred = cv2.GaussianBlur(img_gray, (5, 5), 0)
        _, thresh3 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        tentativas.append(cv2.cvtColor(thresh3, cv2.COLOR_GRAY2BGR))
        
        for processed_img in tentativas:
            url, _, _ = self.qr_detector.detectAndDecode(processed_img)
            if url:
                return url
        
        return None
    
    def extrair_dados_url(self, url: str) -> DadosNFCe:
        """
        Extrai dados da NFCe acessando a URL da SEFAZ
        
        Args:
            url: URL do QR Code da NFCe
            
        Returns:
            DadosNFCe com informações extraídas
        """
        dados = DadosNFCe(url_consulta=url)
        
        if not REQUESTS_AVAILABLE:
            dados.erro = "Biblioteca requests não disponível"
            return dados
        
        try:
            # Desativar avisos de SSL
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Identificar estado pela URL
            dados.estado = self._identificar_estado(url)
            
            # Extrair chave de acesso da URL
            dados.chave_acesso = self._extrair_chave_acesso(url)
            
            # Acessar página da SEFAZ
            response = requests.get(url, headers=self.HEADERS, timeout=15, verify=False)
            response.raise_for_status()
            
            # Parse do HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair dados conforme layout do estado
            self._extrair_dados_html(soup, dados)
            
            dados.sucesso = True
            
        except requests.Timeout:
            dados.erro = "Timeout ao acessar SEFAZ"
        except requests.RequestException as e:
            dados.erro = f"Erro de conexão: {str(e)}"
        except Exception as e:
            dados.erro = f"Erro ao processar: {str(e)}"
        
        return dados
    
    def _identificar_estado(self, url: str) -> str:
        """Identifica o estado pela URL"""
        url_lower = url.lower()
        
        estados_map = {
            'sp.gov.br': 'SP', 'fazenda.sp': 'SP', 'nfce.fazenda.sp': 'SP',
            'rj.gov.br': 'RJ', 'fazenda.rj': 'RJ',
            'mg.gov.br': 'MG', 'fazenda.mg': 'MG',
            'rs.gov.br': 'RS', 'sefaz.rs': 'RS',
            'pr.gov.br': 'PR', 'fazenda.pr': 'PR',
            'sc.gov.br': 'SC', 'sef.sc': 'SC',
            'ba.gov.br': 'BA', 'sefaz.ba': 'BA',
            'pe.gov.br': 'PE', 'sefaz.pe': 'PE',
            'ce.gov.br': 'CE', 'sefaz.ce': 'CE',
            'go.gov.br': 'GO', 'sefaz.go': 'GO',
            'df.gov.br': 'DF', 'fazenda.df': 'DF',
            'es.gov.br': 'ES', 'sefaz.es': 'ES',
            'mt.gov.br': 'MT', 'sefaz.mt': 'MT',
            'ms.gov.br': 'MS', 'sefaz.ms': 'MS',
            'pa.gov.br': 'PA', 'sefa.pa': 'PA',
            'am.gov.br': 'AM', 'sefaz.am': 'AM',
            'ma.gov.br': 'MA', 'sefaz.ma': 'MA',
            'pb.gov.br': 'PB', 'sefaz.pb': 'PB',
            'rn.gov.br': 'RN', 'set.rn': 'RN',
            'al.gov.br': 'AL', 'sefaz.al': 'AL',
            'se.gov.br': 'SE', 'sefaz.se': 'SE',
            'pi.gov.br': 'PI', 'sefaz.pi': 'PI',
            'to.gov.br': 'TO', 'sefaz.to': 'TO',
            'ro.gov.br': 'RO', 'sefin.ro': 'RO',
            'ac.gov.br': 'AC', 'sefaz.ac': 'AC',
            'ap.gov.br': 'AP', 'sefaz.ap': 'AP',
            'rr.gov.br': 'RR', 'sefaz.rr': 'RR',
        }
        
        for pattern, estado in estados_map.items():
            if pattern in url_lower:
                return estado
        
        return "BR"
    
    def _extrair_chave_acesso(self, url: str) -> str:
        """Extrai a chave de acesso da URL"""
        # Padrão: 44 dígitos consecutivos
        match = re.search(r'chNFe=(\d{44})', url)
        if match:
            return match.group(1)
        
        match = re.search(r'p=(\d{44})', url)
        if match:
            return match.group(1)
        
        # Tentar encontrar 44 dígitos em qualquer lugar
        match = re.search(r'(\d{44})', url)
        if match:
            return match.group(1)
        
        return ""
    
    def _extrair_dados_html(self, soup: BeautifulSoup, dados: DadosNFCe):
        """Extrai dados do HTML da página da SEFAZ"""
        
        # Tentar diferentes seletores comuns
        self._extrair_emitente(soup, dados)
        self._extrair_valores(soup, dados)
        self._extrair_itens(soup, dados)
        self._extrair_pagamento(soup, dados)
        self._extrair_data(soup, dados)
    
    def _extrair_emitente(self, soup: BeautifulSoup, dados: DadosNFCe):
        """Extrai dados do emitente"""
        # Seletores comuns para nome do emitente
        seletores_nome = [
            'div.txtTopo',
            'div.emit',
            '.txtTopo',
            '#u20',
            '.NFCCabecalho_SubTitulo',
            'div[class*="emit"]',
            'span[class*="razao"]',
        ]
        
        for seletor in seletores_nome:
            elem = soup.select_one(seletor)
            if elem and elem.get_text(strip=True):
                dados.emitente_nome = elem.get_text(strip=True)
                break
        
        # Se não encontrou, tentar por texto
        if not dados.emitente_nome:
            for div in soup.find_all(['div', 'span']):
                text = div.get_text(strip=True)
                # Procurar por padrões de nome de empresa
                if text and len(text) > 5 and len(text) < 100:
                    if any(x in text.upper() for x in ['LTDA', 'EIRELI', 'S/A', 'ME', 'EPP', 'COMERCIO', 'SUPERMERCADO', 'MERCADO', 'LOJA']):
                        dados.emitente_nome = text
                        break
        
        # Extrair CNPJ
        cnpj_pattern = re.compile(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}')
        cnpj_match = cnpj_pattern.search(soup.get_text())
        if cnpj_match:
            dados.emitente_cnpj = cnpj_match.group()
    
    def _extrair_valores(self, soup: BeautifulSoup, dados: DadosNFCe):
        """Extrai valores totais"""
        texto_completo = soup.get_text(separator=' ', strip=True)
        
        # 1. Tentar encontrar "Total a Pagar" ou similar (Alta confiança)
        patterns_alta_prioridade = [
            r'(?:VALOR|TOTAL)\s*A\s*PAGAR[:\s]*R?\$?\s*([\d.,]+)',
            r'TOTAL\s*DA\s*NOTA[:\s]*R?\$?\s*([\d.,]+)',
        ]
        
        for pattern in patterns_alta_prioridade:
            matches = re.findall(pattern, texto_completo, re.IGNORECASE)
            if matches:
                # Geralmente o último é o correto (caso haja repetições)
                valor_str = matches[-1].replace('.', '').replace(',', '.')
                try:
                    dados.valor_total = float(valor_str)
                    break
                except ValueError:
                    continue
        
        # 2. Se não encontrou, tentar "Total" genérico (Baixa confiança)
        if not dados.valor_total:
            # Procurar por "Total" isolado, mas pegar o ÚLTIMO encontrado
            # pois o total geral costuma ficar no rodapé
            pattern_generico = r'\bTOTAL[:\s]*R?\$?\s*([\d.,]+)'
            matches = re.findall(pattern_generico, texto_completo, re.IGNORECASE)
            if matches:
                valor_str = matches[-1].replace('.', '').replace(',', '.')
                try:
                    dados.valor_total = float(valor_str)
                except ValueError:
                    pass
        
        # Procurar valor dos produtos
        match = re.search(r'(?:Valor\s*dos?\s*)?Produtos?[:\s]*R?\$?\s*([\d.,]+)', texto_completo, re.IGNORECASE)
        if match:
            valor_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                dados.valor_produtos = float(valor_str)
            except ValueError:
                pass
    
    def _extrair_itens(self, soup: BeautifulSoup, dados: DadosNFCe):
        """Extrai lista de itens"""
        # Seletores comuns para tabela de itens
        tabelas = soup.select('table')
        
        for tabela in tabelas:
            rows = tabela.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    # Tentar extrair item
                    item = self._parse_item_row(cols)
                    if item and item.descricao:
                        dados.itens.append(item)
        
        # Se não encontrou em tabelas, tentar divs
        if not dados.itens:
            self._extrair_itens_divs(soup, dados)
    
    def _parse_item_row(self, cols) -> Optional[ItemNFCe]:
        """Parse de uma linha de item"""
        item = ItemNFCe()
        
        try:
            # Usar separator=' ' para evitar que textos colem (ex: Produto(Código) -> Produto (Código))
            texts = [col.get_text(separator=' ', strip=True) for col in cols]
            texts = [t for t in texts if t]
            
            if len(texts) >= 2:
                # 1. Descrição: geralmente a primeira coluna com texto longo
                for text in texts:
                    # Ignorar colunas que parecem ser apenas código ou numéricas
                    if len(text) > 2 and not re.match(r'^[\d\s.,]+$', text):
                        # Ignorar cabeçalhos
                        if any(h in text.upper() for h in ['CÓDIGO', 'DESCRIÇÃO', 'QTD', 'UN', 'VALOR', 'TOTAL']):
                            if len(text) < 15: continue
                        
                        if not item.descricao:
                            item.descricao = text
                            # Limpar sufixos comuns que grudam (ex: (Código: ...))
                            item.descricao = re.split(r'\(Cód', item.descricao, flags=re.IGNORECASE)[0].strip()
                            break
                
                # 2. Valor: procurar padrão monetário nas colunas
                # Priorizar as últimas colunas (geralmente Total é a última)
                for text in reversed(texts):
                    # Padrão R$ 0,00 ou 0,00
                    # Aceita espaços entre R$ e o número
                    match = re.search(r'(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})', text)
                    if match:
                        valor_str = match.group(1).replace('.', '').replace(',', '.')
                        try:
                            val = float(valor_str)
                            if val > 0:
                                item.valor_total = val
                                break
                        except: pass
                
                # 3. Quantidade
                for text in texts:
                    # Padrão Qtd: 1,00 ou apenas 1,00 UN
                    match = re.search(r'(?:Qtde?|Qtd)[:\s]*([\d.,]+)', text, re.IGNORECASE)
                    if match:
                        try:
                            item.quantidade = float(match.group(1).replace(',', '.'))
                            break
                        except: pass
                    
                    # Padrão numérico solto seguido de UN/KG
                    match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:UN|KG|L|M|PCT|CX|PC)', text, re.IGNORECASE)
                    if match:
                        try:
                            item.quantidade = float(match.group(1).replace(',', '.'))
                            break
                        except: pass

                if item.descricao:
                    # Ignorar linhas que parecem totais ou cabeçalhos
                    termos_ignorados = ['TOTAL', 'SUBTOTAL', 'VALOR', 'PAGAMENTO', 'TROCO', 'EMITENTE', 'CNPJ', 'IE', 'A PAGAR', 'TRIBUTOS']
                    if any(termo in item.descricao.upper() for termo in termos_ignorados):
                        return None
                    return item
        except Exception:
            pass
        
        return None
    
    def _extrair_itens_divs(self, soup: BeautifulSoup, dados: DadosNFCe):
        """Tenta extrair itens de divs quando não há tabela"""
        # Usar separator newline para processar linha a linha
        texto = soup.get_text(separator='\n')
        linhas = texto.split('\n')
        
        for linha in linhas:
            linha = linha.strip()
            if not linha: continue
            
            # Tentar encontrar padrão: NOME DO PRODUTO ... VALOR
            # Ex: CERVEJA 350ML 10 UN x 3,50 (35,00)
            
            # Regex para capturar valor no final da linha (formato brasileiro 0,00)
            match_valor = re.search(r'(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})\s*$', linha)
            
            if match_valor:
                valor_str = match_valor.group(1).replace('.', '').replace(',', '.')
                try:
                    valor = float(valor_str)
                    
                    # O que vem antes é a descrição (simplificado)
                    descricao = linha[:match_valor.start()].strip()
                    
                    # Limpar sufixos de quantidade se houver (ex: 2 UN x 10,00)
                    # Remove "2 UN x 10,00" do final da descrição
                    descricao = re.sub(r'\d+\s*(?:UN|KG|L|M|PCT|CX|PC)?\s*[xX]\s*[\d.,]+.*$', '', descricao, flags=re.IGNORECASE).strip()
                    
                    # Validar descrição
                    termos_ignorados = ['TOTAL', 'SUBTOTAL', 'VALOR', 'PAGAMENTO', 'TROCO', 'EMITENTE', 'CNPJ', 'IE', 'A PAGAR', 'TRIBUTOS', 'DINHEIRO', 'CARTAO', 'CREDITO', 'DEBITO']
                    
                    # Descrição deve ter tamanho mínimo e não ser apenas números
                    if len(descricao) > 3 and not descricao.replace(' ', '').isdigit():
                        if not any(t in descricao.upper() for t in termos_ignorados):
                            item = ItemNFCe()
                            item.descricao = descricao
                            item.valor_total = valor
                            dados.itens.append(item)
                except:
                    continue
    
    def _extrair_pagamento(self, soup: BeautifulSoup, dados: DadosNFCe):
        """Extrai forma de pagamento"""
        texto = soup.get_text()
        
        # Formas de pagamento comuns
        formas = ['DINHEIRO', 'CARTÃO', 'CREDITO', 'DÉBITO', 'DEBITO', 'PIX', 'VALE', 'CHEQUE']
        
        for forma in formas:
            if forma in texto.upper():
                dados.forma_pagamento = forma.title()
                break
        
        # Valor pago
        match = re.search(r'(?:Valor\s*)?Pago[:\s]*R?\$?\s*([\d.,]+)', texto, re.IGNORECASE)
        if match:
            try:
                dados.valor_pago = float(match.group(1).replace('.', '').replace(',', '.'))
            except ValueError:
                pass
        
        # Troco
        match = re.search(r'Troco[:\s]*R?\$?\s*([\d.,]+)', texto, re.IGNORECASE)
        if match:
            try:
                dados.troco = float(match.group(1).replace('.', '').replace(',', '.'))
            except ValueError:
                pass
    
    def _extrair_data(self, soup: BeautifulSoup, dados: DadosNFCe):
        """Extrai data de emissão"""
        texto = soup.get_text()
        
        # Padrões de data
        patterns = [
            r'(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}(?::\d{2})?)',  # DD/MM/YYYY HH:MM:SS
            r'(\d{2}/\d{2}/\d{4})',  # DD/MM/YYYY
            r'(\d{4}-\d{2}-\d{2})T?(\d{2}:\d{2}(?::\d{2})?)?',  # ISO format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, texto)
            if match:
                try:
                    data_str = match.group(1)
                    if '/' in data_str:
                        if len(match.groups()) > 1 and match.group(2):
                            dados.data_emissao = datetime.strptime(
                                f"{data_str} {match.group(2)}", 
                                "%d/%m/%Y %H:%M:%S" if ':' in match.group(2) and match.group(2).count(':') == 2 else "%d/%m/%Y %H:%M"
                            )
                        else:
                            dados.data_emissao = datetime.strptime(data_str, "%d/%m/%Y")
                    else:
                        dados.data_emissao = datetime.fromisoformat(data_str)
                    break
                except ValueError:
                    continue
    
    def processar_imagem(self, image_data) -> DadosNFCe:
        """
        Processa imagem completa: lê QR Code e extrai dados
        
        Args:
            image_data: bytes da imagem, caminho ou PIL Image
            
        Returns:
            DadosNFCe com todos os dados extraídos
        """
        # Primeiro, ler o QR Code
        url = self.ler_qrcode(image_data)
        
        if not url:
            dados = DadosNFCe()
            dados.erro = "Não foi possível ler o QR Code da imagem. Certifique-se de que o QR Code está visível e nítido."
            return dados
        
        # Se é uma URL válida, extrair dados
        if url.startswith('http'):
            return self.extrair_dados_url(url)
        else:
            dados = DadosNFCe()
            dados.erro = f"QR Code não contém URL válida: {url[:100]}"
            return dados


# Instância global
qrcode_service = QRCodeService()


# Função auxiliar para uso direto
def ler_cupom_qrcode(image_data) -> DadosNFCe:
    """
    Função de conveniência para ler cupom fiscal via QR Code
    
    Args:
        image_data: bytes da imagem, caminho do arquivo ou PIL Image
        
    Returns:
        DadosNFCe com os dados extraídos
    """
    return qrcode_service.processar_imagem(image_data)
