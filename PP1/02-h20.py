                    # CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
# Prova Prática 1 – PP1
# Resolva os problemas usando a linguagem de programação Python e os conceitos da disciplina Lógica de Programação.
# Acadêmico: Alcides Pollazzon
#  -----------------------------------------------------------------------------------------------------------------------------------
# Problema 02:  A água é um nutriente essencial. Sem ela, o corpo não pode funcionar com perfeição. 
# Cada pessoa precisa de uma quantidade diferente de água para hidratar o corpo. A dose ideal, ou seja, 
# a necessidade diária em litros é calculada através da fórmula: massa (em kg) vezes 0,03. Elabore o programa que realize esse cálculo.

# [Intro]
print("Calculadora Para Hidratação")

# Calulo
h20 = float(input("Insira a massa em quilos (kg) >#  ")) * 0.03

# Resultado
print(f"A Quantidade Ideal de H20 a ser Consumida é igual a {round(h20 , 2)} Litro(s) / Dia")



