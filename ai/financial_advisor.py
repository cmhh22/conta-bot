"""
Asesor Financiero con IA - Analiza datos del negocio y genera insights accionables.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from database.connection import get_db_connection
from database.repositories import MovimientoRepository, DeudaRepository
from services.contabilidad_service import ContabilidadService, DeudaService
from services.inventario_service import InventarioService
from utils.currency import convert_to_usd

logger = logging.getLogger(__name__)


class FinancialAdvisor:
    """Motor de analisis financiero inteligente."""

    @classmethod
    def generar_analisis(cls, tipo: str = "general") -> Dict[str, Any]:
        """Genera un analisis financiero completo."""
        dispatch = {
            "general": cls._analisis_general,
            "gastos": cls._analisis_gastos,
            "ingresos": cls._analisis_ingresos,
            "inventario": cls._analisis_inventario,
            "deudas": cls._analisis_deudas,
            "tendencias": cls._analisis_tendencias,
        }
        handler = dispatch.get(tipo, cls._analisis_general)
        return handler()

    @classmethod
    def _analisis_general(cls) -> Dict[str, Any]:
        """Dashboard ejecutivo del negocio."""
        balances = ContabilidadService.obtener_balance()
        deudas = DeudaService.obtener_deudas_pendientes()
        historial_7d = ContabilidadService.obtener_historial(7)
        historial_30d = ContabilidadService.obtener_historial(30)

        # Calcular totales en USD
        total_usd = 0.0
        for _caja, monedas in balances.items():
            for moneda, monto in monedas.items():
                total_usd += convert_to_usd(monto, moneda)

        # Metricas de actividad
        ingresos_7d = sum(
            m["monto"] for m in historial_7d
            if m["tipo"] == "ingreso" and m["moneda"] == "usd"
        )
        gastos_7d = sum(
            m["monto"] for m in historial_7d
            if m["tipo"] == "gasto" and m["moneda"] == "usd"
        )

        ingresos_30d = sum(
            convert_to_usd(m["monto"], m["moneda"])
            for m in historial_30d
            if m["tipo"] in ("ingreso", "venta")
        )
        gastos_30d = sum(
            convert_to_usd(m["monto"], m["moneda"])
            for m in historial_30d
            if m["tipo"] == "gasto"
        )

        # Deudas
        total_por_pagar = sum(
            convert_to_usd(d["monto"], d["moneda"]) for d in deudas.get("por_pagar", [])
        )
        total_por_cobrar = sum(
            convert_to_usd(d["monto"], d["moneda"]) for d in deudas.get("por_cobrar", [])
        )

        # Alertas
        alertas = cls._generar_alertas(balances, deudas, historial_7d)

        # Ganancias
        try:
            ganancias = InventarioService.calcular_ganancias()
        except Exception:
            ganancias = {"margen_bruto_usd": 0, "ingresos_total_usd": 0, "costos_total_usd": 0}

        mensaje = "📊 <b>ANALISIS FINANCIERO INTELIGENTE</b>\n"
        mensaje += "━" * 30 + "\n\n"

        # Resumen ejecutivo
        mensaje += "💼 <b>Resumen Ejecutivo</b>\n"
        mensaje += f"  Capital total: <b>{total_usd:,.2f} USD</b>\n"
        mensaje += f"  Ganancia acumulada: <b>{ganancias['margen_bruto_usd']:,.2f} USD</b>\n\n"

        # Flujo de caja (7 dias)
        flujo_neto = ingresos_7d - gastos_7d
        emoji_flujo = "📈" if flujo_neto >= 0 else "📉"
        mensaje += f"💰 <b>Flujo de Caja (7 dias)</b>\n"
        mensaje += f"  🟢 Ingresos: +{ingresos_7d:,.2f} USD\n"
        mensaje += f"  🔴 Gastos: -{gastos_7d:,.2f} USD\n"
        mensaje += f"  {emoji_flujo} Neto: <b>{flujo_neto:+,.2f} USD</b>\n\n"

        # Flujo mensual
        flujo_mensual = ingresos_30d - gastos_30d
        emoji_mes = "📈" if flujo_mensual >= 0 else "📉"
        mensaje += f"📅 <b>Flujo Mensual (30 dias)</b>\n"
        mensaje += f"  {emoji_mes} Ingresos: {ingresos_30d:,.2f} USD\n"
        mensaje += f"  {emoji_mes} Gastos: {gastos_30d:,.2f} USD\n"
        mensaje += f"  {emoji_mes} Neto: <b>{flujo_mensual:+,.2f} USD</b>\n\n"

        # Deudas
        mensaje += "📋 <b>Posicion de Deudas</b>\n"
        mensaje += f"  ❌ Por pagar: {total_por_pagar:,.2f} USD\n"
        mensaje += f"  ✅ Por cobrar: {total_por_cobrar:,.2f} USD\n"
        posicion_neta = total_por_cobrar - total_por_pagar
        emoji_deuda = "✅" if posicion_neta >= 0 else "⚠️"
        mensaje += f"  {emoji_deuda} Posicion neta: <b>{posicion_neta:+,.2f} USD</b>\n\n"

        # Alertas
        if alertas:
            mensaje += "🚨 <b>Alertas</b>\n"
            for alerta in alertas:
                mensaje += f"  {alerta}\n"
            mensaje += "\n"

        # Recomendaciones
        recomendaciones = cls._generar_recomendaciones(
            total_usd, flujo_neto, total_por_pagar, total_por_cobrar, gastos_30d, ingresos_30d
        )
        if recomendaciones:
            mensaje += "💡 <b>Recomendaciones</b>\n"
            for rec in recomendaciones:
                mensaje += f"  {rec}\n"

        return {
            "success": True,
            "message": mensaje,
            "data": {
                "total_usd": total_usd,
                "flujo_7d": flujo_neto,
                "flujo_30d": flujo_mensual,
                "por_pagar": total_por_pagar,
                "por_cobrar": total_por_cobrar,
            },
        }

    @classmethod
    def _analisis_gastos(cls) -> Dict[str, Any]:
        """Analisis detallado de gastos."""
        historial = ContabilidadService.obtener_historial(30)
        gastos = [m for m in historial if m["tipo"] == "gasto"]

        if not gastos:
            return {
                "success": True,
                "message": "📊 No gastos registrados en los ultimos 30 dias.",
            }

        total_usd = sum(convert_to_usd(g["monto"], g["moneda"]) for g in gastos)
        promedio_diario = total_usd / 30

        # Agrupar por description (categorias)
        categorias: Dict[str, float] = {}
        for g in gastos:
            desc = g["descripcion"].split()[0] if g["descripcion"] else "Otros"
            categorias[desc] = categorias.get(desc, 0) + convert_to_usd(g["monto"], g["moneda"])

        top_categorias = sorted(categorias.items(), key=lambda x: x[1], reverse=True)[:5]

        # Comparar semanas
        ahora = datetime.now()
        hace_7 = ahora - timedelta(days=7)
        hace_14 = ahora - timedelta(days=14)

        gastos_semana_actual = sum(
            convert_to_usd(g["monto"], g["moneda"])
            for g in gastos
            if _parse_fecha(g["fecha"]) >= hace_7
        )
        gastos_semana_anterior = sum(
            convert_to_usd(g["monto"], g["moneda"])
            for g in gastos
            if hace_14 <= _parse_fecha(g["fecha"]) < hace_7
        )

        mensaje = "💸 <b>ANALISIS DE GASTOS (30 dias)</b>\n"
        mensaje += "━" * 30 + "\n\n"
        mensaje += f"💰 Total gastado: <b>{total_usd:,.2f} USD</b>\n"
        mensaje += f"📊 Promedio diario: {promedio_diario:,.2f} USD\n"
        mensaje += f"📅 Operaciones: {len(gastos)}\n\n"

        # Tendencia semanal
        if gastos_semana_anterior > 0:
            cambio = ((gastos_semana_actual - gastos_semana_anterior) / gastos_semana_anterior) * 100
            emoji = "📈" if cambio > 0 else "📉"
            mensaje += f"📊 <b>Tendencia Semanal</b>\n"
            mensaje += f"  Esta semana: {gastos_semana_actual:,.2f} USD\n"
            mensaje += f"  Semana anterior: {gastos_semana_anterior:,.2f} USD\n"
            mensaje += f"  {emoji} Cambio: {cambio:+.1f}%\n\n"

        # Top categorias
        if top_categorias:
            mensaje += "📋 <b>Principales Categorias</b>\n"
            for i, (cat, monto) in enumerate(top_categorias, 1):
                pct = (monto / total_usd * 100) if total_usd > 0 else 0
                barra = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                mensaje += f"  {i}. {cat}: {monto:,.2f} USD ({pct:.0f}%)\n"
                mensaje += f"     {barra}\n"

        return {"success": True, "message": mensaje}

    @classmethod
    def _analisis_ingresos(cls) -> Dict[str, Any]:
        """Analisis detallado de ingresos."""
        historial = ContabilidadService.obtener_historial(30)
        ingresos = [m for m in historial if m["tipo"] in ("ingreso", "venta")]

        if not ingresos:
            return {
                "success": True,
                "message": "📊 No ingresos registrados en los ultimos 30 dias.",
            }

        total_usd = sum(convert_to_usd(i["monto"], i["moneda"]) for i in ingresos)
        ventas = [i for i in ingresos if i["tipo"] == "venta"]
        otros = [i for i in ingresos if i["tipo"] == "ingreso"]

        mensaje = "💰 <b>ANALISIS DE INGRESOS (30 dias)</b>\n"
        mensaje += "━" * 30 + "\n\n"
        mensaje += f"💵 Total ingresos: <b>{total_usd:,.2f} USD</b>\n"
        mensaje += f"🛒 Por ventas: {sum(convert_to_usd(v['monto'], v['moneda']) for v in ventas):,.2f} USD\n"
        mensaje += f"💲 Otros ingresos: {sum(convert_to_usd(o['monto'], o['moneda']) for o in otros):,.2f} USD\n"
        mensaje += f"📅 Operaciones: {len(ingresos)}\n\n"

        # Promedio
        promedio_diario = total_usd / 30
        mensaje += f"📊 Promedio diario: {promedio_diario:,.2f} USD\n"
        mensaje += f"📊 Promedio por operation: {total_usd / len(ingresos):,.2f} USD\n"

        return {"success": True, "message": mensaje}

    @classmethod
    def _analisis_inventario(cls) -> Dict[str, Any]:
        """Analisis del estado del inventario."""
        productos = InventarioService.obtener_stock()

        if not productos:
            return {"success": True, "message": "📦 El inventario esta empty."}

        total_valor = sum(
            p["stock"] * p["costo_unitario"] for p in productos
        )
        total_items = sum(p["stock"] for p in productos)

        # Productos con bajo stock (menos de 5 unidades)
        bajo_stock = [p for p in productos if p["stock"] < 5]

        # Productos mas valiosos
        productos_valor = sorted(
            productos,
            key=lambda p: p["stock"] * p["costo_unitario"],
            reverse=True,
        )[:5]

        mensaje = "📦 <b>ANALISIS DE INVENTARIO</b>\n"
        mensaje += "━" * 30 + "\n\n"
        mensaje += f"📊 Productos distintos: {len(productos)}\n"
        mensaje += f"📦 Total unidades: {total_items:,.0f}\n"
        mensaje += f"💰 Valor del inventario: ~{total_valor:,.2f} USD\n\n"

        if bajo_stock:
            mensaje += "⚠️ <b>Alerta de Stock Bajo</b>\n"
            for p in bajo_stock:
                emoji = "🔴" if p["stock"] <= 1 else "🟡"
                mensaje += f"  {emoji} {p['codigo']}: {p['stock']:.0f} unidades\n"
            mensaje += "\n"

        if productos_valor:
            mensaje += "💎 <b>Productos Mas Valiosos</b>\n"
            for p in productos_valor:
                valor = p["stock"] * p["costo_unitario"]
                mensaje += f"  • {p['codigo']}: {valor:,.2f} USD ({p['stock']:.0f} u. × {p['costo_unitario']:.2f})\n"

        return {"success": True, "message": mensaje}

    @classmethod
    def _analisis_deudas(cls) -> Dict[str, Any]:
        """Analisis detallado de deudas."""
        deudas = DeudaService.obtener_deudas_pendientes()

        por_pagar = deudas.get("por_pagar", [])
        por_cobrar = deudas.get("por_cobrar", [])

        if not por_pagar and not por_cobrar:
            return {"success": True, "message": "✅ No deudas pendientes. Excelente!"}

        total_pagar = sum(convert_to_usd(d["monto"], d["moneda"]) for d in por_pagar)
        total_cobrar = sum(convert_to_usd(d["monto"], d["moneda"]) for d in por_cobrar)

        mensaje = "📋 <b>ANALISIS DE DEUDAS</b>\n"
        mensaje += "━" * 30 + "\n\n"

        if por_pagar:
            mensaje += "❌ <b>Cuentas por Pagar</b>\n"
            # Agrupar por actor
            actores: Dict[str, float] = {}
            for d in por_pagar:
                actores[d["actor_id"]] = actores.get(d["actor_id"], 0) + convert_to_usd(
                    d["monto"], d["moneda"]
                )
            for actor, monto in sorted(actores.items(), key=lambda x: x[1], reverse=True):
                pct = (monto / total_pagar * 100) if total_pagar > 0 else 0
                mensaje += f"  • {actor}: {monto:,.2f} USD ({pct:.0f}%)\n"
            mensaje += f"  💰 <b>Total: {total_pagar:,.2f} USD</b>\n\n"

        if por_cobrar:
            mensaje += "✅ <b>Cuentas por Cobrar</b>\n"
            actores_cobrar: Dict[str, float] = {}
            for d in por_cobrar:
                actores_cobrar[d["actor_id"]] = actores_cobrar.get(d["actor_id"], 0) + convert_to_usd(
                    d["monto"], d["moneda"]
                )
            for actor, monto in sorted(actores_cobrar.items(), key=lambda x: x[1], reverse=True):
                mensaje += f"  • {actor}: {monto:,.2f} USD\n"
            mensaje += f"  💰 <b>Total: {total_cobrar:,.2f} USD</b>\n\n"

        posicion = total_cobrar - total_pagar
        emoji = "✅" if posicion >= 0 else "⚠️"
        mensaje += f"{emoji} <b>Posicion neta: {posicion:+,.2f} USD</b>\n"

        return {"success": True, "message": mensaje}

    @classmethod
    def _analisis_tendencias(cls) -> Dict[str, Any]:
        """Analisis de tendencias con comparacion temporal."""
        historial = ContabilidadService.obtener_historial(30)

        if not historial:
            return {"success": True, "message": "📊 No datos suficientes para analizar tendencias."}

        ahora = datetime.now()

        # Dividir en semanas
        semanas: Dict[int, Dict[str, float]] = {}
        for m in historial:
            fecha = _parse_fecha(m["fecha"])
            semana = (ahora - fecha).days // 7
            if semana not in semanas:
                semanas[semana] = {"ingresos": 0, "gastos": 0}
            monto_usd = convert_to_usd(m["monto"], m["moneda"])
            if m["tipo"] in ("ingreso", "venta"):
                semanas[semana]["ingresos"] += monto_usd
            elif m["tipo"] == "gasto":
                semanas[semana]["gastos"] += monto_usd

        mensaje = "📈 <b>ANALISIS DE TENDENCIAS</b>\n"
        mensaje += "━" * 30 + "\n\n"

        for semana in sorted(semanas.keys()):
            datos = semanas[semana]
            neto = datos["ingresos"] - datos["gastos"]
            emoji = "🟢" if neto >= 0 else "🔴"
            label = "Esta semana" if semana == 0 else f"Hace {semana} semana(s)"
            mensaje += f"{emoji} <b>{label}</b>\n"
            mensaje += f"  Ingresos: +{datos['ingresos']:,.2f} USD\n"
            mensaje += f"  Gastos: -{datos['gastos']:,.2f} USD\n"
            mensaje += f"  Neto: {neto:+,.2f} USD\n\n"

        # Tendencia general
        if len(semanas) >= 2:
            semana_actual = semanas.get(0, {"ingresos": 0, "gastos": 0})
            semana_ant = semanas.get(1, {"ingresos": 0, "gastos": 0})
            neto_actual = semana_actual["ingresos"] - semana_actual["gastos"]
            neto_ant = semana_ant["ingresos"] - semana_ant["gastos"]

            if neto_actual > neto_ant:
                mensaje += "📈 <b>Tendencia: MEJORANDO</b> - El flujo neto mejoro respecto a la semana anterior.\n"
            elif neto_actual < neto_ant:
                mensaje += "📉 <b>Tendencia: EN DESCENSO</b> - El flujo neto empeoro respecto a la semana anterior.\n"
            else:
                mensaje += "➡️ <b>Tendencia: ESTABLE</b> - El flujo se mantiene similar.\n"

        return {"success": True, "message": mensaje}

    @classmethod
    def _generar_alertas(
        cls, balances: Dict, deudas: Dict, historial: List
    ) -> List[str]:
        """Genera alertas basadas en el estado actual."""
        alertas = []

        # Alerta: cajas con saldo muy bajo
        for caja, monedas in balances.items():
            for moneda, saldo in monedas.items():
                if moneda == "usd" and saldo < 50:
                    alertas.append(f"⚠️ Caja {caja.upper()} tiene solo {saldo:.2f} USD")
                elif moneda == "cup" and saldo < 5000:
                    alertas.append(f"⚠️ Caja {caja.upper()} tiene solo {saldo:.2f} CUP")

        # Alerta: deudas grandes
        for d in deudas.get("por_pagar", []):
            if convert_to_usd(d["monto"], d["moneda"]) > 500:
                alertas.append(
                    f"🔴 Deuda grande con {d['actor_id']}: {d['monto']:,.2f} {d['moneda'].upper()}"
                )

        # Alerta: muchos gastos en poco tiempo
        gastos_recientes = [m for m in historial if m["tipo"] == "gasto"]
        if len(gastos_recientes) > 10:
            alertas.append(f"📊 Alto volumen de gastos: {len(gastos_recientes)} en 7 dias")

        # Alerta: productos con stock bajo
        try:
            productos = InventarioService.obtener_stock()
            bajo = [p for p in productos if p["stock"] <= 2]
            if bajo:
                codigos = ", ".join(p["codigo"] for p in bajo[:3])
                alertas.append(f"📦 Stock critico: {codigos}")
        except Exception:
            pass

        return alertas

    @classmethod
    def _generar_recomendaciones(
        cls,
        total_usd: float,
        flujo_neto: float,
        por_pagar: float,
        por_cobrar: float,
        gastos_30d: float,
        ingresos_30d: float,
    ) -> List[str]:
        """Genera recomendaciones basadas en los datos."""
        recs = []

        if flujo_neto < 0:
            recs.append("💡 Flujo negativo esta semana. Revisa los gastos no esenciales.")

        if por_pagar > total_usd * 0.5:
            recs.append("💡 Las deudas representan mas del 50% del capital. Prioriza pagos.")

        if por_cobrar > 0 and por_cobrar > por_pagar:
            recs.append("💡 Tienes mas por cobrar que por pagar. Gestiona los cobros pendientes.")

        if ingresos_30d > 0 and gastos_30d / ingresos_30d > 0.8:
            recs.append("💡 Los gastos son mas del 80% de los ingresos. Optimiza costos.")

        if total_usd > 1000 and flujo_neto > 0:
            recs.append("💡 Buen momento para invertir en inventario o expandir operaciones.")

        if not recs:
            recs.append("✅ El negocio muestra indicadores saludables. Sigue ayes!")

        return recs


def _parse_fecha(fecha_str: str) -> datetime:
    """Parsea una fecha de la base de datos."""
    try:
        return datetime.strptime(fecha_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return datetime.now()
