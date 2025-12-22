"""
Script para popular o banco de dados com dados de exemplo
"""
import json
import os
from datetime import datetime, timedelta
import random
from pathlib import Path
import uuid

# Ajustar o path para importar do projeto
import sys
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import Config
from services.database import db


def _ensure_demo_contas(user_id: str) -> dict:
    """Garante um conjunto mínimo de contas para os dados de exemplo.

    Retorna um dict com chaves: banco, carteira, cartao (ids ou None).
    """
    contas_ids = {"banco": None, "carteira": None, "cartao": None}

    existentes = db.listar_contas(user_id)
    map_nome = {str(c.get("nome") or "").strip().lower(): c for c in existentes}

    def _get_or_create(nome: str, tipo: str, saldo: float = 0.0, fechamento: int | None = None, vencimento: int | None = None):
        key = nome.strip().lower()
        if key in map_nome and map_nome[key].get("id"):
            return map_nome[key]["id"]

        criada = db.criar_conta(
            user_id=user_id,
            nome=nome,
            tipo=tipo,
            saldo_inicial=float(saldo),
            data_saldo_inicial=datetime.now().date().replace(day=1),
            dia_fechamento=fechamento,
            dia_vencimento=vencimento,
        )
        if criada and criada.get("id"):
            return criada["id"]
        return None

    contas_ids["banco"] = _get_or_create("Banco Principal", "banco", saldo=2500.0)
    contas_ids["carteira"] = _get_or_create("Carteira", "carteira", saldo=200.0)
    contas_ids["cartao"] = _get_or_create("Cartão de Crédito", "cartao_credito", saldo=0.0, fechamento=10, vencimento=17)

    return contas_ids


def _ensure_demo_recorrentes(user_id: str, contas_ids: dict, categorias_ids: dict):
    """Cria recorrentes básicas (salário/contas fixas) e gera previstas do mês atual."""
    conta_banco = contas_ids.get("banco")
    if not conta_banco:
        return

    existentes = db.listar_recorrentes(user_id)
    chaves = {f"{r.get('descricao','')}|{r.get('tipo')}|{r.get('dia_do_mes')}|{r.get('conta_id')}" for r in existentes}

    def _upsert(descricao: str, tipo: str, valor: float, dia: int, categoria_nome: str | None):
        chave = f"{descricao}|{tipo}|{dia}|{conta_banco}"
        if chave in chaves:
            return
        rec = {
            "user_id": user_id,
            "conta_id": conta_banco,
            "categoria_id": categorias_ids.get(categoria_nome) if categoria_nome else None,
            "descricao": descricao,
            "valor": float(valor),
            "tipo": tipo,
            "dia_do_mes": int(dia),
        }
        db.criar_recorrente(rec)

    _upsert("Salário", "receita", 5000.0, 5, "Salário")
    _upsert("Aluguel", "despesa", 1200.0, 10, "Moradia")
    _upsert("Internet", "despesa", 100.0, 12, "Moradia")
    _upsert("Academia", "despesa", 120.0, 15, "Lazer")

    hoje = datetime.now().date()
    db.gerar_previstas_mes(user_id, ano=hoje.year, mes=hoje.month)

def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except Exception:
        return False


def _resolve_user_id(user_id: str | None, email: str | None, nome: str | None) -> str:
    """Resolve o user_id de forma segura.

    - Garante que existe um usuário no storage atual e retorna o id.
    """
    if user_id:
        return str(user_id)

    email_final = (email or getattr(Config, "SINGLE_USER_EMAIL", "meu@app.local")).strip()
    nome_final = (nome or getattr(Config, "SINGLE_USER_NAME", "Usuário")).strip() or "Usuário"

    user = db.buscar_usuario_por_email(email=email_final)
    if not user:
        user = db.criar_usuario(email=email_final, nome=nome_final)
        if user and user.get("id"):
            try:
                db.criar_categorias_padrao(user_id=str(user.get("id")))
            except Exception:
                pass

    if not user or not user.get("id"):
        raise RuntimeError("Não foi possível criar/buscar o usuário para popular dados")
    return str(user.get("id"))


def popular_dados_exemplo(user_id: str):
    """
    Popula o banco com dados de exemplo
    """
    print("🚀 Iniciando população do banco de dados...")

    # Tornar o dataset mais consistente a cada execução
    try:
        random.seed(str(user_id))
    except Exception:
        random.seed(0)
    
    # 1. Criar categorias de despesas
    categorias_despesas = [
        {"nome": "Alimentação", "icone": "🍔", "tipo": "despesa"},
        {"nome": "Transporte", "icone": "🚗", "tipo": "despesa"},
        {"nome": "Moradia", "icone": "🏠", "tipo": "despesa"},
        {"nome": "Saúde", "icone": "💊", "tipo": "despesa"},
        {"nome": "Educação", "icone": "📚", "tipo": "despesa"},
        {"nome": "Lazer", "icone": "🎮", "tipo": "despesa"},
        {"nome": "Vestuário", "icone": "👕", "tipo": "despesa"},
        {"nome": "Tecnologia", "icone": "💻", "tipo": "despesa"},
    ]
    
    # 2. Criar categorias de receitas
    categorias_receitas = [
        {"nome": "Salário", "icone": "💰", "tipo": "receita"},
        {"nome": "Freelance", "icone": "💼", "tipo": "receita"},
        {"nome": "Investimentos", "icone": "📈", "tipo": "receita"},
        {"nome": "Outros", "icone": "💵", "tipo": "receita"},
    ]
    
    print("\n📦 Verificando e criando categorias...")
    categorias_ids = {}

    # 0. Contas (opcional, depende do schema)
    contas_ids = _ensure_demo_contas(user_id)
    
    # Buscar categorias existentes
    # Inclui categorias inativas (soft delete) para poder reativar ao popular novamente
    categorias_existentes = db.listar_categorias(user_id, include_inactive=True)
    categorias_map = {f"{c['nome']}_{c['tipo']}": c for c in categorias_existentes}

    for cat in categorias_despesas + categorias_receitas:
        chave = f"{cat['nome']}_{cat['tipo']}"
        existente = categorias_map.get(chave)

        if existente:
            # Se estava inativa por 'limpar', reativar para voltar a aparecer na UI
            if not existente.get("ativo", True):
                atualizada = db.atualizar_categoria(existente["id"], {"ativo": True, "icone": cat["icone"]})
                if atualizada:
                    existente = atualizada
                    print(f"♻️ Categoria reativada: {cat['nome']} ({cat['tipo']})")

            categorias_ids[cat["nome"]] = existente["id"]
            print(f"  ✓ {cat['icone']} {cat['nome']} (já existe)")
            continue

        # Criar nova categoria
        categoria_criada = db.criar_categoria(
            user_id=user_id,
            nome=cat["nome"],
            tipo=cat["tipo"],
            icone=cat["icone"]
        )
        if categoria_criada and "id" in categoria_criada:
            categorias_ids[cat["nome"]] = categoria_criada["id"]
            print(f"  ✓ {cat['icone']} {cat['nome']} (criada)")
        else:
            print(f"  ❌ Erro ao criar {cat['nome']}")
    
    # 3. Criar orçamentos para categorias de despesa
    print("\n💰 Verificando e criando orçamentos...")
    orcamentos_config = {
        "Alimentação": 800.00,
        "Transporte": 400.00,
        "Moradia": 1700.00,
        "Saúde": 300.00,
        "Educação": 500.00,
        "Lazer": 400.00,
        "Vestuário": 300.00,
        "Tecnologia": 200.00,
    }
    
    # Buscar orçamentos existentes
    orcamentos_existentes = db.listar_orcamentos(user_id)
    cats_com_orcamento = {o["categoria_id"] for o in orcamentos_existentes}
    
    for cat_nome, valor in orcamentos_config.items():
        if cat_nome in categorias_ids:
            cat_id = categorias_ids[cat_nome]
            if cat_id in cats_com_orcamento:
                print(f"  ✓ {cat_nome}: R$ {valor:.2f} (já existe)")
            else:
                db.definir_orcamento(user_id, cat_id, valor)
                print(f"  ✓ {cat_nome}: R$ {valor:.2f} (criado)")
    
    # 4. Criar transações dos últimos 3 meses (dataset menor e mais realista)
    print("\n📝 Criando transações...")
    
    # Debug: Mostrar categorias mapeadas
    print(f"\n🔍 Categorias disponíveis: {list(categorias_ids.keys())}")
    
    hoje = datetime.now().date()
    
    def _add_tx(descricao: str, tipo: str, data_tx: date, valor: float, categoria_nome: str):
        cat_id = categorias_ids.get(categoria_nome)
        if not cat_id:
            return
        payload = {
            "user_id": user_id,
            "descricao": descricao,
            "valor": float(valor),
            "tipo": tipo,
            "data": data_tx.isoformat(),
            "categoria_id": cat_id,
            "modo_lancamento": "manual",
        }
        if contas_ids.get("banco"):
            payload["conta_id"] = contas_ids.get("banco")
        db.criar_transacao(payload)

    total_tx_aprox = 0

    for mes in range(3):
        ref = (hoje.replace(day=15) - timedelta(days=30 * mes))
        base_mes = ref.replace(day=1)

        # Receita: salário
        _add_tx("Salário", "receita", base_mes.replace(day=5), 5000.00, "Salário")
        total_tx_aprox += 1

        # Receita: freelance (1 a cada ~2 meses)
        if random.random() > 0.55:
            valor_free = round(random.uniform(700, 1800), 2)
            _add_tx("Projeto Freelance", "receita", base_mes.replace(day=20), valor_free, "Freelance")
            total_tx_aprox += 1

        # Fixas (como transações realizadas no histórico)
        _add_tx("Aluguel", "despesa", base_mes.replace(day=10), 1200.00, "Moradia")
        _add_tx("Internet", "despesa", base_mes.replace(day=12), 100.00, "Moradia")
        _add_tx("Conta de Luz", "despesa", base_mes.replace(day=20), round(random.uniform(140, 220), 2), "Moradia")
        _add_tx("Conta de Água", "despesa", base_mes.replace(day=22), round(random.uniform(80, 130), 2), "Moradia")
        _add_tx("Academia", "despesa", base_mes.replace(day=15), 120.00, "Lazer")
        _add_tx("Streaming", "despesa", base_mes.replace(day=7), 39.90, "Lazer")
        total_tx_aprox += 6

        # Variáveis (poucas, para ficar legível)
        _add_tx("Supermercado", "despesa", base_mes.replace(day=3), round(random.uniform(180, 320), 2), "Alimentação")
        _add_tx("Supermercado", "despesa", base_mes.replace(day=18), round(random.uniform(160, 290), 2), "Alimentação")
        _add_tx("Restaurante", "despesa", base_mes.replace(day=24), round(random.uniform(60, 140), 2), "Alimentação")
        _add_tx("Uber", "despesa", base_mes.replace(day=8), round(random.uniform(25, 65), 2), "Transporte")
        _add_tx("Uber", "despesa", base_mes.replace(day=26), round(random.uniform(25, 75), 2), "Transporte")
        total_tx_aprox += 5

        print(f"  ✓ Mês {mes+1}: ~{(1 + 6 + 5)} transações criadas")
    
    # 5. Recorrentes + previstas do mês (opcional)
    _ensure_demo_recorrentes(user_id, contas_ids=contas_ids, categorias_ids=categorias_ids)

    print("\n✅ Banco de dados populado com sucesso!")
    print(f"   - {len(categorias_ids)} categorias")
    print(f"   - {len(orcamentos_config)} orçamentos")
    print(f"   - ~{total_tx_aprox} transações")
    if contas_ids.get("banco") or contas_ids.get("carteira") or contas_ids.get("cartao"):
        print("   - contas e fixas (quando disponível)")


def limpar_dados(user_id: str, keep_categorias: bool = False):
    """
    Remove todos os dados do usuário
    """
    print("🗑️  Limpando dados do banco...")
    
    # Deletar transações (inclui previstas/substituídas)
    transacoes = db.listar_transacoes(user_id, limite=5000, incluir_previstas=True)
    for t in transacoes:
        db.deletar_transacao(t["id"])
    print(f"  ✓ {len(transacoes)} transações deletadas")

    # Deletar recorrentes
    recorrentes = db.listar_recorrentes(user_id)
    for r in recorrentes:
        rid = r.get("id")
        if rid:
            db.deletar_recorrente(rid)
    if recorrentes:
        print(f"  ✓ {len(recorrentes)} recorrentes deletadas")

    # Deletar contas
    contas = db.listar_contas(user_id)
    for c in contas:
        cid = c.get("id")
        if cid:
            db.deletar_conta(cid)
    if contas:
        print(f"  ✓ {len(contas)} contas deletadas")
    
    # Deletar orçamentos
    orcamentos = db.listar_orcamentos(user_id)
    for o in orcamentos:
        db.deletar_orcamento(o["id"])
    print(f"  ✓ {len(orcamentos)} orçamentos deletados")
    
    # Deletar categorias
    if keep_categorias:
        print("  ↪️  Categorias preservadas (--keep-categorias)")
    else:
        categorias = db.listar_categorias(user_id)
        for c in categorias:
            db.deletar_categoria(c["id"])
        print(f"  ✓ {len(categorias)} categorias deletadas")
    
    print("\n✅ Dados limpos com sucesso!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Popular ou limpar banco de dados")
    parser.add_argument("acao", choices=["popular", "limpar"], help="Ação a executar")
    parser.add_argument("--user-id", default=None, help="ID do usuário (opcional; se omitido, cria/busca pelo e-mail)")
    parser.add_argument("--email", default=None, help="E-mail do usuário (opcional; padrão vem do SINGLE_USER_EMAIL)")
    parser.add_argument("--nome", default=None, help="Nome do usuário (opcional; padrão vem do SINGLE_USER_NAME)")
    parser.add_argument(
        "--keep-categorias",
        action="store_true",
        help="No comando limpar: não desativa/deleta categorias (mantém só apagando transações e orçamentos)",
    )
    
    args = parser.parse_args()
    
    try:
        resolved_user_id = _resolve_user_id(args.user_id, args.email, args.nome)
    except Exception as e:
        print(f"❌ {e}")
        raise SystemExit(2)

    if args.acao == "popular":
        popular_dados_exemplo(resolved_user_id)
    else:
        limpar_dados(resolved_user_id, keep_categorias=args.keep_categorias)
