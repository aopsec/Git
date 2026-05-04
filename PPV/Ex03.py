#                       CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
#   Prova Prática 5 – PPV
#   Acadêmico: Alcides Pollazzon
#   ----------------------------------------------------------------------------------------------------
#   3.Implemente uma função que calcula a idade de uma pessoa. Ela recebe o ano de nascimento da pessoa, 
#       faz o cálculo e retorna à idade. A função principal (main) lê o ano de nascimento digitado pelo 
#       usuário, chama a função e mostra o valor retornado pela função calcula.
#   ----------------------------------------------------------------------------------------------------
def calcula (data,ano_hoje):
    return print(f"O user tem {ano_hoje - data} Anos de Idade ")

if __name__ == '__main__':
    data = int(input("Insira Seu Ano de Nascimento #$ "))
    ano_hoje = int(input("Insira o ANO Atual"))

calcula (data,ano_hoje)

