#  A instrução continue é usada para ignorar o bloco atual e avançar para a próxima iteração, sem executar as instruções dentro do loop.
#Ele pode ser usado com loops while e for.
#Sua tarefa aqui é muito especial: você deve criar um comedor de vogal! Escreva um programa que use:
#um loop for
#o conceito de execução condicional (if-elif-else)
#a declaração continue.
#Seu programa deve:
#peça ao usuário para inserir uma palavra; X
#use user_word = user_word.upper() para converter em maiúsculas a palavra inserida pelo usuário; falaremos sobre métodos de string o método top upper() muito em breve - não se preocupe;
#use execução condicional e a declaração continue para "consumir" as seguintes vogais A, E, I, O, U da palavra inserida;
#imprima as letras não consumidas na tela, cada uma delas em uma linha separada.
#Teste seu programa com os dados que fornecemos para você.

user_word=str(input("Insira uma Palavra... > "))
user_word=user_word.upper()

for letter in user_word:
    if letter in 'AEIOU':
        continue
    print(letter)
    




