"""
Parser de intenciones - Convierte lenguaje natural en actions del sistema.
"""
import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Tipos de intenciones que el sistema puede reconocer."""
    BALANCE = "balance"
    INGRESO = "ingreso"
    GASTO = "gasto"
    TRASPASO = "traspaso"
    DEUDAS = "deudas"
    HISTORIAL = "historial"
    STOCK = "stock"
    VENTA = "venta"
    ENTRADA = "entrada"
    GANANCIA = "ganancia"
    CONSIGNAR = "consignar"
    STOCK_CONSIGNADO = "stock_consignado"
    EXPORTAR = "exportar"
    CONTENEDORES = "containeres"
    CONTENEDOR_CREAR = "container_create"
    CONTENEDOR_LISTAR = "container_listar"
    CONTENEDOR_EDITAR = "container_editar"
    CONTENEDOR_ELIMINAR = "container_delete"
    ANALISIS_FINANCIERO = "analisis_financiero"
    CLARIFICATION = "clarification"
    UNKNOWN = "unknown"
    GREETING = "greeting"
    HELP = "help"


class IntentParser:
    """Parser que identifica intenciones y extrae parametros del lenguaje natural."""
    
    # Patrones para reconocer intenciones
    INTENT_PATTERNS = {
        IntentType.BALANCE: [
            r"balance", r"saldo", r"saldos", r"cuanto hay", r"cuanto tengo",
            r"dinero disponible", r"estado de cajas", r"ver balance"
        ],
        IntentType.INGRESO: [
            r"ingreso", r"ingresar", r"cash intake", r"recib[ii]", r"depositar",
            r"agregar dinero", r"sumar", r"anadir dinero"
        ],
        IntentType.GASTO: [
            r"gasto", r"gastar", r"pagar", r"salida", r"egreso", r"desembolsar",
            r"quitar dinero", r"restar", r"pago de"
        ],
        IntentType.TRASPASO: [
            r"traspaso", r"transferir", r"mover", r"cambio", r"pasar de", r"de.*a",
            r"convertir", r"cambiar de"
        ],
        IntentType.DEUDAS: [
            r"deuda", r"deudas", r"cuentas por pagar", r"cuentas por cobrar",
            r"proveedores", r"vendedores", r"quien debe", r"quien me debe"
        ],
        IntentType.HISTORIAL: [
            r"historial", r"movimientos", r"transactions", r"ultimos", r"recientes",
            r"actividad", r"registro"
        ],
        IntentType.STOCK: [
            r"stock", r"inventario", r"productos", r"mercanc[ii]a", r"existencias",
            r"que hay en stock", r"cuantos productos"
        ],
        IntentType.VENTA: [
            r"venta", r"vender", r"vend[ii]", r"vendido", r"cliente compr[oo]"
        ],
        IntentType.ENTRADA: [
            r"entrada", r"comprar", r"compra", r"compr[oo]", r"lleg[oo] mercanc[ii]a",
            r"nuevo producto", r"agregar producto"
        ],
        IntentType.GANANCIA: [
            r"ganancia", r"ganancias", r"utilidad", r"margen", r"beneficio",
            r"cuanto gan[oe]", r"rentabilidad"
        ],
        IntentType.CONSIGNAR: [
            r"consignar", r"consignaci[oo]n", r"dar a vendedor", r"prestar producto"
        ],
        IntentType.STOCK_CONSIGNADO: [
            r"stock consignado", r"productos consignados", r"que tiene.*vendedor"
        ],
        IntentType.EXPORTAR: [
            r"exportar", r"descargar", r"backup", r"respaldo", r"csv", r"excel"
        ],
        IntentType.CONTENEDORES: [
            r"container", r"containeres", r"gestionar containeres"
        ],
        IntentType.CONTENEDOR_CREAR: [
            r"create container", r"nuevo container", r"agregar container",
            r"anadir container", r"registrar container"
        ],
        IntentType.CONTENEDOR_LISTAR: [
            r"listar containeres", r"ver containeres", r"mostrar containeres",
            r"containeres disponibles", r"todos los containeres"
        ],
        IntentType.CONTENEDOR_EDITAR: [
            r"editar container", r"renombrar container", r"cambiar nombre container",
            r"modificar container", r"update container"
        ],
        IntentType.CONTENEDOR_ELIMINAR: [
            r"delete container", r"borrar container", r"quitar container",
            r"delete.*container", r"borrar.*container"
        ],
        IntentType.GREETING: [
            r"hola", r"buenos d[ii]as", r"buenas tardes", r"buenas noches",
            r"saludos", r"hey", r"hi"
        ],
        IntentType.HELP: [
            r"ayuda", r"help", r"que puedo hacer", r"comandos", r"como funciona"
        ],
        IntentType.ANALISIS_FINANCIERO: [
            r"an[aa]lisis", r"analizar", r"resumen financiero", r"estado del negocio",
            r"c[oo]mo va el negocio", r"c[oo]mo estamos", r"dashboard", r"reporte inteligente",
            r"tendencias", r"insight", r"como vamos", r"asesor[ii]a"
        ],
    }
    
    # Patrones para extraer valores
    MONEDA_PATTERNS = {
        "usd": [r"\busd\b", r"\bd[oo]lar", r"\bd[oo]lares", r"\b\$"],
        "cup": [r"\bcup\b", r"\bpeso", r"\bpesos", r"\bcubano"],
        "cup-t": [r"cup-t", r"transferible", r"cup transferible"]
    }
    
    CAJA_PATTERNS = {
        "cfg": [r"\bcfg\b"],
        "sc": [r"\bsc\b"],
        "trd": [r"\btrd\b"]
    }
    
    @classmethod
    def parse_intent(cls, text: str) -> Tuple[IntentType, Dict[str, Any]]:
        """
        Parsea el texto y retorna la intencion y parametros extraidos.
        
        Returns:
            Tuple de (IntentType, dict con parametros)
        """
        text_lower = text.lower().strip()
        
        # Detectar intencion
        intent = cls._detect_intent(text_lower)
        
        # Extraer parametros segun la intencion
        params = cls._extract_parameters(text_lower, intent)
        
        return intent, params
    
    @classmethod
    def _detect_intent(cls, text: str) -> IntentType:
        """Detecta la intencion principal del texto."""
        # Prioridad: intenciones especificas primero, luego genericas
        # Orden de prioridad (de mas especifico a menos especifico)
        priority_order = [
            IntentType.CONTENEDOR_CREAR,
            IntentType.CONTENEDOR_EDITAR,
            IntentType.CONTENEDOR_ELIMINAR,
            IntentType.CONTENEDOR_LISTAR,
            IntentType.CONTENEDORES,  # Generico al final
        ]
        
        # Primero verificar intenciones especificas en orden de prioridad
        for intent_type in priority_order:
            if intent_type in cls.INTENT_PATTERNS:
                for pattern in cls.INTENT_PATTERNS[intent_type]:
                    if re.search(pattern, text, re.IGNORECASE):
                        return intent_type
        
        # If no specific container intent is found, evaluate other intents
        scores = {}
        
        for intent_type, patterns in cls.INTENT_PATTERNS.items():
            # Skip container intents since they were already processed above
            if intent_type in priority_order:
                continue
                
            score = 0
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 1
            if score > 0:
                scores[intent_type] = score
        
        if scores:
            # Retornar la intencion con mayor score
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return IntentType.UNKNOWN
    
    @classmethod
    def _extract_parameters(cls, text: str, intent: IntentType) -> Dict[str, Any]:
        """Extrae parametros del texto segun la intencion."""
        params = {}
        
        # Extraer numeros (montos, cantidades)
        # Buscar numeros con contexto (ej: "100 USD", "50 CUP", "2 unidades")
        number_patterns = [
            (r'(\d+\.?\d*)\s*(?:usd|d[oo]lar|d[oo]lares|\$)', 'monto_usd'),
            (r'(\d+\.?\d*)\s*(?:cup|peso|pesos)', 'monto_cup'),
            (r'(\d+\.?\d*)\s*(?:unidades?|u\.?|cantidad)', 'cantidad'),
            (r'(\d+\.?\d*)\s*(?:d[ii]a|d[ii]as)', 'days'),
            (r'\b(\d+\.?\d*)\b', 'numero_generico'),  # Cualquier numero
        ]
        
        numbers_found = {}
        for pattern, key in number_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    numbers_found[key] = float(matches[0])
                except ValueError:
                    pass
        
        # Asignar numeros segun contexto
        if 'monto_usd' in numbers_found:
            params['monto'] = numbers_found['monto_usd']
            params['moneda'] = 'usd'
        elif 'monto_cup' in numbers_found:
            params['monto'] = numbers_found['monto_cup']
            params['moneda'] = 'cup'
        elif 'numero_generico' in numbers_found:
            params['monto'] = numbers_found['numero_generico']
        
        if 'cantidad' in numbers_found:
            params['cantidad'] = numbers_found['cantidad']
        elif 'days' in numbers_found:
            params['days'] = int(numbers_found['days'])
        
        # Extraer moneda
        for moneda, patterns in cls.MONEDA_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    params['moneda'] = moneda
                    break
            if 'moneda' in params:
                break
        
        # Extraer caja (buscar patrones como "en CFG", "de SC", "a TRD")
        caja_patterns = [
            (r'(?:en|de|a|desde|hacia)\s+(cfg|sc|trd)', 'caja_directa'),
            (r'\b(cfg|sc|trd)\b', 'caja_simple'),
        ]
        
        for pattern, _ in caja_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                params['caja'] = match.group(1).lower()
                break
        
        # Si hay traspaso, buscar caja destination
        if intent == IntentType.TRASPASO:
            # Buscar patrones como "de X a Y" o "desde X hacia Y"
            traspaso_match = re.search(r'(?:de|desde)\s+(\w+)\s+(?:a|hacia|para)\s+(\w+)', text, re.IGNORECASE)
            if traspaso_match:
                params['caja_source'] = traspaso_match.group(1).lower()
                params['caja_destination'] = traspaso_match.group(2).lower()
        
        # Extraer codigos de producto (mayusculas seguidas de numeros)
        codigo_match = re.search(r'\b[A-Z]+\d+\b', text.upper())
        if codigo_match:
            params['codigo'] = codigo_match.group()
        
        # Extraer nombres propios (vendedores, proveedores, nombres de containeres)
        # Buscar nombres entre comillas o despues de ciertas palabras clave
        nombre_patterns = [
            r'(?:nombre|llamado|llamada|de nombre)\s+["\']?([^"\']+?)(?:\s|$|,|\.)',
            r'(?:container|nombre)\s+["\']?([A-Za-z][a-zA-Z0-9\s]+?)(?:\s|$|,|\.)',
            r'(?:create|nuevo|agregar|anadir)\s+(?:container\s+)?(?:llamado\s+)?["\']?([A-Za-z][a-zA-Z0-9\s]+?)(?:\s|$|,|\.)',
        ]
        
        for pattern in nombre_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                nombre = match.group(1).strip()
                # Limpiar el nombre de espacios extra y caracteres no deseados
                nombre = re.sub(r'\s+', ' ', nombre).strip()
                if len(nombre) > 0 and nombre.lower() not in ['container', 'containeres', 'de', 'nombre']:
                    params['nombre'] = nombre
                    params['actor'] = nombre  # Tambien como actor para compatibilidad
                    break
        
        # If no name was found, search for the last word after "nombre" or "llamado"
        if 'nombre' not in params:
            # Look for patterns like "nombre X" or "llamado X"
            last_word_match = re.search(r'(?:nombre|llamado|llamada)\s+([a-zA-Z0-9]+)', text, re.IGNORECASE)
            if last_word_match:
                nombre = last_word_match.group(1).strip()
                if nombre.lower() not in ['container', 'containeres', 'de']:
                    params['nombre'] = nombre
                    params['actor'] = nombre
        
        # If still not found, search uppercase words or any word after certain verbs
        if 'nombre' not in params:
            # For create container, find the word after "create container"
            create_match = re.search(r'create\s+container\s+(?:de\s+nombre\s+)?([a-zA-Z0-9]+)', text, re.IGNORECASE)
            if create_match:
                nombre = create_match.group(1).strip()
                params['nombre'] = nombre
                params['actor'] = nombre
        
        # Extraer description (texto despues de ciertas palabras clave)
        desc_patterns = [
            r"(?:por|para|motivo|descripci[oo]n|nota|de|del|de la)\s+(.+)",
            r"['\"](.+?)['\"]"
        ]
        for pattern in desc_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                params['descripcion'] = match.group(1).strip()
                break
        
        # Para historial, extraer days
        if intent == IntentType.HISTORIAL:
            days_match = re.search(r'(\d+)\s*(?:d[ii]a|d[ii]as)', text)
            if days_match:
                params['days'] = int(days_match.group(1))
        
        # Para containeres, extraer IDs y nombres
        if intent in (IntentType.CONTENEDOR_EDITAR, IntentType.CONTENEDOR_ELIMINAR):
            # Buscar ID numerico
            id_match = re.search(r'\b(\d+)\b', text)
            if id_match:
                params['id'] = int(id_match.group(1))
                params['cont_id'] = int(id_match.group(1))
        
        # Para editar, extraer "a" o "a" seguido de nuevo nombre
        if intent == IntentType.CONTENEDOR_EDITAR:
            # Buscar patrones como "container X a Y" o "renombrar X como Y"
            edit_patterns = [
                r'(?:container|id)\s+(\d+)\s+(?:a|como|por)\s+([A-Z][a-zA-Z0-9\s]+)',
                r'(?:container|nombre)\s+([A-Z][a-zA-Z0-9\s]+)\s+(?:a|como|por)\s+([A-Z][a-zA-Z0-9\s]+)',
                r'(?:renombrar|cambiar|editar).*?(?:a|como|por)\s+([A-Z][a-zA-Z0-9\s]+)',
            ]
            for pattern in edit_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    if len(match.groups()) == 2:
                        # Dos grupos: source y destination
                        if match.group(1).isdigit():
                            params['id'] = int(match.group(1))
                            params['cont_id'] = int(match.group(1))
                        else:
                            params['nombre_actual'] = match.group(1).strip()
                        params['nuevo_nombre'] = match.group(2).strip()
                    else:
                        # Un grupo: solo nuevo nombre
                        params['nuevo_nombre'] = match.group(1).strip()
                    break
        
        return params

