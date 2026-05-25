# #                      CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
#   Prova Prática 4 – PP4
#   Acadêmico: Alcides Pollazzon
#   ----------------------------------------------------------------------------------------------------
# 1. Implemente o programa que gere a sequência dos números naturais na ordem crescente até um valor 
#    final fornecido (digitado) pelo usuário. Mostre também a quantidade de valores da sequência gerada. 
#   ----------------------------------------------------------------------------------------------------

# [VAR]
num_natural = int(input("Insira o valor de um numero natural ># "))
tabi=[]
# [CORE]
for i in range (0,num_natural+1):
    if num_natural < 0:
        break
    tabi.append(i)
    print (i) # Ordem Crescente 
print(f"A quantidade de valores e = {len(tabi)}") # Quantidade de valores gerados na tabela
