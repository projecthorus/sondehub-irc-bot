#!/usr/bin/env python
#
#   SondeHub-Amateur IRC Bot
#
import argparse
import datetime
import json
import logging
import sondehub
import time


class AmateurPayloads(object):

    payload_db_version = "1.0.0"

    sondehub_amateur_url = "https://amateur.sondehub.org/"

    def __init__(self,
        db_file = "seen_payloads.json",
        min_seen_time = 12, # hours
        callback = None
        ):

        self.db_file = db_file
        self.min_seen_time = min_seen_time * 3600

        self.callback = callback

        self.payload_db = {'version': self.payload_db_version, 'payloads': {}}

        self.load_db()

        self.sondehub = sondehub.Stream(on_message=self.handle_telemetry, prefix="amateur")


    def write_db(self):
        """ Write payload DB out to file """

        _f = open(self.db_file, 'w')
        _f.write(json.dumps(self.payload_db))
        _f.close()
    

    def load_db(self):
        """ Load a payload database file (JSON file) """

        try:
            _f = open(self.db_file, 'r')
            data = _f.read()
            _f.close()

            data_decoded = json.loads(data)

            if data_decoded["version"] == self.payload_db_version:
                # version info matches, load data into local db register.
                self.payload_db = data_decoded
            else:
                self.write_db()

        except Exception as e:
            logging.error(f"Could not load payload DB, clearing out DB - {str(e)}")

            self.write_db()


    def nice_age(self,last_seen):

        # Greater than a day.
        if last_seen > 24*3600:

            _last_days = int(last_seen/(24*3600))
            return f"{_last_days} days ago"
        
        elif last_seen > 3600:
            _last_hours = int(last_seen/3600)
            return f"{_last_hours} hours ago"

        else:
            return "recently"



    def report_telemetry(self, telemetry, last_seen):
        
        if self.callback:
            try:
                self.callback({
                    "payload_callsign": telemetry["payload_callsign"],
                    "last_seen": last_seen,
                    "last_seen_str": self.nice_age(last_seen),
                    "telemetry": telemetry,
                    "url": self.sondehub_amateur_url + telemetry["payload_callsign"]
                })
            except:
                pass

    def handle_telemetry(self, telemetry):
        # Extract the little we need from telemetry.
        _call = telemetry["payload_callsign"]
        _now = time.time()

        
        if _call not in self.payload_db["payloads"]:
            # New payloads, not in DB
            # Update entry in database.
            self.payload_db["payloads"][_call] = _now
            self.write_db()
            # Report
            self.report_telemetry(telemetry, -1)

        else:
            _last_seen_age = _now - self.payload_db["payloads"][_call]
            if _last_seen_age > self.min_seen_time:
                # Report
                self.payload_db["payloads"][_call] = _now
                self.report_telemetry(telemetry, _last_seen_age)
            else:
                self.payload_db["payloads"][_call] = _now

            if _last_seen_age > 3600:
                self.write_db()

            


    
    def close(self):
        logging.info("Writing payload database out to file.")
        self.write_db()
        try:
            self.sondehub.disconnect()
        except:
            pass



if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", help="Enable debug output.", action="store_true"
    )
    args = parser.parse_args()

    # Set log-level to DEBUG if requested
    if args.verbose:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO

    # Set up logging
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", level=logging_level)


    def handle_new_payload(data):
        _str = f"Callsign {data['payload_callsign']} last seen {data['last_seen_str']}, {int(data['telemetry']['alt'])} m altitude. {data['url']}"
        logging.info(_str)

    amateur_payloads = AmateurPayloads(callback=handle_new_payload)


    try:
        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        amateur_payloads.close()