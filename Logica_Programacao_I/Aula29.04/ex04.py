def soma (v1,v2):
    return v1 + v2

def subtraçao (v1,v2):
    return v1 - v2

if  __name__ == '__main__':
    var1=int(input("Insira VAR 01 ># "))
    var2=int(input("Insira VAR 02 ># "))

    user = int(input("Escolha 1 = Adiçao & 2 = Subtraçao"))
    if user == 1:
         print(soma(var1,var2))
    elif user == 2:
        print(subtraçao(var1,var2))
    else:
        print("Opçao Invalida")
        




