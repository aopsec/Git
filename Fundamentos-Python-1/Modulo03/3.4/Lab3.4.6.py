# Cenário
#Era uma vez um chapéu. O chapéu não continha coelhos, mas uma lista de cinco números: 1, 2, 3, 4 e 5.
#Sua tarefa:
#escreva uma linha de código que solicite que o usuário substitua o número do meio na lista por um número inteiro 
# inserido pelo usuário (Etapa 1)
#escreva uma linha de código que remova o último elemento da lista (Etapa 2)
#escreva uma linha de código que imprima o comprimento da lista atual (Etapa 3).
# --------------------------------------------------------------------------------------------------------------------

# Etapa 01  - User Input + Subs
hat = [1,2,3,4,5]
hat [2] = int(input("Insira um valor inteiro... #>"))
print(hat)

# Etapa 02 - Del last 
del hat[4] 
print (hat)

# Etapa 03 - print()
print (len(hat))
