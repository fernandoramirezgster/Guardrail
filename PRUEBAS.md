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
