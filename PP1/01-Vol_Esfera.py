                    # CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
# Prova Prática 1 – PP1
# Resolva os problemas usando a linguagem de programação Python e os conceitos da disciplina Lógica de Programação.
# Acadêmico: Alcides Pollazzon
#  -----------------------------------------------------------------------------------------------------------------------
import math
# Problema 01: Implemente o programa que calcule o volume de uma esfera de raio r. O usuário fornecerá o dado necessário. 
# [ Intro ]
print("Calculadora Volumétrica de Esferas")

# User Input "r"
r = float(input("Insira o Valor de Raio (r) >#  "))

# Fórmula Volume Esfera "py"
    # Lib math
pi = math.pi
vol_esfera1 = (4 * pi * r**3) / 3

    # Pi ==  3.14159
vol_esfera2 = (4 *  3.14159 * r**3) / 3

print(f"O Volume da Esfera de Raio {r} é igual a {vol_esfera1} unidades cúbicas (Pi = {pi} ).\nO Volume da Esfera de Raio {r} é igual a {vol_esfera2} unidades cúbicas (Pi = 3.14159)")




