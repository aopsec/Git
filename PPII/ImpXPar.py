#                      CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
# Prova Prática 2 – PP2
# Acadêmico: Alcides Pollazzon
#  ----------------------------------------------------------------------------------------------------------------------------------------------------------------
# Construa o programa que calcule a média aritmética dos números pares e a média aritmética dos números ímpares. O usuário fornecerá os valores de entrada que pode 
# ser um número qualquer par ou ímpar. A condição de saída será o número 0 (zero).
# Na tela de saída, mostre também a quantidade total de números digitados e a soma total de números digitados.

#[INTRO]
print(">>>>>   I M P A R   x   P A R   <<<<<")

# [Cont]
tab_par = []
tab_imp = []
tab_num = []

# [CORE]
while True:
    print("Pressione zero [0] para terminar")  
    num = int(input("Insira um numero: "))
    if num == 0:
        break
    tab_num.append(num)  

    if num % 2 == 0:
        tab_par.append(num)  
    else:
        tab_imp.append(num)  

# [Outputs]
print(f"\nQuantidade total de números digitados: {len(tab_num)}")
print(f"Soma total dos valores inseridos: {sum(tab_num)}")

if len(tab_par) > 0:
    print(f"Media Aritmetica dos Numeros PARES: {sum(tab_par) / len(tab_par):.2f}")
else:
    print("Nenhum número PAR foi digitado.")

if len(tab_imp) > 0:
    print(f"Media Aritmetica dos Números IMPARES: {sum(tab_imp) / len(tab_imp):.2f}")
else:
    print("Nenhum numero IMPAR foi digitado.")



 
