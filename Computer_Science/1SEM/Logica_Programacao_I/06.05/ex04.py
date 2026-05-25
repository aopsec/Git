def modulo(n):
    if n > 0:
        return n 
    else:
        return -n # n*-1

if __name__  == '__main__':
    n = float(input("Insira um numero # "))
    print(f"O modulo de {n} e = ", modulo(n))
