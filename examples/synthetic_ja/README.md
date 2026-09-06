# Synthetic Japanese example

The bundled corpus describes a fictional image service. It was written for
this repository and contains no production data, copyrighted textbook text,
or recruitment-company information.

Run:

```bash
python -m kag_grounded_kv3
python -m kag_grounded_kv3.evaluation
```

The demo prints only grounded source chunks. Generated sentence, fact, and
path keys are ranking signals and are never passed to the answer layer.

