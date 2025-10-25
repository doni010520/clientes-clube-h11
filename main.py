#!/usr/bin/env python3
"""
Script principal de sincronização Cashbarber → Supabase.

Fluxo completo:
1. Login no Cashbarber
2. Navega até relatório de assinantes
3. Extrai dados da tabela
4. Sincroniza com Supabase
5. Gera relatório final

Uso:
    python main.py --email user@example.com --password secret123
    python main.py --email user@example.com --password secret123 --dry-run
    python main.py --config config.json
"""

import argparse
import sys
import json
import os
from typing import Optional
from datetime import datetime

# Imports dos módulos locais
from cashbarber_full_navigation import login_cashbarber, navigate_to_quantidade_assinantes
from cashbarber_extractor import extract_from_driver
from supabase_integration import sync_from_data

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SyncConfig:
    """Configurações para sincronização."""
    
    def __init__(self, config_dict: dict):
        # Cashbarber credentials
        self.cashbarber_email = config_dict.get('cashbarber_email') or os.getenv('CASHBARBER_EMAIL')
        self.cashbarber_password = config_dict.get('cashbarber_password') or os.getenv('CASHBARBER_PASSWORD')
        
        # Supabase credentials (já gerenciadas por variáveis de ambiente no módulo)
        
        # Opções de execução
        self.headless = config_dict.get('headless', True)
        self.dry_run = config_dict.get('dry_run', False)
        self.direto = config_dict.get('direto', True)  # Usa navegação direta por padrão
        
        # Validação
        if not self.cashbarber_email or not self.cashbarber_password:
            raise ValueError("Email e senha do Cashbarber devem estar configurados")
    
    @classmethod
    def from_file(cls, filepath: str):
        """Carrega configurações de arquivo JSON."""
        with open(filepath, 'r') as f:
            return cls(json.load(f))
    
    @classmethod
    def from_args(cls, args):
        """Carrega configurações de argumentos CLI."""
        return cls({
            'cashbarber_email': args.email,
            'cashbarber_password': args.password,
            'headless': args.headless,
            'dry_run': args.dry_run,
            'direto': args.direto
        })


def run_sync(config: SyncConfig) -> int:
    """
    Executa sincronização completa.
    
    Args:
        config: Configurações da sincronização
    
    Returns:
        Código de saída (0 = sucesso, 1 = erro)
    """
    start_time = datetime.now()
    
    logger.info("=" * 80)
    logger.info("INICIANDO SINCRONIZAÇÃO CASHBARBER → SUPABASE")
    logger.info("=" * 80)
    logger.info(f"Horário de início: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Modo: {'DRY RUN (simulação)' if config.dry_run else 'PRODUÇÃO'}")
    logger.info(f"Headless: {'Sim' if config.headless else 'Não'}")
    logger.info("=" * 80 + "\n")
    
    driver = None
    
    try:
        # ETAPA 1: Login no Cashbarber
        logger.info("\n" + "=" * 80)
        logger.info("ETAPA 1: LOGIN NO CASHBARBER")
        logger.info("=" * 80)
        
        driver = login_cashbarber(
            email=config.cashbarber_email,
            password=config.cashbarber_password,
            headless=config.headless
        )
        
        logger.info("✓ Login realizado com sucesso\n")
        
        # ETAPA 2: Navegação até relatório
        logger.info("=" * 80)
        logger.info("ETAPA 2: NAVEGANDO ATÉ RELATÓRIO DE ASSINANTES")
        logger.info("=" * 80)
        
        if config.direto:
            from cashbarber_full_navigation import navigate_direto
            navigate_direto(driver)
        else:
            navigate_to_quantidade_assinantes(driver)
        
        logger.info("✓ Navegação concluída\n")
        
        # ETAPA 3: Extração de dados
        logger.info("=" * 80)
        logger.info("ETAPA 3: EXTRAINDO DADOS DA TABELA")
        logger.info("=" * 80)
        
        assinantes_data = extract_from_driver(driver)
        logger.info(f"✓ {len(assinantes_data)} registros extraídos\n")
        
        # ETAPA 4: Sincronização com Supabase
        logger.info("=" * 80)
        logger.info("ETAPA 4: SINCRONIZANDO COM SUPABASE")
        logger.info("=" * 80)
        
        sync_stats = sync_from_data(assinantes_data, dry_run=config.dry_run)
        
        # ETAPA 5: Relatório final
        logger.info("\n" + "=" * 80)
        logger.info("SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO")
        logger.info("=" * 80)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"Horário de término: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Duração total: {duration.total_seconds():.2f} segundos")
        logger.info(f"\nResumo:")
        logger.info(f"  - Extraídos: {sync_stats['total_cashbarber']}")
        logger.info(f"  - Atualizados: {sync_stats['atualizados']}")
        logger.info(f"  - Não encontrados: {sync_stats['nao_encontrados']}")
        logger.info(f"  - Erros: {sync_stats['erros']}")
        logger.info("=" * 80 + "\n")
        
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ ERRO DURANTE A SINCRONIZAÇÃO: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
        
    finally:
        if driver:
            driver.quit()
            logger.info("🔒 Navegador fechado")


def main(argv: Optional[list] = None) -> int:
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Sincroniza dados de assinantes do Cashbarber com Supabase"
    )
    
    # Modo de configuração
    config_group = parser.add_mutually_exclusive_group(required=True)
    config_group.add_argument(
        '--config',
        type=str,
        help='Arquivo JSON com configurações'
    )
    config_group.add_argument(
        '--email',
        type=str,
        help='Email de login no Cashbarber'
    )
    
    # Argumentos adicionais (usados com --email)
    parser.add_argument(
        '--password',
        type=str,
        help='Senha de login no Cashbarber'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        default=True,
        help='Executar navegador em modo headless (padrão: True)'
    )
    parser.add_argument(
        '--no-headless',
        action='store_false',
        dest='headless',
        help='Executar navegador com interface gráfica'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simular sem atualizar banco de dados'
    )
    parser.add_argument(
        '--direto',
        action='store_true',
        default=True,
        help='Usar navegação direta via URL (padrão: True)'
    )
    parser.add_argument(
        '--menu',
        action='store_false',
        dest='direto',
        help='Usar navegação via menu (mais lento)'
    )
    
    args = parser.parse_args(argv)
    
    # Validação
    if args.email and not args.password:
        parser.error("--password é obrigatório quando --email é usado")
    
    # Carrega configurações
    try:
        if args.config:
            config = SyncConfig.from_file(args.config)
        else:
            config = SyncConfig.from_args(args)
    except Exception as e:
        logger.error(f"Erro ao carregar configurações: {e}")
        return 1
    
    # Executa sincronização
    return run_sync(config)


if __name__ == "__main__":
    sys.exit(main())
