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

    st.header("💰 Orçamentos e Provisões")
    st.caption("Acompanhe o que foi orçado versus o que foi realizado em cada categoria")

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
                "categoria_id": key,
            }

        valor = float(t.get("valor") or 0)
        if status == "prevista":
            resumo[key]["Previsto"] += valor
        else:
            # status None/realizada entram como realizado
            resumo[key]["Realizado"] += valor

    if not resumo:
        st.info("Sem despesas (previstas ou realizadas) no mês selecionado.")
        return

    rows: List[Dict[str, Any]] = []
    for r in resumo.values():
        previsto = float(r.get("Previsto") or 0)
        realizado = float(r.get("Realizado") or 0)
        categoria_nome = r.get("Categoria", "")
        
        rows.append(
            {
                "Categoria": categoria_nome,
                "Previsto": previsto,
                "Realizado": realizado,
                "Restante": previsto - realizado,
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values(by=["Previsto"], ascending=False)

    # Resumo geral
    total_prev = float(df["Previsto"].sum())
    total_real = float(df["Realizado"].sum())
    total_restante = total_prev - total_real

    st.markdown("### 📊 Resumo do Mês")
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.metric("Orçado", _format_brl(total_prev))
    with c2:
        st.metric("Realizado", _format_brl(total_real))
    with c3:
        percentual = (total_real / total_prev * 100) if total_prev > 0 else 0
        st.metric("Percentual", f"{percentual:.1f}%")
    with c4:
        cor = "🟢" if total_restante >= 0 else "🔴"
        st.metric(f"{cor} Restante", _format_brl(total_restante))

    st.markdown("---")

    # Detalhes por categoria com cards
    st.markdown("### 🏷️ Detalhes por Categoria")
    
    for _, row in df.iterrows():
        categoria = row["Categoria"]
        previsto = float(row["Previsto"])
        realizado = float(row["Realizado"])
        restante = float(row["Restante"])
        percentual_uso = (realizado / previsto * 100) if previsto > 0 else 0
        
        # Indicador de status
        if percentual_uso > 100:
            status = "🔴 Excedido"
            status_color = "#ef4444"
        elif percentual_uso > 80:
            status = "🟡 Atenção"
            status_color = "#f59e0b"
        else:
            status = "🟢 OK"
            status_color = "#10b981"
        
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
        
        with col1:
            st.write(f"**{categoria}**")
        with col2:
            st.metric("Orçado", _format_brl(previsto), label_visibility="collapsed")
        with col3:
            st.metric("Gasto", _format_brl(realizado), label_visibility="collapsed")
        with col4:
            st.metric("Uso", f"{percentual_uso:.0f}%", label_visibility="collapsed")
        with col5:
            st.write(f"<p style='color: {status_color}; font-weight: bold; text-align: center;'>{status}</p>", unsafe_allow_html=True)

    st.markdown("---")

    # Gráfico comparativo
    if PLOTLY_AVAILABLE:
        st.markdown("### 📈 Visualização")
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["Categoria"], 
            y=df["Previsto"], 
            name="Orçado",
            marker_color="#3b82f6",
            text=df["Previsto"].map(lambda x: _format_brl(x)),
            textposition="auto",
        ))
        fig.add_trace(go.Bar(
            x=df["Categoria"], 
            y=df["Realizado"], 
            name="Realizado",
            marker_color="#10b981",
            text=df["Realizado"].map(lambda x: _format_brl(x)),
            textposition="auto",
        ))
        
        fig.update_layout(
            barmode="group",
            height=420,
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#334155"),
        )
        st.plotly_chart(fig, use_container_width=True)
