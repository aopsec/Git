# Atividade 03 — Redes de Computadores

**Disciplina:** Introdução à Computação · **Aluno:** AOPS

## Texto dissertativo

A rede de CFTV descrita exige baixa latência, alta largura de banda e roteamento dinâmico entre muitos nós, o que orienta cada escolha técnica a seguir.

**01. RTSP frente ao HLS.** O RTSP é um protocolo de controle de sessão concebido para transmissão ao vivo, mantendo um canal persistente de comandos (PLAY, PAUSE, TEARDOWN) e transportando a mídia, em geral, sobre RTP/UDP. Já o HLS fragmenta o vídeo em segmentos servidos por HTTP/TCP, modelo voltado à distribuição escalável sob demanda. Para um CFTV em tempo real, o RTSP oferece duas vantagens decisivas: (i) **latência muito menor** — da ordem de centenas de milissegundos, contra vários segundos do HLS, que precisa acumular e bufferizar segmentos antes da reprodução; e (ii) **transporte não orientado à conexão (RTP/UDP)**, que dispensa o estabelecimento e a retransmissão garantida do TCP, reduzindo atraso e sobrecarga e preservando a fluidez das imagens contínuas, além de permitir controle nativo da câmera (p. ex., PTZ) pela própria sessão.

**02. Meio físico e faixa de frequência.** As câmeras devem usar transmissão sem fio por radiofrequência (Wi-Fi), com a faixa de **5 GHz** como a mais indicada (e 6 GHz, via Wi-Fi 6E, onde houver equipamento compatível). A faixa de 2,4 GHz é congestionada, oferece apenas três canais não sobrepostos e menor banda, sofrendo forte interferência num prédio comercial. A faixa de 5 GHz disponibiliza muito mais canais não sobrepostos, maior largura de banda e menos interferência, suportando o tráfego de centenas de câmeras 4K sem gargalos.

**03. Pilha de protocolos.** Para as camadas física e de enlace, o padrão mais adequado da família IEEE 802.11 é o **802.11ax (Wi-Fi 6/6E)**, cujos recursos OFDMA e MU-MIMO atendem com eficiência a alta densidade de nós e a elevada vazão exigidas (o 802.11ac seria o mínimo aceitável). Na camada de rede, usa-se o protocolo **IP** com roteamento dinâmico por **OSPF**, protocolo de estado de enlace que converge bem em topologias com grande quantidade de nós e rotas dinâmicas. Na camada de transporte, o protocolo adequado é o **UDP**, por não ser orientado à conexão: sem handshake nem retransmissão, garante a baixa latência que o streaming RTSP/RTP em tempo real demanda.

---

# Atividade 04 — Segurança Cibernética

**Cenário escolhido:** Dispositivos Domésticos/IoT Modificados — central de emulação/mídia local (TV-box Rockchip modificada) exposta à internet, correlacionada ao projeto **ADV7Box / OpenBox v0.1**.

## 1. Apresentação da infraestrutura

O ativo central é uma *set-top box* baseada em SoC Rockchip (linha RK32xx), originalmente vendida como aparelho de TV/emulação, reaproveitada como central de mídia local na rede doméstica. O aparelho roda Android/AOSP modificado, expõe serviços de streaming e compartilhamento de arquivos e, na configuração de fábrica, comunica-se livremente com a internet. Esse perfil de dispositivo é alvo conhecido de campanhas de comprometimento em larga escala (BadBox 2.0 e botnet Vo1d), que já distribuem firmware infectado na cadeia de suprimentos.

## 2. Mapeamento de ativos

- **Controle físico/lógico do dispositivo:** acesso *root*, firmware no eMMC e bootloader.
- **Dados do usuário:** credenciais de contas, biblioteca de mídia, metadados de uso e tráfego de navegação.
- **Posição na rede:** o box compartilha a LAN doméstica e pode servir de pivô para os demais dispositivos (notebooks, celulares, câmeras, automação).
- **Integridade do serviço:** disponibilidade da central de mídia e confiança do firmware em execução.

## 3. Matriz de Risco

Score = Probabilidade × Impacto. Classificação: 1–6 Baixo · 8–12 Médio · 15–25 Crítico/Alto.

| # | Categoria | Vulnerabilidade | Prob. | Impacto | Score | Classificação |
|---|-----------|-----------------|:-----:|:-------:|:-----:|---------------|
| H1 | Hardware | Interface serial/UART e modo *maskrom* acessíveis; bootloader desbloqueado permitem *reflash* do eMMC soldado | 1 | 4 | 4 | Baixo |
| H2 | Hardware | Firmware de fábrica pré-infectado na cadeia de suprimentos (BadBox 2.0 / Vo1d) — *backdoor* embarcado | 5 | 5 | 25 | **Crítico** |
| S1 | Software | ADB exposto na porta 5555 e credenciais de fábrica (admin/admin) acessíveis pela internet | 5 | 5 | 25 | **Crítico** |
| S2 | Software | AOSP desatualizado e apps de mídia/emulação de fontes não confiáveis (sem assinatura/patches) | 3 | 4 | 12 | Médio |
| R1 | Redes | Ausência de segmentação: box na mesma VLAN da casa e exposto via UPnP/port forwarding | 4 | 5 | 20 | **Crítico** |
| R2 | Redes | Tráfego e DNS em claro (sem TLS/DoH) — sujeito a interceptação e sequestro de DNS (MITM) | 4 | 3 | 12 | Médio |

**Justificativas resumidas:** H2 e S1 recebem nota máxima porque combinam alta frequência real (firmware infectado de fábrica; portas/credenciais padrão abertas) com impacto desastroso (controle remoto *root*). R1 é crítico porque a falta de segmentação transforma um único dispositivo comprometido em ponto de pivô para toda a residência. H1 fica baixo por exigir acesso físico e ferramentas específicas (raro). S2 e R2 são médios: prováveis, mas com impacto contornável por atualização e cifragem.

## 4. Plano de Mitigação Técnico (riscos Alto/Crítico)

**H2 — Firmware pré-infectado.** Substituir o firmware de fábrica por imagem limpa e auditável (Armbian/AOSP verificado, hardening do OpenBox v0.1); validar integridade com *baseline* AIDE e verificação de hash no boot; executar *fingerprint* inicial (Fase 0) antes de colocar o aparelho em produção.

**S1 — ADB e credenciais padrão.** Desabilitar o ADB e fechar a porta 5555; trocar todas as credenciais de fábrica por senhas fortes; aplicar *kill switch* nftables com política *default-deny* de entrada, bloqueando qualquer acesso administrativo a partir da internet.

**R1 — Falta de segmentação.** Isolar o box em **VLAN dedicada** com firewall nftables *default-deny* entre segmentos; remover regras UPnP/port forwarding; rotear a saída por túnel WireGuard *full-tunnel* com DNS cifrado (Pi-hole/Unbound), impedindo que o dispositivo alcance lateralmente a LAN doméstica e contendo qualquer comprometimento ao próprio segmento.

> **Defesa em profundidade:** segmentação de rede + firewall *default-deny* + firmware verificado + monitoramento local cobrem os três eixos (Hardware, Software e Redes), reduzindo os riscos críticos a níveis aceitáveis sem depender de um único controle.
