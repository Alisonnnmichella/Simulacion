# Wrappers dummy para poder construir el simulador (no se usan en estos tests)
from simulacion import HORIZONTE_VACIO, SimuladorMesaAyuda


def interarribo_dummy(_rng) -> float:
    return 1.0

def duracion_dummy(_tipo: str, _rng) -> float:
    return 1.0


def crear_simulador_dummy() -> SimuladorMesaAyuda:
    return SimuladorMesaAyuda(
        cantidad_operadores_it=1,
        cantidad_operadores_tecnico=1,
        cantidad_operadores_dev=1,
        muestrear_interarribo_minutos_it=interarribo_dummy,
        muestrear_duracion_servicio_min=duracion_dummy,
        seed=123,
        debug=False,
    )


def test_lista_vacia_devuelve_hv_y_menos_uno():
    sim = crear_simulador_dummy()
    minimo, idx = sim._minimo_tps_y_indice([])
    assert minimo == HORIZONTE_VACIO
    assert idx == -1


def test_un_elemento_devuelve_valor_y_indice_0():
    sim = crear_simulador_dummy()
    minimo, idx = sim._minimo_tps_y_indice([100.0])
    assert minimo == 100.0
    assert idx == 0


def test_varios_elementos_devuelve_minimo_y_su_indice():
    sim = crear_simulador_dummy()
    minimo, idx = sim._minimo_tps_y_indice([500.0, 200.0, 300.0])
    assert minimo == 200.0
    assert idx == 1


def test_empate_devuelve_el_primer_indice_del_minimo():
    sim = crear_simulador_dummy()
    minimo, idx = sim._minimo_tps_y_indice([10.0, 5.0, 5.0, 7.0])
    assert minimo == 5.0
    assert idx == 1


def test_ignora_inf_si_hay_valores_finitos():
    sim = crear_simulador_dummy()
    minimo, idx = sim._minimo_tps_y_indice([HORIZONTE_VACIO, 250.0, 1000.0])
    assert minimo == 250.0
    assert idx == 1


def test_todos_inf_devuelve_inf_y_menos_uno():
    sim = crear_simulador_dummy()
    minimo, idx = sim._minimo_tps_y_indice([HORIZONTE_VACIO, HORIZONTE_VACIO])
    assert minimo == HORIZONTE_VACIO
    assert idx == -1
