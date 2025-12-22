"""Serviços de mercado/índices (ex.: SELIC).

Implementação simples e robusta para uso no Streamlit.
"""

from __future__ import annotations

from datetime import date
from typing import Optional, Tuple

import requests


BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"


def _sgs_url_ultimos(serie: int, n: int = 1) -> str:
    # Endpoint mais estável para pegar apenas os últimos valores.
    return f"{BCB_SGS_URL.format(serie=serie)}/ultimos/{int(n)}"


def _fetch_sgs_last_value(serie: int, timeout: int = 10) -> Tuple[Optional[date], Optional[float]]:
    """Busca o último valor disponível de uma série do SGS (BCB).

    Retorna (data, valor_percent_aa_ou_percent_ad), dependendo da série.
    Para SELIC meta (1178), o retorno costuma ser % a.a.
    """

    # Buscar apenas o último valor evita payload grande e reduz chance de erro.
    url = _sgs_url_ultimos(serie=serie, n=1)

    headers = {
        "Accept": "application/json,text/plain,*/*",
        "User-Agent": "app-financas/1.0 (requests)",
    }

    # O endpoint SGS do BCB usa tradicionalmente 'formato=json'.
    # Alguns ambientes retornam 406 (Not Acceptable) quando usamos 'format=json'.
    param_variants = (
        {"formato": "json"},
        {"format": "json"},
        None,
    )

    data = None
    last_error: Exception | None = None
    for params in param_variants:
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as e:
            last_error = e
            data = None

    if data is None:
        # Não propaga erro para não quebrar o Streamlit; a tela lida com None.
        try:
            print(f"⚠️ Não foi possível buscar série SGS {serie}: {last_error}")
        except Exception:
            pass
        return None, None

    # A resposta esperada é uma lista de dicts. Se vier outra coisa, trata como falha.
    if not isinstance(data, list) or not data:
        return None, None

    last = data[-1]
    # last: {"data": "dd/mm/aaaa", "valor": "x.xx"}
    try:
        d_str = str(last.get("data") or "")
        dd, mm, yyyy = d_str.split("/")
        d = date(int(yyyy), int(mm), int(dd))
    except Exception:
        d = None

    try:
        v = float(str(last.get("valor")).replace(",", "."))
    except Exception:
        v = None

    return d, v


def obter_selic_meta_aa(timeout: int = 10) -> Tuple[Optional[date], Optional[float]]:
    """Obtém a SELIC Meta (% a.a.) via SGS/BCB.

    Série 1178: Taxa Selic Meta ao ano (% a.a.).
    """

    return _fetch_sgs_last_value(serie=1178, timeout=timeout)


def calcular_rendimento_percentual_selic(
    principal: float,
    selic_aa_percent: float,
    dias: int,
    percentual_selic: float = 100.0,
) -> float:
    """Calcula o valor final para um investimento indexado a % da SELIC.

    - principal: valor investido
    - selic_aa_percent: taxa SELIC anual em % a.a.
    - dias: prazo em dias
    - percentual_selic: ex.: 90 para 90% da SELIC

    Fórmula (aprox.):
      fator = (1 + selic_aa)^(dias/365)
      fator_aj = 1 + (fator - 1) * (percentual_selic/100)
    """

    p = float(principal or 0)
    if p <= 0:
        return 0.0

    if dias <= 0:
        return p

    if selic_aa_percent is None:
        return p

    selic_aa = float(selic_aa_percent) / 100.0
    perc = float(percentual_selic) / 100.0

    fator = (1.0 + selic_aa) ** (float(dias) / 365.0)
    fator_aj = 1.0 + (fator - 1.0) * perc
    return p * fator_aj
