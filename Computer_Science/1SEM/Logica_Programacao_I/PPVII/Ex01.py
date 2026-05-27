#                       CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
#   Prova Prática 7 – PPVII
#   Autor: Alcides Pollazzon
# #   ----------------------------------------------------------------------------------------------------
# 1- Resolva este problema usando lista e as funções de lista. 
# Não use contador e nem somador.
# - Desenvolva o programa que leia vários números digitados pelo usuário
# e use o valor -1 como condição (flag) de saída da estrutura de repetição.
# Na tela de saída, mostre a quantidade de números digitados.
# - Analise o problema e verifique quais são os dados que o usuário precisa
# fornecer (digitar) como entrada.
#   ----------------------------------------------------------------------------------------------------

#[INTRO]
print("Exercicio 01 Prova Pratica 7")

#[CORE]
def ler_numeros():
    numeros = []
    while True:
        n = int(input("Insira um Numero Inteiro"))
        if n == -1:
            break
        else:
            numeros.append(n)
    print(len(numeros))
    return 
ler_numeros()



