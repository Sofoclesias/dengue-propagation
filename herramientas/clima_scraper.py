# LIBRERÍAS

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import multiprocessing as mp
import numpy as np
import pandas as pd
import geopandas as gpd
import pickle
import time
import os
from datetime import datetime
import warnings
import calendar
import locale

# Variables importantes (modificar a discreción)
l = ['rain-3h', 'temperature-2m', 'wind-10m', 'dew', 'clouds-total', 'pressure']    # Variables de búsqueda
partir = int(os.cpu_count() / 2)                                                    # Cantidad de núcleos a utilizar y particiones al dataset de distritos
select = l[1]                                                                       # Selección de la variable de interés (por posición en lista l)
base = 'https://www.ventusky.com/'                                                  # Página web base

# Configuraciones generales
locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
warnings.filterwarnings('ignore')

años = [str(i) for i in range(2020,2025)]
meses = [calendar.month_name[i].lower() for i in range(1, 13)]

options = Options()
options.set_preference('permissions.default.image', 0)
options.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', True)
options.set_preference('intl.accept_languages', 'es-ES')
options.add_argument("--width=1920")
options.add_argument("--height=1080")
options.add_argument("--headless")

# DEFINICIÓN DE FUNCIÓN CLIMASCRAPER

def read_indexes(ruta: str,df: pd.DataFrame):
    with open(ruta,'r',encoding='utf8') as file:
        indexes = {(row.split(',')[2], row.split(',')[3]) for row in file.readlines()[1:]} & {tuple(row) for _, row in df[['Provincia','Distrito']].iterrows()}

    return indexes

def clima_scraper (part: pd.DataFrame, num: int):
    try:
        # Funciones anidadas
        get_vectorial_movement = lambda p_start, p_end: (p_end[0] - p_start[0], p_end[1] - p_start[1])
        center_page = lambda driver: (driver.execute_script("return window.innerWidth;")/2,driver.execute_script("return window.innerHeight;")/2)
        move_vector = lambda p_vect: action.move_by_offset(p_vect[0],p_vect[1])
    
        def get_coords_element (e):
            loc = e.location
            size = e.size
            
            x = loc['x'] + size['width']/2
            y = loc['y'] + size['height']/2
            return (x,y)    
        
        # Selección de valor de inicio
        if os.path.exists(f'anexos/clima/{select}_{num}.csv'): # ya hay una tabla de inicio
            indexes = read_indexes(f'anexos/clima/{select}_{num}.csv',part)

            mask = part[['Provincia','Distrito']].apply(tuple,axis=1).isin(indexes)
            part = part[~mask]
        else:
            pass

        # Inicio de algoritmo    
        for row in range(part.shape[0]):
            # Filas que se añadirán al dataframe
            caso = {'Fecha':[],
                    'Semana':[],
                    'Provincia':[],
                    'Distrito':[],
                    'Min':[],
                    'Max':[]}     
        
            # Recolección de datos
            prov: str = part.iloc[row,0]
            dist: str = part.iloc[row,1]
            lat = part.iloc[row,2]
            lon = part.iloc[row,3]
        
            # Crear enlace
            url = base + f'?p={lat};{lon};12' + f'&l={select}&m=icon'
                
            # Crear instancia del navegador
            driver = webdriver.Firefox(options=options)
            action = webdriver.ActionChains(driver)
            driver.implicitly_wait(300)

            print(f'Inicio {dist.capitalize()}, {num}')

            # Abrir url en el driver
            driver.get(url)
            time.sleep(3)
        
            # Conseguir coordenadas importantes
            hora_min = driver.find_element(By.XPATH, '//a[text()="01:00"]')
            hora_max = driver.find_element(By.XPATH, '//a[text()="13:00"]')
            center = center_page(driver)
            
            # Clickear dropdown
            drop_fecha = driver.find_element(By.XPATH, '//a[@class="t f"]')
            drop_fecha.click()

            for año in años:
                # Colocar año
                set_año = driver.find_element(By.XPATH, f'//select[@id="l"]/option[text()="{año}"]')
                set_año.click()
                time.sleep(1)
                
                for mes in meses:
                    if año=='2024' and mes=='mayo': break
                    else: pass
                    
                    # Colocar mes
                    set_mes = driver.find_element(By.XPATH, f'//select[@id="h"]/option[text()="{mes}"]')
                    set_mes.click()
                    time.sleep(1)
        
                    # Recolectar el último día del mes
                    dias = driver.find_elements(By.XPATH, '//td[@class=" qj"]')
        
                    for dia in [str(int(i)).zfill(2) for i in np.linspace(start=1,stop=int(dias[-1].text),num=5)]:
                        fecha = datetime.strptime(f"{dia} {mes} {año}", "%d %B %Y")

                        set_dia = driver.find_element(By.XPATH, f'//td/a[text()="{dia}"]')
                        set_dia.click()
                        time.sleep(1)
        
                        if select in ['dew','clouds-total','pressure']:
                            # Actualización del valor en el centro de la página por cada cambio de fecha
                            action.move_to_element(hora_min).perform()
                            move_vector(get_vectorial_movement(get_coords_element(hora_min),center))
                            action.perform()
                            time.sleep(2)
                            
                            mini = driver.find_element(By.XPATH, '//span[@class="aa"]').text
                            maxi = mini
                        else:
                            # Mover cursor entre las horas del día y recopilar información
                            # Mover a hora mínima
                            action.move_to_element(hora_min).click().perform()
                            time.sleep(1)
            
                            # Mover al centro
                            move_vector(get_vectorial_movement(get_coords_element(hora_min),center))
                            action.perform()
                            time.sleep(3)
                            mini = driver.find_element(By.XPATH, '//span[@class="aa"]').text

                            # Mover a hora máxima
                            action.move_to_element(hora_max).click().perform()
                            time.sleep(1)
            
                            # Mover al centro
                            move_vector(get_vectorial_movement(get_coords_element(hora_max),center))
                            action.perform()
                            time.sleep(3)
                            maxi = driver.find_element(By.XPATH, '//span[@class="aa"]').text
            
                        # Seteo como diccionario
                        caso['Fecha'] += [fecha]
                        caso['Semana'] += [fecha.isocalendar()[1]]
                        caso['Provincia'] += [prov]
                        caso['Distrito'] += [dist]
                        caso['Min'] += [mini]
                        caso['Max'] += [maxi]
                    
            # Exportar el caso específico
            caso_df = pd.DataFrame(caso)
            caso_df.to_csv(f'anexos/clima/{select}_{num}.csv',index=False,mode='a',header=not os.path.exists(f'anexos/clima/{select}_{num}.csv'))
            
            # Cierra el navegador
            driver.close()    
        
    except Exception as exp:
        print(f'Error {num}: {exp}')
    
if __name__=='__main__':
    # GENERACIÓN DE PARTICIONES
    if os.path.exists(f'partition_{partir}.obj'):
        # Recuperar particiones iniciales
        with open(f'partition_{partir}.obj','rb') as filehandler:
            partition = pickle.load(filehandler)
    else:
        # RECOLECCIÓN DE DISTRITOS A BUSCAR
        distrital = gpd.read_file('anexos/distritos/distritos-peru@bogota-laburbano.geojson')[
            ['nombdep', 'nombprov', 'nombdist', 'geo_point_2d']]
        distrital = distrital[(distrital['nombdep'] == 'LIMA') | (distrital['nombdep'] == 'CALLAO')].reset_index().iloc[:-1, 2:]
        geopoints = distrital.pop('geo_point_2d')
        distrital['lat'] = None
        distrital['lon'] = None

        for row in range(geopoints.shape[0]):
            distrital.iloc[row, 2] = round(eval(geopoints[row])["lat"], 2)
            distrital.iloc[row, 3] = round(eval(geopoints[row])["lon"], 2)

        distrital.columns = ['Provincia', 'Distrito', 'Lat', 'Lon']
        distrital.sort_values(by=['Provincia', 'Distrito'], inplace=True)

        # Parámetros de partición
        n_rows = distrital.shape[0]//partir
        sampling = distrital.copy()
        partition = []
        
        # Creación de particiones sin reemplazo, mutuamente excluyentes
        for i in range(partir-1):
            partition += [sampling.sample(n=n_rows)]
            sampling.drop(partition[i].index,inplace=True)
        partition += [sampling]
        
        # Guardarlo para reusarlo en otra sesión
        with open(f'partition_{partir}.obj','wb') as filehandler:
            pickle.dump(partition,filehandler)

    # Crear procesos para cada chunk de coordenadas, iniciarlos y esperar a que terminen
    with mp.Pool(processes=partir) as pool:
        pool.starmap(clima_scraper, [(partition[i],i) for i in range(partir)])
        pool.close()
        pool.join()

    # Consolidación final de todos los archivos csv
    csvs = [pd.read_csv(f'anexos/clima/{select}_{i}.csv') for i in range(partir)]
    consol = pd.concat(csvs,ignore_index=True)
    consol.to_csv(f'datasets/{select}.csv',index=False)

    print(f'\nProcesamiento de {select} terminado por completo.')
    print('Distritos totales: ',len({(frozenset(row)) for _, row in consol[['Provincia','Distrito']].iterrows()}))