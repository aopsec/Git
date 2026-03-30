# #                      CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
# Prova Prática 3 – PP3
# Acadêmico: Alcides Pollazzon
#  ----------------------------------------------------------------------------------------------------------------------------------------------------------------
# [1] Construa o programa que calcule a média aritmética dos números pares e a média aritmética dos números ímpares. 
# O usuário fornecerá os valores de entrada que pode ser um número qualquer par ou ímpar. A condição de saída será o número 0 (zero).
# Na tela de saída, mostre também a quantidade total de números digitados e a soma total de números digitados.

# [Intro]
tabtotal = []
tabpar = []
tabimp = []

# [Core]
while True:
    n = int(input("Insira as entradas numericas\nInsira [0] para sair >#:   "))
    if n == 0:
        break
    
    tabtotal.append(n)

    if n % 2 == 0:
        tabpar.append(n)
        print(f"Ate o momento a tabela PAR e composta por >>> [{tabpar}]")
    else:
        tabimp.append(n)
        print(f"Ate o momento a tabela IMPAR e composta por >>> [{tabimp}]")

# [Output]
print(f"\nQuantidade total de números digitados: {len(tabtotal)}")
print(f"Soma total dos valores inseridos: {sum(tabtotal)}")

if len(tabpar) > 0:
    print(f"Media Aritmetica dos Numeros PARES: {sum(tabpar) / len(tabpar)}")
else:
    print("Nenhum número PAR foi digitado.")

if len(tabimp) > 0:
    print(f"Media Aritmetica dos Números IMPARES: {sum(tabimp) / len(tabimp)}")
else:
    print("Nenhum numero IMPAR foi digitado.")



    
