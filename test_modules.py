from db.database import DBManager
from utils.mapbox import calculate_distance_and_time

print("Testando banco de dados...")
db = DBManager()
config = db.get_config()
print("Configuração carregada:", config)

print("\nTestando Mapbox...")
origem = "Avenida Paulista, São Paulo"
destinos = ["Rua Augusta, São Paulo"]
resultado = calculate_distance_and_time(origem, destinos)
print("Resultado Mapbox:", resultado)

db.close()
