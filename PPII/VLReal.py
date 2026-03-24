#                      CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
# Prova Prática 2 – PP2
# Acadêmico: Alcides Pollazzon
#  ----------------------------------------------------------------------------------------------------------------------------------------------------------------
# [2] Desenvolva o programa que leia vários valores reais e no final mostre as seguintes informações:
#   A quantidade de valores digitados;
#   A soma dos valores digitados;
#   A média aritmética dos valores digitados;
#   E a quantidade de valores digitados maior que 20.

# [Tab]
tab1 = []

# [INTRO]
print("Insira Quantos Valores Reais Desejar...")

# [CORE]
num_maior_20 = 0

while True:
    num = float(input("Insira os valores >:\n Pressione [0] para Terminar"))
    if num == 0:
        break
    tab1.append(num)
    print(tab1)
    # [Qtd. de valores digitados > 20]
    if num > 20:
        num_maior_20 += 1


# [Infos]

print(f"A qunatidade de valores digitados e igual a: {len(tab1)}")
print(f"A soma de todos os valores e igual a: {sum(tab1)}")
print(f"A media Aritmetica dos valores digitados e igual a: {(sum(tab1)) / (len(tab1))}")
print(f"Quantidade de valores maiores que 20: {num_maior_20}")

