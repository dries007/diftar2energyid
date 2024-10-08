#!/usr/bin/env python

import datetime
import enum
import re
import logging
from collections import defaultdict
from typing import NamedTuple

import requests
import tomllib


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)-8s [%(name)s] %(message)s')
LOG = logging.getLogger("diftar2energyid")

DIFTAR_BASE = 'https://www.mijndiftar.be'
# Groups: Day, Month, Year, Kind, Weight
ENTRY_RE = re.compile(r'^(\d{2})/(\d{2})/(\d{4}) ([A-Z]+)\d+ \d+ (\d+\.\d+) kg$')


class Kind(enum.Enum):
    # Diftar name -> EnergyID name
    GFT = 'organicWaste'
    REST = 'residualWaste'


class Entry(NamedTuple):
    # One entry on the site
    date: datetime.date
    weight: float


def main():
    # Let raise if file is missing.
    with open('diftar2energyid.toml', 'rb') as f:
        settings = tomllib.load(f)

    LOG.info("Settings loaded.")

    # By using a session, the login details are stored (cookies)
    with requests.Session() as s:
        # <3 simple POST request logins
        r = s.post(DIFTAR_BASE + '/Account/Logon', data={
            "Identifier": settings['diftar']['username'],
            "AuthenticationValue": settings['diftar']['password'],
            "LogonByName": "aanmelden",
            "RememberMe": "true",
        })
        r.raise_for_status()
        assert r.url.startswith(DIFTAR_BASE)
        assert not r.url.startswith(DIFTAR_BASE + '/Error')
        assert r.url.startswith(DIFTAR_BASE + '/Aansluitpunten')

        LOG.info("Logged in.")

        # Gotten via Chrome network inspection.
        # Set DisplayLength to 100 to get 100 entries instead of pages of 10.
        # Since there is a max of 100 entries per webhook submit, might as well limit data to that.
        # Should be enough for 1 to 2 years of data, depending on if you actually have both GTF & REST.
        r = s.get(DIFTAR_BASE + '/Aansluitpunten/ShowResultsVerrichtingen', params={
            "sEcho": 1,
            "sSearchFilter": [],
            "DisplayStart": 0,
            "DisplayLength": 100,
            "SortBy": "Verrichtingsdatum",
            "SortDirection": "asc",
            "Verrichtingtypeid": 2,  # "Gewicht". We don't care about account topups etc.
        })
        r.raise_for_status()
        data = r.json()['aaData']
        LOG.info("Got %d entries.", len(data))
        # {
        #   "sEcho": 2,
        #   "iTotalRecords": 41,
        #   "iTotalDisplayRecords": 41,
        #   "aaData": [
        #     [
        #       "23/06/2022",
        #       "gewicht",
        #       "22/06/2022 GFT0040 100861301 1.0 kg",
        #       "<div class='cRight'>€ -0,10</div>"
        #     ],
        #     [
        #       "16/06/2022",
        #       "gewicht",
        #       "15/06/2022 REST0120 100861302 0.0 kg",
        #       "<div class='cRight'>€ 0,00</div>"
        #     ],
        #     ...
        #   ]
        # }

        # Default dict to make appending easier.
        db: dict[Kind, list[Entry]] = defaultdict(list)
        for row in data:
            m = ENTRY_RE.fullmatch(row[2])
            if m is None:
                raise ValueError(f"Could not parse row! {row!r}")
            d, m, y, k, w = m.groups()
            e = Entry(datetime.date(int(y), int(m), int(d)), float(w))
            db[Kind[k]].append(e)
        # We're done appending.
        db = dict(db)



    # Fresh session to nuke cookies from other domain.
    with requests.Session() as s:
        kind: Kind
        for kind in db.keys():
            # If a section is not present in the config, don't send a request for it.
            if kind.name not in settings['energyid']:
                LOG.error("Missing config for %s. Skipping...", kind)
                continue

            LOG.info("Submitting %d entries for %s, dates %s to %s.", len(db[kind]), kind.name, db[kind][-1].date, db[kind][0].date)
            # Send webhook request, with copied properties from config + fixed fields.
            r = s.post(settings['energyid']['url'], json={
                **settings['energyid'][kind.name],
                'metric': kind.value,
                'unit': 'kg',
                # Not properly documented, but this means every entry is a stand-alone measurement.
                'readingType': 'interval',
                # If we'd use midnight, it might go to the previous day due to summer/winter time.
                'data': [[e.date.isoformat() + 'T07:00:00+0000', e.weight] for e in db[kind]]
            })
            r.raise_for_status()


if __name__ == '__main__':
    # noinspection PyBroadException
    try:
        main()
    except Exception:
        logging.exception("Something went wrong!")
        exit(1)
