def calcula_dobro(p_valor):
    dobro = p_valor*2
    return dobro

if  __name__ == '__main__':
    valor = int(input("Valor Inteiro"))
    v_retornado = calcula_dobro(valor)
    print("Valor Retornado pela funçao:", v_retornado)


