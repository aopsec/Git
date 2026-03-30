# #                      CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
# Prova Prática 3 – PP3
# Acadêmico: Alcides Pollazzon
#  ----------------------------------------------------------------------------------------------------
# Escreva o programa que leia o salário dos funcionários de uma empresa e calcule quantos ganham menos 
# que cinco salários mínimos, quantos estão na faixa de cinco (inclusive) até dez (exclusive) e 
# quantos ganham dez ou mais salários mínimos. O valor do salário mínimo será fornecido pelo usuário. 
# Na tela de saída, além da quantidade de funcionários em cada faixa salarial, 
# informe também o valor total da folha de pagamento da empresa.



# [MENU]
print("============================")
print("        F O L H A           ")
print("     S A L A R I A L        ")
print("============================")
print("Cadastre Seu Funcionario Abaixo... ")


# [VAR]
tab_funcionario = []
tab_salario = []
tab_ate_5min = []
tab_5e10min = []
tab_10min = []
salario_min = float(input("Insira o Valor do Salario Minimo(S.M.) Atual >#:   "))

while True:
    print("Pressione [0] para Obter os Resultados")
    nome = (input("Nome:  "))
    salario = float(input("Salario R$:   "))
    tab_funcionario.append(nome)
    tab_salario.append(salario)

    if salario == 0:
        break
    if salario < 5*salario_min:
        tab_ate_5min.append(salario)
        print(f"O Funcionario {nome} , R${salario:.2f} => Recebe ate 5 salarios minimos(S.M.)\n         Total de Funcionarios que recebem Ate 5 S.M. {len(tab_ate_5min)}")
    elif salario >= 10*salario_min:
        tab_10min.append(salario)
        print(f"O Funcionario {nome} , R${salario:.2f} => Recebe Mais 10 salarios minimos(S.M.)\n           Total de Funcionarios que recebem Mais 10 S.M. {len(tab_10min)}")
    else:
        tab_5e10min.append(salario_min) 
        print(f"O Funcionario {nome} , R${salario:.2f} => Recebe entre 10 e 5 salarios minimos(S.M.)\n          Total de Funcionario que recebem Entre 10 e 5 S.M. {len(tab_5e10min)}")
    
# [OUTPUT]
print(f"Total de Funcionarios que recebem Ate 5 S.M. {len(tab_ate_5min)}")
print(f"Total de Funcionarios que recebem Mais 10 S.M. {len(tab_10min)}")
print(f"Total de Funcionario que recebem Entre 10 e 5 S.M. {len(tab_5e10min)}")
print(f"O valor Total da Folha Salarial e igual a: [R${sum(tab_salario):.2f}]")




