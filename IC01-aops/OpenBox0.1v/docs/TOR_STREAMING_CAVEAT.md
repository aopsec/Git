# Tor para Streaming — Por Que Não Funciona

## TL;DR

Não roteie streaming HD/4K via Tor. O OpenBox usa Tor apenas para metadados/lookup. O stream em si trafega via WireGuard direto.

## Análise técnica

### Bandwidth da rede Tor

Métricas oficiais (Tor Metrics, https://metrics.torproject.org/bandwidth.html):

- Bandwidth média por circuito: **1-5 Mbps**
- Top 1% de circuitos: ~10-15 Mbps
- Latência adicional: 100-500ms (3 hops)

### Bandwidth requerido por streaming

| Qualidade | Bitrate típico |
|---|---|
| 480p | 1-2 Mbps |
| 720p | 3-5 Mbps |
| 1080p | 5-8 Mbps |
| 1080p HDR | 10-12 Mbps |
| 4K | 15-25 Mbps |
| 4K HDR | 25-50 Mbps |

Conclusão: **só 480p é viável**, e mesmo assim com risco de buffering constante.

### Bloqueio de BitTorrent

Tor exit policy default rejeita ports BitTorrent comuns:
```
reject *:25, reject *:119, reject *:135-139, reject *:445,
reject *:563, reject *:1214, reject *:4661-4666,
reject *:6346-6429, reject *:6699, reject *:6881-6999
```

Torrentio (addon Stremio) usa DHT/trackers UDP — bloqueado pela maioria dos exits. Tor Project explicita BitTorrent over Tor é desencorajado:
> "BitTorrent is fundamentally incompatible with Tor's design, and we strongly discourage it."

### Correlação de tráfego

Mesmo se passasse, streaming de longa duração com bitrate previsível é suscetível a fingerprinting via traffic analysis. Adversário com visibilidade em ambas as pontas (entry + exit) consegue correlacionar com alta probabilidade.

## O que OpenBox faz

```
Stream HD/4K:
  Stremio -> Pi-hole -> dnscrypt -> WireGuard -> Internet (DIRETO, sem Tor)

Metadados/lookup (quando addon suporta SOCKS5):
  Addon X -> Tor :9050 -> circuit Tor -> destino (latencia OK para JSON)

Anonimato real (use Tor Browser dedicado):
  Browser dedicado -> Tor Browser -> circuit Tor (NAO use Stremio para isso)
```

## O que TVBox OSS errou

O documento original prometia:
> "Stream sob Tor + WireGuard sem impacto mensurável na experiência."

Isso é fisicamente impossível. Quem implementar literalmente vai obter buffering constante e provavelmente bloqueio do exit node ao tentar BitTorrent.

## Referências

- Tor Project FAQ — Bittorrent: https://support.torproject.org/abuse/what-about-criminals/
- Tor Metrics: https://metrics.torproject.org/
- Tor spec — Exit policies: https://spec.torproject.org/dir-spec.html#exit-policies
