# ─── Validação de entrada ───────────────────────────────────────────────────
while True:
    try:
        blocos = int(input("Insira o Total De Blocos (número não-negativo)... > "))
        if blocos < 0:
            print("❌ Erro: O número de blocos deve ser não-negativo!")
            continue
        break
    except ValueError:
        print("❌ Erro: Digite um número inteiro válido!")

altura = 0
camadas = []  # guarda quantos blocos cada camada tem

# ─── Cálculo da altura ───────────────────────────────────────────────────────
print("\n── Construindo pirâmide ──")
while blocos >= altura + 1:
    altura += 1
    blocos -= altura
    camadas.append(altura)  # registra a camada construída
    print(f"  Camada {altura:>3} construída │ blocos restantes: {blocos}")

print(f"\nAltura da pirâmide: {altura}")
print(f"Blocos sobrando   : {blocos}\n")

# ─── Bloco ASCII ─────────────────────────────────────────────────────────────
# Cada bloco tem 3 linhas:
#   topo  →  +--+
#   meio  →  |  |
#   base  →  +--+
TOPO = "+--+"
MEIO = "|  |"
BASE = "+--+"

# ─── Desenho da pirâmide ─────────────────────────────────────────────────────
print("── Pirâmide ──\n")

largura_maxima = altura * len(TOPO)  # largura total da base

for num_blocos in camadas:
    largura_camada = num_blocos * len(TOPO)
    espaco = (largura_maxima - largura_camada) // 2  # centraliza

    linha_topo = " " * espaco + TOPO * num_blocos
    linha_meio = " " * espaco + MEIO * num_blocos
    linha_base = " " * espaco + BASE * num_blocos

    print(linha_topo)
    print(linha_meio)
    print(linha_base)
