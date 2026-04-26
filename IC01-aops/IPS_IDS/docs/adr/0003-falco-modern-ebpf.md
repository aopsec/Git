# ADR 0003: Falco Modern eBPF

## Decision

Use `falco-modern-bpf.service`.

## Reason

Modern Arch kernels expose BTF and avoid legacy driver build churn.

## Consequence

Preflight requires `/sys/kernel/btf/vmlinux`.
