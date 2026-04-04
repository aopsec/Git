#  PROJETO  Jogo da Velha
# Cenário
# Sua tarefa é escrever um programa simples que finge jogar tic-tac-toe com o usuário. 
# Para tornar tudo mais fácil para você, decidimos simplificar o jogo. Aqui estão nossas suposições:

# o computador (ou seja, seu programa) deve jogar usando 'X's;
# o usuário (por exemplo, você) deve jogar usando 'O's;
# o primeiro movimento pertence ao computador - ele sempre coloca seu primeiro 'X' no meio do quadro;
# todos os quadrados são numerados linha por linha, começando com 1 (consulte a sessão de exemplo abaixo para referência)
# o usuário insere seu movimento inserindo o número do quadrado escolhido - o número deve ser válido, ou seja, deve ser um número inteiro, 
# deve ser maior que 0 e menor que 10, e não pode apontar para um campo que já está ocupada;
# o programa verifica se o jogo acabou - há quatro veredictos possíveis: o jogo deve continuar, o jogo termina com um empate, você ganha ou o computador ganha;
# o computador responde seu movimento e a verificação é repetida;
# não implementem qualquer forma de inteligência artificial - uma escolha de campo aleatória feita pelo computador é boa o suficiente para o jogo.
# Requisitos
# Implemente os seguintes recursos:

# o painel deve ser armazenado como uma lista de três elementos, enquanto cada elemento é outra lista de três elementos (as listas internas representam linhas) 
# para que todos os quadrados possam ser acessados usando a seguinte sintaxe:

# board[row][column]
 

# cada um dos elementos da lista interna pode conter "O", "X" ou um dígito que representa o número do quadrado (tal quadrado é considerado livre)
# a aparência do quadro deve ser exatamente igual à apresentada no exemplo.
# implementar as funções definidas para você no editor.

# O desenho de um número inteiro aleatório pode ser feito utilizando uma função Python chamada randrange(). O programa de exemplo abaixo mostra como usá-lo (o programa imprime dez números aleatórios de 0 a 8).

# Observação: a instrução from-import fornece acesso à função randrange definida em um módulo externo do Python chamado de random.

# from random import randrange
 
# for i in range(10):
#  print(randrange(8))
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------

def display_board(board):
 # A função aceita um parâmetro contendo o status atual da placa
 # e o imprime no console.


def enter_move(board):
 # A função aceita o status atual do tabuleiro, pergunta ao usuário sobre sua jogada, 
 # verifica a entrada e atualiza o quadro de acordo com a decisão do usuário.


def make_list_of_free_fields(board):
 # A função navega pelo tabuleiro e constrói uma lista de todas as casas livres; 
 # a lista consiste em tuplas, enquanto cada tupla é um par de números de linha e coluna.


def victory_for(board, sign):
 # A função analisa o estado da placa a fim de verificar se 
 # o jogador usando 'O's ou 'X's ganhou o jogo


def draw_move(board):
 # A função desenha o movimento do computador e atualiza o tabuleiro.
