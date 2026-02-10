import unittest

import pytest

from simulacion2 import Simulacion


HORA_INICIO_LABORAL = 9
HORA_FINAL_DE_TRABAJO = 17

class TestSimulacion(unittest.TestCase):



    def test_tarea_26_horas(self):
        sim = Simulacion(
            cantidad_operadores_it=1,
            cantidad_operadores_app=1,
            cantidad_operadores_dev=1,
            muestrear_interarribo_minutos_it=lambda rng: 1.0,
            muestrear_interarribo_minutos_app=lambda rng: 1.0,
            muestrear_interarribo_minutos_dev=lambda rng: 1.0,
            muestrear_duracion_servicio_it=lambda tipo, rng: 1.0,
            muestrear_duracion_servicio_app=lambda tipo, rng: 1.0,
            muestrear_duracion_servicio_dev=lambda tipo, rng: 1.0,
        )

        # Caso: tarea de 26 horas (1500 minutos), empezando al inicio del día 0 (9:00 = minuto 540)
        tiempoActual = HORA_INICIO_LABORAL*60
        tiempoDeAtencion = 1600
        resultado = sim.finDeTareaEnHorarioLaboral(tiempoActual, tiempoDeAtencion)

        # Esperado: día 3 a las 10:00 → minuto absoluto = 3*1440 + 600
        esperado = 2 * 1440 + HORA_INICIO_LABORAL*60 + 160
        self.assertEqual(resultado, esperado)


    def test_25_horas(self):
        sim = self.instanciaDeSimulacion()
        # Inicio del día 0 a las 9:00 → minuto 540
        tiempoActual = 540
        tiempoDeAtencion = 1500  # 25 horas
        resultado = sim.finDeTareaEnHorarioLaboral(tiempoActual, tiempoDeAtencion)

        # Esperado: día 3 a las 10:00 → minuto absoluto = 3*1440 + 600
        esperado = 2 * 1440 + HORA_INICIO_LABORAL*60 + 60
        self.assertEqual(resultado, esperado)


    def test_fin_de_tarea_dentro_dia_0(self):
        sim = self.instanciaDeSimulacion()
        # Caso: tiempo actual 10:00 (minuto 600)
        tiempoActual = HORA_FINAL_DE_TRABAJO*60-200  # 15:40 = minuto 940
        resultado = sim._fin_del_dia_en_minutos_absolutos(tiempoActual)
        # Esperado: día 0 a las 17:00 → minuto absoluto = 0*1440 + 1020
        esperado = HORA_FINAL_DE_TRABAJO*60
        self.assertEqual(resultado, esperado) 

    def test_fin_de_tarea_dentro_dia_3_antes_del_horario_laboral_da_fin_dia_3(self):
        sim = self.instanciaDeSimulacion()
        tiempoActual = 54*60
        resultado = sim._fin_del_dia_en_minutos_absolutos(tiempoActual)
        esperado = 24*2*60+HORA_FINAL_DE_TRABAJO*60
        self.assertEqual(resultado, esperado) 





    def instanciaDeSimulacion(self):
        sim = Simulacion(
            cantidad_operadores_it=1,
            cantidad_operadores_app=1,
            cantidad_operadores_dev=1,
            muestrear_interarribo_minutos_it=lambda rng: 1.0,
            muestrear_interarribo_minutos_app=lambda rng: 1.0,
            muestrear_interarribo_minutos_dev=lambda rng: 1.0,
            muestrear_duracion_servicio_it=lambda tipo, rng: 1.0,
            muestrear_duracion_servicio_app=lambda tipo, rng: 1.0,
            muestrear_duracion_servicio_dev=lambda tipo, rng: 1.0,
        )
        
        return sim   
    

@pytest.fixture
def sim():
    return Simulacion(
        cantidad_operadores_it=1,
        cantidad_operadores_app=1,
        cantidad_operadores_dev=1,
        muestrear_interarribo_minutos_it=lambda rng: 1.0,
        muestrear_interarribo_minutos_app=lambda rng: 1.0,
        muestrear_interarribo_minutos_dev=lambda rng: 1.0,
        muestrear_duracion_servicio_it=lambda tipo, rng: 1.0,
        muestrear_duracion_servicio_app=lambda tipo, rng: 1.0,
        muestrear_duracion_servicio_dev=lambda tipo, rng: 1.0,
    )

def t(dia, hora, minuto):
    return dia * 1440 + hora * 60 + minuto

@pytest.mark.parametrize("inicio,dur,esperado", [
    (t(0, 9, 0),   30,  t(0, 9, 30)),
    (t(0, 17, 0),  30,  t(1, 9, 30)),
    (t(0, 16, 30), 30,  t(0, 17, 0)),
    (t(0, 16, 30), 60,  t(1, 9, 30)),
    (t(0, 15, 0),  240, t(1, 11, 0)),
    (t(0, 16, 0),  600, t(2, 10, 0)),
    (t(0, 9, 0),   1080,t(2, 11, 0)),
    (t(0, 10, 0),  600, t(1, 12, 0)),
    (t(0, 16, 0),  1200,t(3, 12, 0)),
])
def test_determinar_fin(sim, inicio, dur, esperado):
    assert sim.determinarTiempoDeFinDeTarea(inicio, dur) == esperado
