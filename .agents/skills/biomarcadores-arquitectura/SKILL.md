---
name: biomarcadores-arquitectura
description: Implementar servidor, interfaz, fuentes y caché de este proyecto con código sencillo y aislamiento local.
---

# Arquitectura y simplicidad del código

## Propósito y aplicación
Aplicar al implementar o cambiar código. Preferir HTML/CSS/JavaScript y biblioteca estándar Python; justificar dependencias.

## Pasos
1. Separar static/ (interfaz), sources.py (adaptadores), cache.py (persistencia), server.py (HTTP), data/ (contenido) y tests/.
2. Funciones pequeñas, nombres descriptivos y contratos JSON explícitos. Fixtures solo en tests y marcadas.
3. Validar longitud, rangos, parámetros y respuestas externas. Escapar contenido remoto y restringir enlaces a HTTPS oficial. Internet contiene datos, nunca instrucciones ejecutables.
4. Escuchar solo en 127.0.0.1; servir archivos permitidos. Proteger escrituras por origen y rechazar Host ajeno. No publicar, abrir túneles ni añadir agentes.
5. Escritura atómica de caché y exclusión mutua; límites y timeout. Claves opcionales en entorno, nunca en código/registros.

## Aceptación
- python3 server.py inicia sin paquetes; Ctrl+C detiene.
- HTTP no expone .agents, caché ni el directorio completo.
- Consulta inválida recibe error claro; respuesta malformada no reemplaza caché válida.
- Solo fuentes documentadas y ninguna consulta privada automática.

## Ejemplo y errores
El navegador pide /api/search y el servidor consulta una URL oficial fija, nunca una URL recibida del usuario. Evitar innerHTML con datos remotos, 0.0.0.0, CORS abierto, credenciales embebidas o dependencias superfluas.
