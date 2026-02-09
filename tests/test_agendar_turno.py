import pytest
from simulacion import HORIZONTE_VACIO, SimuladorMesaAyuda

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

def sim_crear_simulador_dummy(sit, tec, dev):
    sim = crear_simulador_dummy(len(sit), len(tec), len(dev))

    sim.TPSIT = sit
    sim.TPSTEC = tec
    sim.TPSDEVS = dev

    # slots libres (se puede sobreescribir en cada test)
    sim.AGIT = [None] * len(sit)
    sim.AGTEC = [None] * len(tec)
    sim.AGDEVS = [None] * len(dev)

    return sim


# -------------------------
# Tests principales
# -------------------------

def test_para_agendar_it_elige_el_menor_tps_entre_ocupados_con_slot_libre(monkeypatch):
    # Ocupados: idx 0 (100), idx 1 (40), idx 3 (70)
    # HV NO cuenta. Debe elegir idx 1 (40)
    sim = sim_crear_simulador_dummy(
        sit=[100.0, 40.0, HORIZONTE_VACIO, 70.0],
        tec=[],
        dev=[],
    )

    # tiempo_arribo = 20 => espera para mejor_tps=40 es 20 (<=30) => no aplica random
    assert sim._buscar_operador_para_agendar("IT", tiempo_arribo_minutos=20.0) == 1


def test_para_agendar_tec_ignora_slots_ocupados_y_elige_menor_tps(monkeypatch):
    sim = sim_crear_simulador_dummy(
        sit=[],
        tec=[60.0, 20.0, 10.0],
        dev=[],
    )
    # bloqueamos el mejor (idx 2) por AG no libre
    sim.AGTEC[2] = "ya_agendado"

    # candidatos: idx 0 (60), idx 1 (20) -> elige idx 1
    # tiempo_arribo=0 => espera 20 (<=30) => no aplica random
    assert sim._buscar_operador_para_agendar("TEC", tiempo_arribo_minutos=0.0) == 1


def test_para_agendar_dev_ignora_hv_y_elije_menor_tps(monkeypatch):
    sim = sim_crear_simulador_dummy(
        sit=[],
        tec=[],
        dev=[HORIZONTE_VACIO, 55.0, 12.0, 99.0],
    )
    # En DEV no existe regla del 50% por espera>30, así que no importa tiempo_arribo
    assert sim._buscar_operador_para_agendar("DEV", tiempo_arribo_minutos=0.0) == 2


# -------------------------
# Casos borde
# -------------------------

def test_para_agendar_devuelve_menos_uno_si_todos_estan_libres_hv(monkeypatch):
    sim = sim_crear_simulador_dummy(
        sit=[HORIZONTE_VACIO, HORIZONTE_VACIO],
        tec=[HORIZONTE_VACIO],
        dev=[HORIZONTE_VACIO, HORIZONTE_VACIO],
    )
    assert sim._buscar_operador_para_agendar("IT", tiempo_arribo_minutos=0.0) == -1
    assert sim._buscar_operador_para_agendar("TEC", tiempo_arribo_minutos=0.0) == -1
    assert sim._buscar_operador_para_agendar("DEV", tiempo_arribo_minutos=0.0) == -1


def test_para_agendar_devuelve_menos_uno_si_todos_tienen_slot_ocupado(monkeypatch):
    sim = sim_crear_simulador_dummy(
        sit=[10.0, 20.0],
        tec=[5.0],
        dev=[7.0, 3.0],
    )
    sim.AGIT = ["x", "x"]
    sim.AGTEC = ["x"]
    sim.AGDEVS = ["x", "x"]

    assert sim._buscar_operador_para_agendar("IT", tiempo_arribo_minutos=0.0) == -1
    assert sim._buscar_operador_para_agendar("TEC", tiempo_arribo_minutos=0.0) == -1
    assert sim._buscar_operador_para_agendar("DEV", tiempo_arribo_minutos=0.0) == -1


def test_para_agendar_tipo_desconocido_cae_en_rama_dev(monkeypatch):
    # Tu implementación: si no es IT ni TEC, usa DEV.
    sim = sim_crear_simulador_dummy(
        sit=[],
        tec=[],
        dev=[30.0, 10.0],
    )
    assert sim._buscar_operador_para_agendar("CUALQUIERA", tiempo_arribo_minutos=0.0) == 1


# -------------------------
# Nuevos tests para la regla del 50% (espera > 30) en IT/TEC
# -------------------------

def test_para_agendar_it_puede_perder_si_espera_mayor_30_y_random_menor_0_5(monkeypatch):
    sim = sim_crear_simulador_dummy(
        sit=[100.0, 60.0],  # mejor_tps = 60
        tec=[],
        dev=[],
    )
    # tiempo_arribo=0 => espera=60 (>30) => aplica regla
    monkeypatch.setattr(sim.rng, "random", lambda: 0.49)  # < 0.5 => pierde
    assert sim._buscar_operador_para_agendar("IT", tiempo_arribo_minutos=0.0) == -1
    assert sim.PERDIDATIEMPOMAS30IT == 1


def test_para_agendar_it_no_pierde_si_espera_mayor_30_y_random_mayor_igual_0_5(monkeypatch):
    sim = sim_crear_simulador_dummy(
        sit=[100.0, 60.0],
        tec=[],
        dev=[],
    )
    monkeypatch.setattr(sim.rng, "random", lambda: 0.5)  # >= 0.5 => NO pierde
    assert sim._buscar_operador_para_agendar("IT", tiempo_arribo_minutos=0.0) == 1
    assert sim.PERDIDATIEMPOMAS30IT == 0


def test_para_agendar_tec_puede_perder_si_espera_mayor_30_y_random_menor_0_5(monkeypatch):
    sim = sim_crear_simulador_dummy(
        sit=[],
        tec=[80.0, 40.0],  # mejor_tps=40
        dev=[],
    )
    # tiempo_arribo=0 => espera=40 (>30)
    monkeypatch.setattr(sim.rng, "random", lambda: 0.1)
    assert sim._buscar_operador_para_agendar("TEC", tiempo_arribo_minutos=0.0) == -1
    assert sim.PERDIDATIEMPOMAS30TEC == 1
