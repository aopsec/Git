#                       CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
#   Prova Prática 4 – PPIV
#   Acadêmico: Alcides Pollazzon
#   ----------------------------------------------------------------------------------------------------
#   4. Elabore o programa para somar todos os números inteiros que são ao mesmo tempo ímpar e múltiplo 
#   de três que se encontram no intervalo de um a quinhentos.
#   ----------------------------------------------------------------------------------------------------

#[VAR\\COUNT]
n1=1
n2=500
soma=0
#[CORE]
for i in range(n1,n2+1,2):
    if i % 2 != 0 and i % 3 == 0:
    
        soma+=i

print(soma)