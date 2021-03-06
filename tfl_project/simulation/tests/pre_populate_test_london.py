import tfl_project.simulation.sim_managment
from pathlib import Path

st_filter = """AND "StartStation Id" IN (1, 6, 14, 98, 393)
                AND "EndStation Id" IN (1, 6, 14, 98, 393)"""

def main():
    lc = tfl_project.simulation.sim_managment.LondonCreator(
        additional_sql_filters=st_filter
    )
    lc.populate_tfl_stations()
    # filter to only stations for testing
    for i in list(lc.london._stations.keys()):
        if i not in [1, 6, 14, 98, 393]:
            lc.london._stations.pop(i)
    lc.populate_station_demand_dicts()
    lc.populate_station_destination_dicts()
    lc.populate_station_duration_params(Path('tfl_project/simulation/tests/files/caches/duration_params'))
    lc.pickle_city('tfl_project/simulation/tests/files/')


if __name__ == "__main__":
    main()