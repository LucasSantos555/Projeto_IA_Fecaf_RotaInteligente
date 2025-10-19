import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from geopy.distance import great_circle 
import os



def haversine_distance(coord1, coord2):
    
    
    return great_circle(coord1, coord2).km

def nearest_neighbor_tsp(points_df, start_id=None):
    """
    Heurística do Vizinho Mais Próximo para sequenciar entregas.
  
    """
    # Mapeia IDs de coordenadas 
    coords = {row['id_entrega']: (row['latitude'], row['longitude']) 
              for index, row in points_df.iterrows()}
    
    if not coords:
        return [], 0.0

    
    current_id = start_id if start_id in coords else next(iter(coords))
    route = [current_id]
    total_distance = 0.0
    unvisited = set(coords.keys())
    unvisited.remove(current_id)

    while unvisited:
        min_distance = float('inf')
        nearest_neighbor_id = None
        current_coord = coords[current_id]

        
        for next_id in unvisited:
            distance = haversine_distance(current_coord, coords[next_id])
            
            if distance < min_distance:
                min_distance = distance
                nearest_neighbor_id = next_id
        
        # Move para o vizinho mais próximo encontrado
        route.append(nearest_neighbor_id)
        total_distance += min_distance
        unvisited.remove(nearest_neighbor_id)
        current_id = nearest_neighbor_id
        
    return route, total_distance



FILE = os.path.join('data', 'entregas.csv')
try:
    df = pd.read_csv(FILE)
except FileNotFoundError:
    print(f"ATENÇÃO: Arquivo {FILE} não encontrado. Gerando 100 dados de teste.")
    
    np.random.seed(42)
    data = {
        'id_entrega': [f'E_{i}' for i in range(100)],
        'latitude': np.random.uniform(-23.6, -23.4, 100),
        'longitude': np.random.uniform(-46.7, -46.5, 100)
    }
    df = pd.DataFrame(data)
    
df['id_entrega'] = df['id_entrega'].astype(str)
X = df[['latitude', 'longitude']]



inertia_values = [] 
k_range = range(1, 11) 
k_ideal = 3 

for k_test in k_range:
    kmeans_model = KMeans(n_clusters=k_test, random_state=42, n_init=10)
    kmeans_model.fit(X)
    inertia_values.append(kmeans_model.inertia_)



k = k_ideal 
kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
df['cluster'] = kmeans.fit_predict(X) 
print(f"\n[PASSO 1] Agrupamento K-Means concluído com K={k}.")

# ---Inicio Sequenciamento TSP por Cluster (Vizinho Mais Próximo) ---

optimized_routes = {}
total_distance_nn_tsp = 0.0

print("\nIniciando Sequenciamento (Vizinho Mais Próximo)...")

for cluster_id in sorted(df['cluster'].unique()):
    cluster_df = df[df['cluster'] == cluster_id].copy()
    
    
    centroid = kmeans.cluster_centers_[cluster_id]
    min_dist_to_centroid = float('inf')
    start_point_id = cluster_df.iloc[0]['id_entrega']
    
    for index, row in cluster_df.iterrows():
        point_coord = (row['latitude'], row['longitude'])
        dist = haversine_distance(centroid, point_coord)
        if dist < min_dist_to_centroid:
            min_dist_to_centroid = dist
            start_point_id = row['id_entrega']

    # Aplica a heurística Vizinho Mais Próximo
    route_ids, distance = nearest_neighbor_tsp(cluster_df, start_id=start_point_id)
    total_distance_nn_tsp += distance
    
    # Mapear IDs para coordenadas para a plotagem
    route_coords = []
    for route_id in route_ids:
        delivery = df[df['id_entrega'] == route_id].iloc[0]
        route_coords.append((delivery['longitude'], delivery['latitude']))
        
    optimized_routes[cluster_id] = {
        'ids': route_ids,
        'distance_km': distance,
        'coords': route_coords
    }
    
    print(f"  - Rota {cluster_id} ({len(route_ids)} entregas). Distância: {distance:.2f} km")

print(f"\nDistância Total Combinada das Rotas: {total_distance_nn_tsp:.2f} km")

# --- 6. PLOTAGEM FINAL: Unificando Cotovelo e Rotas em 2 Subplots ---

# Cria uma figura única com dois subplots (1 linha, 2 colunas)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8)) 
plt.suptitle('Solução de Otimização de Rotas (VRP): K-Means + Vizinho Mais Próximo', fontsize=16, y=1.02)



ax1.plot(k_range, inertia_values, marker='o', linestyle='--', color='b')
ax1.set_title('1. Justificativa Analítica: Método do Cotovelo')
ax1.set_xlabel('Número de Clusters (K)')
ax1.set_ylabel('Inércia')
ax1.axvline(x=k_ideal, color='red', linestyle='-', linewidth=1.5, label=f'K Escolhido = {k_ideal}')
ax1.legend()
ax1.grid(True, alpha=0.5)



colors = plt.cm.get_cmap('viridis', k_ideal)
legend_elements = []

# 6.1 Plotar todos os pontos (Entregas)
ax2.scatter(df['longitude'], df['latitude'], 
                      c=df['cluster'], 
                      cmap=colors, 
                      s=50, 
                      alpha=0.8, 
                      edgecolors='w', 
                      linewidths=0.5)


for cluster_id, route_data in optimized_routes.items():
    route_coords = np.array(route_data['coords'])
    
    # Desenhar as linhas da rota
    ax2.plot(route_coords[:, 0], route_coords[:, 1], 
             color=colors(cluster_id), 
             linestyle='-', 
             linewidth=2.5, 
             alpha=0.7)
    
    
    start_lon, start_lat = route_coords[0]
    ax2.plot(start_lon, start_lat, 
             marker='^', 
             markersize=12, 
             color='red', 
             markeredgecolor='black',
             zorder=5)

    # Preparar a legenda
    legend_elements.append(plt.Line2D([0], [0], color=colors(cluster_id), lw=3, 
                                      label=f'Rota {cluster_id} (Dist.: {route_data["distance_km"]:.2f} km)'))

# Finalizar Legenda
legend_elements.append(plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='red', markeredgecolor='black', markersize=10, label='Ponto Inicial/Depósito'))

ax2.set_title(f'2. Solução Final de Roteamento (K={k} Clusters)')
ax2.set_xlabel('Longitude')
ax2.set_ylabel('Latitude')
ax2.legend(handles=legend_elements, loc='upper right', title="Rotas e Distâncias") 

# Salvar e mostrar o gráfico
if not os.path.exists('outputs'):
    os.makedirs('outputs')
plt.tight_layout(rect=[0, 0.03, 1, 0.95]) 
plt.savefig('outputs/solucao_final_roteamento.png')
plt.show() 

