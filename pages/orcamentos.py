"""Página de provisões/orçamento por transação.

Modelo:
- Provisão/orçamento = transação com status 'prevista'
- Realizado = transação com status 'realizada'

O resumo abaixo agrupa por categoria no mês selecionado.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st

from services.database import db

try:
    import plotly.graph_objects as go

    PLOTLY_AVAILABLE = True
except Exception:
    PLOTLY_AVAILABLE = False


def get_user_id() -> str:
    return st.session_state.get("user_id", "")


def _month_bounds(ref: date) -> Tuple[date, date]:
    inicio = date(ref.year, ref.month, 1)
    ultimo = monthrange(ref.year, ref.month)[1]
    fim = date(ref.year, ref.month, ultimo)
    return inicio, fim


def _format_brl(value: float) -> str:
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def render_orcamentos_page() -> None:
    user_id = get_user_id()
    if not user_id:
        st.warning("Usuário não identificado")
        return

    st.header("💰 Provisões do mês")
    st.caption("Crie provisões lançando transações como 'Prevista'. O resumo agrupa por categoria.")

    ref_mes = st.date_input(
        "Mês de referência",
        value=date.today().replace(day=1),
        key="prov_ref_mes",
    )

    inicio, fim = _month_bounds(ref_mes)

    transacoes = db.listar_transacoes(
        user_id=user_id,
        data_inicio=inicio,
        data_fim=fim,
        tipo="despesa",
        limite=5000,
        incluir_previstas=True,
    )

    # Agrupar por categoria: previsto vs realizado
    resumo: Dict[str, Dict[str, Any]] = {}
    for t in transacoes:
        status = t.get("status")
        if status in {"substituida"}:
            continue

        categoria = t.get("categorias") if isinstance(t.get("categorias"), dict) else None
        categoria_id = str(t.get("categoria_id") or "")
        key = categoria_id or "__sem_categoria__"

        if key not in resumo:
            nome = (categoria or {}).get("nome") or "Sem categoria"
            icone = (categoria or {}).get("icone") or "📦"
            resumo[key] = {
                "Categoria": f"{icone} {nome}",
                "Previsto": 0.0,
                "Realizado": 0.0,
            }

        valor = float(t.get("valor") or 0)
        if status == "prevista":
            resumo[key]["Previsto"] += valor
        else:
            # status None/realizada entram como realizado
            resumo[key]["Realizado"] += valor

    rows: List[Dict[str, Any]] = []
    for r in resumo.values():
        previsto = float(r.get("Previsto") or 0)
        realizado = float(r.get("Realizado") or 0)
        rows.append(
            {
                "Categoria": r.get("Categoria"),
                "Previsto": previsto,
                "Realizado": realizado,
                "Diferença (Previsto - Realizado)": previsto - realizado,
            }
        )

    if not rows:
        st.info("Sem despesas (previstas ou realizadas) no mês selecionado.")
        return

    df = pd.DataFrame(rows)
    df = df.sort_values(by=["Previsto", "Realizado"], ascending=[False, False])

    total_prev = float(df["Previsto"].sum())
    total_real = float(df["Realizado"].sum())
    total_diff = total_prev - total_real

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total previsto", _format_brl(total_prev))
    with c2:
        st.metric("Total realizado", _format_brl(total_real))
    with c3:
        st.metric("Diferença", _format_brl(total_diff))

    st.dataframe(
        df.assign(
            **{
                "Previsto": df["Previsto"].map(_format_brl),
                "Realizado": df["Realizado"].map(_format_brl),
                "Diferença (Previsto - Realizado)": df["Diferença (Previsto - Realizado)"].map(_format_brl),
            }
        ),
        width="stretch",
        hide_index=True,
    )

    if PLOTLY_AVAILABLE:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df["Categoria"], y=df["Previsto"], name="Previsto"))
        fig.add_trace(go.Bar(x=df["Categoria"], y=df["Realizado"], name="Realizado"))
        fig.update_layout(
            barmode="group",
            height=420,
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
