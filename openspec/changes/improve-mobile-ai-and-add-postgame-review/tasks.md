# Tasks

> Aplicar TDD estricto en cada incremento: antes de modificar un archivo existente, ejecutar y registrar la línea base del subconjunto afectado; escribir primero la prueba RED mínima; implementar sólo lo necesario para GREEN; añadir al menos un caso de triangulación (camino feliz y borde); y refactorizar únicamente con las pruebas verdes. No escribir código de producción antes de la prueba RED correspondiente.

## 1. Núcleo de análisis local presupuestado

- [x] 1.1 Ejecutar `pytest tests/test_mobile_controller.py` y registrar una línea base verde antes de cambiar el controlador; verificar que no existen fallos preexistentes.
- [x] 1.2 RED: Añadir en `tests/test_mobile_controller.py` pruebas deterministas para el resultado estructurado de análisis: una posición legal devuelve una mejor jugada legal y evaluación, mientras una posición terminal no devuelve jugada; verificar que ambas fallen contra la API actual.
- [x] 1.3 GREEN: Implementar en `mobile/controller.py` los tipos/resultados de análisis local y la detección explícita de posiciones terminales para satisfacer 1.2; verificar `pytest tests/test_mobile_controller.py` verde.
- [x] 1.4 TRIANGULATE/REFACTOR: Añadir fixtures de mate, ahogado y posición jugable de ambos bandos, y extraer la normalización de evaluación compartida; verificar las pruebas de 1.2 más los nuevos casos verdes sin afirmar jugadas ilegales.
- [x] 1.5 RED: Añadir pruebas con reloj inyectable que demuestren búsqueda iterativa, conservación del último resultado completo al expirar el presupuesto y presupuestos distintos para sugerencia y revisión; verificar que fallen con la búsqueda fija actual.
- [x] 1.6 GREEN: Reemplazar la profundidad fija por negamax iterativo con poda alfa-beta, fecha límite y presupuesto por propósito en `mobile/controller.py`; verificar que las pruebas de 1.5 y las pruebas tácticas existentes sigan verdes.
- [x] 1.7 TRIANGULATE/REFACTOR: Añadir posiciones tácticas deterministas que comprueben que el resultado devuelto sigue siendo legal al agotar el tiempo en mitad de una iteración, y simplificar las constantes de política de presupuesto; verificar `pytest tests/test_mobile_controller.py` verde.

## 2. Coordinación segura y datos de análisis de partida

- [x] 2.1 Ejecutar `pytest tests/test_mobile_controller.py` antes de cambiar coordinación o historial, registrar la línea base y detenerse si falla.
- [x] 2.2 RED: Añadir pruebas con un ejecutor/planificador controlado que reproduzcan resultados atrasados después de una jugada, undo y reinicio; verificar que falle porque un resultado viejo aún puede actualizar el estado.
- [x] 2.3 GREEN: Implementar un coordinador de una sola tarea de CPU con `request_id`, FEN y generación de partida/revisión, cancelación cooperativa y entrega al hilo UI; verificar las pruebas de 2.2 verdes sin actualizar widgets desde el worker.
- [x] 2.4 TRIANGULATE/REFACTOR: Añadir casos para salir de revisión y para completar una solicitud vigente, y centralizar la validación de tokens antes de cualquier actualización; verificar `pytest tests/test_mobile_controller.py` verde.
- [x] 2.5 RED: Añadir pruebas que exijan registros por FEN/ply con evaluación real del motor y mejor continuación, y que rechacen la curva basada solamente en material; verificar que fallen contra `evaluation_curve` actual.
- [x] 2.6 GREEN: Migrar sugerencia, curva e historial del controlador a los registros de análisis aceptados por token; verificar que las nuevas pruebas y las de sugerencias legales existentes pasen.
- [x] 2.7 TRIANGULATE/REFACTOR: Añadir una secuencia con deshacer/rejugar que pruebe que el historial reemplazado no reaparece y refactorizar el almacenamiento inmutable; verificar `pytest tests/test_mobile_controller.py` verde.

## 3. Modelo y ejecución de revisión post-partida

- [x] 3.1 Ejecutar `pytest tests/test_mobile_controller.py` antes de cambiar el modelo de partida terminada y registrar la línea base verde.
- [x] 3.2 RED: Añadir pruebas para capturar una instantánea inmutable (FEN inicial, jugadas y resultado), reconstruir cada ply y conservar la partida finalizada al navegar; verificar que fallen porque todavía no hay modelo de revisión.
- [x] 3.3 GREEN: Implementar el modelo de instantánea y acceso a posiciones de revisión en `mobile/controller.py`; verificar las pruebas de 3.2 verdes y que la pila de movimientos de la partida original no cambie.
- [x] 3.4 TRIANGULATE/REFACTOR: Añadir partidas cortas con captura, promoción o terminal y límites de índice inicial/final, refactorizando la reconstrucción para usar sólo la instantánea; verificar `pytest tests/test_mobile_controller.py` verde.
- [x] 3.5 RED: Añadir pruebas de tabla para los límites de clasificación (mejor, buena, imprecisión, error, blunder), signos de blancas/negras, mate y una jugada terminal sin alternativa; verificar que fallen con la ausencia de entradas de revisión.
- [x] 3.6 GREEN: Implementar `ReviewEntry`, cálculo de pérdida desde el bando que movió y alternativas SAN honestas, usando los resultados del análisis local; verificar las pruebas de 3.5 verdes.
- [x] 3.7 TRIANGULATE/REFACTOR: Añadir casos de pérdida exactamente en cada umbral y de resultado terminal, y extraer constantes de clasificación con nombres claros; verificar `pytest tests/test_mobile_controller.py` verde.
- [x] 3.8 RED: Añadir pruebas con el planificador controlado para progreso incremental, una entrada por cada jugada y cancelación al salir/reiniciar; verificar que fallen contra el controlador sin revisión asíncrona.
- [x] 3.9 GREEN: Implementar el trabajo secuencial de revisión, progreso y cancelación/invalidez con los mismos tokens del coordinador; verificar 3.8 verde y que una devolución tardía no afecte un juego nuevo.
- [x] 3.10 TRIANGULATE/REFACTOR: Añadir una partida de varias jugadas y una cancelación tras la primera entrada, eliminar duplicación entre análisis en vivo y revisión; verificar `pytest tests/test_mobile_controller.py` verde.

## 4. Interfaz Kivy de revisión sin bloqueo

- [x] 4.1 Ejecutar `pytest tests/test_mobile_layout.py tests/test_mobile_packaging.py` y registrar la línea base verde antes de modificar `mobile/app.py` o el layout.
- [x] 4.2 RED: Extender las pruebas de layout/UI para exigir que el resultado final muestre la acción de revisión, que exista progreso, controles Anterior/Siguiente y campos para jugada, categoría, evaluación y alternativa, preservando el tamaño vertical táctil; verificar que fallen contra la pantalla actual.
- [x] 4.3 GREEN: Integrar en `mobile/app.py` el botón condicional, panel de progreso y modo de revisión de una sola pantalla, entregando todas las actualizaciones mediante el hilo principal de Kivy; verificar las pruebas de 4.2 verdes.
- [x] 4.4 TRIANGULATE/REFACTOR: Añadir pruebas para entrar, navegar hasta primera/última posición, salir y reiniciar durante revisión; simplificar el renderizado de tablero para que no mute la partida finalizada; verificar `pytest tests/test_mobile_layout.py tests/test_mobile_controller.py` verde.
- [x] 4.5 Actualizar las comprobaciones de empaquetado sólo si se tocan requisitos/recursos y confirmar que siguen sin permiso `INTERNET`, sin dependencias de red y con Android API 24+; verificar `pytest tests/test_mobile_packaging.py` verde.

## 5. Preferencia de análisis en vivo

- [x] 5.1 Ejecutar `pytest tests/test_mobile_controller.py` y registrar una línea base verde antes de cambiar la preferencia o la coordinación de sugerencias.
- [x] 5.2 RED: Añadir pruebas con un ejecutor controlado que demuestren que desactivar el análisis en vivo cancela/invalida una sugerencia pendiente y evita nuevas solicitudes después de mover, deshacer, reiniciar y voltear; verificar que fallen contra el comportamiento automático actual.
- [x] 5.3 GREEN: Implementar la preferencia de sesión activada por defecto, su API de cambio y el bloqueo de solicitudes/presentación de sugerencias en `mobile/controller.py`; verificar las pruebas de 5.2 verdes.
- [x] 5.4 TRIANGULATE/REFACTOR: Añadir casos para reactivar sobre el FEN vigente y para iniciar una revisión explícita con el análisis en vivo apagado; asegurar que un resultado tardío no restaura una flecha o recomendación; verificar `pytest tests/test_mobile_controller.py` verde.
- [x] 5.5 Ejecutar `pytest tests/test_mobile_layout.py tests/test_mobile_packaging.py` y registrar una línea base verde antes de cambiar los controles Kivy.
- [x] 5.6 RED: Extender las pruebas de UI/layout para exigir un control táctil claramente rotulado, estado visible de análisis activo/inactivo y ausencia de indicador de mejor jugada cuando esté apagado; verificar que fallen contra la pantalla actual.
- [x] 5.7 GREEN: Conectar el control de análisis en vivo y su presentación a `mobile/app.py` mediante el hilo principal de Kivy; verificar las pruebas de 5.6 verdes sin alterar los requisitos offline del empaquetado.
- [x] 5.8 TRIANGULATE/REFACTOR: Probar apagar/reactivar desde la interfaz y conservar las dimensiones táctiles y los controles de revisión; verificar `pytest tests/test_mobile_layout.py tests/test_mobile_controller.py tests/test_mobile_packaging.py` verde.

## 6. Resumen general post-partida

- [x] 6.1 Ejecutar `pytest tests/test_mobile_controller.py` y registrar una línea base verde antes de cambiar los datos de revisión o el resumen.
- [x] 6.2 RED: Añadir pruebas deterministas para un resumen completo que agrupe las cinco categorías, ordene mejores jugadas y momentos críticos, produzca una explicación local y no se publique con entradas parciales; verificar que fallen contra el controlador actual.
- [x] 6.3 GREEN: Implementar el modelo inmutable y la derivación del resumen sólo al completar las entradas válidas de la instantánea activa; verificar las pruebas de 6.2 verdes.
- [x] 6.4 TRIANGULATE/REFACTOR: Añadir casos de partida terminal, empate o colección vacía y cancelación/reinicio, comprobando que ningún resumen obsoleto sobreviva; verificar `pytest tests/test_mobile_controller.py` verde.
- [x] 6.5 Ejecutar `pytest tests/test_mobile_layout.py` y registrar una línea base verde antes de modificar el panel de revisión.
- [x] 6.6 RED: Extender las pruebas de UI/layout para exigir progreso sin resumen final mientras se analiza y, al completar, un panel de resumen con conteos, mejores jugadas, momentos críticos y aviso de IA local; verificar que fallen contra la pantalla actual.
- [x] 6.7 GREEN: Mostrar el resumen completo en `mobile/app.py` sin bloquear Kivy y sin reemplazar la navegación por jugadas; verificar las pruebas de 6.6 verdes.
- [x] 6.8 TRIANGULATE/REFACTOR: Probar navegación, salida y reinicio con el resumen visible, preservando el tablero final y tamaño táctil; verificar `pytest tests/test_mobile_layout.py tests/test_mobile_controller.py` verde.

## 7. Validación integrada de APK

- [x] 7.1 Ejecutar `pytest tests/test_mobile_controller.py tests/test_mobile_layout.py tests/test_mobile_packaging.py` y verificar toda la suite móvil verde, registrando el total de pruebas y la evidencia TDD por tarea.
- [ ] 7.2 Construir una APK de prueba con la configuración existente e instalarla en un dispositivo/emulador Android API 24+; verificar manualmente que el análisis en vivo se active/desactive sin resultados viejos, que la revisión de una partida terminada muestre progreso, navegación y resumen completo, y que reiniciar/salir no muestre datos atrasados.
