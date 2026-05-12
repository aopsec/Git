#                       CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
#   Prova Prática 6 – PPVI
#   Acadêmico: Alcides Pollazzon
#   ----------------------------------------------------------------------------------------------------

#   1. Simule uma calculadora com as quatro operações aritméticas. Implemente uma função para cada operação 
#       aritmética. Ela recebe dois valores e não retorna nada. A função executa o cálculo e mostra o 
#       resultado do cálculo. O usuário fornecerá a operação desejada (operador: +, -, x, / ) e os dois 
#       valores dentro do programa (função main) que chamará uma das quatro funções. 
#       O resultado do cálculo será mostrado dentro de cada função. Use variável local.
#   ----------------------------------------------------------------------------------------------------

# [INTRO]
print("     Python   Calculator  ")

# [MENU]
op1 = "+"
op2 = "-"
op3 = "x"
op4 = "/"



# [CORE]

def soma (x,y):
    r = x + y
    print(r)

def sub(x,y):
    r = x - y
    print(r)

def multi(x,y):
    r = x * y
    print(r)

def div (x,y):
    r = x / y
    print(r)


if __name__ == '__main__':
    x = float(input("Insira 1 valor $# "))
    y = float(input("Insira 2 valor $# "))
    operacao = str(input(f" >>>>>   Escolha A Operacao Desejada     <<<<<\n1.[{op1}]\n2.[{op2}]\n3.[{op3}]\n4.[{op4}]\n Insira aqui... $# "))
    if operacao == op1:
        soma(x,y)
    if operacao == op2:
        sub(x,y)
    if operacao == op3:
        multi(x,y)
    if operacao == op4:
        div(x,y)

