#                       CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
#   Prova Prática 4 – PPIV
#   Acadêmico: Alcides Pollazzon
#   ----------------------------------------------------------------------------------------------------
#   2. Implemente o programa que gere a sequência dos números naturais na ordem decrescente até o valor 
#   zero e o valor inicial será fornecido (digitado) pelo usuário. Mostre também a quantidade de valores
#   da sequência gerada. 
#   ----------------------------------------------------------------------------------------------------
# [VAR]
num_natural = int(input("Insira o valor de um numero natural ># "))
tabi=[]
# [CORE]
for i in range (num_natural,-1, -1): # Utilizar o passo "-1" para ordens decrescentes 
    if num_natural < 0:
        break
    tabi.append(i)
    print (i) # Ordem Decrescente
print(f"A quantidade de valores e = {len(tabi)}") # Quantidade de valores gerados na tabela
