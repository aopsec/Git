def positivo_nulo_negativo(n):
    if n > 0:
        print("Valor Positivo")
    elif n == 0:
        print("Valor NULO")
    else:
        print("Valor Negativo")

if __name__ == '__main__':
    positivo_nulo_negativo(7)
    positivo_nulo_negativo(0)
    positivo_nulo_negativo(-7)