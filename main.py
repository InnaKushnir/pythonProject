import pvlib
import pandas as pd
import matplotlib.pyplot as plt
from pvlib.location import Location
from pvlib.pvsystem import PVSystem
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS

coordinates = [
    (32.2, -111.0, 'Tucson', 700, 'Etc/GMT+7'),
    (35.1, -106.6, 'Albuquerque', 1500, 'Etc/GMT+7'),
    (37.8, -122.4, 'San Francisco', 10, 'Etc/GMT+8'),
    (52.5, 13.4, 'Berlin', 34, 'Etc/GMT-1'),
]
sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')

sapm_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')
print(len(sandia_modules.all()), len(sapm_inverters.all()))

module = sandia_modules['Canadian_Solar_CS5P_220M___2009_']

inverter = sapm_inverters['ABB__MICRO_0_25_I_OUTD_US_208__208V_']

temperature_model_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']

temp_air = [22.0, 23.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 24.0]
relative_humidity = [50, 60, 70, 70, 70, 70, 70, 70, 70, 70, 70, 70, 60, 60, 60, 60, 60, 60, 60, 60, 60, 50, 50, 50]
ghi = [0, 900, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800]
dni = [0, 700, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, 600, ]
dhi = [0, 150, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
IR = [0, 200, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, ]
wind_speed = [5, 6, 7, 7,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6]
wind_direction = [180, 190, 200, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180]
pressure = [970, 970, 970, 970, 970, 970, 970, 970, 970, 970, 970, 970, 970, 970, 970, 970, 970, 970, 970, 970, 970, 970, 970, 970]


system = {'module': module, 'inverter': inverter,
          'surface_azimuth': 180}
values_data = [temp_air, relative_humidity, ghi, dni, dhi, IR, wind_speed, wind_direction, pressure]
parameter_names = ['temp_air', 'relative_humidity', 'ghi', 'dni', 'dhi', 'IR', 'wind_speed', 'wind_direction', 'pressure']

energies = {}
target_date_ = [pd.Timestamp(2023, 8, 22), pd.Timestamp(2023, 8, 23)]
print(target_date_)
weather_data = []
for target_date in target_date_:

    for i in range(24):
        weather_ = {}
        for j, values in enumerate(values_data):
            hour = i % 24
            date = target_date + pd.Timedelta(hours=hour)
            weather_[date] = [temp_air[i], relative_humidity[i], ghi[i], dni[i], dhi[i], IR[i], wind_speed[i], wind_direction[i], pressure[i]]
        weather_data.append(weather_)


hourly_energy_data = pd.DataFrame(index=pd.date_range(target_date_[0], periods=24, freq='H'))

for target_date in target_date_:
    for i in range(24):
        weather = weather_data[i]
        latitude, longitude, name, altitude, timezone = coordinates[3]
        system['surface_tilt'] = latitude
        date = target_date + pd.Timedelta(hours=i)
        solpos = pvlib.solarposition.get_solarposition(
            time=date,
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            temperature=list(weather.values())[0][0],    # weather_data[0][pd.Timestamp('2023-08-22 00:00:00')][0]
            pressure=pvlib.atmosphere.alt2pres(altitude),
        )


        dni_extra = pvlib.irradiance.get_extra_radiation(list(weather.keys())[0]) #pd.Timestamp('2023-08-22 00:00:00')
        airmass = pvlib.atmosphere.get_relative_airmass(solpos['apparent_zenith'])
        pressure = pvlib.atmosphere.alt2pres(altitude)
        am_abs = pvlib.atmosphere.get_absolute_airmass(airmass, pressure)
        aoi = pvlib.irradiance.aoi(
            system['surface_tilt'],
            system['surface_azimuth'],
            solpos["apparent_zenith"],
            solpos["azimuth"],
        )

        total_irradiance = pvlib.irradiance.get_total_irradiance(
            system['surface_tilt'],
            system['surface_azimuth'],
            solpos['apparent_zenith'],
            solpos['azimuth'],
            list(weather.values())[0][3],
            list(weather.values())[0][2],
            list(weather.values())[0][4],
            dni_extra=dni_extra,
            model='haydavies',
        )

        cell_temperature = pvlib.temperature.sapm_cell(
            total_irradiance['poa_global'],
            list(weather.values())[0][0],    # temp_air
            list(weather.values())[0][6],    # wind
            **temperature_model_parameters,
        )
        effective_irradiance = pvlib.pvsystem.sapm_effective_irradiance(
            total_irradiance['poa_direct'],
            total_irradiance['poa_diffuse'],
            am_abs,
            aoi,
            module,
        )
        dc = pvlib.pvsystem.sapm(effective_irradiance, cell_temperature, module)
        ac = pvlib.inverter.sandia(dc['v_mp'], dc['p_mp'], inverter)
        annual_energy = ac.sum()
        # hourly_energy_data[name] = ac
        hourly_energy_data.loc[date, name] = ac[0]
        energies[name] = annual_energy
energies = pd.Series(energies)
print(energies, hourly_energy_data)
energies.plot(kind='bar', rot=0)
# latitude = 40.7128
# longitude = -74.0060
#
# weather_data = pd.read_csv('weather.csv', index_col='datetime', parse_dates=True)
# weather_data['timestamp'] = weather_data.index.to_series().apply(lambda x: x.timestamp())
# sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
# print(sandia_modules)
# solar_data = pvlib.clearsky.ineichen(
#     weather_data['timestamp'],
#     latitude,
#     longitude,
#     weather_data['temperature_c'],
#     weather_data['precipitation_mm'],
# )
#
# solar_position = pvlib.solarposition.get_solarposition(
#     weather_data.index,
#     latitude,
#     longitude,
# )
#
# # Розраховуємо сонячну радіацію
# total_irradiance = pvlib.irradiance.get_total_irradiance(
#     surface_tilt=20,  # Кут нахилу панелей
#     surface_azimuth=180,  # Азимут панелей
#     solar_zenith=solar_position['zenith'],
#     solar_azimuth=solar_position['azimuth'],
#     dni=solar_data['dni'],
#     ghi=solar_data['ghi'],
#     dhi=solar_data['dhi'],
# )
#
#
# # Розраховуємо виробництво енергії
# system = pvlib.pvsystem.PVSystem(module_parameters={'pdc0': 240, 'gamma_pdc': -0.004})

# dc = system.sapm(effective_irradiance=total_irradiance['poa_global'], temp_cell=weather_data['temperature_c'])


# ac = system.snlinverter(dc['p_mp'])


# # Записуємо результат в DataFrame
# weather_data['solar_generation (kW)'] = ac
#
# # Вивід результатів
# print(weather_data['solar_generation (kW)'])

if __name__ == '__main__':
    pass

