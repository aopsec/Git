#                       CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
#   Prova Prática 4 – PPIV
#   Acadêmico: Alcides Pollazzon
#   ----------------------------------------------------------------------------------------------------
#   Refaça o programa anterior mostrando todas as pedras de um dominó sem repetição.
#   Observe que a pedra "0 - 1" e a pedra "1 - 0" é a mesma.
#   ----------------------------------------------------------------------------------------------------

#[INTRO]
print(">>> Contagem das Pedras de Domino <<<\n[Sem Repeticoes]")

#[CORE]
for p1 in range(0,7):
    for p2 in range(p1,7):
        print(f"{p1}|{p2}")
    

