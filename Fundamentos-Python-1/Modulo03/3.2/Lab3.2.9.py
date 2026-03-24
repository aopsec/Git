# A declaração break é usada para sair/encerrar um loop.
#Projete um programa que use um loop while e 
#solicite continuamente que o usuário insira uma palavra, a menos que o usuário insira "chupacabra" como a palavra de saída secreta, 
# caso em que a mensagem "Você saiu do loop com sucesso".
# Deve ser impresso na tela, e o loop deve terminar.
#Não imprima nenhuma das palavras inseridas pelo usuário. Use o conceito de execução condicional e a declaração break.

counter=0
secret_word = "chupacabra"

user_word = str(input("Advinhe a palavra secreta.. >>>"))
while True:
    user_word = str(input("Tente novamente..."))
    if user_word == secret_word:
        print("Você saiu do loop com sucesso")
        break
    counter+=1
 

