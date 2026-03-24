# Spathiphyllum, mais conhecido como um lírio da paz ou planta de vela branca, é um dos mais populares plantas de interior que filtra as toxinas nocivas do ar. Alguns dos efeitos tóxicos que ele neutraliza incluem o benzeno, o formaldeído e a amônia.
# Imagine que seu programa de computador adora essas fábricas. Sempre que recebe uma entrada na forma da palavra Spathiphyllum, involuntariamente grita para o console a seguinte string: "Spathiphyllum é a melhor fábrica de todos os tempos!"
# Escreva um programa que utilize o conceito de execução condicional, use uma string como entrada e:
# imprime a frase "Sim - Spathiphyllum é a melhor
# fábrica de todos os tempos!" para a tela se a sequência inserida for "Spathiphyllum" (maiúscula)
# imprime "Não, eu quero um grande Spathiphyllum!" se a sequência inserida for "spathiphyllum" (letra minúscula)
# imprime "Spathiphyllum! Not[input]!", Caso contrário. Nota: [input] é a string usada como entrada.

plant = input("Digite o nome da planta: ")
if plant == "Spathiphyllum":
    print("Sim - Spathiphyllum é a melhor")
elif plant == "spathiphyllum":
    print("Não, eu quero um grande Spathiphyllum!")
else:
    print ("Spathiphyllum! Not ", plant)
