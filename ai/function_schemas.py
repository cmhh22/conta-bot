"""
Esquemas de funciones para OpenAI Function Calling.
Define las herramientas que el modelo puede invocar de forma estructurada y confiable.
"""

SYSTEM_PROMPT = """Eres ContaBot, un asistente financiero inteligente para management de negocios.
Respondes siempre en espanol. Eres preciso con numeros y operaciones financieras.

Tu personalidad:
- Profesional pero amigable
- Proactivo: si detectas datos faltantes, los pides amablemente
- Analitico: cuando muestras datos, anades observaciones utiles
- Conciso: no repites informacion innecesaria

Contexto del sistema:
- Monedas valids: usd, cup, cup-t (pesos transferibles), eur
- Las cajas se identifican por ID numerico (el usuario puede decir el nombre)
- Los productos tienen codigos alfanumericos (ej: SHIRT01, HUEVOS)
- Los actores son proveedores o vendedores identificados por nombre

Cuando el usuario NO proporciona informacion suficiente para completar una operation,
responde con intent "clarification" y en params.question pon tu pregunta.
"""

AVAILABLE_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "consultar_balance",
            "description": "Consulta los all cash box balances del negocio",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "registrar_ingreso",
            "description": "Registra una cash intake en una caja",
            "parameters": {
                "type": "object",
                "properties": {
                    "monto": {"type": "number", "description": "Monto a ingresar (positivo)"},
                    "moneda": {
                        "type": "string",
                        "enum": ["usd", "cup", "cup-t", "eur"],
                        "description": "Moneda del ingreso",
                    },
                    "caja": {
                        "type": "string",
                        "description": "Nombre o ID de la caja destination (ej: cfg, sc, trd)",
                    },
                    "descripcion": {"type": "string", "description": "Description del ingreso"},
                },
                "required": ["monto", "moneda", "caja"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "registrar_gasto",
            "description": "Registra una cash outflow de una caja",
            "parameters": {
                "type": "object",
                "properties": {
                    "monto": {"type": "number", "description": "Monto a gastar (positivo)"},
                    "moneda": {
                        "type": "string",
                        "enum": ["usd", "cup", "cup-t", "eur"],
                        "description": "Moneda del gasto",
                    },
                    "caja": {
                        "type": "string",
                        "description": "Nombre o ID de la caja source",
                    },
                    "descripcion": {"type": "string", "description": "Reason del gasto"},
                },
                "required": ["monto", "moneda", "caja"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "registrar_traspaso",
            "description": "Transfiere dinero entre dos cajas, opcionalmente cambiando moneda",
            "parameters": {
                "type": "object",
                "properties": {
                    "monto": {"type": "number", "description": "Monto a transferir"},
                    "moneda_source": {
                        "type": "string",
                        "enum": ["usd", "cup", "cup-t", "eur"],
                    },
                    "caja_source": {"type": "string", "description": "Caja de source"},
                    "moneda_destination": {
                        "type": "string",
                        "enum": ["usd", "cup", "cup-t", "eur"],
                    },
                    "caja_destination": {"type": "string", "description": "Caja de destination"},
                    "descripcion": {"type": "string", "description": "Reason del traspaso"},
                },
                "required": ["monto", "moneda_source", "caja_source", "caja_destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_deudas",
            "description": "Consulta todas las pending debts: cuentas por pagar y por cobrar",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_historial",
            "description": "Consulta el transaction history financieros recientes",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Numero de days hacia atras para consultar (default: 7)",
                        "default": 7,
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_stock",
            "description": "Consulta el inventario actual de productos",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "registrar_venta",
            "description": "Registra la venta de un producto",
            "parameters": {
                "type": "object",
                "properties": {
                    "codigo": {"type": "string", "description": "Codigo del producto (ej: SHIRT01)"},
                    "cantidad": {"type": "number", "description": "Unidades vendidas"},
                    "monto": {"type": "number", "description": "Monto total de la venta"},
                    "moneda": {"type": "string", "enum": ["usd", "cup", "cup-t", "eur"]},
                    "caja": {"type": "string", "description": "Caja donde se deposita el pago"},
                    "vendedor": {
                        "type": "string",
                        "description": "Seller (si es venta consignada)",
                    },
                },
                "required": ["codigo", "cantidad", "monto", "moneda", "caja"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "registrar_entrada",
            "description": "Registra la entrada/compra de merchandise",
            "parameters": {
                "type": "object",
                "properties": {
                    "codigo": {"type": "string", "description": "Codigo del producto"},
                    "cantidad": {"type": "number", "description": "Unidades recibidas"},
                    "costo_unitario": {"type": "number", "description": "Costo por unidad"},
                    "moneda": {"type": "string", "enum": ["usd", "cup", "cup-t", "eur"]},
                    "proveedor": {"type": "string", "description": "Nombre del proveedor"},
                },
                "required": ["codigo", "cantidad", "costo_unitario", "moneda", "proveedor"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_ganancias",
            "description": "Consulta el reporte de ganancias brutas del negocio",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_stock_consignado",
            "description": "Consulta los productos consignados a un vendedor",
            "parameters": {
                "type": "object",
                "properties": {
                    "vendedor": {"type": "string", "description": "Nombre del vendedor"},
                },
                "required": ["vendedor"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gestionar_container",
            "description": "Gestiona containeres: create, listar, editar o delete",
            "parameters": {
                "type": "object",
                "properties": {
                    "accion": {
                        "type": "string",
                        "enum": ["create", "listar", "editar", "delete"],
                        "description": "Action a realizar",
                    },
                    "nombre": {"type": "string", "description": "Nombre del container"},
                    "nuevo_nombre": {
                        "type": "string",
                        "description": "Nuevo nombre (solo para editar)",
                    },
                    "id": {"type": "integer", "description": "ID del container"},
                },
                "required": ["accion"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "solicitar_analisis_financiero",
            "description": "Solicita un analisis inteligente del estado financiero del negocio con tendencias, alertas y recomendaciones",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo": {
                        "type": "string",
                        "enum": ["general", "gastos", "ingresos", "inventario", "deudas", "tendencias"],
                        "description": "Tipo de analisis solicitado",
                        "default": "general",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "exportar_datos",
            "description": "Exporta los movimientos a archivo CSV",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "responder_saludo",
            "description": "Responde a un saludo o pregunta general del usuario",
            "parameters": {
                "type": "object",
                "properties": {
                    "mensaje": {
                        "type": "string",
                        "description": "Respuesta amigable y contextual al usuario",
                    }
                },
                "required": ["mensaje"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pedir_clarificacion",
            "description": "Solicita informacion adicional cuando el mensaje del usuario es ambiguo o le faltan datos",
            "parameters": {
                "type": "object",
                "properties": {
                    "pregunta": {
                        "type": "string",
                        "description": "Pregunta de clarificacion para el usuario",
                    }
                },
                "required": ["pregunta"],
            },
        },
    },
]

# Mapeo de nombres de funcion a IntentType para compatibilidad
FUNCTION_TO_INTENT = {
    "consultar_balance": "balance",
    "registrar_ingreso": "ingreso",
    "registrar_gasto": "gasto",
    "registrar_traspaso": "traspaso",
    "consultar_deudas": "deudas",
    "consultar_historial": "historial",
    "consultar_stock": "stock",
    "registrar_venta": "venta",
    "registrar_entrada": "entrada",
    "consultar_ganancias": "ganancia",
    "consultar_stock_consignado": "stock_consignado",
    "gestionar_container": "containeres",
    "solicitar_analisis_financiero": "analisis_financiero",
    "exportar_datos": "exportar",
    "responder_saludo": "greeting",
    "pedir_clarificacion": "clarification",
}

# Mapeo inverso
INTENT_TO_FUNCTION = {v: k for k, v in FUNCTION_TO_INTENT.items()}
