from simulacion import normalizar_a_horario_laboral, sumar_minutos_laborales

MINUTOS_POR_DIA = 24 * 60
INICIO = 9 * 60
FIN = 18 * 60

# Pruebas para la función normalizar_a_horario_laboral

def test_antes_de_9_mueve_a_9_mismo_dia():
    assert normalizar_a_horario_laboral(0) == INICIO          # 00:00 -> 09:00 día 0
    assert normalizar_a_horario_laboral(8*60 + 59) == INICIO  # 08:59 -> 09:00 día 0

def test_dentro_del_turno_se_mantiene():
    assert normalizar_a_horario_laboral(INICIO) == INICIO         # 09:00 día 0
    assert normalizar_a_horario_laboral(10*60) == 10*60           # 10:00 día 0
    assert normalizar_a_horario_laboral(FIN - 1) == FIN - 1       # 17:59 día 0

def test_a_partir_de_18_va_a_9_del_dia_siguiente():
    # OJO: esto asume tu regla actual: 18:00 (>=) ya cuenta como fuera
    assert normalizar_a_horario_laboral(FIN) == MINUTOS_POR_DIA + INICIO     # 18:00 -> 09:00 día 1
    assert normalizar_a_horario_laboral(FIN + 1) == MINUTOS_POR_DIA + INICIO # 18:01 -> 09:00 día 1

def test_dia_1_antes_de_9_mueve_a_9_dia_1():
    assert normalizar_a_horario_laboral(MINUTOS_POR_DIA + 150) == MINUTOS_POR_DIA + INICIO  # 02:30 día 1 -> 09:00 día 1

def test_dia_1_en_9_se_mantiene():
    assert normalizar_a_horario_laboral(MINUTOS_POR_DIA + INICIO) == MINUTOS_POR_DIA + INICIO


def minutos(dia: int, hh: int, mm: int = 0) -> int:
    """Helper: convierte Día + HH:MM a minutos absolutos."""
    return dia * MINUTOS_POR_DIA + hh * 60 + mm

def test_duracion_cero_normaliza_inicio():
    # Día 0 08:00 + 0 => normaliza a 09:00
    inicio = minutos(0, 8, 0)
    resultado = sumar_minutos_laborales(inicio, 0)
    esperado = minutos(0, 9, 0)
    assert resultado == esperado

def test_suma_dentro_del_mismo_dia():
    inicio = minutos(1,10,0)
    resultado = sumar_minutos_laborales(inicio,6*60)  # +6 horas
    esperado = minutos(1,16,0) 
    assert resultado == esperado

def test_suma_mas_de_un_dia():
    inicio = minutos(1,10,0)
    resultado = sumar_minutos_laborales(inicio,10*60)  # +10 horas
    esperado = minutos(2,11,0) 
    assert resultado == esperado

