# HermesAgent

---

*Um agente de IA que roda 100% no seu computador, na sua placa de vídeo, sem mandar nada para a internet.*

---

## O que é o HermesAgent?

O **HermesAgent** pega o agente de inteligência artificial **Hermes**, da Nous Research,
e o coloca para rodar **dentro do seu próprio computador** — usando a placa de vídeo
**RTX 4070 Ti** — de um jeito **seguro e isolado**.

Em palavras simples, ele faz três coisas:

1. **Pensa localmente.** O "cérebro" da IA (o modelo `hermes3:8b`) roda na sua placa de
   vídeo. Suas perguntas e seus arquivos **não saem do seu computador**.
2. **Fica preso numa caixa (Docker).** O agente roda dentro de containers isolados. Se
   algo der errado, o estrago fica contido — ele não tem acesso livre ao seu sistema.
3. **Só fala com a internet pela porta da frente.** Toda tentativa de acessar a internet
   passa por um "porteiro" (o proxy Squid) que **bloqueia tudo por padrão** e só deixa
   passar os endereços que você liberar de propósito.

Ele se conecta ao **meta-vault ObsidianAgent**: trabalha sobre as suas notas, mas a pasta
de notas geradas automaticamente (`Vault/Generated/`) fica **somente-leitura**, para não
bagunçar nada.

---

## Por que "arquitetura mais segura"?

O próprio manual do Hermes diz uma coisa importante:

> *"A única barreira de segurança contra uma IA adversária é o sistema operacional."*

Ou seja: filtros e avisos dentro do programa **não bastam**. A proteção de verdade vem de
**isolar o processo inteiro** (é o que o Docker faz aqui) e de **cortar a saída para a
internet** (é o que a divisão de redes + o porteiro Squid fazem). É exatamente essa a
postura que este projeto adota. Os detalhes técnicos estão em
[`docs/HARDENING.md`](docs/HARDENING.md).

---

## Requisitos

- **Linux Arch** com a placa **NVIDIA RTX 4070 Ti** (driver NVIDIA já instalado e funcionando).
- **Docker** e **Docker Compose** instalados.
- Permissão de administrador (**sudo**) — para instalar o componente que liga a placa de
  vídeo ao Docker.
- Espaço em disco: cerca de **5 GB** para o modelo de IA + alguns GB para a imagem do Docker.

> ⚠️ **Importante:** este projeto só roda na máquina física com a placa de vídeo. Ele **não**
> roda em nuvem nem em CI — lá não há GPU. Na nuvem só dá para conferir os arquivos (revisão).

---

## Como usar (passo a passo)

### Passo 1 — Preparar o arquivo de configuração

Dentro da pasta do projeto:

```bash
cp .env.example .env
```

Abra o `.env` e ajuste `HERMES_UID` e `HERMES_GID` para os seus (rode `id -u` e `id -g`
para descobrir).

### Passo 2 — Instalar tudo de uma vez

```bash
make setup
```

Esse comando, em ordem, faz:

1. Instala o `nvidia-container-toolkit` (liga a placa de vídeo ao Docker).
2. Gera a configuração da GPU para o Docker (CDI).
3. Testa se a placa aparece dentro de um container.
4. Baixa e monta a imagem do Hermes.
5. Baixa o modelo de IA `hermes3:8b` (uma vez só).
6. Sobe todos os serviços.

> Ele vai pedir a senha de administrador (sudo) em algumas etapas — é normal.

### Passo 3 — Conversar com o agente

```bash
docker exec hermes hermes chat -q "ping"
```

Se tudo estiver certo, ele responde usando o modelo local. Para confirmar que a placa de
vídeo está trabalhando, rode `nvidia-smi` em outro terminal e veja o processo `ollama`
usando memória da GPU.

### Painel web (opcional)

O painel fica disponível **apenas no seu próprio computador**, em
`http://127.0.0.1:9119` (ninguém da rede consegue acessar).

---

## Comandos úteis

| Comando | O que faz |
|---|---|
| `make setup` | Instalação completa (placa de vídeo + build + modelo + subir) |
| `make gpu-check` | Confere se a placa de vídeo aparece dentro do Docker |
| `make up` / `make down` | Liga / desliga os serviços |
| `make logs` | Mostra o que o agente está fazendo |
| `make verify` | Confere os arquivos (sintaxe do compose e dos scripts) |

---

## Segurança em uma frase

A IA pensa na sua placa de vídeo, fica trancada num container, e só acessa a internet por
um porteiro que **bloqueia tudo por padrão**. Quer entender o porquê de cada trava? Leia
[`docs/HARDENING.md`](docs/HARDENING.md).
