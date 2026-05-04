#                       CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
#   Prova Prática 5 – PPV
#   Acadêmico: Alcides Pollazzon
#   ----------------------------------------------------------------------------------------------------
#   1. Desenvolva uma função que recebe uma mensagem e um número, ela mostra a mensagem e o número e 
#       não retorna nada. A função main chama a função passando os dois argumentos lidos, ou seja, 
#       digitados pelo usuário. 
#   ----------------------------------------------------------------------------------------------------

# [CORE]
def funcao_01 (msg,num):
    print(msg ,num )
    return

# [MAIN]
if __name__ == '__main__':
    msg = input("Insira     uma     Mensagem    AQUI ># ")
    num = input("Insira     um      Numero      AQUI ># ")

funcao_01(msg,num)