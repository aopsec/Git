                    # CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
# Prova Prática 1 – PP1
# Resolva os problemas usando a linguagem de programação Python e os conceitos da disciplina Lógica de Programação.
# Acadêmico: Alcides Pollazzon
#  -----------------------------------------------------------------------------------------------------------------------------------------------------------------
# Problema 04: Desenvolva o programa que classifique dois valores inteiros quaisquer em ordem crescente. Os valores serão fornecidos pelo usuário. 

# [Intro]

int01 = int(input("Insira o Valor De um Número Inteiro... ># "))
int02 = int(input("Insira o Valor de Outro Número Inteiro... ># "))


# Numeros Inteiros em Ordem Crescente com Condicionais If / ELif / Else
if int01 > int02:
    print(f"{int02}\n{int01}")
elif int01 == int02:
    print(f"{int01} = {int02}")
else:
    print(f"{int01}\n{int02}")

# sorted 
print(f"Utilizando o built in 'sorted'... {sorted([int01,int02])}")

