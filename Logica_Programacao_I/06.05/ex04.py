def modulo(n):
    if n > 0:
        return n 
    else:
        return n*-1

if __name__  == '__main__':
    n = float(input("Insira um numero # "))
    print(modulo(n))
