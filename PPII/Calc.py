#                      CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
# Prova Prática 2 – PP2
# Acadêmico: Alcides Pollazzon
#  ----------------------------------------------------------------------------------------------------------------------------------------------------------------
# (1) Elabore o programa que simule uma calculadora com as quatro operações aritméticas básicas. O usuário fornecerá dois números e a operação aritmética desejada.
#  Mostre o menu com estes símbolos (+ , - , * , / ) para o usuário escolher a operação aritmética. 
# Utilize o comando “se . . . senão . . . ” encadeado, ou seja, “if . . . else . . . ” encadeado. 

# [INTRO]
print("===========================")
print("    CALCULADORA PYTHON     ")
print("===========================")

# [Menu]
print("Operações Aritmétricas \n    Pressione o Numero Equivalente a Operacao Desejada ")
print("[1] = |+| (Adicao)")
print("[2] = |-| (Subtracao)")
print("[3] = |*| (Multiplicacao)")
print("[4] = |/| (Divisao)")
print("[0] = Exit")


# [Var]
num01 = float(input("Digite o Numero 01 >: "))
num02 = float(input("Digite o Numero 02 >: " ))



# [CORE]    
opr = int(input(""))

if opr == 1:
    result = num01 + num02
    print(f"{num01} + {num02} = {result}")
elif opr == 2:
    result = num01 - num02 
    print(f"{num01} - {num02} = {result}")
elif opr == 3:
    result = num01 * num02
    print(f"{num01} * {num02} = {result}")
elif opr == 4: 
    if num02 == 0:
        print("Divisao por Zero [0] nao e Permitido!")
    else:
        result = num01 / num02 
        print(f"{num01} / {num02} = {result}")
elif opr == 0:  
    print ("Encerrando... \n Volte Sempre!")
else:
    print("\n  Opção inválida. Execute o programa novamente.")
