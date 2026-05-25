#                       CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
#   Prova Prática 5 – PPV
#   Acadêmico: Alcides Pollazzon
#   ----------------------------------------------------------------------------------------------------
#   2.Crie uma função para somar três valores. Ela recebe os três valores, calcula a soma e retorna o 
#       resultado do cálculo. A função main lê os três valores inteiros, chama a função passando os 
#       valores lidos e depois mostra o valor retornado pela função, ou seja, o resultado obtido.
#   ----------------------------------------------------------------------------------------------------
# [CORE]
def soma (v1,v2,v3):
    return print(f"A soma dos 3 valores e igual a =  [{v1 + v2 + v3}]")

if __name__ == '__main__':
    v1 = int(input("Insira o V1 #$ "))
    v2 = int(input("Insira o V2 #$ "))
    v3 = int(input("Insira o V3 #$ "))

soma(v1,v2,v3)