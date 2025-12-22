"""
Serviço de banco de dados com suporte a Supabase e fallback local (JSON)
"""
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import json
from pathlib import Path
import uuid

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    create_client = None
    Client = None
    SUPABASE_AVAILABLE = False

from config import Config


class LocalDatabase:
    """Banco de dados local usando arquivos JSON"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Arquivos de dados
        self.usuarios_file = self.data_dir / "usuarios.json"
        self.categorias_file = self.data_dir / "categorias.json"
        self.transacoes_file = self.data_dir / "transacoes.json"
        self.orcamentos_file = self.data_dir / "orcamentos.json"
        
        # Inicializar arquivos se não existirem
        self._init_files()
    
    def _init_files(self):
        """Inicializa arquivos de dados"""
        for file in [self.usuarios_file, self.categorias_file, self.transacoes_file, self.orcamentos_file]:
            if not file.exists():
                file.write_text("[]", encoding="utf-8")
    
    def _read_json(self, file: Path) -> List[Dict]:
        """Lê dados de um arquivo JSON"""
        try:
            return json.loads(file.read_text(encoding="utf-8"))
        except Exception:
            return []
    
    def _write_json(self, file: Path, data: List[Dict]):
        """Escreve dados em um arquivo JSON"""
        file.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    
    def _generate_id(self) -> str:
        """Gera um ID único"""
        return str(uuid.uuid4())


class DatabaseService:
    """Serviço para operações no banco de dados (Supabase ou Local)"""
    
    _instance: Optional["DatabaseService"] = None
    _client: Optional[Client] = None
    _local_db: Optional[LocalDatabase] = None
    _use_local: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None and self._local_db is None:
            self._initialize()
    
    def _initialize(self):
        """Inicializa o banco de dados (Supabase ou Local)"""
        # Tentar Supabase primeiro
        if SUPABASE_AVAILABLE and Config.SUPABASE_URL and Config.SUPABASE_KEY:
            try:
                self._client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
                # Testar conexão
                self._client.table("usuarios").select("id").limit(1).execute()
                print("✅ Conectado ao Supabase")
                return
            except Exception as e:
                print(f"⚠️ Erro ao conectar ao Supabase: {e}")
                print("📁 Usando banco de dados local como fallback")
        
        # Fallback para banco local
        print("📁 Usando banco de dados local (JSON)")
        self._local_db = LocalDatabase()
        self._use_local = True
    
    @property
    def is_connected(self) -> bool:
        return self._client is not None or self._local_db is not None
    
    @property
    def is_local(self) -> bool:
        return self._use_local
    
    # ==================== USUÁRIOS ====================
    
    def criar_usuario(self, email: str, nome: str, auth_id: str = None) -> Optional[Dict]:
        """Cria um novo usuário"""
        if self._use_local:
            usuarios = self._local_db._read_json(self._local_db.usuarios_file)
            novo_usuario = {
                "id": self._local_db._generate_id(),
                "email": email,
                "nome": nome,
                "auth_id": auth_id,
                "ativo": True,
                "created_at": datetime.now().isoformat()
            }
            usuarios.append(novo_usuario)
            self._local_db._write_json(self._local_db.usuarios_file, usuarios)
            return novo_usuario
        
        if not self._client:
            return None
            
        try:
            data = {"email": email, "nome": nome, "auth_id": auth_id, "ativo": True}
            result = self._client.table("usuarios").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Erro ao criar usuário: {e}")
            return None
    
    def buscar_usuario_por_email(self, email: str) -> Optional[Dict]:
        """Busca usuário pelo email"""
        if self._use_local:
            usuarios = self._local_db._read_json(self._local_db.usuarios_file)
            for u in usuarios:
                if u.get("email") == email:
                    return u
            return None
        
        if not self._client:
            return None
            
        try:
            result = self._client.table("usuarios").select("*").eq("email", email).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Erro ao buscar usuário: {e}")
            return None
    
    def buscar_usuario_por_id(self, user_id: str) -> Optional[Dict]:
        """Busca usuário pelo ID"""
        if self._use_local:
            usuarios = self._local_db._read_json(self._local_db.usuarios_file)
            for u in usuarios:
                if u.get("id") == user_id:
                    return u
            return None
        
        if not self._client:
            return None
            
        try:
            result = self._client.table("usuarios").select("*").eq("id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Erro ao buscar usuário: {e}")
            return None
    
    # ==================== CATEGORIAS ====================
    
    def criar_categorias_padrao(self, user_id: str) -> bool:
        """Cria categorias padrão para um novo usuário"""
        if self._use_local:
            categorias = self._local_db._read_json(self._local_db.categorias_file)
            for tipo, cats in Config.CATEGORIAS_PADRAO.items():
                for cat in cats:
                    categorias.append({
                        "id": self._local_db._generate_id(),
                        "user_id": user_id,
                        "nome": cat["nome"],
                        "tipo": "receita" if tipo == "receitas" else "despesa",
                        "icone": cat["icone"],
                        "ativo": True,
                        "created_at": datetime.now().isoformat()
                    })
            self._local_db._write_json(self._local_db.categorias_file, categorias)
            return True
        
        if not self._client:
            return False
            
        try:
            categorias = []
            for tipo, cats in Config.CATEGORIAS_PADRAO.items():
                for cat in cats:
                    categorias.append({
                        "user_id": user_id,
                        "nome": cat["nome"],
                        "tipo": "receita" if tipo == "receitas" else "despesa",
                        "icone": cat["icone"],
                        "ativo": True
                    })
            self._client.table("categorias").insert(categorias).execute()
            return True
        except Exception as e:
            print(f"Erro ao criar categorias padrão: {e}")
            return False
    
    def listar_categorias(self, user_id: str, tipo: str = None, include_inactive: bool = False) -> List[Dict]:
        """Lista categorias do usuário.

        Por padrão retorna apenas categorias ativas. Para incluir categorias desativadas
        (soft delete), use include_inactive=True.
        """
        if self._use_local:
            categorias = self._local_db._read_json(self._local_db.categorias_file)
            resultado = [c for c in categorias if c.get("user_id") == user_id and (include_inactive or c.get("ativo", True))]
            if tipo:
                resultado = [c for c in resultado if c.get("tipo") == tipo]
            return sorted(resultado, key=lambda x: x.get("nome", ""))
        
        if not self._client:
            return []
            
        try:
            query = self._client.table("categorias").select("*").eq("user_id", user_id)
            if not include_inactive:
                query = query.eq("ativo", True)
            if tipo:
                query = query.eq("tipo", tipo)
            result = query.order("nome").execute()
            return result.data or []
        except Exception as e:
            print(f"Erro ao listar categorias: {e}")
            return []
    
    def criar_categoria(self, user_id: str, nome: str, tipo: str, icone: str = "📦") -> Optional[Dict]:
        """Cria uma nova categoria"""
        if self._use_local:
            categorias = self._local_db._read_json(self._local_db.categorias_file)
            nova_categoria = {
                "id": self._local_db._generate_id(),
                "user_id": user_id,
                "nome": nome,
                "tipo": tipo,
                "icone": icone,
                "ativo": True,
                "created_at": datetime.now().isoformat()
            }
            categorias.append(nova_categoria)
            self._local_db._write_json(self._local_db.categorias_file, categorias)
            return nova_categoria
        
        if not self._client:
            return None
            
        try:
            data = {"user_id": user_id, "nome": nome, "tipo": tipo, "icone": icone, "ativo": True}
            result = self._client.table("categorias").insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            # Se a categoria já existe (mesmo inativa), o UNIQUE(user_id,nome,tipo) pode bloquear.
            # Nesse caso, reativar e retornar a categoria existente.
            msg = str(e)
            try:
                if "duplicate key" in msg.lower() or "unique" in msg.lower():
                    existente = (
                        self._client.table("categorias")
                        .select("*")
                        .eq("user_id", user_id)
                        .eq("nome", nome)
                        .eq("tipo", tipo)
                        .limit(1)
                        .execute()
                    )
                    if existente.data:
                        cat_id = existente.data[0].get("id")
                        if cat_id:
                            atualizado = (
                                self._client.table("categorias")
                                .update({"ativo": True, "icone": icone})
                                .eq("id", cat_id)
                                .execute()
                            )
                            return atualizado.data[0] if atualizado.data else existente.data[0]
            except Exception:
                pass

            print(f"Erro ao criar categoria: {e}")
            return None
    
    def atualizar_categoria(self, categoria_id: str, dados: Dict) -> Optional[Dict]:
        """Atualiza uma categoria"""
        if self._use_local:
            categorias = self._local_db._read_json(self._local_db.categorias_file)
            for i, c in enumerate(categorias):
                if c.get("id") == categoria_id:
                    categorias[i].update(dados)
                    categorias[i]["updated_at"] = datetime.now().isoformat()
                    self._local_db._write_json(self._local_db.categorias_file, categorias)
                    return categorias[i]
            return None
        
        if not self._client:
            return None
            
        try:
            # Não incluir updated_at no Supabase (o trigger cuida disso)
            dados_limpos = {k: v for k, v in dados.items() if k != "updated_at"}
            print(f"🔍 Atualizando categoria {categoria_id}: {dados_limpos}")
            result = self._client.table("categorias").update(dados_limpos).eq("id", categoria_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Erro ao atualizar categoria: {e}")
            return None
    
    def deletar_categoria(self, categoria_id: str) -> bool:
        """Desativa uma categoria"""
        return self.atualizar_categoria(categoria_id, {"ativo": False}) is not None
    
    # ==================== TRANSAÇÕES ====================
    
    def criar_transacao(self, transacao: Dict) -> Optional[Dict]:
        """Cria uma nova transação"""
        if self._use_local:
            transacoes = self._local_db._read_json(self._local_db.transacoes_file)
            nova_transacao = {
                "id": self._local_db._generate_id(),
                **transacao,
                "created_at": datetime.now().isoformat()
            }
            # Converter data para string se necessário
            if isinstance(nova_transacao.get("data"), (datetime, date)):
                nova_transacao["data"] = nova_transacao["data"].isoformat()
            transacoes.append(nova_transacao)
            self._local_db._write_json(self._local_db.transacoes_file, transacoes)
            print(f"✅ Transação salva localmente: {nova_transacao['descricao']}")
            return nova_transacao
        
        if not self._client:
            print("❌ Cliente Supabase não disponível")
            return None
            
        try:
            print(f"📤 Enviando transação para Supabase: {transacao}")
            if isinstance(transacao.get("data"), (datetime, date)):
                transacao["data"] = transacao["data"].isoformat()
            result = self._client.table("transacoes").insert(transacao).execute()
            print(f"✅ Transação salva no Supabase: {result.data}")
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Erro ao criar transação no Supabase: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def criar_transacoes_em_lote(self, transacoes: List[Dict]) -> List[Dict]:
        """Cria múltiplas transações de uma vez"""
        if self._use_local:
            resultado = []
            for t in transacoes:
                r = self.criar_transacao(t)
                if r:
                    resultado.append(r)
            print(f"✅ {len(resultado)} transações salvas localmente")
            return resultado
        
        if not self._client:
            print("❌ Cliente Supabase não disponível")
            return []
            
        try:
            print(f"📤 Enviando {len(transacoes)} transações para Supabase")
            for t in transacoes:
                if isinstance(t.get("data"), (datetime, date)):
                    t["data"] = t["data"].isoformat()
            result = self._client.table("transacoes").insert(transacoes).execute()
            print(f"✅ {len(result.data)} transações salvas no Supabase")
            return result.data or []
        except Exception as e:
            print(f"❌ Erro ao criar transações em lote no Supabase: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def listar_transacoes(
        self, 
        user_id: str, 
        data_inicio: date = None, 
        data_fim: date = None,
        tipo: str = None,
        categoria_id: str = None,
        limite: int = 100
    ) -> List[Dict]:
        """Lista transações com filtros"""
        if self._use_local:
            transacoes = self._local_db._read_json(self._local_db.transacoes_file)
            categorias = self._local_db._read_json(self._local_db.categorias_file)
            cat_map = {c["id"]: c for c in categorias}
            
            resultado = [t for t in transacoes if t.get("user_id") == user_id]
            
            if data_inicio:
                data_inicio_str = data_inicio.isoformat() if isinstance(data_inicio, date) else data_inicio
                resultado = [t for t in resultado if t.get("data", "") >= data_inicio_str]
            
            if data_fim:
                data_fim_str = data_fim.isoformat() if isinstance(data_fim, date) else data_fim
                resultado = [t for t in resultado if t.get("data", "") <= data_fim_str]
            
            if tipo:
                resultado = [t for t in resultado if t.get("tipo") == tipo]
            
            if categoria_id:
                resultado = [t for t in resultado if t.get("categoria_id") == categoria_id]
            
            # Adicionar dados da categoria
            for t in resultado:
                cat_id = t.get("categoria_id")
                if cat_id and cat_id in cat_map:
                    t["categorias"] = cat_map[cat_id]
            
            # Ordenar por data decrescente e limitar
            resultado.sort(key=lambda x: x.get("data", ""), reverse=True)
            return resultado[:limite]
        
        if not self._client:
            return []
            
        try:
            query = self._client.table("transacoes").select(
                "*, categorias(id, nome, icone)"
            ).eq("user_id", user_id)
            
            if data_inicio:
                query = query.gte("data", data_inicio.isoformat())
            if data_fim:
                query = query.lte("data", data_fim.isoformat())
            if tipo:
                query = query.eq("tipo", tipo)
            if categoria_id:
                query = query.eq("categoria_id", categoria_id)
            
            result = query.order("data", desc=True).limit(limite).execute()
            return result.data or []
        except Exception as e:
            print(f"Erro ao listar transações: {e}")
            return []
    
    def atualizar_transacao(self, transacao_id: str, dados: Dict) -> Optional[Dict]:
        """Atualiza uma transação"""
        if self._use_local:
            transacoes = self._local_db._read_json(self._local_db.transacoes_file)
            for i, t in enumerate(transacoes):
                if t.get("id") == transacao_id:
                    if isinstance(dados.get("data"), (datetime, date)):
                        dados["data"] = dados["data"].isoformat()
                    transacoes[i].update(dados)
                    transacoes[i]["updated_at"] = datetime.now().isoformat()
                    self._local_db._write_json(self._local_db.transacoes_file, transacoes)
                    return transacoes[i]
            return None
        
        if not self._client:
            return None
            
        try:
            if isinstance(dados.get("data"), (datetime, date)):
                dados["data"] = dados["data"].isoformat()
            # Não incluir updated_at no Supabase (o trigger cuida disso)
            dados_limpos = {k: v for k, v in dados.items() if k != "updated_at"}
            result = self._client.table("transacoes").update(dados_limpos).eq("id", transacao_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Erro ao atualizar transação: {e}")
            return None
    
    def deletar_transacao(self, transacao_id: str) -> bool:
        """Deleta uma transação"""
        if self._use_local:
            transacoes = self._local_db._read_json(self._local_db.transacoes_file)
            transacoes = [t for t in transacoes if t.get("id") != transacao_id]
            self._local_db._write_json(self._local_db.transacoes_file, transacoes)
            return True
        
        if not self._client:
            return False
            
        try:
            self._client.table("transacoes").delete().eq("id", transacao_id).execute()
            return True
        except Exception as e:
            print(f"Erro ao deletar transação: {e}")
            return False
    
    # ==================== RELATÓRIOS ====================
    
    def resumo_por_categoria(self, user_id: str, data_inicio: date, data_fim: date) -> List[Dict]:
        """Retorna resumo de gastos por categoria"""
        transacoes = self.listar_transacoes(user_id, data_inicio, data_fim)
        
        resumo = {}
        for t in transacoes:
            cat = t.get("categorias") or {"nome": "Sem categoria", "icone": "❓"}
            cat_nome = cat.get("nome", "Sem categoria")
            
            if cat_nome not in resumo:
                resumo[cat_nome] = {
                    "categoria": cat_nome,
                    "icone": cat.get("icone", "📦"),
                    "total_receitas": 0,
                    "total_despesas": 0,
                    "quantidade": 0
                }
            
            if t["tipo"] == "receita":
                resumo[cat_nome]["total_receitas"] += float(t["valor"])
            else:
                resumo[cat_nome]["total_despesas"] += float(t["valor"])
            resumo[cat_nome]["quantidade"] += 1
        
        return list(resumo.values())
    
    def totais_periodo(self, user_id: str, data_inicio: date, data_fim: date) -> Dict:
        """Retorna totais de receitas e despesas do período"""
        transacoes = self.listar_transacoes(user_id, data_inicio, data_fim)
        
        totais = {"receitas": 0, "despesas": 0, "saldo": 0}
        for t in transacoes:
            if t["tipo"] == "receita":
                totais["receitas"] += float(t["valor"])
            else:
                totais["despesas"] += float(t["valor"])
        
        totais["saldo"] = totais["receitas"] - totais["despesas"]
        return totais

    # ==================== ORÇAMENTOS ====================
    
    def definir_orcamento(self, user_id: str, categoria_id: str, valor_limite: float, periodo: str = "mensal") -> Optional[Dict]:
        """Cria ou atualiza um orçamento para uma categoria"""
        if self._use_local:
            orcamentos = self._local_db._read_json(self._local_db.orcamentos_file)
            
            # Verificar se já existe orçamento para esta categoria
            for i, o in enumerate(orcamentos):
                if o.get("user_id") == user_id and o.get("categoria_id") == categoria_id and o.get("ativo", True):
                    # Atualizar existente
                    orcamentos[i]["valor_limite"] = valor_limite
                    orcamentos[i]["periodo"] = periodo
                    orcamentos[i]["updated_at"] = datetime.now().isoformat()
                    self._local_db._write_json(self._local_db.orcamentos_file, orcamentos)
                    return orcamentos[i]
            
            # Criar novo
            novo_orcamento = {
                "id": self._local_db._generate_id(),
                "user_id": user_id,
                "categoria_id": categoria_id,
                "valor_limite": valor_limite,
                "periodo": periodo,
                "ativo": True,
                "created_at": datetime.now().isoformat()
            }
            orcamentos.append(novo_orcamento)
            self._local_db._write_json(self._local_db.orcamentos_file, orcamentos)
            return novo_orcamento
        
        if not self._client:
            return None
            
        try:
            # Verificar duplicidade
            existente = self._client.table("orcamentos").select("id").eq("user_id", user_id).eq("categoria_id", categoria_id).eq("ativo", True).execute()
            
            if existente.data:
                # Atualizar (não incluir updated_at, o trigger cuida disso)
                orc_id = existente.data[0]["id"]
                data = {
                    "valor_limite": valor_limite,
                    "periodo": periodo
                }
                result = self._client.table("orcamentos").update(data).eq("id", orc_id).execute()
                return result.data[0] if result.data else None
            else:
                # Se existir orçamento inativo (soft delete), reativar em vez de inserir.
                existente_inativo = (
                    self._client.table("orcamentos")
                    .select("id")
                    .eq("user_id", user_id)
                    .eq("categoria_id", categoria_id)
                    .limit(1)
                    .execute()
                )

                if existente_inativo.data:
                    orc_id = existente_inativo.data[0]["id"]
                    data = {
                        "valor_limite": valor_limite,
                        "periodo": periodo,
                        "ativo": True
                    }
                    result = self._client.table("orcamentos").update(data).eq("id", orc_id).execute()
                    return result.data[0] if result.data else None

                # Criar
                data = {
                    "user_id": user_id,
                    "categoria_id": categoria_id,
                    "valor_limite": valor_limite,
                    "periodo": periodo,
                    "ativo": True
                }
                result = self._client.table("orcamentos").insert(data).execute()
                return result.data[0] if result.data else None
        except Exception as e:
            print(f"Erro ao definir orçamento: {e}")
            return None

    def criar_orcamento(self, user_id: str, categoria_id: str, valor_limite: float, periodo: str = "mensal") -> Optional[Dict]:
        """Mantido para compatibilidade, mas redireciona para definir_orcamento"""
        return self.definir_orcamento(user_id, categoria_id, valor_limite, periodo)

    def listar_orcamentos(self, user_id: str) -> List[Dict]:
        """Lista orçamentos do usuário com progresso calculado"""
        if self._use_local:
            orcamentos = self._local_db._read_json(self._local_db.orcamentos_file)
            categorias = self._local_db._read_json(self._local_db.categorias_file)
            cat_map = {c["id"]: c for c in categorias}
            
            resultado = [o for o in orcamentos if o.get("user_id") == user_id and o.get("ativo", True)]
            
            # Calcular progresso
            hoje = date.today()
            inicio_mes = hoje.replace(day=1).isoformat()
            fim_mes = hoje.isoformat() # Até hoje
            
            transacoes = self._local_db._read_json(self._local_db.transacoes_file)
            
            for o in resultado:
                cat_id = o.get("categoria_id")
                if cat_id in cat_map:
                    o["categoria"] = cat_map[cat_id]
                
                # Somar gastos da categoria no mês
                gastos = sum(
                    float(t["valor"]) 
                    for t in transacoes 
                    if t.get("user_id") == user_id 
                    and t.get("categoria_id") == cat_id 
                    and t.get("tipo") == "despesa"
                    and t.get("data", "") >= inicio_mes
                )
                o["valor_gasto"] = gastos
                o["saldo_restante"] = float(o["valor_limite"]) - gastos
            
            return resultado
        
        if not self._client:
            return []
            
        try:
            # Buscar orçamentos
            orcamentos = self._client.table("orcamentos").select("*, categorias(nome, icone)").eq("user_id", user_id).eq("ativo", True).execute()
            lista_orcamentos = orcamentos.data or []
            
            # Calcular gastos (simplificado - ideal seria uma view ou function no banco)
            hoje = date.today()
            inicio_mes = hoje.replace(day=1).isoformat()
            
            for o in lista_orcamentos:
                cat_id = o.get("categoria_id")
                gastos = self._client.table("transacoes").select("valor").eq("user_id", user_id).eq("categoria_id", cat_id).eq("tipo", "despesa").gte("data", inicio_mes).execute()
                
                total_gasto = sum(float(t["valor"]) for t in gastos.data) if gastos.data else 0
                o["valor_gasto"] = total_gasto
                o["saldo_restante"] = float(o["valor_limite"]) - total_gasto
                
            return lista_orcamentos
        except Exception as e:
            print(f"Erro ao listar orçamentos: {e}")
            return []

    def deletar_orcamento(self, orcamento_id: str) -> bool:
        """Remove um orçamento (soft delete)"""
        if self._use_local:
            orcamentos = self._local_db._read_json(self._local_db.orcamentos_file)
            for i, o in enumerate(orcamentos):
                if o.get("id") == orcamento_id:
                    orcamentos[i]["ativo"] = False
                    self._local_db._write_json(self._local_db.orcamentos_file, orcamentos)
                    return True
            return False
        
        if not self._client:
            return False
            
        try:
            self._client.table("orcamentos").update({"ativo": False}).eq("id", orcamento_id).execute()
            return True
        except Exception as e:
            print(f"Erro ao deletar orçamento: {e}")
            return False


# Instância global
db = DatabaseService()
