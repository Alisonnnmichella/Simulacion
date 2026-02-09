import pytest
from simulacion import SimuladorMesaAyuda, HORIZONTE_VACIO, INICIO_TURNO_MIN, MINUTOS_POR_DIA

def interarribo_dummy(_rng) -> float:
    return 1.0

def duracion_dummy(_tipo: str, _rng) -> float:
    return 1.0

def crear_simulador_dummy(cantidad_it, cantidad_tec, cantidad_dev) -> SimuladorMesaAyuda:
    return SimuladorMesaAyuda(
        cantidad_operadores_it=cantidad_it,
        cantidad_operadores_tecnico=cantidad_tec,
        cantidad_operadores_dev=cantidad_dev,
        muestrear_interarribo_minutos_it=interarribo_dummy,
        muestrear_duracion_servicio_min=duracion_dummy,
        seed=123,
        debug=False,
    )

def test_3_arribos_it_tec_ocupan_devs_y_arribo_dev_se_agenda(monkeypatch):
    # ✅ Setup: 0 IT, 0 TEC, 2 DEVs
    # Entonces IT y TEC “derraman” al pool DEV y lo ocupan.
    sim = crear_simulador_dummy(cantidad_it=0, cantidad_tec=0, cantidad_dev=2)

    # Forzamos el orden de arribos: IT, TEC, DEV
    tipos = iter(["IT", "TEC", "DEV"])
    monkeypatch.setattr(sim, "_sortear_tipo_servicio", lambda: next(tipos))

    # Duraciones largas para que los 2 DEVs sigan ocupados cuando llegue el DEV.
    duraciones = iter([100.0, 100.0, 5.0])  # IT=100, TEC=100, DEV=5
    monkeypatch.setattr(sim, "_obtener_duracion_servicio_minutos", lambda _tipo: next(duraciones))

    # Tiempos de arribo (dentro de horario laboral)
    t0 = 0 * MINUTOS_POR_DIA + INICIO_TURNO_MIN + 1  # 09:01
    t1 = t0 + 1                                       # 09:02
    t2 = t0 + 2                                       # 09:03

    # --- Arribo 1: IT -> lo atiende DEV 0
    sim._procesar_arribo(t0)
    assert sim.TPSDEVS[0] != HORIZONTE_VACIO
    assert sim.TPSDEVS[1] == HORIZONTE_VACIO
    assert sim.TIPO_EN_SERVICIO_DEV[0] == "IT"

    # --- Arribo 2: TEC -> lo atiende DEV 1
    sim._procesar_arribo(t1)
    assert sim.TPSDEVS[1] != HORIZONTE_VACIO
    assert sim.TIPO_EN_SERVICIO_DEV[0] == "IT"
    assert sim.TIPO_EN_SERVICIO_DEV[1] == "TEC"

    # --- Arribo 3: DEV -> no hay dev libre => se agenda
    sim._procesar_arribo(t2)

    # Debe agendarse en el DEV que termina antes.
    # Como el DEV0 empezó antes (t0) y duración es igual, termina antes que DEV1.
    assert sim.AGDEVS[0] is not None
    assert sim.AGDEVS[0].tipo_servicio == "DEV"
    assert sim.AGDEVS[1] is None
    assert sim.perdidos_por_tipo["DEV"] == 0

    # Extra (opcional): al terminar DEV0, debe arrancar lo agendado
    fin_dev0 = sim.TPSDEVS[0]
    sim._procesar_salida(fin_dev0, "DEV", 0)

    # Se consumió el slot agendado y DEV0 vuelve a estar ocupado con el DEV agendado
    assert sim.AGDEVS[0] is None
    assert sim.TPSDEVS[0] != HORIZONTE_VACIO
    assert sim.TIPO_EN_SERVICIO_DEV[0] == "DEV"

    # Y además contaste el “atendido” correcto del primer trabajo (era IT atendido por DEV)
    assert sim.atendidos_por_tipo["IT"] == 1
