# SAP HANA Cloud Trial — Setup Completo
*Completado: 28 marzo 2026*

---

## Resumen

Integración entre **DesktopCommanderPy MCP Server** y **SAP HANA Cloud Free Tier** completada y verificada.

---

## Cuenta BTP Trial

| Campo | Valor |
|-------|-------|
| Global Account | `074356eftrial` |
| Subaccount | `trial` |
| Region | US East (VA) - AWS |
| User ID SAP | `P2011947838` |
| Email | `eduardo76@gmail.com` |
| URL Cockpit | https://cockpit.hanatrial.ondemand.com/trial |

---

## Instancia HANA Cloud — TestMCPs

| Campo | Valor |
|-------|-------|
| Nombre | `TestMCPs` |
| Tipo | SAP HANA Database |
| Plan | `hana-free` (Free Tier) |
| Version | 2026.2.5 (QRC 1/2026) |
| Internal version | 4.00.000.00.1773772603 |
| Runtime | Cloud Foundry |
| Availability Zone | us-east-1c |
| Memoria | 16 GB |
| Storage | 80 GB |
| Compute | 1 vCPU |
| Estado | Running |

---

## Conexion SQL

| Campo | Valor |
|-------|-------|
| Host | `20178d0a-d4af-4825-bba6-11a2aa151d20.hna1.prod-us10.hanacloud.ondemand.com` |
| Port | `443` |
| User | `DBADMIN` |
| Schema | `DBADMIN` |
| SSL/TLS | Enabled |

---

## AVISO Free Tier

La instancia se detiene automaticamente tras inactividad.
Para arrancarla:
1. https://cockpit.hanatrial.ondemand.com/trial
2. Subaccount trial -> Servicios -> Instancias y suscripciones
3. `...` junto a `TestMCPs` -> Open SAP HANA Cloud Central
4. Boton Start o `...` -> Start

---

## Configuracion MCP

### Opcion A - Variables de entorno (claude_desktop_config.json)

```json
"env": {
  "HANA_HOST": "20178d0a-d4af-4825-bba6-11a2aa151d20.hna1.prod-us10.hanacloud.ondemand.com",
  "HANA_PORT": "443",
  "HANA_USER": "DBADMIN",
  "HANA_PASSWORD": "<tu_password>",
  "HANA_SCHEMA": ""
}
```

### Opcion B - Fichero config/hana_config.yaml

Ver `config/hana_config.yaml.example` como plantilla.
El fichero real esta en .gitignore — nunca subir credenciales al repo.

---

## Tools HANA disponibles

| Tool | Descripcion | Estado |
|------|-------------|--------|
| `hana_test_connection` | Verifica credenciales, version, SSL | OK verificado |
| `hana_list_schemas` | Lista schemas visibles | OK verificado |
| `hana_execute_query` | SELECT/DML tabulado | OK disponible |
| `hana_execute_ddl` | CREATE/ALTER/DROP | OK disponible |
| `hana_describe_table` | Estructura columnas, tipos, PKs | OK disponible |
| `hana_get_row_count` | Cuenta filas sin full scan | OK disponible |
| `hana_list_tables` | Tablas y vistas de un schema | OK disponible |
| `hana_get_system_info` | Info sistema memoria/CPU | BUG - ver abajo |

### Bug conocido: hana_get_system_info

Query usa columna `ACTIVE_STATUS` inexistente en HANA 2026.2.5.
Pendiente fix en `core/tools/hana.py`.

---

## Verificacion real de conexion

```
Conexion exitosa a SAP HANA Cloud
  Host:    20178d0a-d4af-4825-bba6-11a2aa151d20.hna1.prod-us10.hanacloud.ondemand.com:443
  Usuario: DBADMIN
  Schema:  DBADMIN
  Version: 4.00.000.00.1773772603
  SSL/TLS: activado
```

---

## Schemas disponibles

| Schema | Owner | Sistema |
|--------|-------|---------|
| DBADMIN | DBADMIN | NO |
| SYS | SYS | SI |
| SYSTEM | SYSTEM | SI |
| _SYS_BI | SYS | SI |
| _SYS_DI | _SYS_DI | SI |
| _SYS_EPM | _SYS_EPM | SI |
| _SYS_HOST_SNAPSHOT | _SYS_HOST_SNAPSHOT | SI |
| _SYS_PLAN_STABILITY | _SYS_PLAN_STABILITY | SI |
| _SYS_REMOTE_CONTROLLER | SYS | SI |
| _SYS_SQL_ANALYZER | _SYS_SQL_ANALYZER | SI |
| _SYS_STATISTICS | _SYS_STATISTICS | SI |
| _SYS_TASK | _SYS_TASK | SI |

---

## Pendientes

- Fix bug hana_get_system_info (columna ACTIVE_STATUS)
- Reiniciar Claude Desktop para activar env vars del config.json
- Probar hana_execute_query con SELECT basico
- Crear tabla de prueba en schema DBADMIN
