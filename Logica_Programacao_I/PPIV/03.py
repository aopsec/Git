#                       CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
#   Prova Prática 4 – PPIV
#   Acadêmico: Alcides Pollazzon
#   ----------------------------------------------------------------------------------------------------
#   3. Elabore o programa para somar todos os números inteiros que se encontram no intervalo de um a 
#   quinhentos.
#   ----------------------------------------------------------------------------------------------------

# [VAR]
n1=1
n2=500

# [INTRO]
print("Somatorio Dos Numeros Inteiros ate 500:")

# [CORE]
def soma(n1,n2):
    som4=0
    for i in range(n1,n2+1):
        som4+=i
    print(som4)

soma(n1,n2)


