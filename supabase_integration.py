"""
Integração com Supabase para atualização de dados de assinantes.

Este módulo gerencia:
1. Conexão com Supabase
2. Busca de clientes existentes
3. Atualização de tipo de plano e status
4. Matching inteligente de nomes (fuzzy matching)
"""

import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging
from supabase import create_client, Client
from difflib import SequenceMatcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ClienteSupabase:
    """Representa um cliente no banco Supabase."""
    id: str
    nome: str
    telefone: Optional[str]
    plano_atual: Optional[str]
    status_assinatura: Optional[str]


class SupabaseIntegration:
    """Gerencia integração com Supabase."""
    
    def __init__(
        self, 
        url: str = None, 
        key: str = None, 
        table_name: str = None,
        column_nome: str = None,
        column_plano: str = None,
        column_status: str = None
    ):
        """
        Inicializa conexão com Supabase.
        
        Args:
            url: URL do projeto Supabase (se None, usa variável de ambiente)
            key: Service role key (se None, usa variável de ambiente)
            table_name: Nome da tabela de clientes (padrão via env ou 'clientes')
            column_nome: Nome da coluna com nome do cliente (padrão: 'nome')
            column_plano: Nome da coluna para plano (padrão: 'plano_atual')
            column_status: Nome da coluna para status (padrão: 'status_assinatura')
        """
        self.url = url or os.getenv('SUPABASE_URL')
        self.key = key or os.getenv('SUPABASE_SERVICE_KEY')
        self.table_name = table_name or os.getenv('SUPABASE_TABLE_NAME', 'clientes')
        
        # Nomes das colunas configuráveis
        self.column_nome = column_nome or os.getenv('COLUMN_NOME', 'nome')
        self.column_plano = column_plano or os.getenv('COLUMN_PLANO', 'plano_atual')
        self.column_status = column_status or os.getenv('COLUMN_STATUS', 'status_assinatura')
        
        if not self.url or not self.key:
            raise ValueError(
                "SUPABASE_URL e SUPABASE_SERVICE_KEY devem estar configurados"
            )
        
        self.client: Client = create_client(self.url, self.key)
        logger.info(f"✓ Conectado ao Supabase: {self.url}")
    
    def get_all_clientes(self) -> List[ClienteSupabase]:
        """
        Busca todos os clientes do banco.
        
        Returns:
            Lista de clientes
        """
        try:
            response = self.client.table(self.table_name).select('*').execute()
            
            clientes = [
                ClienteSupabase(
                    id=row['id'],
                    nome=row.get(self.column_nome, ''),
                    telefone=row.get('telefone'),
                    plano_atual=row.get(self.column_plano),
                    status_assinatura=row.get(self.column_status)
                )
                for row in response.data
            ]
            
            logger.info(f"✓ {len(clientes)} clientes carregados da tabela '{self.table_name}'")
            return clientes
            
        except Exception as e:
            logger.error(f"Erro ao buscar clientes: {e}")
            raise
    
    def find_cliente_by_name(
        self, 
        nome_busca: str, 
        clientes: List[ClienteSupabase],
        threshold: float = 0.85
    ) -> Optional[ClienteSupabase]:
        """
        Busca cliente por nome usando fuzzy matching.
        
        Args:
            nome_busca: Nome para buscar
            clientes: Lista de clientes disponíveis
            threshold: Limiar de similaridade (0-1)
        
        Returns:
            Cliente encontrado ou None
        """
        nome_busca_lower = nome_busca.lower().strip()
        
        best_match = None
        best_ratio = 0.0
        
        for cliente in clientes:
            nome_cliente_lower = cliente.nome.lower().strip()
            
            # Match exato
            if nome_busca_lower == nome_cliente_lower:
                return cliente
            
            # Fuzzy matching
            ratio = SequenceMatcher(None, nome_busca_lower, nome_cliente_lower).ratio()
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = cliente
        
        if best_ratio >= threshold:
            return best_match
        
        return None
    
    def update_cliente(
        self, 
        cliente_id: str, 
        plano: str, 
        status: str,
        update_timestamp: bool = True
    ) -> bool:
        """
        Atualiza plano e status de um cliente.
        
        Args:
            cliente_id: ID do cliente
            plano: Tipo de plano
            status: Status da assinatura
            update_timestamp: Se True, tenta atualizar campo de timestamp (se existir)
        
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            update_data = {
                self.column_plano: plano,
                self.column_status: status
            }
            
            # Tenta adicionar timestamp se a coluna existir
            if update_timestamp:
                timestamp_column = os.getenv('COLUMN_TIMESTAMP', 'ultima_sincronizacao')
                update_data[timestamp_column] = 'now()'
            
            response = self.client.table(self.table_name)\
                .update(update_data)\
                .eq('id', cliente_id)\
                .execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar cliente {cliente_id}: {e}")
            return False
    
    def sync_assinantes(
        self, 
        assinantes_cashbarber: List[Dict],
        dry_run: bool = False
    ) -> Dict:
        """
        Sincroniza dados de assinantes do Cashbarber com Supabase.
        
        Args:
            assinantes_cashbarber: Lista de assinantes extraídos
            dry_run: Se True, apenas simula sem atualizar
        
        Returns:
            Estatísticas da sincronização
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"INICIANDO SINCRONIZAÇÃO {'(DRY RUN)' if dry_run else ''}")
        logger.info(f"{'='*60}\n")
        
        clientes_supabase = self.get_all_clientes()
        
        stats = {
            'total_cashbarber': len(assinantes_cashbarber),
            'total_supabase': len(clientes_supabase),
            'encontrados': 0,
            'atualizados': 0,
            'nao_encontrados': 0,
            'erros': 0,
            'nao_encontrados_lista': []
        }
        
        for assinante in assinantes_cashbarber:
            nome = assinante['nome']
            plano = assinante['plano']
            status = assinante['status']
            
            # Busca cliente no Supabase
            cliente = self.find_cliente_by_name(nome, clientes_supabase)
            
            if cliente:
                stats['encontrados'] += 1
                
                logger.info(f"✓ Match encontrado: '{nome}' → '{cliente.nome}'")
                logger.info(f"  Plano: {plano}")
                logger.info(f"  Status: {status}")
                
                if not dry_run:
                    if self.update_cliente(cliente.id, plano, status):
                        stats['atualizados'] += 1
                        logger.info(f"  ✓ Atualizado com sucesso")
                    else:
                        stats['erros'] += 1
                        logger.error(f"  ✗ Erro ao atualizar")
                else:
                    logger.info(f"  → [DRY RUN] Seria atualizado")
                    stats['atualizados'] += 1
            else:
                stats['nao_encontrados'] += 1
                stats['nao_encontrados_lista'].append(nome)
                logger.warning(f"✗ Cliente não encontrado: '{nome}'")
        
        self._log_final_stats(stats, dry_run)
        return stats
    
    def _log_final_stats(self, stats: Dict, dry_run: bool) -> None:
        """Imprime estatísticas finais da sincronização."""
        logger.info(f"\n{'='*60}")
        logger.info(f"RESULTADO DA SINCRONIZAÇÃO {'(DRY RUN)' if dry_run else ''}")
        logger.info(f"{'='*60}")
        logger.info(f"Total no Cashbarber: {stats['total_cashbarber']}")
        logger.info(f"Total no Supabase:   {stats['total_supabase']}")
        logger.info(f"Encontrados:         {stats['encontrados']}")
        logger.info(f"Atualizados:         {stats['atualizados']}")
        logger.info(f"Não encontrados:     {stats['nao_encontrados']}")
        logger.info(f"Erros:               {stats['erros']}")
        
        if stats['nao_encontrados_lista']:
            logger.info(f"\nClientes não encontrados:")
            for nome in stats['nao_encontrados_lista'][:10]:  # Mostra apenas 10
                logger.info(f"  - {nome}")
            
            if len(stats['nao_encontrados_lista']) > 10:
                logger.info(f"  ... e mais {len(stats['nao_encontrados_lista']) - 10}")
        
        logger.info(f"{'='*60}\n")


def sync_from_data(assinantes_data: List[Dict], dry_run: bool = False) -> Dict:
    """
    Função helper para sincronizar dados extraídos com Supabase.
    
    Args:
        assinantes_data: Lista de dicionários com dados dos assinantes
        dry_run: Se True, apenas simula sem atualizar
    
    Returns:
        Estatísticas da sincronização
    """
    integration = SupabaseIntegration()
    return integration.sync_assinantes(assinantes_data, dry_run=dry_run)
