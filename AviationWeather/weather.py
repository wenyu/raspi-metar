import requests
import logging
import csv
import itertools
import re

L = logging.getLogger(__name__)

class AviationWeather:
    ENDPOINT = "https://aviationweather.gov/adds/dataserver_current/httpparam"
    
    @classmethod
    def _basicRequest(cls, *args, **kwargs):
        params = {
            "requestType": "retrieve",
            "format": "csv",
        }
        params.update(kwargs)
        L.info("Params: %s", params)
        with requests.get(cls.ENDPOINT, params) as resp:
            content = resp.content.decode("UTF-8").strip().split("\n")

        L.debug("%s", content)
        assert content[0] == "No errors"
        if content[1] != "No warnings":
            L.warning(content[1])
        L.info("Elapsed time: %s", content[2])
        
        result = csv.DictReader(
            map(lambda x: x.strip(","), content[6:]),
            fieldnames=content[5].strip(",").split(","))
        return list(result)
    
    @classmethod
    def _mostRecentSelector(cls, key):
        return lambda l: max(l, key=lambda o: o[key])
    
    @classmethod
    def _groupByStation(cls, l, mostRecent=None):
        selector = cls._mostRecentSelector(mostRecent) if mostRecent else list
        return dict(map(
            lambda x: (x[0], selector(x[1])),
            itertools.groupby(l, lambda x: x["station_id"]))
        )
        
    @classmethod
    def METAR(cls, *args, hoursBeforeNow=3, mostRecent=True, **kwargs):
        result = cls._groupByStation(
            cls._basicRequest(
                stationString=",".join(args),
                dataSource="metars",
                hoursBeforeNow=hoursBeforeNow),
            "observation_time" if mostRecent else None)
        return result
    
    @classmethod
    def TAF(cls, *args, hoursBeforeNow=8, mostRecent=True, **kwargs):
        result = cls._groupByStation(
            cls._basicRequest(
                stationString=",".join(args),
                dataSource="tafs",
                hoursBeforeNow=hoursBeforeNow),
            "issue_time" if mostRecent else None
        )
        return result

    @classmethod
    def FlightCategory(cls, w, preferGiven=True):
        fc = w["flight_category"].upper()
        if fc not in ["VFR", "MVFR", "IFR", "LIFR"]:
            fc = ""
        if fc and preferGiven:
            return fc
            
        vis = float("0" + w["visibility_statute_mi"])
        ceil = int('0' + w["cloud_base_ft_agl"])
        if not ceil:
            ceil = 1000000
            for _, base in re.findall(r'\s(BKN|OVC|VV)(\d+)', w["raw_text"]):
                ceil = min(ceil, int(base) * 100)
            
        if vis < 1.0 or ceil < 500:
            return "LIFR"
        if vis < 3.0 or ceil < 1000:
            return "IFR"
        if vis <= 5.0 or ceil <= 3000:
            return "MVFR"
        return "VFR"