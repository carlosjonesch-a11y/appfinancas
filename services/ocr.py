"""
Serviço de OCR para leitura de cupons fiscais
Suporta NFCe e SAT com extração automática de dados
"""
import re
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
import io

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from config import Config


@dataclass
class ItemExtraido:
    """Item extraído do cupom"""
    codigo: str = ""
    descricao: str = ""
    quantidade: float = 1.0
    valor_unitario: float = 0.0
    valor_total: float = 0.0
    categoria_sugerida: str = ""


@dataclass
class CupomExtraido:
    """Dados extraídos do cupom fiscal"""
    estabelecimento: str = ""
    cnpj: str = ""
    endereco: str = ""
    data: Optional[datetime] = None
    itens: List[ItemExtraido] = None
    subtotal: float = 0.0
    desconto: float = 0.0
    total: float = 0.0
    forma_pagamento: str = ""
    texto_bruto: str = ""
    confianca: float = 0.0
    
    def __post_init__(self):
        if self.itens is None:
            self.itens = []


class OCRService:
    """Serviço de OCR para processamento de cupons fiscais"""
    
    _reader: Optional["easyocr.Reader"] = None
    
    def __init__(self):
        self._initialize_reader()
    
    def _initialize_reader(self):
        """Inicializa o leitor EasyOCR"""
        if not EASYOCR_AVAILABLE:
            print("⚠️ EasyOCR não instalado. Execute: pip install easyocr")
            return
        
        if OCRService._reader is None:
            try:
                OCRService._reader = easyocr.Reader(
                    Config.OCR_IDIOMAS,
                    gpu=Config.OCR_GPU,
                    download_enabled=True,
                    model_storage_directory=None,
                    user_network_directory=None,
                    recog_network='standard',
                    detector=True,
                    recognizer=True,
                    verbose=False,
                    quantize=True,
                    cudnn_benchmark=False
                )
                print("✅ EasyOCR inicializado")
            except Exception as e:
                print(f"❌ Erro ao inicializar EasyOCR: {e}")
    
    @property
    def is_available(self) -> bool:
        """Verifica se o OCR está disponível"""
        return EASYOCR_AVAILABLE and OCRService._reader is not None
    
    def preprocessar_imagem(self, image: Image.Image) -> Image.Image:
        """Pré-processa a imagem para melhor OCR preservando qualidade"""
        if not PIL_AVAILABLE:
            return image
        
        # Redimensionar se muito grande (manter qualidade)
        max_dimension = 3000
        width, height = image.size
        if width > max_dimension or height > max_dimension:
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Converter para RGB se necessário (melhor para OCR)
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')
        
        # Processamento suave com OpenCV se disponível
        if CV2_AVAILABLE and image.mode == 'RGB':
            img_array = np.array(image)
            
            # Converter para escala de cinza
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Aplicar denoising suave
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            
            # Aumentar contraste adaptativo (CLAHE)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            
            # Aplicar threshold adaptativo para binarização inteligente
            binary = cv2.adaptiveThreshold(
                enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            
            image = Image.fromarray(binary)
        elif image.mode == 'RGB':
            # Fallback sem OpenCV - processamento mínimo
            image = image.convert('L')
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
        
        return image
    
    def extrair_texto(self, image_data) -> Tuple[str, float]:
        """
        Extrai texto da imagem
        
        Args:
            image_data: PIL Image, bytes, ou caminho do arquivo
            
        Returns:
            Tuple[texto, confiança média]
        """
        if not self.is_available:
            return "", 0.0
        
        try:
            # Converter para PIL Image se necessário
            if isinstance(image_data, bytes):
                image = Image.open(io.BytesIO(image_data))
            elif isinstance(image_data, str):
                image = Image.open(image_data)
            elif PIL_AVAILABLE and isinstance(image_data, Image.Image):
                image = image_data
            else:
                return "", 0.0
            
            # Salvar imagem original para comparação
            original_size = image.size
            
            # Pré-processar
            image_processed = self.preprocessar_imagem(image)
            
            # Converter para array numpy
            img_array = np.array(image_processed) if CV2_AVAILABLE else image_processed
            
            # Executar OCR com configurações otimizadas
            # Desabilitar pin_memory para evitar warning
            import os
            os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
            
            results = OCRService._reader.readtext(
                img_array,
                detail=1,
                paragraph=False,
                min_size=10,
                text_threshold=0.5,
                low_text=0.3,
                batch_size=1,
                workers=0
            )
            
            # Extrair texto e calcular confiança média
            textos = []
            confiancas = []
            
            for (bbox, text, confidence) in results:
                textos.append(text)
                confiancas.append(confidence)
            
            texto_completo = "\n".join(textos)
            confianca_media = sum(confiancas) / len(confiancas) if confiancas else 0.0
            
            return texto_completo, confianca_media
            
        except Exception as e:
            print(f"Erro no OCR: {e}")
            return "", 0.0
    
    def extrair_dados_cupom(self, image_data) -> CupomExtraido:
        """
        Extrai dados estruturados do cupom fiscal
        
        Args:
            image_data: PIL Image, bytes, ou caminho do arquivo
            
        Returns:
            CupomExtraido com dados estruturados
        """
        texto, confianca = self.extrair_texto(image_data)
        
        if not texto:
            return CupomExtraido(texto_bruto="", confianca=0.0)
        
        cupom = CupomExtraido(
            texto_bruto=texto,
            confianca=confianca
        )
        
        # Extrair dados do texto
        cupom.estabelecimento = self._extrair_estabelecimento(texto)
        cupom.cnpj = self._extrair_cnpj(texto)
        cupom.data = self._extrair_data(texto)
        cupom.total = self._extrair_total(texto)
        cupom.itens = self._extrair_itens(texto)
        cupom.forma_pagamento = self._extrair_forma_pagamento(texto)
        
        return cupom
    
    def _extrair_estabelecimento(self, texto: str) -> str:
        """Extrai nome do estabelecimento"""
        linhas = texto.split('\n')
        
        # Se primeira linha é código curto (ex: "LF, 2"), combinar com próxima linha
        primeira = linhas[0].strip() if len(linhas) > 0 else ""
        segunda = linhas[1].strip() if len(linhas) > 1 else ""
        
        # Detectar código curto (ex: "LF, 2" ou "LF 2")
        if primeira and re.match(r'^[A-Z]{1,3}[\s,]+\d{1,2}$', primeira):
            # Combinar com segunda linha e limpar
            nome_completo = f"{primeira} {segunda}"
            # Normalizar: remover vírgula extra
            nome_completo = nome_completo.replace(', ', ' ')
            # Corrigir erros comuns de OCR
            nome_completo = nome_completo.replace('@', 'E')  # @ → E
            nome_completo = re.sub(r'\bI0S\b', 'IOS', nome_completo)  # I0S → IOS
            nome_completo = re.sub(r'\b([A-Z]+)0([A-Z]+)\b', r'\1O\2', nome_completo)  # 0 → O
            nome_completo = re.sub(r'ACESSOR\s+IOS', 'ACESSORIOS', nome_completo)  # ACESSOR IOS → ACESSORIOS
            nome_completo = re.sub(r'BIJUTEIIAS', 'BIJUTERIAS', nome_completo)  # BIJUTEIIAS → BIJUTERIAS
            nome_completo = re.sub(r'LTUA', 'LTDA', nome_completo)  # LTUA → LTDA
            # Limpar caracteres especiais
            nome_completo = re.sub(r'[^a-zA-Z0-9\s]', ' ', nome_completo)
            nome_completo = ' '.join(nome_completo.split())
            if len(nome_completo) > 8:
                return nome_completo
        
        # Caso padrão: procurar primeira linha significativa
        for i, linha in enumerate(linhas[:8]):
            linha = linha.strip()
            # Ignorar linhas muito curtas
            if not linha or len(linha) < 8:
                continue
            # Ignorar linhas com CNPJ, CPF, CEP, data, códigos
            if re.search(r'\d{2}[./-]\d{3}[./-]\d{3}', linha):
                continue
            if re.search(r'\d{2}[/.-]\d{2}[/.-]\d{4}', linha):
                continue
            # Ignorar linhas que são só números/pontuação
            if re.match(r'^[\d\s.,:-]+$', linha):
                continue
            # Ignorar linha inicial com códigos tipo "LF, 2"
            if re.match(r'^[A-Z]{1,3}[\s,]+\d+$', linha):
                continue
            # Pegar primeira linha com texto significativo
            if len(linha) > 8 and sum(c.isalpha() for c in linha) > 5:
                # Limpar e corrigir OCR
                linha = linha.replace('@', 'E')
                linha = re.sub(r'\bI0S\b', 'IOS', linha)
                linha = re.sub(r'[^a-zA-Z0-9\s]', ' ', linha)
                linha = ' '.join(linha.split())
                if len(linha) > 8:
                    return linha
        
        return ""
    
    def _extrair_cnpj(self, texto: str) -> str:
        """Extrai CNPJ do texto"""
        # Remover quebras de linha para facilitar busca
        texto_linha_unica = texto.replace('\n', ' ')
        
        # Padrões CNPJ: XX.XXX.XXX/XXXX-XX
        padroes = [
            r'CNPJ\s*:\s*(\d{2}[.\s]\d{3}[.\s]\d{3}\s*[/\s]\s*\d{4}[-\s]\d{2})',
            r'(\d{2}[.]\d{3}[.]\d{3}\s*[/]\s*\d{4}[-]\d{2})',
        ]
        
        for padrao in padroes:
            match = re.search(padrao, texto_linha_unica, re.IGNORECASE)
            if match:
                cnpj_str = match.group(1) if match.lastindex else match.group(0)
                cnpj = re.sub(r'[^\d]', '', cnpj_str)
                if len(cnpj) == 14:
                    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        
        return ""
    
    def _extrair_data(self, texto: str) -> Optional[datetime]:
        """Extrai data do cupom"""
        # Padrões de data brasileiros
        padroes = [
            r'(\d{2})[/.-](\d{2})[/.-](\d{4})',  # DD/MM/YYYY
            r'(\d{2})[/.-](\d{2})[/.-](\d{2})',  # DD/MM/YY
        ]
        
        for padrao in padroes:
            match = re.search(padrao, texto)
            if match:
                try:
                    dia, mes, ano = match.groups()
                    if len(ano) == 2:
                        ano = f"20{ano}"
                    return datetime(int(ano), int(mes), int(dia))
                except ValueError:
                    continue
        
        return None
    
    def _extrair_total(self, texto: str) -> float:
        """Extrai valor total do cupom"""
        texto_lower = texto.lower()
        linhas = texto_lower.split('\n')
        linhas_relevantes = '\n'.join(linhas[-50:])  # Últimas 50 linhas
        
        # Padrões para encontrar total
        padroes = [
            r'valor\s+total\s*[:\s.]?\s*r\$?\s*(\d+)\s*[,.]\s*(\d{2})',
            r'total\s*[:\s.]?\s*r\$?\s*(\d+)\s*[,.]\s*(\d{2})',
            r'total\s+a\s+pagar\s*[:\s.]?\s*r\$?\s*(\d+)\s*[,.]\s*(\d{2})',
            r'valor\s+pago[\s_]*r\$?\s*(\d+)\s*[,.]\s*(\d{2})',
        ]
        
        for padrao in padroes:
            matches = re.finditer(padrao, linhas_relevantes)
            for match in matches:
                if match.lastindex == 2:
                    valor_int = match.group(1)
                    valor_dec = match.group(2)
                    valor = float(f"{valor_int}.{valor_dec}")
                    if valor > 0:
                        return valor
        
        # Se não encontrou, procurar linha que contenha "total" seguida de valor isolado
        for i, linha in enumerate(linhas):
            if 'total' in linha and i >= len(linhas) - 50:  # Apenas últimas 50 linhas
                # Procurar valor nas próximas 3 linhas
                for j in range(i+1, min(i+4, len(linhas))):
                    proxima_linha = linhas[j]
                    match_valor = re.search(r'^\s*(\d+)\s*[,.]\s*(\d{2})\s*$', proxima_linha)
                    if match_valor:
                        valor_int = match_valor.group(1)
                        valor_dec = match_valor.group(2)
                        valor = float(f"{valor_int}.{valor_dec}")
                        if valor > 5:  # Valor mínimo razoável
                            return valor
        
        return 0.0
    
    def _extrair_itens(self, texto: str) -> List[ItemExtraido]:
        """Extrai itens do cupom - detecta códigos de barras e valores"""
        itens = []
        linhas = texto.split('\n')
        
        for i, linha in enumerate(linhas):
            linha = linha.strip()
            
            # Ignorar linhas curtas ou vazias
            if not linha or len(linha) < 10:
                continue
            
            # Ignorar cabeçalhos/rodapés conhecidos
            if any(x in linha.lower() for x in ['cnpj', 'cpf:', 'chave', 'danfe', 'consulte', 'obrigado', 'qtd', 'total']):
                continue
            
            # Detectar código de barras EAN-13 (13 dígitos), opcionalmente seguido de descrição
            match = re.match(r'^(\d{13})(?:\s+(.+))?$', linha)
            if not match:
                continue
            
            codigo = match.group(1)
            desc_inicial = match.group(2).strip() if match.group(2) else ""
            
            descricao_partes = []
            if desc_inicial:
                descricao_partes.append(desc_inicial)
            
            valor_total = 0.0
            numeros_acumulados = []
            
            # Procurar descrição e valores nas próximas 12 linhas
            for j in range(i+1, min(i+13, len(linhas))):
                prox = linhas[j].strip()
                
                if not prox:
                    continue
                
                # Parar se encontrar outro código
                if re.match(r'^\d{10,14}', prox):
                    break
                
                # Parar em seções conhecidas
                if any(x in prox.lower() for x in ['qtd', 'total', 'forma', 'pagamento']):
                    break
                
                # Procurar valor formatado: "35,00" ou "JUN 35,00" ou "35 ,00"
                match_valor = re.search(r'(\d+)\s*[,. ]\s*(\d{2})', prox)
                if match_valor:
                    # Extrair texto antes do valor (pode ser descrição)
                    texto_antes = prox[:match_valor.start()].strip()
                    if texto_antes and len(texto_antes) > 2 and texto_antes[0].isalpha():
                        descricao_partes.append(texto_antes)
                    
                    # Pegar o valor
                    val_int = match_valor.group(1)
                    val_dec = match_valor.group(2)
                    valor = float(f"{val_int}.{val_dec}")
                    
                    # Primeiro valor encontrado é o total
                    if valor_total == 0.0:
                        valor_total = valor
                    break
                
                # Coletar números isolados (ex: "45", "4", "00")
                # Também detectar "0O" ou "Oo" (OCR confunde O com 0)
                if re.match(r'^[\dOo]{1,3}[^\w]*$', prox):
                    # Converter O/o para 0
                    num_text = prox.replace('O', '0').replace('o', '0')
                    nums = re.findall(r'\d+', num_text)
                    numeros_acumulados.extend(nums)
                    continue
                
                # Texto puro (descrição)
                if re.match(r'^[A-Z][A-Za-z\s/.-]{3,}', prox):
                    descricao_partes.append(prox)
            
            # Se não encontrou valor formatado, tentar montar dos números acumulados
            if valor_total == 0.0 and len(numeros_acumulados) >= 2:
                # Procurar melhor par: priorizar números com 2 dígitos no final
                melhor_valor = 0.0
                for idx in range(len(numeros_acumulados)-1):
                    num1 = numeros_acumulados[idx]
                    num2 = numeros_acumulados[idx+1]
                    
                    # Priorizar quando o decimal tem exatamente 2 dígitos
                    if len(num2) == 2:
                        try:
                            valor_candidato = float(f"{num1}.{num2}")
                            # Validar que é um valor razoável (entre 1.00 e 9999.99)
                            if 1.0 <= valor_candidato <= 9999.99:
                                # Se num1 tem 2 dígitos, é mais provável ser correto
                                if len(num1) == 2:
                                    valor_total = valor_candidato
                                    break
                                # Guardar como candidato mas continuar procurando
                                elif melhor_valor == 0.0:
                                    melhor_valor = valor_candidato
                        except:
                            continue
                
                # Se não encontrou par perfeito, usar o melhor candidato
                if valor_total == 0.0 and melhor_valor > 0:
                    valor_total = melhor_valor
            
            # Criar item se tem descrição e valor
            if descricao_partes and valor_total > 0:
                descricao = ' '.join(descricao_partes)
                descricao = re.sub(r'\s+', ' ', descricao)
                descricao = re.sub(r'[^a-zA-Z0-9\s/.-]', '', descricao)
                
                if len(descricao) > 3:
                    item = ItemExtraido(
                        codigo=codigo,
                        descricao=descricao,
                        quantidade=1,
                        valor_unitario=valor_total,
                        valor_total=valor_total,
                        categoria_sugerida=self._sugerir_categoria(descricao)
                    )
                    itens.append(item)
        
        return itens
    
    def _extrair_forma_pagamento(self, texto: str) -> str:
        """Extrai forma de pagamento"""
        texto_lower = texto.lower()
        
        formas = {
            "Cartão de Crédito": ["credito", "crédito", "credit"],
            "Cartão de Débito": ["debito", "débito", "debit"],
            "PIX": ["pix"],
            "Dinheiro": ["dinheiro", "especie", "espécie", "cash"],
            "Vale": ["vale", "voucher", "alimentação", "refeição"]
        }
        
        for forma, palavras in formas.items():
            for palavra in palavras:
                if palavra in texto_lower:
                    return forma
        
        return ""
    
    def _converter_valor(self, valor_str: str) -> float:
        """Converte string de valor para float"""
        try:
            # Remover espaços e R$
            valor_str = valor_str.replace(' ', '').replace('R$', '').strip()
            
            # Tratar formato brasileiro (1.234,56) vs americano (1,234.56)
            if ',' in valor_str and '.' in valor_str:
                # Assumir formato brasileiro
                valor_str = valor_str.replace('.', '').replace(',', '.')
            elif ',' in valor_str:
                valor_str = valor_str.replace(',', '.')
            
            return float(valor_str)
        except ValueError:
            return 0.0
    
    def _sugerir_categoria(self, descricao: str) -> str:
        """Sugere categoria baseado na descrição do item"""
        descricao_lower = descricao.lower()
        
        for categoria, palavras in Config.PALAVRAS_CHAVE_CATEGORIAS.items():
            for palavra in palavras:
                if palavra in descricao_lower:
                    return categoria
        
        return "Outros"


# Instância global
ocr = OCRService()
