# Sua tarefa é escrever e testar uma função que usa dois argumentos (um ano e um mês) e retorna o número de dias para o determinado par de ano-mês 
# (embora apenas fevereiro seja sensível ao valor do year, sua função deve ser universal).
# A parte inicial da função está pronta. Agora, convença a função a não retornar None se os argumentos não fizerem sentido.
# Obviamente, você pode (e deve) usar a função previamente testada e escrita (LAB 4.3.1.6). Pode ser muito útil. 
# Recomendamos que você use uma lista com os comprimentos dos meses. 
# Você pode criá-lo dentro da função - esse truque diminuirá significativamente o código.

def is_year_leap(year):
    if year % 4 != 0:
        return False
    elif year % 100 != 0:
        return True
    elif year % 400 != 0:
        return False
    else:
        return True


def days_in_month(year, month):
    if year < 1 or month < 1 or month > 12: # Teste Argumentos
        return None
    months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month == 2 and is_year_leap(year): # Fev em ano 366 
        return 29
    return months[month -1]
    
#---------------------------------------------------------------
test_years = [1900, 2000, 2016, 1987]
test_months = [2, 2, 1, 11]
test_results = [28, 29, 31, 30]
for i in range(len(test_years)):
    yr = test_years[i]
    mo = test_months[i]
    print(yr, mo, "->", end="")

    result = days_in_month(yr, mo)
    if result == test_results[i]:
        print("OK")
    else:
        print("Fracassado")