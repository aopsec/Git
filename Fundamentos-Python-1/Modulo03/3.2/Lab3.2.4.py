# Um jovem mágico escolheu um número secreto. Ele o ocultou em uma variável chamada secret_number. 
# Ele quer que todos que executam seu programa joguem o jogo Adivinhe o número secreto e adivinhem qual número ele escolheu para eles. Quem não adivinhar o número ficará para sempre em um loop infinito! 
# Infelizmente, ele não sabe como completar o código.
# Sua tarefa é ajudar o mágico a preencher o código no editor de forma que o código:
# solicitará que o usuário insira um número inteiro; vai usar um while loop;
# verificará se o número inserido pelo usuário é igual ao número escolhido pelo mágico. 
# Se o número escolhido pelo usuário for diferente do número secreto do mago, 
# o usuário deverá ver a mensagem "Ha ha! Você está preso no meu loop!" 
# E será solicitado a inserir um número novamente. Se o número inserido pelo usuário corresponder ao número escolhido pelo mago, ele deverá ser impresso na tela, 
# e o mago deve dizer as seguintes palavras: "Muito bem, trouxa! Você está livre agora."
# O mágico está contando com você! Não o desaponte.
# INFORMAÇÕES EXTRA : 
# A propósito, observe a função print(). A maneira como usamos aqui é chamada de impressão de várias linhas. 
# Você pode usar aspas triplas para imprimir sequências de caracteres em várias linhas para facilitar a leitura ou criar um design especial baseado em texto. Experimente.
secret_number = 777
counter=0
print(
"""
+===================================+
| Bem vindo ao meu jogo, trouxa!    |
| Insira um número inteiro          |
| e adivinhar o número que tenho    |
| escolhidos para você.             |
| Então, qual é o número secreto?   |
+===================================+
""")

user_number=int(input("Tente Advinhar meu Numero Secreto OU Morra preso dentro do meu Loop..."))

while user_number != secret_number:
    while counter < 77:
        print('''Ha ha!''' "Você está preso no meu loop!")
        counter = counter + 1
    user_number=int(input("Tente novamente..."))
    
print("Muito bem, trouxa! Você está livre agora.")