# SII Invoice Scraper

Scraper para obtener facturas de compra desde el portal del Servicio de Impuestos Internos (SII), procesarlas y sincronizarlas con MongoDB.

El scraper inicia sesión en SII, navega al Registro de Compras y Ventas, consulta los RUTs asociados al usuario, obtiene documentos aceptados y pendientes, normaliza los datos y los guarda en la colección `invoices_supplier`.

---

## ¿Qué hace este scraper?

Este proyecto automatiza el siguiente flujo:

1. Inicia sesión en SII usando usuario y contraseña, o certificado digital.
2. Navega hasta el Registro de Compras y Ventas.
3. Selecciona el periodo de consulta si se entrega mes y/o año.
4. Recorre los RUTs disponibles para el usuario autenticado.
5. Consulta documentos aceptados.
6. Consulta documentos pendientes.
7. Extrae facturas electrónicas, facturas exentas y notas de crédito.
8. Construye un DataFrame crudo con los datos obtenidos desde SII.
9. Limpia y normaliza los datos.
10. Sincroniza las facturas con MongoDB.
11. Inserta documentos nuevos.
12. Actualiza el estado de documentos existentes.
13. Guarda progreso temporal por usuario para evitar reprocesar en caso de errores.
14. Cierra sesión y libera el navegador al finalizar.

---

## Estructura del proyecto

```txt
sii_invoice_scraper/
  main.py
  Pipfile
  Pipfile.lock
  .env
  .gitignore
  install.bat
  run_scraper.bat
  install.sh
  run_scraper.sh

  sii_scraper/
    __init__.py
    settings.py
    credentials.py
    progress_store.py
    invoice_transformer.py
    invoice_repository.py
    runner.py
    sii_scraper.py
```

---

## Módulos principales

### `main.py`

Punto de entrada del proyecto.

Responsabilidades:

* leer argumentos de consola;
* configurar logging;
* crear la conexión a MongoDB;
* inicializar dependencias;
* crear el runner;
* ejecutar el scraper;
* cerrar la conexión a MongoDB.

---

### `settings.py`

Carga la configuración principal desde variables de entorno.

Responsabilidades:

* leer `MONGODB_URI`;
* definir la base de datos;
* definir archivo de progreso;
* definir si Selenium corre en modo headless;
* definir si se usará certificado;
* definir cantidad máxima de reintentos.

---

### `credentials.py`

Carga credenciales SII desde variables de entorno.

Busca pares con el siguiente formato:

```env
SII_USER_1=11111111-1
SII_PASS_1=password1

SII_USER_2=22222222-2
SII_PASS_2=password2
```

Retorna un diccionario con la forma:

```py
{
    "11111111-1": "password1",
    "22222222-2": "password2",
}
```

---

### `progress_store.py`

Administra el archivo de progreso temporal.

Este archivo permite registrar qué usuarios ya fueron procesados durante una corrida. Si el scraper falla en medio del proceso, se puede volver a ejecutar sin repetir usuarios que ya terminaron correctamente.

Archivo por defecto:

```txt
sii_progress.txt
```

Responsabilidades:

* cargar usuarios completados;
* marcar usuarios como completados;
* eliminar el archivo de progreso al finalizar correctamente.

---

### `sii_scraper.py`

Contiene la clase `SiiScraper`.

Responsabilidades:

* iniciar sesión en SII;
* iniciar sesión con certificado si está configurado;
* navegar al Registro de Compras y Ventas;
* seleccionar mes y año;
* seleccionar RUTs;
* consultar documentos;
* extraer documentos aceptados;
* extraer documentos pendientes;
* recorrer tablas paginadas;
* cerrar sesión;
* cerrar navegador;
* retornar un DataFrame crudo.

Este módulo no limpia datos ni interactúa con MongoDB.

---

### `invoice_transformer.py`

Contiene la clase `InvoiceTransformer`.

Responsabilidades:

* seleccionar las columnas utilizadas por el sistema;
* normalizar textos;
* convertir fechas desde Chile a UTC;
* convertir montos a enteros;
* estandarizar tipo de pago;
* dejar el DataFrame listo para persistencia.

---

### `invoice_repository.py`

Contiene la clase `InvoiceRepository`.

Responsabilidades:

* acceder a la colección `invoices_supplier`;
* buscar facturas existentes por `supplier_id` y `number`;
* actualizar el estado de facturas existentes;
* insertar facturas nuevas;
* retornar cantidades insertadas y actualizadas.

---

### `runner.py`

Contiene la clase `SiiScraperRunner`.

Responsabilidades:

* cargar credenciales SII;
* cargar usuarios ya completados;
* ejecutar `SiiScraper` por usuario;
* enviar el DataFrame crudo al transformer;
* sincronizar datos con MongoDB;
* marcar usuarios como completados;
* limpiar archivo de progreso al terminar.

---

## Requisitos

* Python 3.10 o superior.
* Google Chrome instalado.
* Acceso a internet.
* Acceso a MongoDB Atlas.
* Credenciales SII válidas.
* Pipenv.
* Selenium.
* WebDriver Manager.
* pandas.
* pymongo.
* python-dotenv.

---

## Variables de entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
MONGODB_URI=mongodb+srv://usuario:password@cluster.mongodb.net/
DB_NAME=arrocera_erp_db

HEADLESS=true
USE_CERTIFICATE=false
MAX_RETRIES=3
PROGRESS_FILE=sii_progress.txt

SII_USER_1=11111111-1
SII_PASS_1=password1

SII_USER_2=22222222-2
SII_PASS_2=password2
```

---

## Descripción de variables

| Variable          | Obligatoria | Descripción                                                         |
| ----------------- | ----------: | ------------------------------------------------------------------- |
| `MONGODB_URI`     |          Sí | URI de conexión a MongoDB Atlas.                                    |
| `DB_NAME`         |          No | Nombre de la base de datos. Por defecto: `arrocera_erp_db`.         |
| `HEADLESS`        |          No | Ejecuta Chrome sin interfaz gráfica. Por defecto: `true`.           |
| `USE_CERTIFICATE` |          No | Usa flujo de ingreso con certificado digital. Por defecto: `false`. |
| `MAX_RETRIES`     |          No | Cantidad máxima de reintentos. Por defecto: `3`.                    |
| `PROGRESS_FILE`   |          No | Archivo temporal de progreso. Por defecto: `sii_progress.txt`.      |
| `SII_USER_N`      |          Sí | Usuario/RUT SII.                                                    |
| `SII_PASS_N`      |          Sí | Contraseña correspondiente al usuario SII.                          |

---

## Instalación en Windows

Ejecutar una vez:

```bat
install.bat
```

Contenido recomendado:

```bat
@echo off
cd /d "%~dp0"

echo Installing pipenv...
py -m pip install --user pipenv

echo Installing project dependencies...
pipenv install

echo.
echo Installation completed.
pause
```

Para ejecutar manualmente:

```bat
run_scraper.bat
```

Contenido recomendado:

```bat
@echo off
cd /d "%~dp0"

echo Running SII invoice scraper...
pipenv run python main.py

echo.
echo Scraper finished.
pause
```

Para usar con Programador de tareas de Windows, se recomienda una versión sin `pause`:

```bat
@echo off
cd /d "%~dp0"

pipenv run python main.py
```

---

## Instalación en Linux

Ejecutar una vez:

```bash
chmod +x install.sh
./install.sh
```

Contenido recomendado de `install.sh`:

```bash
#!/usr/bin/env bash

set -e

cd "$(dirname "$0")"

echo "Installing pipenv..."
python3 -m pip install --user pipenv

export PATH="$HOME/.local/bin:$PATH"

echo "Installing project dependencies..."
pipenv install

echo "Installation completed."
```

Para ejecutar:

```bash
chmod +x run_scraper.sh
./run_scraper.sh
```

Contenido recomendado de `run_scraper.sh`:

```bash
#!/usr/bin/env bash

set -e

cd "$(dirname "$0")"

echo "Running SII invoice scraper..."
pipenv run python main.py

echo "Scraper finished."
```

---

## Ejecución manual

Ejecutar el scraper para el periodo por defecto del SII:

```bash
pipenv run python main.py
```

Ejecutar para un mes específico:

```bash
pipenv run python main.py --month 06
```

Ejecutar para un año específico:

```bash
pipenv run python main.py --year 2026
```

Ejecutar para mes y año específicos:

```bash
pipenv run python main.py --month 06 --year 2026
```

---

## Flujo general de ejecución

```txt
main.py
  -> carga settings
  -> crea MongoClient
  -> crea Credentials
  -> crea ProgressStore
  -> crea InvoiceTransformer
  -> crea InvoiceRepository
  -> crea SiiScraperRunner
  -> ejecuta runner.run()
```

Luego el runner ejecuta:

```txt
1. Carga credenciales SII.
2. Carga usuarios completados desde sii_progress.txt.
3. Recorre cada usuario configurado.
4. Ejecuta SiiScraper.
5. Obtiene DataFrame crudo.
6. Agrega campo sii_user.
7. Limpia y normaliza datos.
8. Sincroniza facturas con MongoDB.
9. Marca usuario como completado.
10. Limpia archivo de progreso al finalizar.
```

---

## Flujo interno del scraper SII

```txt
SiiScraper
  -> inicia sesión
  -> navega al Registro de Compras y Ventas
  -> espera selector de RUTs
  -> selecciona periodo si corresponde
  -> selecciona cada RUT
  -> consulta documentos
  -> procesa documentos aceptados
  -> procesa documentos pendientes
  -> retorna DataFrame crudo
```

---

## Documentos procesados

El scraper procesa documentos aceptados y pendientes.

### Documentos aceptados

* Factura Electrónica.
* Factura no Afecta o Exenta Electrónica.
* Nota de Crédito Electrónica.

Estados usados:

```txt
accepted
accepted_exempt
```

Tipos usados:

```txt
invoice
credit_note
```

---

### Documentos pendientes

* Factura Electrónica pendiente.
* Factura no Afecta o Exenta Electrónica pendiente.
* Nota de Crédito Electrónica pendiente.

Estados usados:

```txt
pending
pending_exempt
```

Tipos usados:

```txt
invoice
credit_note
```

---

## Campos del DataFrame crudo

El scraper retorna un DataFrame con las siguientes columnas:

```txt
type_purchase
supplier_id
supplier_name
number
date
date_accepted
type
exent_total
net_total
iva
other_tax
iva_not
code_iva_not
total
total_activo
iva_activo
iva_comun
tax_no_credit
iva_no_retenido
type_document_ref
folio_ref
tabaco_puro
tabaco_cigarrillos
tabaco_elaborado
nce_or_nde
rut_holding
status
doc_type
```

---

## Campos finales normalizados

Después de pasar por `InvoiceTransformer`, se conservan principalmente:

```txt
supplier_id
supplier_name
number
date
date_accepted
type
exent_total
net_total
iva
other_tax
total
rut_holding
status
doc_type
sii_user
```

---

## Normalización de datos

El transformer realiza las siguientes operaciones:

* conserva solo las columnas necesarias;
* reemplaza puntos en campos de texto;
* transforma textos a minúsculas;
* convierte `supplier_id` a mayúsculas;
* convierte fechas desde formato SII a `datetime`;
* localiza fechas en zona horaria `America/Santiago`;
* convierte fechas a UTC;
* convierte montos a enteros;
* reemplaza valores vacíos por cero;
* transforma tipo `"p"` a `"contado"`.

---

## Sincronización con MongoDB

La colección utilizada es:

```txt
invoices_supplier
```

La sincronización usa como filtro:

```py
{
    "supplier_id": row["supplier_id"],
    "number": row["number"],
}
```

Si la factura ya existe:

```txt
actualiza status
```

Si la factura no existe:

```txt
inserta documento completo
```

---

## Archivo de progreso

El scraper usa un archivo temporal para evitar reprocesar usuarios dentro de una misma corrida:

```txt
sii_progress.txt
```

Ejemplo:

```txt
11111111-1
22222222-2
```

Si un usuario ya fue marcado como completado, el runner lo omite.

Al finalizar correctamente el proceso, el archivo se elimina.

---

## `.gitignore` recomendado

```gitignore
.env
sii_progress.txt
__pycache__/
*.pyc
.DS_Store
```

---

## Logs

El scraper registra mensajes para:

* inicio de navegación;
* ingreso al Registro de Compras y Ventas;
* RUT actualmente procesado;
* documentos no disponibles;
* tablas sin datos pendientes;
* clics interceptados;
* errores por timeout;
* errores por RUT;
* errores fatales;
* cierre de sesión;
* cierre del navegador.

---

## Consideraciones importantes

* El portal SII puede cambiar su HTML, por lo que los selectores Selenium podrían requerir ajustes.
* El modo certificado depende del comportamiento del navegador y del certificado instalado localmente.
* Si `HEADLESS=true` falla por temas del portal o certificado, probar con `HEADLESS=false`.
* Si el scraper falla antes de terminar, el archivo `sii_progress.txt` permite retomar evitando usuarios ya completados.
* Si falla un RUT específico, el scraper continúa con el siguiente.
* Si ocurre un error fatal, `scrape_all()` retorna los datos parciales obtenidos hasta ese momento.

---

## Problemas comunes

### No se encontraron credenciales SII

Verificar que existan pares válidos:

```env
SII_USER_1=11111111-1
SII_PASS_1=password1
```

Cada usuario debe tener su contraseña con el mismo índice.

---

### No se cargaron las opciones de RUT

Puede ocurrir si:

* las credenciales son incorrectas;
* el SII cambió el flujo de login;
* el usuario no tiene empresas asociadas;
* el portal está lento;
* el navegador no terminó de cargar correctamente.

---

### Error con certificado digital

Si el flujo con certificado falla, probar primero con:

```env
USE_CERTIFICATE=false
```

o ejecutar con navegador visible:

```env
HEADLESS=false
```

---

### Chrome no inicia

Verificar que Google Chrome esté instalado.

`webdriver-manager` descarga automáticamente el driver compatible, pero Chrome debe existir en el sistema.

---

### Facturas duplicadas

El repositorio evita duplicados usando:

```txt
supplier_id + number
```

Si ya existe una factura, solo actualiza el campo `status`.

---

## Seguridad

No subir `.env` al repositorio.

Las credenciales SII y la URI de MongoDB deben mantenerse fuera del historial de Git. Si una credencial fue subida accidentalmente, se debe rotar inmediatamente.
