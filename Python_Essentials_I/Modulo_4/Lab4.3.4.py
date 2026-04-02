# Sua tarefa é escrever e testar uma função que usa um argumento (um ano) e retorna True se o ano for um ano bissexto ou False caso contrário.
# A semente da função já é mostrada no código esqueleto do editor.
# Nota: também preparamos um código de teste curto, que você pode usar para testar sua função.
# O código usa duas listas - uma com os dados de teste e a outra contendo os resultados esperados. O código informará se algum dos resultados é inválido.




def is_year_leap(year):
    if year % 4 != 0:
        return False
    elif year % 100 != 0:
        return True
    elif year % 400 != 0:
        return False
    else:
        return True

test_data = [1900, 2000, 2016, 1987]
test_results = [False, True, True, False]
for i in range(len(test_data)):
    yr = test_data[i]
    print(yr,"-> ",end="")
    result = is_year_leap(yr)
    if result == test_results[i]:
        print("OK")
    else:
        print("Fracassado")
