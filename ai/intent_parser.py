"""
Parser de intenciones - Convierte lenguaje natural en acciones del sistema.
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
    CONTENEDORES = "contenedores"
    CONTENEDOR_CREAR = "contenedor_crear"
    CONTENEDOR_LISTAR = "contenedor_listar"
    CONTENEDOR_EDITAR = "contenedor_editar"
    CONTENEDOR_ELIMINAR = "contenedor_eliminar"
    ANALISIS_FINANCIERO = "analisis_financiero"
    CLARIFICATION = "clarification"
    UNKNOWN = "unknown"
    GREETING = "greeting"
    HELP = "help"


class IntentParser:
    """Parser que identifica intenciones y extrae parámetros del lenguaje natural."""
    
    # Patrones para reconocer intenciones
    INTENT_PATTERNS = {
        IntentType.BALANCE: [
            r"balance", r"saldo", r"saldos", r"cuanto hay", r"cuanto tengo",
            r"dinero disponible", r"estado de cajas", r"ver balance"
        ],
        IntentType.INGRESO: [
            r"ingreso", r"ingresar", r"entrada de dinero", r"recib[ií]", r"depositar",
            r"agregar dinero", r"sumar", r"añadir dinero"
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
            r"historial", r"movimientos", r"transacciones", r"últimos", r"recientes",
            r"actividad", r"registro"
        ],
        IntentType.STOCK: [
            r"stock", r"inventario", r"productos", r"mercanc[ií]a", r"existencias",
            r"que hay en stock", r"cuantos productos"
        ],
        IntentType.VENTA: [
            r"venta", r"vender", r"vend[ií]", r"vendido", r"cliente compr[oó]"
        ],
        IntentType.ENTRADA: [
            r"entrada", r"comprar", r"compra", r"compr[oó]", r"lleg[oó] mercanc[ií]a",
            r"nuevo producto", r"agregar producto"
        ],
        IntentType.GANANCIA: [
            r"ganancia", r"ganancias", r"utilidad", r"margen", r"beneficio",
            r"cuanto gan[oé]", r"rentabilidad"
        ],
        IntentType.CONSIGNAR: [
            r"consignar", r"consignaci[oó]n", r"dar a vendedor", r"prestar producto"
        ],
        IntentType.STOCK_CONSIGNADO: [
            r"stock consignado", r"productos consignados", r"que tiene.*vendedor"
        ],
        IntentType.EXPORTAR: [
            r"exportar", r"descargar", r"backup", r"respaldo", r"csv", r"excel"
        ],
        IntentType.CONTENEDORES: [
            r"contenedor", r"contenedores", r"gestionar contenedores"
        ],
        IntentType.CONTENEDOR_CREAR: [
            r"crear contenedor", r"nuevo contenedor", r"agregar contenedor",
            r"añadir contenedor", r"registrar contenedor"
        ],
        IntentType.CONTENEDOR_LISTAR: [
            r"listar contenedores", r"ver contenedores", r"mostrar contenedores",
            r"contenedores disponibles", r"todos los contenedores"
        ],
        IntentType.CONTENEDOR_EDITAR: [
            r"editar contenedor", r"renombrar contenedor", r"cambiar nombre contenedor",
            r"modificar contenedor", r"actualizar contenedor"
        ],
        IntentType.CONTENEDOR_ELIMINAR: [
            r"eliminar contenedor", r"borrar contenedor", r"quitar contenedor",
            r"eliminar.*contenedor", r"borrar.*contenedor"
        ],
        IntentType.GREETING: [
            r"hola", r"buenos d[ií]as", r"buenas tardes", r"buenas noches",
            r"saludos", r"hey", r"hi"
        ],
        IntentType.HELP: [
            r"ayuda", r"help", r"que puedo hacer", r"comandos", r"como funciona"
        ],
        IntentType.ANALISIS_FINANCIERO: [
            r"an[aá]lisis", r"analizar", r"resumen financiero", r"estado del negocio",
            r"c[oó]mo va el negocio", r"c[oó]mo estamos", r"dashboard", r"reporte inteligente",
            r"tendencias", r"insight", r"como vamos", r"asesor[ií]a"
        ],
    }
    
    # Patrones para extraer valores
    MONEDA_PATTERNS = {
        "usd": [r"\busd\b", r"\bd[oó]lar", r"\bd[oó]lares", r"\b\$"],
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
        Parsea el texto y retorna la intención y parámetros extraídos.
        
        Returns:
            Tuple de (IntentType, dict con parámetros)
        """
        text_lower = text.lower().strip()
        
        # Detectar intención
        intent = cls._detect_intent(text_lower)
        
        # Extraer parámetros según la intención
        params = cls._extract_parameters(text_lower, intent)
        
        return intent, params
    
    @classmethod
    def _detect_intent(cls, text: str) -> IntentType:
        """Detecta la intención principal del texto."""
        # Prioridad: intenciones específicas primero, luego genéricas
        # Orden de prioridad (de más específico a menos específico)
        priority_order = [
            IntentType.CONTENEDOR_CREAR,
            IntentType.CONTENEDOR_EDITAR,
            IntentType.CONTENEDOR_ELIMINAR,
            IntentType.CONTENEDOR_LISTAR,
            IntentType.CONTENEDORES,  # Genérico al final
        ]
        
        # Primero verificar intenciones específicas en orden de prioridad
        for intent_type in priority_order:
            if intent_type in cls.INTENT_PATTERNS:
                for pattern in cls.INTENT_PATTERNS[intent_type]:
                    if re.search(pattern, text, re.IGNORECASE):
                        return intent_type
        
        # Si no se encontró intención específica de contenedores, buscar otras
        scores = {}
        
        for intent_type, patterns in cls.INTENT_PATTERNS.items():
            # Saltar las intenciones de contenedores ya que las procesamos arriba
            if intent_type in priority_order:
                continue
                
            score = 0
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 1
            if score > 0:
                scores[intent_type] = score
        
        if scores:
            # Retornar la intención con mayor score
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return IntentType.UNKNOWN
    
    @classmethod
    def _extract_parameters(cls, text: str, intent: IntentType) -> Dict[str, Any]:
        """Extrae parámetros del texto según la intención."""
        params = {}
        
        # Extraer números (montos, cantidades)
        # Buscar números con contexto (ej: "100 USD", "50 CUP", "2 unidades")
        number_patterns = [
            (r'(\d+\.?\d*)\s*(?:usd|d[oó]lar|d[oó]lares|\$)', 'monto_usd'),
            (r'(\d+\.?\d*)\s*(?:cup|peso|pesos)', 'monto_cup'),
            (r'(\d+\.?\d*)\s*(?:unidades?|u\.?|cantidad)', 'cantidad'),
            (r'(\d+\.?\d*)\s*(?:d[ií]a|d[ií]as)', 'dias'),
            (r'\b(\d+\.?\d*)\b', 'numero_generico'),  # Cualquier número
        ]
        
        numbers_found = {}
        for pattern, key in number_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    numbers_found[key] = float(matches[0])
                except ValueError:
                    pass
        
        # Asignar números según contexto
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
        elif 'dias' in numbers_found:
            params['dias'] = int(numbers_found['dias'])
        
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
        
        # Si hay traspaso, buscar caja destino
        if intent == IntentType.TRASPASO:
            # Buscar patrones como "de X a Y" o "desde X hacia Y"
            traspaso_match = re.search(r'(?:de|desde)\s+(\w+)\s+(?:a|hacia|para)\s+(\w+)', text, re.IGNORECASE)
            if traspaso_match:
                params['caja_origen'] = traspaso_match.group(1).lower()
                params['caja_destino'] = traspaso_match.group(2).lower()
        
        # Extraer códigos de producto (mayúsculas seguidas de números)
        codigo_match = re.search(r'\b[A-Z]+\d+\b', text.upper())
        if codigo_match:
            params['codigo'] = codigo_match.group()
        
        # Extraer nombres propios (vendedores, proveedores, nombres de contenedores)
        # Buscar nombres entre comillas o después de ciertas palabras clave
        nombre_patterns = [
            r'(?:nombre|llamado|llamada|de nombre)\s+["\']?([^"\']+?)(?:\s|$|,|\.)',
            r'(?:contenedor|nombre)\s+["\']?([A-Za-z][a-zA-Z0-9\s]+?)(?:\s|$|,|\.)',
            r'(?:crear|nuevo|agregar|añadir)\s+(?:contenedor\s+)?(?:llamado\s+)?["\']?([A-Za-z][a-zA-Z0-9\s]+?)(?:\s|$|,|\.)',
        ]
        
        for pattern in nombre_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                nombre = match.group(1).strip()
                # Limpiar el nombre de espacios extra y caracteres no deseados
                nombre = re.sub(r'\s+', ' ', nombre).strip()
                if len(nombre) > 0 and nombre.lower() not in ['contenedor', 'contenedores', 'de', 'nombre']:
                    params['nombre'] = nombre
                    params['actor'] = nombre  # También como actor para compatibilidad
                    break
        
        # Si no se encontró nombre, buscar la última palabra después de "nombre" o "llamado"
        if 'nombre' not in params:
            # Buscar patrones como "nombre X" o "llamado X"
            last_word_match = re.search(r'(?:nombre|llamado|llamada)\s+([a-zA-Z0-9]+)', text, re.IGNORECASE)
            if last_word_match:
                nombre = last_word_match.group(1).strip()
                if nombre.lower() not in ['contenedor', 'contenedores', 'de']:
                    params['nombre'] = nombre
                    params['actor'] = nombre
        
        # Si aún no se encontró, buscar palabras en mayúsculas o cualquier palabra después de ciertos verbos
        if 'nombre' not in params:
            # Para crear contenedor, buscar la palabra después de "crear contenedor"
            crear_match = re.search(r'crear\s+contenedor\s+(?:de\s+nombre\s+)?([a-zA-Z0-9]+)', text, re.IGNORECASE)
            if crear_match:
                nombre = crear_match.group(1).strip()
                params['nombre'] = nombre
                params['actor'] = nombre
        
        # Extraer descripción (texto después de ciertas palabras clave)
        desc_patterns = [
            r"(?:por|para|motivo|descripci[oó]n|nota|de|del|de la)\s+(.+)",
            r"['\"](.+?)['\"]"
        ]
        for pattern in desc_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                params['descripcion'] = match.group(1).strip()
                break
        
        # Para historial, extraer días
        if intent == IntentType.HISTORIAL:
            dias_match = re.search(r'(\d+)\s*(?:d[ií]a|d[ií]as)', text)
            if dias_match:
                params['dias'] = int(dias_match.group(1))
        
        # Para contenedores, extraer IDs y nombres
        if intent in (IntentType.CONTENEDOR_EDITAR, IntentType.CONTENEDOR_ELIMINAR):
            # Buscar ID numérico
            id_match = re.search(r'\b(\d+)\b', text)
            if id_match:
                params['id'] = int(id_match.group(1))
                params['cont_id'] = int(id_match.group(1))
        
        # Para editar, extraer "a" o "a" seguido de nuevo nombre
        if intent == IntentType.CONTENEDOR_EDITAR:
            # Buscar patrones como "contenedor X a Y" o "renombrar X como Y"
            edit_patterns = [
                r'(?:contenedor|id)\s+(\d+)\s+(?:a|como|por)\s+([A-Z][a-zA-Z0-9\s]+)',
                r'(?:contenedor|nombre)\s+([A-Z][a-zA-Z0-9\s]+)\s+(?:a|como|por)\s+([A-Z][a-zA-Z0-9\s]+)',
                r'(?:renombrar|cambiar|editar).*?(?:a|como|por)\s+([A-Z][a-zA-Z0-9\s]+)',
            ]
            for pattern in edit_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    if len(match.groups()) == 2:
                        # Dos grupos: origen y destino
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

