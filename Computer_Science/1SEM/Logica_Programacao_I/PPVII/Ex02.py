#                       CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
#   Prova Prática 7 – PPVII
#   Autor: Alcides Pollazzon
#   ----------------------------------------------------------------------------------------------------
# 2- Resolva este problema usando lista e as funções de lista. 
# Não use contador e nem somador.

# - Desenvolva o programa que calcule a média aritmética de uma turma,
# onde cada aluno realizou uma avaliação. Não sabemos a quantidade de
# alunos, por isso usaremos o valor “-1” como condição (flag) de saída.
#   Na tela de saída, mostre a média aritmética da turma e a quantidade
# de alunos da turma.
# - Analise o problema e verifique quais são os dados que o usuário precisa
# fornecer (digitar) como entrada.
#   ----------------------------------------------------------------------------------------------------

#[CORE]
def media_turma():
    notas_turma=[]
    while True:
        notas=float(input("Insira a Nota ># "))
        if notas == -1:
            break
        else:
            notas_turma.append(notas)
    media_aritmetrica = sum(notas_turma) / len(notas_turma)
    return media_aritmetrica

resultado = media_turma()
print(f"A media da Turma e igual a : {resultado}")


