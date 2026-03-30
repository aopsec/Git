# #                      CEUB - FATECS | Lógica de Programação | Prof. Barbosa 
# Prova Prática 3 – PP3
# Acadêmico: Alcides Pollazzon
#  ----------------------------------------------------------------------------------------------------------------------------------------------------------------
#[3] Em uma eleição presidencial, existem três candidatos. Os votos são informados através de código. Os dados utilizados para escrutinagem obedecem à seguinte codificação: 
# 1, 2, 3 - voto dos respectivos candidatos;
# 5 - voto nulo;					6 - voto em branco;
# Elabore o programa que calcule o total de votos de cada candidato, total de votos nulos, total de votos em branco, percentual de votos nulos e percentual de votos em branco.

# [VAR]
totvotos = []
cand1 = 0
cand2 = 0
cand3 = 0
nul = 0
brnc = 0

# [Intro]
print("============================")
print("         U R N A            ")
print("    E L E T R O N I C A     ")
print("============================")
print("E L E I C O E S   2 0 2 6   ")
print("============================")

print(input("Insira o CPF: "))
print(input("Insira o N.Eleitor: "))

# [CORE]
while True:
    print("Para Selecionar o Candidato Desejado\n   Pressione:")
    print("[1] Luis Inacio Lula Da Silva (PT) \n[2] Flavio Bolsonaro (PL)\n[3] Leo Pericles (UP)\n[5] NULO\n[6] BRANCO\n[0] SAIR ")
    voto = int(input())
    totvotos.append(voto)
    total = len(totvotos)
    if voto == 0:
        break
    if voto == 1:
        cand1+=1
        print(f"Obrigado por votar!\n   Seu candidato Atualmente possui {cand1}")
        
    elif voto == 2:
        cand2+=1
        print(f"Obrigado por votar!\n   Seu candidato atualmente possui {cand2}")
        
    elif voto == 3:
        cand3+=1
        print(f"Obrigado por votar!\n   Seu candidato atualmente possui {cand3}")
        
    elif voto == 5:
        nul+=1
        print(f"Obrigado por votar!\n   Voce Votou NULO\n           Total de Votos NULO = [{nul}] , {float((nul / total)*100):.2f}% do total dos votos")
        
    elif voto == 6:
        brnc+=1
        print(f"Obrigado por votar!\n   Voce Votou NULO\n           Total de Votos BRANCO = [{brnc}] , {float((brnc / total)*100):.2f}% do total dos votos")
   
 
  # [OUTPUT]
total_final = len(totvotos)
print("============================")
print("     R E S U L T A D O S    ")
print("============================")
if total_final == 0:
    print("Nenhum voto registrado.")
else:
    print(f"Total de Votos Computados : {total_final}")
    print(f"Candidato 1 (Lula/PT)     : {cand1} voto(s) - {cand1 / total_final * 100:.2f}%")
    print(f"Candidato 2 (Bolsonaro/PL): {cand2} voto(s) - {cand2 / total_final * 100:.2f}%")
    print(f"Candidato 3 (Pericles/UP) : {cand3} voto(s) - {cand3 / total_final * 100:.2f}%")
    print(f"Votos Nulos               : {nul} voto(s) - {nul / total_final * 100:.2f}%")
    print(f"Votos em Branco           : {brnc} voto(s) - {brnc / total_final * 100:.2f}%")
 