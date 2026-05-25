#!/usr/bin/env python3
#----------------------------------------------------------------------------
# Project	: pg.py
#----------------------------------------------------------------------------
# Date		: 
#----------------------------------------------------------------------------
# WheremI	: 
#----------------------------------------------------------------------------
# CreatedBy	: https://github.com/aopsec
#----------------------------------------------------------------------------

def termo_geral_pg(a1, n, q):
    """
    Calcula o enésimo termo de uma Progressão Geométrica
    Fórmula: an = a1 * q^(n-1)
    """
    an = a1 * q**(n-1)
    return an
 
def soma_pg_finita(a1, n, q):
    """
    Calcula a soma dos n primeiros termos de uma PG finita
    Fórmula: Sn = a1 * (q^n - 1) / (q - 1)
    """
    if q == 1:
        return a1 * n
    sn = a1 * (q**n - 1) / (q - 1)
    return sn
 
def gerar_sequencia_pg(a1, n_termos, q):
    """Gera a sequência de acessos por dia"""
    sequencia = []
    for dia in range(1, n_termos + 1):
        acessos = termo_geral_pg(a1, dia, q)
        sequencia.append((dia, int(acessos)))
    return sequencia
 
if __name__ == '__main__':
    print("="*70)
    print(" SISTEMATIZAÇÃO 02 - MATEMÁTICA PARA COMPUTAÇÃO")
    print(" Simulação de Crescimento de Acessos em Plataforma de Streaming")
    print("="*70)
    print()
    
    # Dados do problema
    a1 = 30  # Primeiro dia: 30 acessos
    q = 3    # Razão: acessos triplicam diariamente
    dias_analisados = 5
    
    print(" DADOS DO PROBLEMA")
    print("-" * 70)
    print(f"  • Dia 1: {a1} acessos")
    print(f"  • Razão da PG (q): {q} (acessos triplicam diariamente)")
    print(f"  • Período analisado: {dias_analisados} dias")
    print()
    
    # DESAFIO 1: Modelagem da PG
    print(" DESAFIO 1: MODELAGEM DA PG")
    print("-" * 70)
    print("Fórmula do Termo Geral da Progressão Geométrica:")
    print()
    print("  an = a₁ · q**(n-1)")
    print()
    print("Onde:")
    print(f"  • a₁ = {a1} (primeiro termo - acessos no dia 1)")
    print(f"  • q = {q} (razão - fator de crescimento diário)")
    print(f"  • n = número do dia")
    print()
    print("Substituindo os valores:")
    print(f"  an = {a1} · {q}^(n-1)")
    print()
    
    # DESAFIO 2: Acessos no 5º dia
    print(" DESAFIO 2: NÚMERO DE ACESSOS NO 5º DIA")
    print("-" * 70)
    n_dia_5 = 5
    acessos_dia_5 = termo_geral_pg(a1, n_dia_5, q)
    
    print(f"Utilizando a fórmula: a₅ = {a1} · {q}^(5-1)")
    print(f"                      a₅ = {a1} · {q}^4")
    print(f"                      a₅ = {a1} · {q**4}")
    print(f"                      a₅ = {int(acessos_dia_5)}")
    print()
    print(f"✓ RESULTADO: No 5º dia haverá {int(acessos_dia_5):,} acessos")
    print()
    
    # Mostrar progressão diária
    print(" PROGRESSÃO DIÁRIA (DIA 1 ao DIA 5)")
    print("-" * 70)
    sequencia = gerar_sequencia_pg(a1, dias_analisados, q)
    for dia, acessos in sequencia:
        print(f"  Dia {dia}: {acessos:>6,} acessos")
    print()
    
    # DESAFIO 3: Soma total acumulada
    print(" DESAFIO 3: TOTAL DE ACESSOS ACUMULADOS (DIA 1 ao DIA 5)")
    print("-" * 70)
    soma_total = soma_pg_finita(a1, dias_analisados, q)
    
    print(f"Utilizando a fórmula da soma finita: S₅ = a₁ · (q^n - 1) / (q - 1)")
    print()
    print(f"  S₅ = {a1} · ({q}^5 - 1) / ({q} - 1)")
    print(f"  S₅ = {a1} · ({q**5} - 1) / {q - 1}")
    print(f"  S₅ = {a1} · {q**5 - 1} / {q - 1}")
    print(f"  S₅ = {a1} · {(q**5 - 1) / (q - 1):.1f}")
    print(f"  S₅ = {int(soma_total):,}")
    print()
    print(f"✓ RESULTADO: Total acumulado de {int(soma_total):,} acessos")
    print()
    
    # Verificação por soma direta
    soma_verificacao = sum(acessos for _, acessos in sequencia)
    print("Verificação (soma direta):")
    print(f"  {' + '.join(str(acessos) for _, acessos in sequencia)} = {soma_verificacao:,} ✓")
    print()
    
    # DESAFIO 4: Análise crítica
    print(" DESAFIO 4: ANÁLISE CRÍTICA DO CRESCIMENTO EXPONENCIAL")
    print("-" * 70)
    print()
    print("Dificuldades que uma empresa de tecnologia enfrenta com crescimento rápido:")
    print()
    print("1. INFRAESTRUTURA E ESCALABILIDADE")
    print("   • Crescimento exponencial exige aumento proporcional de servidores,")
    print("     banda de rede e armazenamento de dados")
    print("   • Custos operacionais crescem rapidamente (energia, manutenção, pessoal)")
    print("   • Risco de indisponibilidade do serviço se a infraestrutura não")
    print("     acompanhar o crescimento (picos de acesso podem derrubar a plataforma)")
    print()
    print("2. GERENCIAMENTO DE QUALIDADE E SEGURANÇA")
    print("   • Mais usuários = maior volume de dados a proteger")
    print("   • Risco aumentado de ataques cibernéticos (DDoS, invasões)")
    print("   • Desafios em manter qualidade do serviço (latência, buffering)")
    print("   • Dificuldade em auditar e monitorar todas as atividades dos usuários")
    print("   • Necessidade de implementar medidas de segurança mais robustas")
    print()
    
    print("="*70)
    print("="*70)