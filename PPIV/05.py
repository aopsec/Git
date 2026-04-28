#                       CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
#   Prova Prática 4 – PPIV
#   Acadêmico: Alcides Pollazzon
#   ----------------------------------------------------------------------------------------------------
#   Elabore o programa que mostre todas as pedras de um dominó. Não se preocupe com as pedras repetidas.
#   ----------------------------------------------------------------------------------------------------

#[INTRO]
print(">>> Todas as Pedras de Domino <<<")

#[CORE]
for p1 in range(0,7):
    for p2 in range(0,7):
        print(f"{p1}|{p2}")


