def maximo (n1,n2):
    if n1 > n2:
        return n1 
    else:
        return n2


def minimo (n1,n2):
    if n1 < n2:
        return n1
    else:
        return n2
    

if __name__ == '__main__':
    n1= int(input("Primeiro numero #$ "))
    n2= int(input("Segundo numero #$ "))
    resultado = maximo(n1,n2)
    print(resultado)
    print("\nMaior Valor = ", maximo(n1,n2))
    print("\nMenor Valor = ", minimo(n1,n2))
