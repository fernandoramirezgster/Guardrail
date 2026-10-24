# Verificación de la fase 1

- Entorno: Python 3.12, Linux.
- Comando: `python -m pytest -q`.
- Resultado: **32 pruebas aprobadas**.
- `python -m pip check`: sin incompatibilidades de dependencias.
- Se verificaron los endpoints con TestClient y proveedores simulados.
- No se llamó a un proveedor real ni se verificó la ejecución en Windows.
- Starlette emitió un aviso de deprecación sobre su integración con HTTPX; no hubo fallos.
- `requirements-lock.txt` conserva todas las versiones del entorno verificado.
- No se midió resistencia a ataques, ASR, FPR ni rendimiento experimental.

Las pruebas cubren permitir, ocultar, bloquear, REVIEW, entrada/salida saneada vacía,
errores internos, salida inválida del proveedor y omisión del texto original
en respuestas bloqueadas y errores de validación.

# Verificación de la fase 2 (en curso)

- Entorno: Python 3.12.13, Windows 11, sin torch instalado.
- Comando: `python -m pytest -q`.
- Resultado tras integrar las fases 3 y 4: **109 pruebas aprobadas, 11 omitidas**
  (las omitidas son `-m models`, que requieren los modelos descargados).
- La decisión la toma el motor de políticas; se añadió la regla `revisar_inyeccion_probable`.
- Se verificó que el clasificador se aplica a fragmentos RAG en `/chat` y `/rag/evaluate`.
- Se corrigió el separador del contexto RAG enviado al LLM (enviaba `\n` literal).
- Política híbrida verificada con clasificadores simulados: umbrales BLOCK/REVIEW/ALLOW,
  REVIEW sobre MASK, reglas que bloquean aunque el clasificador diga benigno, error del
  clasificador → 503 sin detalles internos, sin llamada al LLM tras un bloqueo.
- Dependencias de `requirements.txt` resueltas con `uv pip compile` para
  Linux/Python 3.12; la imagen Docker **no** se construyó (Docker no instalado).
- Pendiente: ejecutar `pytest -m models` y el benchmark con los modelos reales.

Línea base con `python -m experiments.run_benchmark` (solo reglas, `es_custom`, 32 muestras): TPR 0.125 (2/16 inyecciones),
FPR 0.000. Las reglas de la fase 1 apenas cubren variantes en español no literales.
