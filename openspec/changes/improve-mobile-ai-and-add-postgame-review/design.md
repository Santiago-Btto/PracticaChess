# Design

## Context

La APK usa Kivy y `python-chess`, no incluye Stockfish ni otro binario nativo, y `buildozer.spec` no declara permiso de Internet. `MobileGameController` hoy combina reglas de partida, búsqueda negamax de profundidad fija, sugerencias y datos de curva; recalcula sincrónicamente después de cambios de partida. Conserva SAN, instantáneas y `board.move_stack`, pero la pantalla de `mobile/app.py` es una única vista de tablero sin estado de revisión.

Este diseño implementa los contratos de `mobile-local-analysis` y `mobile-postgame-review`; la motivación está en [proposal.md](proposal.md).

## Goals / Non-Goals

**Goals:**

- Mantener análisis y revisión completamente locales y compatibles con el empaquetado Android existente.
- Aumentar la calidad táctica del motor con un resultado útil aun cuando se agote el tiempo disponible.
- Garantizar que el trabajo de CPU no congele el bucle de Kivy ni pueda aplicar datos de una partida o posición reemplazada.
- Dejar que el usuario controle el análisis local en vivo sin afectar la revisión post-partida solicitada explícitamente.
- Modelar una partida finalizada de forma inmutable para revisarla incrementalmente y navegarla sin mutar la partida activa.
- Derivar un resumen general honesto sólo de una revisión completa de la instantánea de partida activa.
- Hacer determinista la lógica de presupuesto, caducidad y clasificación para poder probarla sin esperas reales.

**Non-Goals:**

- Integrar Stockfish, una API remota, cuentas de usuario, sincronización de PGN o permisos nuevos.
- Convertir la APK en un modo competitivo Humano vs. IA, modificar reglas de ajedrez o garantizar una fuerza/Elo concreto.
- Ofrecer análisis multi-PV, variantes profundas interactivas, apertura con base de datos remota o revisión de variantes creadas por el usuario.
- Persistir la preferencia de análisis entre cierres de la aplicación, asignar Elo al motor local o presentar el resumen como análisis de Stockfish.

## Decisions

### 1. Motor local iterativo y cooperativamente cancelable

Se conservará el evaluador heurístico y la búsqueda negamax existente, sustituyendo la profundidad fija por iteración de profundidades con poda alfa-beta, ordenamiento de jugadas actual y un reloj inyectable. Cada iteración completa publica sólo su mejor resultado completamente calculado. La búsqueda verificará una señal de cancelación y la fecha límite regularmente; una cancelación o vencimiento durante una iteración descartará esa iteración y devolverá el último resultado completo. Las posiciones terminales devolverán un resultado explícito sin jugada.

El presupuesto será una política por propósito: corto para sugerencia interactiva y mayor para una posición de revisión. Los valores iniciales se definirán como constantes fácilmente ajustables y se pasarán explícitamente, en vez de reutilizar una única constante de dificultad.

Se descarta añadir un motor binario externo: elevaría complejidad de ABI, tamaño y empaquetado Android. También se descarta sólo subir `SEARCH_DEPTH`: conserva bloqueos impredecibles en dispositivos lentos. Una tabla de transposición acotada por trabajo podrá añadirse si las mediciones muestran que cabe en memoria; no será requisito de la primera entrega.

### 2. Coordinador de solicitudes aislado del estado Kivy

Se introducirá un coordinador local de análisis en la capa móvil que acepte instantáneas FEN (o copias de tablero), propósito, presupuesto y un token de generación. El coordinador ejecutará una sola solicitud de CPU a la vez en un worker; el motor nunca tocará widgets ni el tablero vivo. Toda solicitud obtiene un `request_id` monotónico y se considera actual sólo si coinciden `request_id`, FEN y generación de partida/revisión al publicar.

Las mutaciones de juego (mover, deshacer, reiniciar, restaurar posición) y la salida/reemplazo de revisión invalidarán la generación y señalarán cancelación. Los resultados se entregarán al hilo UI con `Clock.schedule_once` o un adaptador equivalente; el controlador volverá a validar el token antes de actualizar sugerencia, curva, progreso o datos de revisión. Esto también permite una cola de pruebas síncrona/falsa.

Se descarta analizar el objeto `Board` compartido o actualizar widgets desde un hilo trabajador, porque puede producir carreras y violar el modelo de hilos de Kivy. Se descarta iniciar un hilo por jugada sin cola, porque competirían por CPU y harían más probable el resultado atrasado.

### 3. Datos de análisis coherentes y explicables

El controlador almacenará registros inmutables por posición con FEN, índice de ply, evaluación del motor desde la perspectiva de blancas, mejor jugada y variación disponible. La curva de evaluación se derivará de estos registros, sustituyendo el proxy material-only actual.

Para clasificar una jugada se normalizarán la evaluación de la mejor decisión antes de mover y la evaluación después de la jugada realizada al bando que movió. La pérdida será `max(0, mejor_antes - evaluacion_despues)`. Se usarán límites constantes en centipeones: `<=15` mejor jugada, `<=50` buena, `<=120` imprecisión, `<=250` error y `>250` blunder; resultados de mate se normalizarán a una pérdida decisiva. El registro conservará la categoría, SAN de la jugada realizada, alternativa en SAN si existe, evaluaciones y estado terminal.

Se descarta comparar sólo material o una puntuación con signos mezclados: daría clasificaciones engañosas, particularmente para negras, y no permitiría explicar la sugerencia real del motor.

### 4. Instantánea inmutable y progreso incremental de revisión

Al iniciar revisión, el controlador capturará la FEN inicial, lista ordenada de movimientos de la línea principal (UCI/SAN) y resultado, sin reutilizar el tablero editable. Reconstruirá tableros de revisión desde esa instantánea para cada ply. Un trabajo secuencial analizará, para cada jugada, la posición anterior y la posterior necesaria, emitirá un `ReviewEntry` y actualizará progreso `(completadas, total)` en el hilo UI. Procesar una jugada a la vez reduce el pico de CPU y permite cancelar rápido.

La UI conservará una sola pantalla: añadirá una acción de revisión visible sólo al terminar, un panel de progreso y un modo revisión con navegación Anterior/Siguiente. La posición seleccionada se renderizará desde la instantánea de revisión y el panel mostrará jugada, categoría, cambio de evaluación y alternativa. Al salir se limpiará el estado visual de revisión y se restaurará el tablero de la partida finalizada; al reiniciar se comenzará una generación de partida nueva.

Se descarta abrir una segunda aplicación/pantalla sin estado compartido: duplicaría el flujo de tablero y haría más fácil perder la correspondencia entre entrada y posición. También se descarta bloquear hasta completar toda la partida: una partida larga dejaría la interfaz inutilizable.

### 5. Preferencia de análisis en vivo aislada de la revisión explícita

El controlador mantendrá una preferencia de sesión `live_analysis_enabled`, activada por defecto. Sólo las solicitudes automáticas de propósito interactivo respetarán esa preferencia. Al desactivarla, el controlador invalidará y cancelará la solicitud de sugerencia actual, limpiará la recomendación y sus indicadores visibles, y no programará nuevas sugerencias después de mover, deshacer, reiniciar o voltear. Al reactivarla, solicitará una sola evaluación para el FEN vigente.

La revisión post-partida iniciada por el usuario seguirá usando su propósito y presupuesto propios aunque el análisis en vivo esté desactivado. Los mismos tokens de posición, solicitud y generación validarán las devoluciones, de modo que un resultado de sugerencia anterior no pueda reaparecer al apagar la preferencia ni contaminar una revisión.

La UI añadirá un control táctil rotulado y un estado visible de análisis activo/inactivo. Se descarta usar la preferencia como un ajuste de fuerza o de presupuesto: eso haría ambiguo si la petición debe ejecutarse y no satisface la necesidad de ocultar las mejores jugadas.

### 6. Resumen post-partida inmutable y completo

Cuando todas las `ReviewEntry` de una misma instantánea terminen, el controlador derivará un resumen inmutable: conteos de mejor, buena, imprecisión, error y blunder; una selección ordenada de mejores jugadas y momentos críticos; y una explicación general basada exclusivamente en las categorías y pérdidas calculadas por la IA local. No se publicará un resumen parcial durante el progreso ni se reutilizarán entradas de otra instantánea.

El panel de revisión mostrará mientras tanto progreso explícito y, una vez completo, un resumen compacto o desplazable con los conteos y momentos destacados; el detalle por jugada seguirá siendo la fuente para recorrer toda la línea. El texto advertirá que es una evaluación de IA local, no de Stockfish. Se descarta inventar un Elo, una variante multi-PV o conclusiones no respaldadas por los registros de revisión.

## Risks / Trade-offs

- [Más profundidad consume batería y varía entre dispositivos] → presupuestos conservadores por propósito, cancelación cooperativa y ajuste mediante mediciones en un dispositivo Android representativo.
- [El intérprete Python puede tardar en observar una cancelación dentro de un nodo costoso] → comprobar reloj y evento de cancelación en la entrada de búsqueda, por nodo y entre iteraciones; entregar siempre el último resultado completo.
- [Un callback tardío puede contaminar una nueva partida] → exigir triple validación FEN, `request_id` y generación antes de toda actualización de estado o UI.
- [Una heurística local no equivale a Stockfish] → presentar las categorías como evaluación de la IA local y mantener los límites en constantes calibrables, cubiertos por fixtures tácticos.
- [La información de revisión no cabe bien en pantallas angostas] → reutilizar el layout vertical existente, textos cortos, controles táctiles y pruebas de tamaño vertical antes de empaquetar.
- [Listas de mejores jugadas y momentos críticos pueden crecer demasiado] → limitar el panel general a una selección ordenada y conservar el detalle completo en la navegación existente.
- [Desactivar el análisis podría dejar una flecha o resumen atrasado] → invalidar el token antes de limpiar presentación y publicar resumen sólo si sigue vigente la instantánea completa.
- [Partidas guardadas o sesiones no tienen formato de persistencia] → limitar la instantánea a la sesión actual; no se introduce migración de almacenamiento.

## Migration Plan

1. Añadir el motor presupuestado, el coordinador y pruebas unitarias sin cambiar la interacción visual.
2. Migrar sugerencia y curva a los nuevos registros de análisis, conservando la validación de legalidad de la UI.
3. Añadir el modelo de instantánea/revisión, luego los widgets y callbacks Kivy en el hilo principal.
4. Añadir la preferencia de análisis en vivo y el resumen de revisión, con pruebas deterministas de cancelación, completitud y presentación.
5. Ejecutar la suite móvil y pruebas de empaquetado; construir e instalar una APK de prueba en Android API 24+ para comprobar fluidez, cancelación, preferencia, navegación y resumen.
5. Si aparecen regresiones de rendimiento, reducir los presupuestos o desactivar la entrega incremental de la revisión mediante las constantes de política, sin tocar reglas, historial ni formato de usuario.
