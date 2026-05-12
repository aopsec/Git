

## Qdrant persistence validation

Qdrant persistence is validated when Docker inspect shows a bind mount or volume with:

```text
Destination: /qdrant/storage
RW: true
```

Current validated mount:

```text
Type: bind
Source: /home/aops/.local/qdrant/storage
Destination: /qdrant/storage
RW: true
```

Validation command:

```bash
# [FIX-PERSIST-01] Certify persistence only for writable bind or volume mounts.
if docker inspect qdrant-local --format '{{json .Mounts}}' \
  | jq -e '.[] | select(
      .Destination == "/qdrant/storage"
      and (.Type == "bind" or .Type == "volume")
      and .RW == true
    )' >/dev/null; then
  echo "QDRANT_STORAGE_PERSISTENCE_OK"
else
  echo "QDRANT_STORAGE_PERSISTENCE_MISSING"
fi
```

Expected result:

```text
QDRANT_STORAGE_PERSISTENCE_OK
```
