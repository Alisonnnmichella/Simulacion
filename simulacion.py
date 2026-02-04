# simulador_mesa_ayuda.py
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional, List, Tuple, Callable, Dict


# ------------------------------------------------------------
# Constantes de tiempo (minutos absolutos)
# Día 0: 00:00 = 0
# Día 0: 09:00 = 540
# Día 0: 18:00 = 1080
# Día 1: 09:00 = 1980 (540 + 1440)
# ------------------------------------------------------------
MINUTOS_POR_DIA: int = 24 * 60
INICIO_TURNO_MIN: int = 9 * 60
FIN_TURNO_MIN: int = 18 * 60

HORIZONTE_VACIO: float = float("inf")  # HV: no hay salida programada


# ------------------------------------------------------------
# Funciones de horario laboral
# ------------------------------------------------------------
def normalizar_a_horario_laboral(tiempo_minutos: float) -> float:
    """
    Si 'tiempo_minutos' cae fuera de 9-18, lo mueve al próximo instante válido:
    - antes de 9:00 => 9:00 del mismo día
    - después de 18:00 => 9:00 del día siguiente
    """
    dia = int(tiempo_minutos // MINUTOS_POR_DIA)
    minuto_del_dia = tiempo_minutos % MINUTOS_POR_DIA

    if minuto_del_dia < INICIO_TURNO_MIN:
        return dia * MINUTOS_POR_DIA + INICIO_TURNO_MIN

    if minuto_del_dia >= FIN_TURNO_MIN:
        return (dia + 1) * MINUTOS_POR_DIA + INICIO_TURNO_MIN

    return tiempo_minutos


def sumar_minutos_laborales(tiempo_inicio_minutos: float, duracion_minutos: float) -> float:
    """
    Suma 'duracion_minutos' contando SOLO minutos dentro del horario 9-18.
    Si se llega al fin del turno, continúa al día siguiente 9:00.
    """
    tiempo_actual = normalizar_a_horario_laboral(tiempo_inicio_minutos)
    minutos_restantes = duracion_minutos

    while minutos_restantes > 0:
        dia = int(tiempo_actual // MINUTOS_POR_DIA)
        fin_hoy = dia * MINUTOS_POR_DIA + FIN_TURNO_MIN

        minutos_disponibles_hoy = fin_hoy - tiempo_actual
        if minutos_restantes <= minutos_disponibles_hoy:
            return tiempo_actual + minutos_restantes

        minutos_restantes -= minutos_disponibles_hoy
        tiempo_actual = (dia + 1) * MINUTOS_POR_DIA + INICIO_TURNO_MIN

    return tiempo_actual


def formatear_tiempo(tiempo_minutos: float) -> str:
    """
    Convierte minutos absolutos a un texto útil para debug: "Día X HH:MM".
    """
    dia = int(tiempo_minutos // MINUTOS_POR_DIA)
    minuto_del_dia = int(tiempo_minutos % MINUTOS_POR_DIA)
    hh = minuto_del_dia // 60
    mm = minuto_del_dia % 60
    return f"Día {dia} {hh:02d}:{mm:02d}"


# ------------------------------------------------------------
# Modelos
# ------------------------------------------------------------
@dataclass
class Trabajo:
    tiempo_arribo_minutos: float
    tipo_servicio: str                 # "IT" | "TEC" | "DEV"
    duracion_servicio_minutos: float       # sorteada al ARRIBO o PENDIENTE
    tomadoPorDev: bool = False          # si fue tomado por DEV


@dataclass
class ResultadoSimulacion:
    perdidos_por_tipo: Dict[str, int]
    atendidos_por_tipo: Dict[str, int]
    espera_promedio_por_tipo_min: Dict[str, float]


# ------------------------------------------------------------
# Simulador estilo cátedra (próximo evento)
# ------------------------------------------------------------
class SimuladorMesaAyuda:
    """
    Variables principales (como el diagrama):
    - T: tiempo actual
    - TPLL: tiempo del próximo arribo
    - TPSIT[i], TPSTEC[j], TPSDEVS[k]: tiempo fin del servicio del operador
      (HV cuando no tiene salida programada)
    Reglas:
    - Atender si hay operador libre.
    - Si no hay libre: agendar en un operador específico ocupado con slot libre (1 por operador).
    - Si no hay slot para agendar: se pierde.
    - Operador "libre" SOLO si no está atendiendo (TPS=HV) y no tiene trabajo asignado (slot None).
    """

    def __init__(
        self,
        cantidad_operadores_it: int,
        cantidad_operadores_tecnico: int,
        cantidad_operadores_dev: int,
        muestrear_interarribo_min: Callable[[random.Random], float],
        muestrear_duracion_servicio_min: Callable[[str, random.Random], float],
        seed: int = 1,
        debug: bool = False,
    ):
        self.rng = random.Random(seed)
        self.debug = debug

        self.cantidad_operadores_it = cantidad_operadores_it
        self.cantidad_operadores_tecnico = cantidad_operadores_tecnico
        self.cantidad_operadores_dev = cantidad_operadores_dev

        # Wrappers inyectados (los vas a cambiar después)
        self.muestrear_interarribo_min = muestrear_interarribo_min
        self.muestrear_duracion_servicio_min = muestrear_duracion_servicio_min

        # Vectores TPS (fin de servicio por operador)
        self.TPSIT: List[float] = [HORIZONTE_VACIO] * cantidad_operadores_it
        self.TPSTEC: List[float] = [HORIZONTE_VACIO] * cantidad_operadores_tecnico
        self.TPSDEVS: List[float] = [HORIZONTE_VACIO] * cantidad_operadores_dev

        # 1 trabajo calendarizado por operador (asignado a un operador específico)
        self.AGIT: List[Optional[Trabajo]] = [None] * cantidad_operadores_it
        self.AGTEC: List[Optional[Trabajo]] = [None] * cantidad_operadores_tecnico
        self.AGDEVS: List[Optional[Trabajo]] = [None] * cantidad_operadores_dev
        self.TrabajoPendiente: List[Trabajo] = []
        self.DEVATENCIONIT = 0 
        self.DEVATENCIONTEC = 0 
        self.PERDIDATIEMPOMAS30IT = 0
        self.PERDIDATIEMPOMAS30TEC = 0
        self.TIPO_EN_SERVICIO_DEV: List[Optional[str]] = [None] * cantidad_operadores_dev



        # Métricas
        self.perdidos_por_tipo = {"IT": 0, "TEC": 0, "DEV": 0}
        self.atendidos_por_tipo = {"IT": 0, "TEC": 0, "DEV": 0}
        self.suma_espera_por_tipo_min = {"IT": 0.0, "TEC": 0.0, "DEV": 0.0}

    # -----------------------------
    # Wrappers internos declarativos
    # -----------------------------
    def _obtener_siguiente_interarribo_minutos(self) -> float:
        return self.muestrear_interarribo_min(self.rng)

    def _obtener_duracion_servicio_minutos(self, tipo_servicio: str) -> float:
        return self.muestrear_duracion_servicio_min(tipo_servicio, self.rng)

    # -----------------------------
    # Sorteo del tipo (70/20/10)
    # -----------------------------
    def _sortear_tipo_servicio(self) -> str:
        u = self.rng.random()
        if u < 0.70:
            return "IT"
        if u < 0.90:
            return "TEC"
        return "DEV"

    # -----------------------------
    # Cálculo de mínimos (como en cátedra)
    # -----------------------------
    def _minimo_tps_y_indice(self, vector_tps: List[float]) -> Tuple[float, int]:
        if not vector_tps:
            return HORIZONTE_VACIO, -1

        minimo = HORIZONTE_VACIO
        indice_minimo = -1
        for i, v in enumerate(vector_tps):
            if v < minimo:
                minimo = v
                indice_minimo = i
        return minimo, indice_minimo

    def _elegir_siguiente_salida(self) -> Tuple[float, str, int]:
        min_it, idx_it = self._minimo_tps_y_indice(self.TPSIT)
        min_tec, idx_tec = self._minimo_tps_y_indice(self.TPSTEC)
        min_dev, idx_dev = self._minimo_tps_y_indice(self.TPSDEVS)

        tiempo_minimo = min(min_it, min_tec, min_dev)
        if tiempo_minimo == HORIZONTE_VACIO:
            return HORIZONTE_VACIO, "", -1

        # Prioridad en empate (prioridad it)
        if min_it == tiempo_minimo:
            return tiempo_minimo, "IT", idx_it
        if min_tec == tiempo_minimo:
            return tiempo_minimo, "TEC", idx_tec
        return tiempo_minimo, "DEV", idx_dev

    # -----------------------------
    # Reglas: libre / agendar
    # -----------------------------
    def _buscar_operador_libre(self, trabajo: Trabajo) -> int:
        """
        Libre SOLO si:
        - TPS == HV (no está atendiendo)
        - y NO tiene trabajo asignado (AG == None)
        """
        tipo_servicio = trabajo.tipo_servicio
        if tipo_servicio == "IT":
            for i in range(self.cantidad_operadores_it):
                if self.TPSIT[i] == HORIZONTE_VACIO and self.AGIT[i] is None:
                    return i
            for i in range(self.cantidad_operadores_dev):
                if self.TPSDEVS[i] == HORIZONTE_VACIO and self.AGDEVS[i] is None:
                    self.DEVATENCIONIT += 1
                    trabajo.tomadoPorDev = True
                    return i
            return -1

        if tipo_servicio == "TEC":
            for i in range(self.cantidad_operadores_tecnico):
                if self.TPSTEC[i] == HORIZONTE_VACIO and self.AGTEC[i] is None:
                    return i
            for i in range(self.cantidad_operadores_dev):
                if self.TPSDEVS[i] == HORIZONTE_VACIO and self.AGDEVS[i] is None:
                    self.DEVATENCIONTEC += 1
                    trabajo.tomadoPorDev = True
                    return i
            return -1
        
        for i in range(self.cantidad_operadores_dev):
            if self.TPSDEVS[i] == HORIZONTE_VACIO and self.AGDEVS[i] is None:
                return i
        return -1

    def _buscar_operador_para_agendar(self, tipo_servicio: str, tiempo_arribo_minutos) -> int:
        """
        Se agenda SOLO si el operador está ocupado (TPS != HV) y su slot está libre.
        Elegimos el que termina antes (menor TPS).
        """
        mejor_indice = -1
        mejor_tps = HORIZONTE_VACIO

        if tipo_servicio == "IT":
            for i in range(self.cantidad_operadores_it):
                ocupado = self.TPSIT[i] != HORIZONTE_VACIO
                slot_libre = self.AGIT[i] is None
                if ocupado and slot_libre and self.TPSIT[i] < mejor_tps:
                    mejor_tps = self.TPSIT[i]
                    mejor_indice = i
            
            if mejor_tps-tiempo_arribo_minutos>30 and self.rng.random() < 0.5:
                self.PERDIDATIEMPOMAS30IT += 1
                return -1
            
            return mejor_indice

        if tipo_servicio == "TEC":
            for i in range(self.cantidad_operadores_tecnico):
                ocupado = self.TPSTEC[i] != HORIZONTE_VACIO
                slot_libre = self.AGTEC[i] is None
                if ocupado and slot_libre and self.TPSTEC[i] < mejor_tps:
                    mejor_tps = self.TPSTEC[i]
                    mejor_indice = i
            
            if mejor_tps-tiempo_arribo_minutos>30 and self.rng.random() < 0.5:
                self.PERDIDATIEMPOMAS30TEC += 1
                return -1        
            return mejor_indice

        for i in range(self.cantidad_operadores_dev):
            ocupado = self.TPSDEVS[i] != HORIZONTE_VACIO
            slot_libre = self.AGDEVS[i] is None
            if ocupado and slot_libre and self.TPSDEVS[i] < mejor_tps:
                mejor_tps = self.TPSDEVS[i]
                mejor_indice = i
        return mejor_indice

    # -----------------------------
    # Acciones sobre eventos
    # -----------------------------
    def _iniciar_servicio(self, tiempo_actual_minutos: float, trabajo: Trabajo, indice_operador: int):
        """
        Arranca servicio:
        - normaliza inicio a horario laboral
        - acumula espera
        - programa el fin del servicio en TPS = inicio + duracion (en tiempo laboral)
        """
        inicio_servicio = normalizar_a_horario_laboral(tiempo_actual_minutos)

        espera = inicio_servicio - trabajo.tiempo_arribo_minutos
        self.suma_espera_por_tipo_min[trabajo.tipo_servicio] += espera

        fin_servicio = sumar_minutos_laborales(inicio_servicio, trabajo.duracion_servicio_minutos)

        if trabajo.tipo_servicio == "IT" and trabajo.tomadoPorDev == False:
            self.TPSIT[indice_operador] = fin_servicio
        elif trabajo.tipo_servicio == "TEC" and trabajo.tomadoPorDev == False:
            self.TPSTEC[indice_operador] = fin_servicio
        else:
            self.TPSDEVS[indice_operador] = fin_servicio
            self.TIPO_EN_SERVICIO_DEV[indice_operador] = trabajo.tipo_servicio
        if self.debug:
            print(
                f"[INICIO] {trabajo.tipo_servicio} op={indice_operador} "
                f"arribo={formatear_tiempo(trabajo.tiempo_arribo_minutos)} "
                f"inicio={formatear_tiempo(inicio_servicio)} "
                f"fin={formatear_tiempo(fin_servicio)}"
            )

    def _agendar_trabajo(self, tipo_servicio: str, indice_operador: int, trabajo: Trabajo):
        if tipo_servicio == "IT":
            self.AGIT[indice_operador] = trabajo
        elif tipo_servicio == "TEC":
            self.AGTEC[indice_operador] = trabajo
        else:
            self.AGDEVS[indice_operador] = trabajo

        if self.debug:
            print(
                f"[AGENDA] {tipo_servicio} op={indice_operador} "
                f"arribo={formatear_tiempo(trabajo.tiempo_arribo_minutos)}"
            )

    def _procesar_arribo(self, tiempo_arribo_minutos: float):
        """
        ARRIBO:
        - sortea tipo
        - sortea duración de servicio del trabajo
        - intenta atender / agendar / perder
        """
        tipo = self._sortear_tipo_servicio()
        duracion = self._obtener_duracion_servicio_minutos(tipo)
        trabajo = Trabajo(tiempo_arribo_minutos=tiempo_arribo_minutos, tipo_servicio=tipo, duracion_servicio_minutos=duracion)

        indice_libre = self._buscar_operador_libre(trabajo)
        if indice_libre != -1:
            self._iniciar_servicio(tiempo_arribo_minutos, trabajo, indice_libre)
            return

        indice_para_agendar = self._buscar_operador_para_agendar(tipo, tiempo_arribo_minutos)
        if indice_para_agendar != -1:
            self._agendar_trabajo(tipo, indice_para_agendar, trabajo)
            return

        self.perdidos_por_tipo[tipo] += 1
        if self.debug:
            print(f"[PERDIDO] {tipo} arribo={formatear_tiempo(tiempo_arribo_minutos)}")

    def _procesar_pendiente(self, indicePendiente: int, tiempo):
        """
        PENDIENTE:
        - se sabe el tiempo que tarda la tarea
        - intenta atender / perder
        """
        trabajo = self.TrabajoPendiente[indicePendiente]

        tipo = trabajo.tipo_servicio
        tiempo_arribo_minutos = trabajo.tiempo_arribo_minutos

        indice_libre = self._buscar_operador_libre(trabajo)
        if indice_libre != -1:
            self._iniciar_servicio(tiempo_arribo_minutos, trabajo, indice_libre)
            return

        self.perdidos_por_tipo[tipo] += 1
        if self.debug:
            print(f"[PERDIDO] {tipo} arribo={formatear_tiempo(tiempo_arribo_minutos)}")

    def _procesar_salida(self, tiempo_salida_min: float, tipo: str, indice_operador: int):
        """
        SALIDA:
        - operador termina -> TPS = HV
        - si tenía agendado -> lo inicia (no queda libre)
        - si no -> queda libre
        """
        tipo_atendido = tipo
        if(tipo is not None and tipo == "DEV"):
            tipo_atendido = self.TIPO_EN_SERVICIO_DEV[indice_operador] or "DEV"
            self.TIPO_EN_SERVICIO_DEV[indice_operador] = None
        self.atendidos_por_tipo[tipo_atendido] += 1
        if self.debug:
            print(f"[FIN] pool={tipo} op={indice_operador} atendio={tipo_atendido} ...")

        if tipo == "IT":
            self.TPSIT[indice_operador] = HORIZONTE_VACIO
            trabajo_agendado = self.AGIT[indice_operador]
            self.AGIT[indice_operador] = None
            if trabajo_agendado is not None:
                self._iniciar_servicio(tiempo_salida_min, trabajo_agendado, indice_operador)

        elif tipo == "TEC":
            self.TPSTEC[indice_operador] = HORIZONTE_VACIO
            trabajo_agendado = self.AGTEC[indice_operador]
            self.AGTEC[indice_operador] = None
            if trabajo_agendado is not None:
                self._iniciar_servicio(tiempo_salida_min, trabajo_agendado, indice_operador)

        else:  # DEV
            self.TPSDEVS[indice_operador] = HORIZONTE_VACIO
            trabajo_agendado = self.AGDEVS[indice_operador]
            self.AGDEVS[indice_operador] = None
            if trabajo_agendado is not None:
                self._iniciar_servicio(tiempo_salida_min, trabajo_agendado, indice_operador)

    # -----------------------------
    # Loop principal: próximo evento
    # -----------------------------
    def correr(self, dias: int) -> ResultadoSimulacion:
        """
        Simula 'dias' jornadas laborales completas.
        Arribos y servicios se programan en tiempo laboral (saltando la noche).
        """
        if dias < 1:
            raise ValueError("dias debe ser >= 1")
        tiempo_inicio_sim = 0 * MINUTOS_POR_DIA + INICIO_TURNO_MIN
        tiempo_fin_sim = (dias - 1) * MINUTOS_POR_DIA + FIN_TURNO_MIN  # fin del último día

        T = tiempo_inicio_sim

        # TPLL inicial: se suma interarribo en TIEMPO LABORAL
        TPLL = sumar_minutos_laborales(T, self._obtener_siguiente_interarribo_minutos())

        if self.debug:
            print(f"Inicio sim: {formatear_tiempo(T)} | Primer TPLL: {formatear_tiempo(TPLL)}")

        while T < tiempo_fin_sim:
            min_trabajo_programado, tipo_salida, idx_operador = self._elegir_siguiente_salida()

            # Decisión de cátedra:
            # Si TPLL >= minTiempoTrabajoProgramado -> SALIDA
            if min_trabajo_programado != HORIZONTE_VACIO and TPLL >= min_trabajo_programado:
                T = min_trabajo_programado
                self._procesar_salida(T, tipo_salida, idx_operador)
            else:
                T = TPLL
                self._procesar_arribo(T)

                # Programar próximo arribo en tiempo laboral
                TPLL = sumar_minutos_laborales(T, self._obtener_siguiente_interarribo_minutos())

        espera_promedio = {
            tipo: (self.suma_espera_por_tipo_min[tipo] / self.atendidos_por_tipo[tipo])
            if self.atendidos_por_tipo[tipo] > 0 else 0.0
            for tipo in ["IT", "TEC", "DEV"]
        }

        return ResultadoSimulacion(
            perdidos_por_tipo=self.perdidos_por_tipo,
            atendidos_por_tipo=self.atendidos_por_tipo,
            espera_promedio_por_tipo_min=espera_promedio,
        )
