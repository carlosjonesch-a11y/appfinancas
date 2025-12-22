"""Importação simples de OFX (cartão) e conciliação básica.

Objetivo: o mais simples possível.
- Lê OFX via ofxparse (suporta OFX 1.x/2.x na maioria dos casos).
- Normaliza para lista de transações: data, valor, descricao, fitid.

Conciliação:
- Evita duplicar por (fitid) quando possível.
- Caso não exista suporte no banco para ofx_fitid, faz uma checagem simples por (data + valor + descricao).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional, Tuple


@dataclass
class OfxTx:
    fitid: str
    data: date
    valor: float
    descricao: str


def _to_date(dt) -> Optional[date]:
    if dt is None:
        return None
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt
    if isinstance(dt, datetime):
        return dt.date()
    return None


def parse_ofx_bytes(content: bytes) -> List[OfxTx]:
    """Parse de OFX a partir de bytes."""
    try:
        from ofxparse import OfxParser  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("Dependência 'ofxparse' não instalada.") from e

    # ofxparse espera file-like
    import io

    fh = io.BytesIO(content)
    ofx = OfxParser.parse(fh)

    txs: List[OfxTx] = []

    # Alguns OFX vêm com múltiplas contas; para cartão normalmente é 1.
    accounts = []
    if getattr(ofx, "account", None) is not None:
        accounts = [ofx.account]
    elif getattr(ofx, "accounts", None):
        accounts = list(ofx.accounts)

    for acc in accounts:
        stm = getattr(acc, "statement", None)
        if not stm:
            continue
        for t in getattr(stm, "transactions", []) or []:
            d = _to_date(getattr(t, "date", None))
            if not d:
                continue

            fitid = str(getattr(t, "id", "") or "")
            name = str(getattr(t, "payee", "") or "")
            memo = str(getattr(t, "memo", "") or "")
            desc = (memo or name or "").strip()
            if not desc:
                desc = "Compra cartão"

            try:
                amount = float(getattr(t, "amount", 0) or 0)
            except Exception:
                amount = 0.0

            # Para cartão, em geral despesas vêm negativas.
            valor = abs(amount)

            txs.append(OfxTx(fitid=fitid, data=d, valor=valor, descricao=desc))

    # Ordenar por data
    txs.sort(key=lambda x: (x.data, x.valor, x.descricao))
    return txs


def sugerir_match_simples(
    ofx: OfxTx,
    existentes: List[dict],
) -> Optional[dict]:
    """Match simples possível: data + valor (arredondado 2 casas).

    Se houver múltiplos, retorna o primeiro.
    """
    alvo_val = round(float(ofx.valor), 2)
    for t in existentes:
        try:
            v = round(float(t.get("valor") or 0), 2)
        except Exception:
            continue
        if v != alvo_val:
            continue
        # data pode vir ISO
        d = None
        try:
            d = datetime.fromisoformat(str(t.get("data")).replace("Z", "+00:00")).date()
        except Exception:
            d = None
        if d != ofx.data:
            continue
        return t
    return None
