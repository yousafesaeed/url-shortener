from flask import request
from sqlalchemy import func, Float
from ua_parser import user_agent_parser
from ip2geotools.databases.noncommercial import DbIpCity
from geopy.distance import distance
import datetime

from database import *


class Analyzer:
    def __init__(self):
        self.short_url = ""
        self.user_agent = ""
        self.response_time = ""
        self.user_details = user_agent_parser.Parse(self.user_agent)

    def get_entry_time(self):
        return datetime.datetime.now().strftime("%d-%m-%Y.%H:%M:%S")

    def get_platform(self):
        return self.user_details["os"]["family"]

    def get_browser(self):
        browser = self.user_details["user_agent"]["family"]
        browser_version = ".".join(
            [
                self.user_details["user_agent"][key]
                for key in ("major", "minor", "patch")
                if self.user_details["user_agent"][key] is not None
            ]
        )
        return f"{browser}-{browser_version}"

    def get_ip(self):
        import random

        # Define the actions
        actions = ["action1", "action2", "action3", "action4"]

        # Assign probabilities to each action
        probabilities = [0.25, 0.25, 0.25, 0.25]

        # Choose an action based on the assigned probabilities
        chosen_action = random.choices(actions, weights=probabilities)[0]

        # Perform the chosen action
        if chosen_action == "action1":
            return "8.8.8.8"
        elif chosen_action == "action2":
            return "8.8.4.4"
            # Do something else
        elif chosen_action == "action3":
            # Do another thing
            return "1.1.1.1"
        else:
            # Do yet another thing
            return "204.106.240.53"

        if request.environ.get("HTTP_X_FORWARDED_FOR") is None:
            return request.environ["REMOTE_ADDR"]
        else:
            # if behind a proxy
            return request.environ["HTTP_X_FORWARDED_FOR"]

    def get_location(self):
        client_ip = self.get_ip()
        client_details = DbIpCity.get(client_ip)
        return {
            "city": client_details.city,
            "region": client_details.region,
            "country": client_details.country,
            "latitude": client_details.latitude,
            "longitude": client_details.longitude,
        }

    def get_distance(self):
        client_ip = self.get_ip()
        server_ip = request.remote_addr
        client_details = DbIpCity.get(client_ip)
        server_details = DbIpCity.get(server_ip)
        return distance(
            (client_details.latitude, client_details.longitude),
            (server_details.latitude, server_details.longitude),
        ).km

    def track(self):
        client_location = self.get_location()

        new_stat = Stat(
            short_url=self.short_url,
            entry_time=self.get_entry_time(),
            response_time=self.response_time,
            platform=self.get_platform(),
            browser=self.get_browser(),
            ip=self.get_ip(),
            city=client_location["city"],
            region=client_location["region"],
            country=client_location["country"],
            latitude=client_location["latitude"],
            longitude=client_location["longitude"],
            distance=f"{self.get_distance():.10f}",
        )
        db.session.add(new_stat)
        db.session.commit()

    def total_entries(self):
        urls = db.session.query(Stat).where(Stat.short_url == self.short_url)
        return urls.count()

    def total_unique_entries(self):
        urls = (
            db.session.query(Stat)
            .where(Stat.short_url == self.short_url)
            .group_by(Stat.ip)
        )
        return urls.count()

    def analyze(self):
        average_response_time = db.session.query(
            func.avg(func.cast(Stat.response_time, Float))
        ).scalar()

        top_platforms = (
            db.session.query(Stat.platform, func.count(Stat.platform))
            .group_by(Stat.platform)
            .order_by(func.count(Stat.platform).desc())
            .limit(3)
            .all()
        )

        top_browsers = (
            db.session.query(Stat.browser, func.count(Stat.browser))
            .group_by(Stat.browser)
            .order_by(func.count(Stat.browser).desc())
            .limit(3)
            .all()
        )

        top_countries = (
            db.session.query(Stat.country, func.count(Stat.country))
            .group_by(Stat.country)
            .order_by(func.count(Stat.country).desc())
            .limit(10)
            .all()
        )

        top_regions = (
            db.session.query(Stat.region, func.count(Stat.region))
            .group_by(Stat.region)
            .order_by(func.count(Stat.region).desc())
            .limit(10)
            .all()
        )

        top_cities = (
            db.session.query(Stat.city, func.count(Stat.city))
            .group_by(Stat.city)
            .order_by(func.count(Stat.city).desc())
            .limit(10)
            .all()
        )
        average_distance = db.session.query(
            func.avg(func.cast(Stat.distance, Float))
        ).scalar()

        return {
            "most_frequent_entry_time_of_day": most_frequent_entry_time_of_day,
            "most_frequent_entry_time_of_month": most_frequent_entry_time_of_month,
            "most_frequent_entry_time_of_year": most_frequent_entry_time_of_year,
            "average_response_time": average_response_time,
            "top_platform": top_platforms,
            "top_browser": top_browsers,
            "top_countries": top_countries,
            "top_regions": top_regions,
            "top_cities": top_cities,
            "average_distance": average_distance,
        }

    def delete(self):
        urls = db.session.query(Stat).where(Stat.short_url == self.short_url)
        for url in urls:
            db.session.delete(url)
            db.session.commit()
