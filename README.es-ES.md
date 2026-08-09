

# browser-harness-bidi ♞

Conecta un LLM directamente a un navegador real con un **harness de WebDriver bidi** ligero y editable.

Un WebSocket hacia un navegador compatible con WebDriver, un daemon diminuto, un espacio de trabajo de ayuda editable. El agente escribe lo que falta durante la ejecución. El harness se mejora a sí mismo en cada ejecución.

```text
  * agent: needs browser state or an action
  |
  * browser-harness-bidi helpers
  |
  * WebDriver bidi WebSocket
  |
  * WebDriver-capable browser
      - Firefox via geckodriver
      - Chrome via ChromeDriver bidi
  |
  ✓ page inspected, clicked, typed, extracted, or captured
```

Cuando una tarea necesita un auxiliar reutilizable que no pertenece al paquete central, el agente puede agregarlo a `agent-workspace/agent_helpers.py` y usarlo en la próxima ejecución.

**bidi no es una capa sigilosa. Es la capa estándar de automatización.** WebDriver bidi estándar puede exponer `navigator.webdriver`. Este proyecto se centra en un control de navegador correcto y orientado al futuro, no en ocultar la automatización.

## Prompt de configuración

Pega esto en Codex o Claude Code:

```text
Set up https://github.com/AndrewDzzz/browser-harness-bidi for me.

Read `install.md` and follow the steps to install browser-harness-bidi and run the managed Firefox bidi smoke test.
```

## Inicio rápido

```bash
uv tool install -e .

bidi-firefox <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

`bidi-firefox` inicia geckodriver, solicita un WebSocket WebDriver bidi, ejecuta tu script y cierra la sesión administrada.

## ¿Por qué bidi?

El proyecto original `browser-use/browser-harness` demostró una estructura fundamental: un harness de navegador debe ser lo suficientemente pequeño para que un agente lo comprenda y lo suficientemente editable para que un agente lo repare. Este proyecto mantiene esa forma, pero establece **WebDriver bidi** como el centro de gravedad.

bidi es la capa orientada al futuro porque:

- es un estándar de automatización de navegadores W3C;
- es nativo de la automatización moderna de Firefox y cuenta con soporte creciente en las herramientas de Chrome;
- es bidireccional por diseño, con flujos de comandos y eventos sobre WebSocket;
- es compatible con infraestructuras de WebDriver como geckodriver, chromedriver, Selenium Grid y proveedores de pruebas en la nube;
- es una abstracción limpia para contextos de navegador, ámbitos de scripts, acciones de entrada, registros y eventos de red.

```text
bidi = the cross-browser WebDriver standard for automation
```

## Arquitectura

- `install.md` - instalación inicial y arranque del navegador
- `SKILL.md` - uso diario del agente
- `src/browser_harness_bidi/` - paquete central de bidi protegido
- `src/browser_harness/` - envoltura de compatibilidad para la ruta de importación original y la CLI
- `agent-workspace/agent_helpers.py` - código auxiliar que edita el agente
- `agent-workspace/domain-skills/` - habilidades reutilizables específicas por sitio (opcionales)
- `interaction-skills/` - mecánicas reutilizables de interacción bidi
- `tests/unit/` - pruebas unitarias rápidas para el comportamiento de los auxiliares

Más detalles: [docs/architecture.md](docs/architecture.md)

## Qué funciona realmente

- Firefox administrado: `bidi-firefox <<'PY' ... PY` inicia geckodriver y Firefox por ti.
- bidi manual: establece `BIDI_WS` o `BIDI_WEBDRIVER_URL` y usa `bidi-harness`.
- Navegación y pestañas: `new_tab()`, `goto_url()`, `reload()`, `list_tabs()`, `switch_tab()`, `ensure_real_tab()`.
- Capturas de pantalla y PDFs: `capture_screenshot()`, `print_pdf()`.
- JavaScript y protocolo sin procesar: `js(expressión)`, `bidi("módulo.comando", ...)`.
- Entrada y selectores: `click_at_xy()`, `click_selector()`, `type_text()`, `press_key()`, `fill_input()`, `wait_for_element()`, `get_text()`.
- Almacenamiento y cookies: auxiliares simples de localStorage, sessionStorage y cookies de documento del mismo origen.
- Observación de red: `network_events()`, `capture_network_during()`, `summarize_network()`, `wait_for_network_idle()`.

## Compatibilidad con navegadores

Firefox Desktop es la opción principal. Chrome y Chromium son compatibles a través de ChromeDriver/WebDriver bidi cuando el controlador devuelve un `webSocketUrl`. Edge es experimental. Safari y los navegadores móviles no son compatibles con este harness actualmente.

Matriz completa: [docs/browser-support.md](docs/browser-support.md)

## Modos de conexión

Consulta [docs/connection.md](docs/connection.md) para la configuración de Firefox administrado, WebSocket bidi directo de Firefox, geckodriver y ChromeDriver.

## Habilidades de interacción

Las notas reutilizables de interacción bidi se encuentran en `interaction-skills/`:

- `browser-basics.md`
- `forms-and-input.md`
- `network-and-storage.md`

Los agentes deben leer la habilidad de interacción correspondiente antes de agregar código auxiliar de un solo uso.

## Habilidades de dominio

Establece `BH_DOMAIN_SKILLS=1` para habilitar `agent-workspace/domain-skills/`. Estos son manuales de procedimientos opcionales por sitio que se muestran mediante `goto_url(url)`.

Las habilidades de dominio deben contener patrones de URL duraderos, selectores, estados de página y notas de flujo de trabajo. No deben contener credenciales, datos privados ni instrucciones para evadir la detección.

## Contribuyentes

- [AndrewDzzz](https://github.com/AndrewDzzz) - propietario y mantenedor del proyecto.
- Codex - socio de implementación, documentación e iteración del harness bidi.

## Contribuir

Las PR y las mejoras son bienvenidas. La mejor manera de ayudar es hacer que bidi sea aburridamente útil:

- agrega pruebas unitarias para el comportamiento de los auxiliares en `tests/unit/`;
- mejora la cobertura de pruebas rápidas (smoke tests) para Firefox y ChromeDriver;
- agrega habilidades de interacción nativas de bidi;
- contribuye con habilidades de dominio pequeñas y enfocadas en `agent-workspace/domain-skills/<site>/`;
- mantén `agent-workspace/agent_helpers.py` como el punto de extensión vacío que los agentes editan durante tareas reales.

Prefiere parches pequeños. Si falta un auxiliar, primero demuestra que puede expresarse con `bidi("module.command", ...)` sin procesar, y luego envuélvelo solo si es ampliamente reutilizable.

## Nota sobre el proyecto original

browser-harness-bidi está inspirado en la arquitectura y el flujo de trabajo de [browser-use/browser-harness](https://github.com/browser-use/browser-harness), licenciado bajo MIT. Reimplementa la capa de transporte y auxiliar alrededor de WebDriver bidi, manteniendo un flujo de trabajo compatible y de harness pequeño para agentes.
