# [VAR]
list=[]
soma = 0


# [CORE]
while True:
    x=input("Insira um Valor: ")
    
    if x == "stop":
        break
    x = int(x)
    list.append(x)

print(list)

for x in list:
    print(x)

print(len(list))
print(sum(list))


# sum sem somador 
for x in list:
    soma += x
print(soma)

print(max(list))
print(min(list))


y = int(input("Confira se o valor esta na lista: "))

if y in list:
    print("O Valor esta na Lista")

else: 
    print("O Valor NAO esta na Lista")

