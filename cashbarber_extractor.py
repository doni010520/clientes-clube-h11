"""
Extrator de dados de assinantes do Cashbarber.

Este módulo é responsável por:
1. Extrair dados da tabela de assinantes após navegação
2. Processar e estruturar os dados
3. Atualizar banco Supabase com tipo de plano e status

Campos extraídos:
- Cliente (nome)
- Plano (tipo de assinatura)
- Status (Em dia, Pagamento recusado, etc)
- Data de criação
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Assinante:
    """Representa um assinante com suas informações."""
    nome: str
    plano: str
    status: str
    data_criacao: str
    
    def to_dict(self) -> Dict:
        """Converte para dicionário para facilitar integração."""
        return {
            'nome': self.nome,
            'plano': self.plano,
            'status': self.status,
            'data_criacao': self.data_criacao
        }


class CashbarberExtractor:
    """Extrator de dados de assinantes do Cashbarber."""
    
    def __init__(self, driver: webdriver.Chrome):
        """
        Inicializa o extrator com driver já autenticado e navegado.
        
        Args:
            driver: Instância do Chrome WebDriver já posicionada na página do relatório
        """
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)
    
    def wait_for_table_load(self) -> None:
        """Aguarda o carregamento completo da tabela de resultados."""
        try:
            logger.info("Aguardando carregamento da tabela...")
            
            # Aguarda a presença da tabela
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-striped tbody"))
            )
            
            # Aguarda pelo menos uma linha de dados (não apenas o header)
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-striped tbody tr"))
            )
            
            logger.info("✓ Tabela carregada com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao aguardar carregamento da tabela: {e}")
            raise
    
    def extract_assinantes(self) -> List[Assinante]:
        """
        Extrai todos os assinantes da tabela HTML.
        
        Returns:
            Lista de objetos Assinante com os dados extraídos
        """
        try:
            self.wait_for_table_load()
            
            # Pega o HTML completo da página
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Localiza a tabela
            table = soup.find('table', class_='table-striped')
            if not table:
                raise ValueError("Tabela não encontrada no HTML")
            
            tbody = table.find('tbody')
            if not tbody:
                raise ValueError("Corpo da tabela não encontrado")
            
            assinantes = []
            rows = tbody.find_all('tr')
            
            logger.info(f"Processando {len(rows)} linhas da tabela...")
            
            for row in rows:
                cols = row.find_all('td')
                
                # Pula linha de total (tem colspan)
                if len(cols) < 4 or cols[0].get('colspan'):
                    continue
                
                try:
                    assinante = Assinante(
                        nome=cols[0].text.strip(),
                        plano=cols[1].text.strip(),
                        status=cols[2].text.strip(),
                        data_criacao=cols[3].text.strip()
                    )
                    assinantes.append(assinante)
                    
                except Exception as e:
                    logger.warning(f"Erro ao processar linha: {e}")
                    continue
            
            logger.info(f"✓ {len(assinantes)} assinantes extraídos com sucesso")
            return assinantes
            
        except Exception as e:
            logger.error(f"Erro ao extrair assinantes: {e}")
            raise
    
    def get_total_count(self) -> Optional[int]:
        """
        Extrai o total de assinantes da última linha da tabela.
        
        Returns:
            Número total de assinantes ou None se não encontrado
        """
        try:
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            table = soup.find('table', class_='table-striped')
            if not table:
                return None
            
            tbody = table.find('tbody')
            if not tbody:
                return None
            
            # Última linha tem o total
            last_row = tbody.find_all('tr')[-1]
            total_col = last_row.find_all('td')[-1]
            
            if total_col.find('b'):
                total_text = total_col.find('b').text.strip()
                return int(total_text)
            
            return None
            
        except Exception as e:
            logger.warning(f"Não foi possível extrair total: {e}")
            return None
    
    def normalize_status(self, status: str) -> str:
        """
        Normaliza o status para formato padronizado.
        
        Args:
            status: Status original da tabela
        
        Returns:
            Status normalizado
        """
        status_map = {
            'Em dia': 'ativo',
            'Pagamento recusado': 'inadimplente',
            'Cancelado': 'cancelado',
            'Pendente': 'pendente'
        }
        
        return status_map.get(status, 'desconhecido')
    
    def filter_by_status(self, assinantes: List[Assinante], status: str) -> List[Assinante]:
        """
        Filtra assinantes por status específico.
        
        Args:
            assinantes: Lista de assinantes
            status: Status para filtrar
        
        Returns:
            Lista filtrada de assinantes
        """
        return [a for a in assinantes if a.status.lower() == status.lower()]
    
    def get_statistics(self, assinantes: List[Assinante]) -> Dict:
        """
        Gera estatísticas sobre os assinantes extraídos.
        
        Args:
            assinantes: Lista de assinantes
        
        Returns:
            Dicionário com estatísticas
        """
        stats = {
            'total': len(assinantes),
            'por_status': {},
            'por_plano': {}
        }
        
        # Conta por status
        for assinante in assinantes:
            status = assinante.status
            stats['por_status'][status] = stats['por_status'].get(status, 0) + 1
        
        # Conta por plano
        for assinante in assinantes:
            plano = assinante.plano
            stats['por_plano'][plano] = stats['por_plano'].get(plano, 0) + 1
        
        return stats


def extract_from_driver(driver: webdriver.Chrome) -> List[Dict]:
    """
    Função helper para extrair dados de um driver já posicionado.
    
    Args:
        driver: WebDriver do Selenium já autenticado e na página do relatório
    
    Returns:
        Lista de dicionários com dados dos assinantes
    """
    extractor = CashbarberExtractor(driver)
    assinantes = extractor.extract_assinantes()
    
    # Log de estatísticas
    stats = extractor.get_statistics(assinantes)
    logger.info(f"\nEstatísticas extraídas:")
    logger.info(f"  Total: {stats['total']}")
    logger.info(f"  Por Status: {stats['por_status']}")
    logger.info(f"  Planos únicos: {len(stats['por_plano'])}")
    
    return [a.to_dict() for a in assinantes]
