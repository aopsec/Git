# Ouça esta história: um garoto e seu pai, um programador de computador, estão jogando com blocos de madeira. Eles estão construindo uma pirâmide.
#A pirâmide deles é um pouco esquisita, pois na verdade é uma parede em forma de pirâmide - é plana. A pirâmide é empilhada de acordo com um princípio simples: 
# cada camada inferior contém um bloco a mais do que a camada acima.
#A figura ilustra a regra usada pelos construtores:
# Sua tarefa é escrever um programa que lê o número de blocos que os construtores têm e gera a altura da pirâmide que pode ser construída usando esses blocos.
#Nota: a altura é medida pelo número de camadas totalmente concluídas; se os construtores não tiverem um número suficiente de blocos e não puderem concluir a próxima camada, 
# eles terminarão seu trabalho imediatamente.
#Teste seu código usando os dados que fornecemos.
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Base == 3 Blocos == 6           Altura == 3 > + 3
# Base == 4 , Blocos == 4321=10 , Altura == 4 > + 4
# Base == 5 , BLocos == 54321=15, Altura == 5 > + 5
# A relacao entre altura e blocos e:
#   Blocos = (A * (A + 1)) / 2
# Camada == Altura , 

blocos=int(input("Insira o Total De Blocos... > "))
altura=0

while blocos >= altura + 1:
    altura += 1
    blocos -= altura
   
print("Sua Piramide Tera: ",altura,"Blocos de Altura" )


