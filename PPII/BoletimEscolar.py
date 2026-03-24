#                      CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
# Prova Prática 2 – PP2
# Acadêmico: Alcides Pollazzon
#  ----------------------------------------------------------------------------------------------------------------------------------------------------------------

# [3] Implemente o programa que leia a nota de vários alunos de uma turma e gere uma tela de saída com as seguintes informações: 
# a quantidade de alunos que fizeram a prova, 
# a quantidade de alunos aprovados, 
# a quantidade de alunos reprovados e a média da turma. Considere que o aluno será aprovado com nota for maior ou igual a cinco. 

# [INTRO]
print("===========================")
print("     BOLETIM ESCOLAR       ")
print("===========================")

print(">>> Pressione [-1] para Terminar... <<<")

# [Contadores]
total_alunos = 0
aprovados = 0 
reprovados = 0
soma_notas = 0

#[CORE]
while True:
    nome = str(input("Insira o Nome do Aluno >: "))
    nota = float(input(f"Insira a nota do Aluno [{nome}] >: "))
    
    if nota == -1: 
        break
# Att Cont.
    total_alunos += 1
    soma_notas += nota
# Aprovados & Reprovados
    if nota >= 5:
        aprovados += 1
        print(f"{nome}: APROVADO\n")
    else:
        reprovados += 1
        print (f"{nome}: REPROVADO\n")
# Resultado
print("===========================")
print("        RESULTADO          ")
print("===========================")

if total_alunos > 0:
    media = soma_notas / total_alunos
    print(f"Total de alunos:  {total_alunos}")
    print(f"Aprovados:        {aprovados}")
    print(f"Reprovados:       {reprovados}")
    print(f"Média da turma:   {media:.2f}")
else:
    print("Nenhum aluno foi registrado.")
