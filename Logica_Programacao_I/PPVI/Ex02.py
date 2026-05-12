#                       CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
#   Prova Prática 6 – PPVI
#   Acadêmico: Alcides Pollazzon
#   ----------------------------------------------------------------------------------------------------
#     2. Elabore a função fatorial que recebe o valor inteiro e retorna seu fatorial. O valor será lido 
#        no programa (função main) que chama a função fatorial passando o valor lido. O programa 
#        (função main) recebe o valor retornado pela função fatorial e gera a tela de saída. 
# 
#       Lembre-se que fatorial de n ( n! ) é a multiplicação dos números naturais de 1 até n.
#           0! = 1		1! = 1			n! = 1 x 2 x 3 x . . . x (n - 1) x n.
#   ----------------------------------------------------------------------------------------------------

#[CORE]
def fatorial(x):
    r = 1
    for i in range(x,0,-1):              
        r *= i
    return r

if __name__ == '__main__':
    x = int(input("Insira um Numero Para Calcular o seu Fatorial\n ># "))
    r = fatorial(x)
    print(r)