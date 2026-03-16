                    # CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
# Prova Prática 1 – PP1
# Resolva os problemas usando a linguagem de programação Python e os conceitos da disciplina Lógica de Programação.
# Acadêmico: Alcides Pollazzon
#  -----------------------------------------------------------------------------------------------------------------------------------------------------------------

# Problema 03: Construa o programa que tendo como dados de entrada dois pontos quaisquer do plano cartesiano, P(x1, y1) e Q(x2, y2), calcule a distância entre eles.

# [Intro]
x1 = float(input("Insira o valor Cardinal referente à x1 (Ponto P) ># "))
y1 = float(input("Insira o valor Cardinal referente à y1 (Ponto P) ># "))
x2 = float(input("Insira o valor Cardinal referente à x2 (Ponto Q) ># "))
y2 = float(input("Insira o valor Cardinal referente à y2 (Ponto Q) ># "))

# Fórmula em Py:
dist = ((x2 - x1)**2 + (y2 - y1)**2)**0.5

print(f"A Distância Entre os pontos PQ é igual à aproximadamente {round(dist , 2)} ({dist})")




