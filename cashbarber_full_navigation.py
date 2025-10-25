"""
Script completo para acessar o relatório de Quantidade de Assinantes no Cashbarber.

Este script realiza:
1. Login no painel Cashbarber
2. Navegação pelo menu: Relatórios → Assinaturas → Quantidade de assinantes
3. Aplica filtros (opcional)

Uso:
    python cashbarber_full_navigation.py <email> <senha> [--headless]
"""

import argparse
import sys
import os
import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service


# ============================================================================
# FUNÇÃO DE LOGIN
# ============================================================================

def login_cashbarber(email: str, password: str, headless: bool = False) -> webdriver.Chrome:
    """
    Realiza o login no painel Cashbarber e retorna o driver autenticado.
    
    Args:
        email: E-mail de acesso ao painel
        password: Senha de acesso ao painel
        headless: Se True, executa o navegador em modo headless
    
    Returns:
        webdriver.Chrome: Instância do driver do Chrome já autenticado
    
    Raises:
        RuntimeError: Se o login falhar
    """
    LOGIN_URL = "https://painel.cashbarber.com.br/login"
    
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    
    chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', 'chromedriver')
    
    try:
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
    except Exception:
        driver = webdriver.Chrome(options=options)
    
    driver.get(LOGIN_URL)
    wait = WebDriverWait(driver, 20)
    
    email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
    password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
    
    email_input.clear()
    email_input.send_keys(email)
    password_input.clear()
    password_input.send_keys(password)
    
    try:
        login_button = driver.find_element(By.ID, "kt_login_signin_submit")
    except NoSuchElementException:
        login_button = driver.find_element(By.XPATH, "//button[contains(., 'Acessar')]")
    
    login_button.click()
    
    try:
        wait.until(lambda drv: "/login" not in drv.current_url)
    except TimeoutException:
        driver.quit()
        raise RuntimeError("Falha no login: verifique as credenciais.")
    
    return driver


# ============================================================================
# FUNÇÃO DE NAVEGAÇÃO
# ============================================================================

def navigate_to_quantidade_assinantes(driver: webdriver.Chrome, wait_time: int = 20) -> None:
    """
    Navega até a página de Quantidade de Assinantes.
    
    Sequência: Relatórios → Assinaturas → Quantidade de assinantes
    
    Args:
        driver: Instância do webdriver Chrome já autenticado
        wait_time: Tempo máximo de espera em segundos
    
    Raises:
        TimeoutException: Se algum elemento não for encontrado
    """
    wait = WebDriverWait(driver, wait_time)
    
    # Passo 1: Clicar em "Relatórios"
    print("\n[1/4] Abrindo menu 'Relatórios'...")
    try:
        wait.until(EC.presence_of_element_located((By.ID, "kt_aside_menu")))
        
        relatorios_menu = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//span[@class='kt-menu__link-text' and contains(text(), 'Relatórios')]")
            )
        )
        
        relatorios_menu.click()
        time.sleep(0.5)
        print("      ✓ Menu 'Relatórios' aberto")
        
    except TimeoutException:
        raise TimeoutException("Não foi possível localizar o menu 'Relatórios'")
    
    # Passo 2: Clicar em "Assinaturas"
    print("[2/4] Abrindo submenu 'Assinaturas'...")
    try:
        assinaturas_submenu = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//li[@class='kt-menu__item kt-menu__item--submenu']//span[contains(text(), 'Assinaturas')]/parent::a")
            )
        )
        
        assinaturas_submenu.click()
        time.sleep(0.5)
        print("      ✓ Submenu 'Assinaturas' aberto")
        
    except TimeoutException:
        raise TimeoutException("Não foi possível localizar o submenu 'Assinaturas'")
    
    # Passo 3: Clicar em "Quantidade de assinantes"
    print("[3/4] Acessando 'Quantidade de assinantes'...")
    try:
        quantidade_assinantes_link = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[@href='/relatorio/relatorio19']")
            )
        )
        
        quantidade_assinantes_link.click()
        
        wait.until(lambda drv: "/relatorio/relatorio19" in drv.current_url)
        print("      ✓ Página do relatório carregada")
        
    except TimeoutException:
        raise TimeoutException("Não foi possível acessar 'Quantidade de assinantes'")
    
    # Passo 4: Verificar se há botão de filtrar
    print("[4/4] Procurando opções de filtro...")
    try:
        time.sleep(1)
        
        filtrar_button = driver.find_element(
            By.XPATH, 
            "//button[contains(text(), 'Filtrar') or contains(text(), 'filtrar')]"
        )
        
        if filtrar_button:
            filtrar_button.click()
            print("      ✓ Filtro aplicado")
            time.sleep(0.5)
    except NoSuchElementException:
        print("      ℹ Nenhum filtro adicional necessário")
    
    print("\n✅ Navegação concluída com sucesso!")


def navigate_direto(driver: webdriver.Chrome) -> None:
    """
    Alternativa: Acessa diretamente a URL do relatório.
    
    Args:
        driver: Instância do webdriver Chrome já autenticado
    """
    RELATORIO_URL = "https://painel.cashbarber.com.br/relatorio/relatorio19"
    
    print("\nNavegando diretamente para o relatório...")
    driver.get(RELATORIO_URL)
    
    wait = WebDriverWait(driver, 20)
    wait.until(lambda drv: "/relatorio/relatorio19" in drv.current_url)
    print("✅ Relatório carregado!")


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def main(argv: Optional[list] = None) -> int:
    """
    Executa o fluxo completo: login + navegação.
    """
    parser = argparse.ArgumentParser(
        description="Acessa o relatório de Quantidade de Assinantes no Cashbarber"
    )
    parser.add_argument("email", help="E-mail de acesso")
    parser.add_argument("password", help="Senha de acesso")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executa o navegador em modo headless (sem interface gráfica)"
    )
    parser.add_argument(
        "--direto",
        action="store_true",
        help="Acessa diretamente a URL do relatório (mais rápido)"
    )
    
    args = parser.parse_args(argv)
    
    driver = None
    try:
        # Login
        print("=" * 60)
        print("INICIANDO LOGIN NO PAINEL CASHBARBER")
        print("=" * 60)
        driver = login_cashbarber(args.email, args.password, headless=args.headless)
        print("✅ Login realizado com sucesso!")
        
        # Navegação
        print("\n" + "=" * 60)
        print("NAVEGANDO ATÉ RELATÓRIO DE ASSINATURAS")
        print("=" * 60)
        
        if args.direto:
            navigate_direto(driver)
        else:
            navigate_to_quantidade_assinantes(driver)
        
        # Aguarda para visualização (apenas se não for headless)
        if not args.headless:
            print("\n" + "=" * 60)
            print("Navegador aberto. Pressione Enter para fechar...")
            print("=" * 60)
            input()
        else:
            # Em modo headless, aguarda alguns segundos
            time.sleep(3)
            print("\nModo headless: finalizando automaticamente.")
        
        return 0
        
    except Exception as exc:
        print(f"\n❌ ERRO: {exc}")
        return 1
    finally:
        if driver:
            driver.quit()
            print("🔒 Navegador fechado.")


if __name__ == "__main__":
    sys.exit(main())
