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

from services.database import db

def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except Exception:
        return False


def _resolve_user_id(user_id: str | None, email: str | None, nome: str | None) -> str:
    """Resolve o user_id de forma segura.

    - Supabase: exige UUID. Se não vier UUID, permite resolver/criar via email.
    - Local: permite fallback para "demo_user".
    """
    if db.is_local:
        return user_id or "demo_user"

    # Supabase
    if user_id:
        if not _is_uuid(user_id):
            raise ValueError("No Supabase, o --user-id precisa ser um UUID válido.")
        return user_id

    if email:
        existente = db.buscar_usuario_por_email(email)
        if existente and "id" in existente:
            return existente["id"]

        nome_final = nome or email.split("@")[0] or "Usuário Demo"
        criado = db.criar_usuario(email=email, nome=nome_final)
        if criado and "id" in criado:
            print(f"✅ Usuário criado: {email} (id={criado['id']})")
            return criado["id"]

        raise RuntimeError("Não foi possível criar o usuário no Supabase.")

    raise ValueError("No Supabase, informe --user-id (UUID) ou --email para resolver/criar o usuário.")


def popular_dados_exemplo(user_id: str):
    """
    Popula o banco com dados de exemplo
    """
    print("🚀 Iniciando população do banco de dados...")
    
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
        "Moradia": 1500.00,
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
    
    # 4. Criar transações dos últimos 3 meses
    print("\n📝 Criando transações...")
    
    # Debug: Mostrar categorias mapeadas
    print(f"\n🔍 Categorias disponíveis: {list(categorias_ids.keys())}")
    
    hoje = datetime.now().date()
    
    # Receitas mensais
    for mes in range(3):
        data_receita = hoje - timedelta(days=30*mes)
        data_receita = data_receita.replace(day=5)  # Dia 5 de cada mês
        # Salário
        db.criar_transacao({
            "user_id": user_id,
            "descricao": "Salário",
            "valor": 5000.00,
            "tipo": "receita",
            "data": data_receita.isoformat(),
            "categoria_id": categorias_ids.get("Salário"),
            "modo_lancamento": "manual"
        })
        print(f"  ✓ Receita: Salário - R$ 5000.00 ({data_receita})")
        
        # Freelance (aleatório)
        if random.random() > 0.5:
            valor_free = random.uniform(500, 2000)
            db.criar_transacao({
                "user_id": user_id,
                "descricao": "Projeto Freelance",
                "valor": valor_free,
                "tipo": "receita",
                "data": data_receita.isoformat(),
                "categoria_id": categorias_ids.get("Freelance"),
                "modo_lancamento": "manual"
            })
            print(f"  ✓ Receita: Freelance - R$ {valor_free:.2f} ({data_receita})")
    
    # Despesas variadas
    despesas_exemplos = [
        # Alimentação
        ("Supermercado", "Alimentação", (150, 300), 8),
        ("Restaurante", "Alimentação", (40, 120), 6),
        ("Lanchonete", "Alimentação", (15, 50), 10),
        
        # Transporte
        ("Combustível", "Transporte", (100, 200), 4),
        ("Uber", "Transporte", (20, 60), 8),
        
        # Moradia
        ("Aluguel", "Moradia", (1200, 1200), 3),
        ("Conta de Luz", "Moradia", (150, 250), 3),
        ("Conta de Água", "Moradia", (80, 120), 3),
        ("Internet", "Moradia", (100, 100), 3),
        
        # Saúde
        ("Farmácia", "Saúde", (50, 150), 4),
        ("Consulta Médica", "Saúde", (150, 300), 2),
        
        # Educação
        ("Curso Online", "Educação", (100, 300), 2),
        ("Livros", "Educação", (50, 150), 3),
        
        # Lazer
        ("Cinema", "Lazer", (40, 80), 4),
        ("Streaming", "Lazer", (30, 50), 3),
        ("Academia", "Lazer", (100, 150), 3),
        
        # Vestuário
        ("Roupas", "Vestuário", (80, 300), 3),
        ("Calçados", "Vestuário", (100, 250), 2),
        
        # Tecnologia
        ("App Store", "Tecnologia", (20, 80), 3),
        ("Equipamentos", "Tecnologia", (100, 500), 2),
    ]
    
    for mes in range(3):
        transacoes_criadas = 0
        for desc, cat_nome, (min_val, max_val), qtd in despesas_exemplos:
            for _ in range(qtd // 3 + (1 if mes == 0 else 0)):  # Mais transações no mês atual
                dias_atras = random.randint(1 + 30*mes, 30 + 30*mes)
                data_trans = hoje - timedelta(days=dias_atras)
                valor = random.uniform(min_val, max_val)
                
                # Garantir que a categoria existe
                cat_id = categorias_ids.get(cat_nome)
                if not cat_id:
                    print(f"⚠️ Categoria não encontrada: {cat_nome} (disponíveis: {list(categorias_ids.keys())})")
                    continue
                
                db.criar_transacao({
                    "user_id": user_id,
                    "descricao": desc,
                    "valor": valor,
                    "tipo": "despesa",
                    "data": data_trans.isoformat(),
                    "categoria_id": cat_id,
                    "modo_lancamento": "manual"
                })
                transacoes_criadas += 1
        
        print(f"  ✓ Mês {mes+1}: {transacoes_criadas} despesas criadas")
    
    print("\n✅ Banco de dados populado com sucesso!")
    print(f"   - {len(categorias_ids)} categorias")
    print(f"   - {len(orcamentos_config)} orçamentos")
    print(f"   - ~{sum(qtd for _, _, _, qtd in despesas_exemplos) + 6} transações")


def limpar_dados(user_id: str, keep_categorias: bool = False):
    """
    Remove todos os dados do usuário
    """
    print("🗑️  Limpando dados do banco...")
    
    # Deletar transações
    transacoes = db.listar_transacoes(user_id)
    for t in transacoes:
        db.deletar_transacao(t["id"])
    print(f"  ✓ {len(transacoes)} transações deletadas")
    
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
    parser.add_argument("--user-id", default=None, help="ID do usuário (UUID no Supabase)")
    parser.add_argument("--email", default=None, help="Email do usuário (para resolver/criar no Supabase)")
    parser.add_argument("--nome", default=None, help="Nome do usuário (usado ao criar via --email)")
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
