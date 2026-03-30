# #                      CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
# Prova Prática 3 – PP3
# Acadêmico: Alcides Pollazzon
#  ----------------------------------------------------------------------------------------------------------------------------------------------------------------
#[2] Desenvolva o programa que leia vários valores reais e no final mostre as seguintes informações:
#A quantidade de valores digitados;
#A soma dos valores digitados;
#A média aritmética dos valores digitados;
#O maior valor digitado;
#O menor valor digitado;
#E a quantidade de valores digitados maior ou igual a 50.

#[VAR]
tabn = []
n_maior_50 = 0

# [CORE]
while True:
    n = float(input("Insira um Valor Real\n pressione [0] para Sair... #>: "))
    tabn.append(n)
    if n == 0:
        tabn.remove(0)    
        break
    if n >= 50:
        n_maior_50 += 1
    print(tabn)

# [1]
print(f"[1] A quantidade de Valores Inseridos e igual a : [{len(tabn)}]")

# [2]
print(f"[2] A somas dos valores Inseridos e igual a : [{sum(tabn):.2f}]")

# [3]
print(f"[3] A Media Aritmetrica dos valores Inseridos [{sum(tabn) /len(tabn):.2f}]")

# [4]
print(f"[4] O MAIOR Numero Inserido e igual a: [{max(tabn):.2f}]")

# [5]
print(f"[5] O MENOR Numero Inserio e igual a [{min(tabn):.2f}]")

# [6]
print(f"[6] Quantidade de valores digitados maior ou igual a 50: [{n_maior_50}]")

