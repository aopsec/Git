def calc_minutos(hora,min):
    return 60*hora + min

if __name__ == '__main__':
    # print("Hora Atual em MINUTOS = ",calc_minutos(int(input("Insira a HORA Atual > ")),int(input("Insira os MIN Atual > "))))
    # print("Hora Atual em MINUTOS = ",calc_minutos(hora=int(input("Insira a HORA Atual > ")),min=int(input("Insira os MIN Atual > "))))
    h1 = print(int(input("Insira a HORA Atual # ")))
    m1 = print(int(input("Insira o MIN Atual # ")))
    calc_minutos(hora=h1,min=m1)
    h2 = print(int(input("Insira a HORA Atual # ")))
    m2 = print(int(input("Insira o MIN Atual # ")))
    calc_minutos(hora=h2,min=m2)

